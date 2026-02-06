from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from crew_rostering.solver.solve_instance import solve_instance

"""
Default run (VS Code / local):
    python scripts/generate_scenarios.py

Override example:
    python scripts/generate_scenarios.py --variants data/scenarios/batch_002/variants.json
"""

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variants",
        type=Path,
        default=Path("data/scenarios/batch_001/variants.json"),
        help="Path to variants.json"
    )
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--save-solution", action="store_true")
    args = parser.parse_args()

    spec = read_json(args.variants)
    base_dir = Path(spec["base_instance_dir"])
    batch_name = args.variants.parent.name  # batch_001
    scenarios_root = Path("data/scenarios") / batch_name

    out_root = Path("outputs/scenarios") / batch_name
    out_root.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []

    for v in spec["variants"]:
        sid = v["id"]
        inst_dir = scenarios_root / sid

        # If someone wants to include baseline but didn't generate it, fallback to base.
        if not inst_dir.exists():
            if sid.upper() in ("S000", "BASE", "BASELINE") or v.get("name") == "baseline":
                inst_dir = base_dir
            else:
                raise FileNotFoundError(f"Missing scenario dir: {inst_dir}")

        res = solve_instance(
            inst_dir,
            time_limit=args.time_limit,
            num_workers=args.num_workers,
            save_solution=args.save_solution,
            save_breakdown=True,
            out_root=Path("outputs"),
            tag=batch_name,
        )
        res["scenario_id"] = sid
        res["scenario_name"] = v.get("name", "")
        res["n_changes"] = len(v.get("changes", []))
        results.append(res)

    # Write results.csv
    csv_path = out_root / "results.csv"
    fieldnames = [
        "scenario_id",
        "scenario_name",
        "n_changes",
        "status",
        "objective",
        "objective_from_terms",
        "spread",
        "worked_days",
        "preference_cost",
        "weekly_rest_shortfall",
        "late_to_early_total",
        "solution_json",
        "objective_breakdown_json",
        "instance_dir",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fieldnames})

    # Summary.json (robustness quick view)
    feasible = [r for r in results if r.get("status") in ("OPTIMAL", "FEASIBLE")]
    summary = {
        "batch": batch_name,
        "n_total": len(results),
        "n_feasible": len(feasible),
        "feasible_rate": (len(feasible) / len(results)) if results else 0.0,
        "worst_objective": max((r["objective"] for r in feasible), default=None),
        "best_objective": min((r["objective"] for r in feasible), default=None),
        "avg_objective": (sum(r["objective"] for r in feasible) / len(feasible)) if feasible else None,
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Saved: {csv_path}")
    print(f"Saved: {out_root / 'summary.json'}")
    print(f"Feasible: {summary['n_feasible']}/{summary['n_total']} ({summary['feasible_rate']:.0%})")


if __name__ == "__main__":
    main()
