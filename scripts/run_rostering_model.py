from __future__ import annotations

import sys
from pathlib import Path
import argparse
from crew_rostering.solver.solve_instance import solve_instance

DEFAULT_INSTANCE_DIR = Path("data/generated/v4")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--instance-dir", type=Path, default=DEFAULT_INSTANCE_DIR)
    p.add_argument("--time-limit", type=float, default=10.0)
    args = p.parse_args()

    res = solve_instance(args.instance_dir, time_limit=args.time_limit, save_solution=True, save_breakdown=True)
    print("Status:", res["status"])
    if res["status"] not in ("OPTIMAL", "FEASIBLE"):
        return
    print("objective:", res["objective"])
    print("spread:", res["spread"])
    print("worked_days:", res["worked_days"])
    print("preference_cost:", res["preference_cost"])
    print("weekly_rest_shortfall:", res["weekly_rest_shortfall"])
    print("late_to_early_total:", res["late_to_early_total"])
    print("solution_json:", res.get("solution_json"))
    print("objective_breakdown_json:", res.get("objective_breakdown_json"))

if __name__ == "__main__":
    main()
