from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ortools.sat.python import cp_model

from crew_rostering.preprocessing.loaders import (
    load_crew,
    load_duties,
    load_scenario,
    load_preferences,
)
from crew_rostering.preprocessing.eligibility import compute_eligibility
from crew_rostering.preprocessing.duty_conflicts import compute_conflict_pairs
from crew_rostering.model.rostering_model import build_rostering_model


def objective_breakdown(solver: cp_model.CpSolver, rm: Any, weights: Dict[str, int]) -> Dict[str, Any]:
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
        "objective_value": float(solver.ObjectiveValue()),
        "objective_from_terms": int(total),
        "terms": terms,
    }


def solve_instance(
    instance_dir: Path,
    *,
    time_limit: float = 10.0,
    num_workers: int = 4,
    save_solution: bool = True,
    save_breakdown: bool = True,
    out_root: Path = Path("outputs"),
    tag: str | None = None,
) -> Dict[str, Any]:
    """
    Solve one instance directory and return KPIs + output paths.

    If tag is provided, outputs go to:
      outputs/scenarios/<tag>/<instance_name>/
    otherwise:
      outputs/solutions/ and outputs/report/
    """
    instance_dir = instance_dir.resolve()
    scenario = load_scenario(instance_dir / "scenario.json")
    crew = load_crew(instance_dir / "crew.json")
    duties = load_duties(instance_dir / "duties.json")
    prefs = load_preferences(instance_dir / "preferences.json")  # optional loader returns []

    eligible = compute_eligibility(crew, duties)
    conflicts = compute_conflict_pairs(duties, scenario.min_rest_minutes)

    rm = build_rostering_model(
        crew,
        duties,
        eligible,
        conflicts,
        horizon_days=scenario.horizon_days,
        max_consecutive_work_days=scenario.max_consecutive_work_days,
        min_rest_days_per_week=scenario.min_rest_days_per_week,
        late_end_threshold_min=scenario.late_end_threshold_min,
        early_start_threshold_min=scenario.early_start_threshold_min,
        weights=scenario.weights,
        off_requests=prefs,
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = int(num_workers)

    status = solver.Solve(rm.model)
    status_name = solver.StatusName(status)

    # Output directories
    inst_name = instance_dir.name  # e.g. v3 or S002
    if tag:
        base_out = out_root / "scenarios" / tag / inst_name
    else:
        base_out = out_root

    sol_dir = base_out / "solutions"
    rep_dir = base_out / "report"
    sol_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)

    result: Dict[str, Any] = {
        "instance_dir": str(instance_dir),
        "instance_name": inst_name,
        "status": status_name,
        "objective": float(solver.ObjectiveValue()) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return result

    spread = solver.Value(rm.max_load) - solver.Value(rm.min_load)
    result.update(
        {
            "spread": int(spread),
            "worked_days": int(solver.Value(rm.worked_days)),
            "preference_cost": int(solver.Value(rm.preference_cost)),
            "weekly_rest_shortfall": int(solver.Value(rm.weekly_rest_shortfall_total)),
            "late_to_early_total": int(solver.Value(rm.late_to_early_total)),
        }
    )

    breakdown = objective_breakdown(solver, rm, scenario.weights)
    result["objective_from_terms"] = breakdown["objective_from_terms"]

    if save_breakdown:
        (rep_dir / "objective_breakdown.json").write_text(json.dumps(breakdown, indent=2), encoding="utf-8")
        result["objective_breakdown_json"] = str(rep_dir / "objective_breakdown.json")

    # Build duty -> assigned crew list (for stability analysis later)
    assigned_by_duty: Dict[str, List[str]] = {}
    for (c_id, d_id), var in rm.x.items():
        if solver.Value(var) == 1:
            assigned_by_duty.setdefault(d_id, []).append(c_id)

    if save_solution:
        out_path = sol_dir / "rostering_solution.json"
        payload = {
            "instance_dir": str(instance_dir),
            "status": status_name,
            "objective_value": float(solver.ObjectiveValue()),
            "kpis": {
                "spread": int(spread),
                "worked_days": int(solver.Value(rm.worked_days)),
                "preference_cost": int(solver.Value(rm.preference_cost)),
                "weekly_rest_shortfall": int(solver.Value(rm.weekly_rest_shortfall_total)),
                "late_to_early_total": int(solver.Value(rm.late_to_early_total)),
            },
            "assignments": {k: sorted(v) for k, v in assigned_by_duty.items()},
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        result["solution_json"] = str(out_path)

    return result
