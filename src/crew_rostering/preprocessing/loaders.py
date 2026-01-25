from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty
from crew_rostering.domain.preferences import OffRequest



@dataclass(frozen=True)
class Scenario:
    horizon_days: int
    min_rest_minutes: int
    max_consecutive_work_days: int
    min_rest_days_per_week: int
    late_end_threshold_min: int
    early_start_threshold_min: int
    weights: Dict[str, int]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
    

def load_crew(path: Path) -> List[CrewMember]:
    obj = _read_json(path)
    crew_list = obj.get("crew", [])
    return [
        CrewMember(
            crew_id=c["crew_id"],
            role=c["role"],
            base=c["base"],
            qualified_types=list(c["qualified_types"]),
            max_minutes=int(c["max_minutes"]),
        )
        for c in crew_list
    ]


def load_duties(path: Path) -> List[Duty]:
    obj = _read_json(path)
    duties_list = obj.get("duties", [])
    return [
        Duty(
            duty_id=d["duty_id"],
            day=int(d["day"]),
            start_min=int(d["start_min"]),
            end_min=int(d["end_min"]),
            base=d["base"],
            aircraft_type=d["aircraft_type"],
            coverage=dict(d["coverage"]),
        )
        for d in duties_list
    ]


def load_scenario(path: Path) -> Scenario:
    obj = _read_json(path)
    return Scenario(
        horizon_days=int(obj["horizon_days"]),
        min_rest_minutes=int(obj["min_rest_minutes"]),
        max_consecutive_work_days=int(obj["max_consecutive_work_days"]),
        min_rest_days_per_week=int(obj.get("min_rest_days_per_week", 0)),
        late_end_threshold_min=int(obj.get("late_end_threshold_min", 1200)),
        early_start_threshold_min=int(obj.get("early_start_threshold_min", 480)),
        weights=dict(obj.get("weights", {})),
    )

def load_preferences(path:Path) -> List[OffRequest]:
    if not path.exists():
        return []  # preferences are optional

    obj = _read_json(path)
    reqs = obj.get("off_requests", [])
    return [
        OffRequest(
            crew_id = r["crew_id"],
            day = int(r["day"]),
            penalty = int(r["penalty"]),
        )
        for r in reqs
    ]
        
    