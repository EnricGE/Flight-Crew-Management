from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def apply_changes(
    crew_obj: Dict[str, Any],
    duties_obj: Dict[str, Any],
    scenario_obj: Dict[str, Any],
    prefs_obj: Dict[str, Any],
    changes: List[Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Apply a list of small perturbations to base instance objects."""
    crew = crew_obj.get("crew", [])
    duties = duties_obj.get("duties", [])
    off_requests = prefs_obj.get("off_requests", [])

    duty_by_id = {d["duty_id"]: d for d in duties}

    for ch in changes:
        ch_type = ch["type"]

        if ch_type == "remove_crew":
            cid = ch["crew_id"]
            crew = [c for c in crew if c["crew_id"] != cid]

            # also remove their off-requests (optional but sensible)
            off_requests = [r for r in off_requests if r["crew_id"] != cid]

        elif ch_type == "extend_duty":
            d_id = ch["duty_id"]
            delta = int(ch.get("delta_end_min", 0))
            d = duty_by_id[d_id]
            d["end_min"] = int(d["end_min"]) + delta
            if d["end_min"] < d["start_min"]:
                d["end_min"] = d["start_min"]

        elif ch_type == "shift_duty":
            d_id = ch["duty_id"]
            ds = int(ch.get("delta_start_min", 0))
            de = int(ch.get("delta_end_min", 0))
            d = duty_by_id[d_id]
            d["start_min"] = int(d["start_min"]) + ds
            d["end_min"] = int(d["end_min"]) + de
            if d["end_min"] < d["start_min"]:
                d["end_min"] = d["start_min"]

        elif ch_type == "add_off_request":
            off_requests.append(
                {
                    "crew_id": ch["crew_id"],
                    "day": int(ch["day"]),
                    "penalty": int(ch["penalty"]),
                }
            )

        elif ch_type == "remove_off_request":
            cid = ch["crew_id"]
            day = int(ch["day"])
            off_requests = [r for r in off_requests if not (r["crew_id"] == cid and int(r["day"]) == day)]

        else:
            raise ValueError(f"Unknown change type: {ch_type}")

    return (
        {"crew": crew},
        {"duties": list(duty_by_id.values())},
        scenario_obj,
        {"off_requests": off_requests},
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--variants",
        type=Path,
        default=Path("data/scenarios/batch_001/variants.json"),
        help="Path to variants.json"
    )

    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("data/scenarios"),
        help="Output root directory"
    )

    args = parser.parse_args()

    variants_path = args.variants.resolve()
    if not variants_path.exists():
        raise FileNotFoundError(f"variants.json not found: {variants_path}")

    variants_spec = read_json(args.variants)
    base_dir = Path(variants_spec["base_instance_dir"])

    crew_base = read_json(base_dir / "crew.json")
    duties_base = read_json(base_dir / "duties.json")
    scenario_base = read_json(base_dir / "scenario.json")
    prefs_path = base_dir / "preferences.json"
    prefs_base = read_json(prefs_path) if prefs_path.exists() else {"off_requests": []}

    batch_name = args.variants.parent.name  # e.g. data/scenarios/batch_001/variants.json -> batch_001
    batch_out = args.out_root / batch_name
    batch_out.mkdir(parents=True, exist_ok=True)

    for v in variants_spec["variants"]:
        sid = v["id"]
        changes = v.get("changes", [])

        crew_obj, duties_obj, scenario_obj, prefs_obj = apply_changes(
            crew_obj=json.loads(json.dumps(crew_base)),
            duties_obj=json.loads(json.dumps(duties_base)),
            scenario_obj=json.loads(json.dumps(scenario_base)),
            prefs_obj=json.loads(json.dumps(prefs_base)),
            changes=changes,
        )

        out_dir = batch_out / sid
        write_json(out_dir / "crew.json", crew_obj)
        write_json(out_dir / "duties.json", duties_obj)
        write_json(out_dir / "scenario.json", scenario_obj)

        # Only write preferences if non-empty (keeps optional semantics clean)
        if prefs_obj.get("off_requests"):
            write_json(out_dir / "preferences.json", prefs_obj)

        # Store a small metadata file (useful later)
        meta = {"id": sid, "name": v.get("name", ""), "changes": changes}
        write_json(out_dir / "meta.json", meta)

    print(f"Generated {len(variants_spec['variants'])} scenarios into: {batch_out}")


if __name__ == "__main__":
    main()
