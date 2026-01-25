from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
from ortools.sat.python import cp_model

from crew_rostering.preprocessing.loaders import load_crew, load_duties, load_scenario, load_preferences
from crew_rostering.preprocessing.eligibility import compute_eligibility
from crew_rostering.preprocessing.duty_conflicts import compute_conflict_pairs
from crew_rostering.preprocessing.coverage_check import check_coverage_feasibility
from crew_rostering.model.rostering_model import build_rostering_model
from crew_rostering.visualization.report import build_report_frames, save_plots, save_tables


DEFAULT_INSTANCE_DIR = Path("data/generated/v4")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-dir", type=Path, default=DEFAULT_INSTANCE_DIR)
    parser.add_argument("--time-limit", type=float, default=10.0)
    args = parser.parse_args()

    inst = args.instance_dir

    scenario = load_scenario(inst / "scenario.json")
    crew = load_crew(inst / "crew.json")
    duties = load_duties(inst / "duties.json")
    prefs = load_preferences(inst / "preferences.json")

    eligible = compute_eligibility(crew, duties)
    conflicts = compute_conflict_pairs(duties, scenario.min_rest_minutes)
    issues = check_coverage_feasibility(crew, duties, eligible)

    if issues:
        print("\nCoverage feasibility issues (model will be infeasible):")
        for i in issues[:10]:
            print(
                f"  Duty {i.duty_id} (day {i.day}) role={i.role}: "
                f"required={i.required}, eligible={i.eligible_count}"
            )
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        return

    rm = build_rostering_model(
        crew, duties, eligible, conflicts,
        horizon_days=scenario.horizon_days,
        max_consecutive_work_days=scenario.max_consecutive_work_days,
        min_rest_days_per_week=scenario.min_rest_days_per_week,
        weights=scenario.weights,
        off_requests=prefs,
        late_end_threshold_min = scenario.late_end_threshold_min,
        early_start_threshold_min = scenario.early_start_threshold_min,
        )
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = 4

    status = solver.Solve(rm.model)
    
    print("Status:", solver.StatusName(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible roster found.")
        return

    # --- KPIs (short terminal output) ---
    spread = solver.Value(rm.max_load) - solver.Value(rm.min_load)
    breakdown = objective_breakdown(solver, rm, scenario.weights)

    obj = int(round(solver.ObjectiveValue()))
    obj_terms = int(breakdown["objective_from_terms"])
    if obj != obj_terms:
        print(f"WARNING: objective mismatch: solver={obj} vs terms={obj_terms}")

    print("\nKPIs")
    print(f"  objective: {solver.ObjectiveValue():.0f}")
    print(f"  spread: {spread}")
    print(f"  worked_days: {solver.Value(rm.worked_days)}")
    print(f"  preference_cost: {solver.Value(rm.preference_cost)}")
    print(f"  weekly_rest_shortfall: {solver.Value(rm.weekly_rest_shortfall_total)}")
    print(f"  late_to_early_total: {solver.Value(rm.late_to_early_total)}")

    print("\nObjective breakdown (contribution)")
    terms = breakdown["terms"]
    for k in ["fairness_spread", "worked_days", "off_request", "weekly_rest_shortfall", "late_to_early"]:
        t = terms[k]
        if t["weight"] == 0:
            continue
        print(f"  {k}: {t['weight']} × {t['value']} = {t['contribution']}")

    # --- Outputs paths (define early, then print) ---
    out_dir = Path("outputs/solutions")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rostering_solution.json"

    report_dir = Path("outputs/report")
    report_dir.mkdir(parents=True, exist_ok=True)

    print("\nOutputs")
    print(f"  solution_json: {out_path}")
    print(f"  report_dir: {report_dir}")

    # --- Assignments (no terminal print; save to files) ---
    assigned_by_duty: Dict[str, List[str]] = {}
    assign_rows = []
    for (c_id, d_id), var in rm.x.items():
        if solver.Value(var) == 1:
            assigned_by_duty.setdefault(d_id, []).append(c_id)
            assign_rows.append({"duty_id": d_id, "crew_id": c_id})

    # Save solution JSON (+ breakdown inside)
    payload = {
        "instance_dir": str(inst),
        "status": solver.StatusName(status),
        "objective_value": solver.ObjectiveValue(),
        "objective_breakdown": breakdown,
        "fairness": {
            "max_load": solver.Value(rm.max_load),
            "min_load": solver.Value(rm.min_load),
            "spread": spread,
        },
        "workloads": {c.crew_id: solver.Value(rm.total_minutes[c.crew_id]) for c in crew},
        "assignments": assigned_by_duty,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Save objective breakdown JSON (separate file, convenient for diffing)
    (report_dir / "objective_breakdown.json").write_text(
        json.dumps(breakdown, indent=2), encoding="utf-8"
    )

    # Optional: assignments.csv
    if assign_rows:
        pd.DataFrame(assign_rows).sort_values(["duty_id", "crew_id"]).to_csv(
            report_dir / "assignments.csv", index=False
        )

    # --- Build report tables/plots (details go to files only) ---
    frames = build_report_frames(
        solver=solver,
        rm=rm,
        crew=crew,
        duties=duties,
        scenario=scenario,
        off_requests=prefs,
    )
    save_plots(frames, report_dir)
    save_tables(frames, report_dir)


def objective_breakdown(solver: cp_model.CpSolver, rm, weights: dict) -> dict:
    fairness_w = int(weights.get("fairness_spread", 0))
    worked_days_w = int(weights.get("worked_days", 0))
    pref_w = int(weights.get("off_request", 0))
    weekly_rest_w = int(weights.get("weekly_rest_shortfall", 0))
    late_to_early_w = int(weights.get("late_to_early", 0))

    spread = solver.Value(rm.max_load) - solver.Value(rm.min_load)
    worked_days = solver.Value(rm.worked_days)
    preference_cost = solver.Value(rm.preference_cost)
    weekly_rest = solver.Value(rm.weekly_rest_shortfall_total)
    late_to_early = solver.Value(rm.late_to_early_total)

    terms = {
        "fairness_spread": {"weight": fairness_w, "value": spread, "contribution": fairness_w * spread},
        "worked_days": {"weight": worked_days_w, "value": worked_days, "contribution": worked_days_w * worked_days},
        "off_request": {"weight": pref_w, "value": preference_cost, "contribution": pref_w * preference_cost},
        "weekly_rest_shortfall": {"weight": weekly_rest_w, "value": weekly_rest, "contribution": weekly_rest_w * weekly_rest},
        "late_to_early": {"weight": late_to_early_w, "value": late_to_early, "contribution": late_to_early_w * late_to_early},
    }

    total = sum(t["contribution"] for t in terms.values())

    return {
        "objective_value": solver.ObjectiveValue(),
        "objective_from_terms": total,   # should match objective_value for integer objectives
        "terms": terms,
    }


if __name__ == "__main__":
    main()
