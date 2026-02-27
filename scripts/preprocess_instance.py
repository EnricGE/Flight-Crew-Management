from __future__ import annotations

import argparse
from pathlib import Path

from crew_rostering.preprocessing.loaders import load_crew, load_duties, load_scenario
from crew_rostering.preprocessing.eligibility import compute_eligibility
from crew_rostering.preprocessing.duty_conflicts import compute_conflict_pairs

DEFAULT_INSTANCE_DIR = Path("data/generated/v4")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-dir", type=Path, default=DEFAULT_INSTANCE_DIR)
    args = parser.parse_args()

    inst = args.instance_dir

    scenario = load_scenario(inst / "scenario.json")
    crew = load_crew(inst / "crew.json")
    duties = load_duties(inst / "duties.json")

    c0 = crew[0]
    d0 = duties[0]
    print("EXAMPLE crew:", c0)
    print("EXAMPLE duty:", d0)
    print("duty.coverage:", d0.coverage, "type:", type(d0.coverage))
    print("coverage keys:", list(d0.coverage.keys()))
    print("check role in coverage:", c0.role in d0.coverage)
    print("check base match:", c0.base == d0.base)
    print("check aircraft match:", d0.aircraft_type in c0.qualified_types)


    eligible = compute_eligibility(crew, duties)
    conflicts = compute_conflict_pairs(duties, scenario.min_rest_minutes)

    n_true = sum(1 for v in eligible.values() if v)
    print(f"Eligible pairs: {n_true} / {len(eligible)}")
    print(f"Conflict pairs: {len(conflicts)}")
    print("First conflicts:", conflicts[:10])


if __name__ == "__main__":
    main()