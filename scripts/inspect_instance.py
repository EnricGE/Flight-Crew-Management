from __future__ import annotations

import argparse
from pathlib import Path
from collections import Counter

from crew_rostering.preprocessing.loaders import load_crew, load_duties, load_scenario
from crew_rostering.preprocessing.validate_crew_duties import validate_crew, validate_duties


DEFAULT_INSTANCE_DIR = Path("data/generated/v0")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--instance-dir",
        type=Path,
        default=DEFAULT_INSTANCE_DIR,
        help="Path to instance folder (default: data/generated/v0)",
    )
    args = parser.parse_args()

    inst = args.instance_dir

    scenario = load_scenario(inst / "scenario.json")
    crew = load_crew(inst / "crew.json")
    duties = load_duties(inst / "duties.json")

    validate_crew(crew)
    validate_duties(duties, horizon_days=scenario.horizon_days)

    print(f"Horizon days: {scenario.horizon_days}")
    print(f"Crew count: {len(crew)}")
    print("Crew by role:", dict(Counter(c.role for c in crew)))

    duties_by_day = Counter(d.day for d in duties)
    print("Duties by day:", dict(sorted(duties_by_day.items())))
    print(f"Min rest minutes: {scenario.min_rest_minutes}")


if __name__ == "__main__":
    main()