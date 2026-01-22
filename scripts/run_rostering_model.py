from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from ortools.sat.python import cp_model

from crew_rostering.preprocessing.loaders import load_crew, load_duties, load_scenario
from crew_rostering.preprocessing.eligibility import compute_eligibility
from crew_rostering.preprocessing.duty_conflicts import compute_conflict_pairs
from crew_rostering.model.rostering_model import build_rostering_model


DEFAULT_INSTANCE_DIR = Path("data/generated/v1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-dir", type=Path, default=DEFAULT_INSTANCE_DIR)
    parser.add_argument("--time-limit", type=float, default=10.0)
    args = parser.parse_args()

    inst = args.instance_dir

    scenario = load_scenario(inst / "scenario.json")
    crew = load_crew(inst / "crew.json")
    duties = load_duties(inst / "duties.json")

    eligible = compute_eligibility(crew, duties)
    conflicts = compute_conflict_pairs(duties, scenario.min_rest_minutes)

    rm = build_rostering_model(
        crew, duties, eligible, conflicts,
        horizon_days=scenario.horizon_days,
        max_consecutive_work_days=scenario.max_consecutive_work_days,
        weights=scenario.weights,
        )
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = 4

    status = solver.Solve(rm.model)

    print("Status:", solver.StatusName(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible roster found.")
        return
    
    print("\nKPIs:")
    print("  objective:", solver.ObjectiveValue())
    print("  spread:", solver.Value(rm.max_load) - solver.Value(rm.min_load))
    print("  worked_days:", sum(solver.Value(rm.work[(c.crew_id, day)]) for c in crew for day in range(1, scenario.horizon_days + 1)))
    
    print("\nFairness:")
    print("  max_load:", solver.Value(rm.max_load))
    print("  min_load:", solver.Value(rm.min_load))
    print("  spread  :", solver.Value(rm.max_load) - solver.Value(rm.min_load))

    print("\nWork pattern (1=works):")
    for c in crew:
        pattern = [solver.Value(rm.work[(c.crew_id, day)]) for day in range(1, scenario.horizon_days + 1)]
        print(f"  {c.crew_id}: {pattern}")

    print("\nCrew workloads:")
    for c in crew:
        print(f"  {c.crew_id}: {solver.Value(rm.total_minutes[c.crew_id])} min")
    
    # Build a duty -> assigned crew list
    assigned_by_duty: Dict[str, List[str]] = {}
    for (c_id, d_id), var in rm.x.items():
        if solver.Value(var) == 1:
            assigned_by_duty.setdefault(d_id, []).append(c_id)

    # Print nicely
    print("\nAssignments:")
    for d_id in sorted(assigned_by_duty.keys()):
        print(f"  {d_id}: {assigned_by_duty[d_id]}")

    # Save output
    out_dir = Path("outputs/solutions")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rostering_solution.json"

    payload = {
    "instance_dir": str(inst),
    "status": solver.StatusName(status),
    "objective_value": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
    "fairness": {
        "max_load": solver.Value(rm.max_load),
        "min_load": solver.Value(rm.min_load),
        "spread": solver.Value(rm.max_load) - solver.Value(rm.min_load),
    },
    "workloads": {c.crew_id: solver.Value(rm.total_minutes[c.crew_id]) for c in crew},
    "assignments": assigned_by_duty,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
