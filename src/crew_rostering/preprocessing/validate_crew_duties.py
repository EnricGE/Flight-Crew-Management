from __future__ import annotations

from typing import Iterable, Sequence

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty


ALLOWED_ROLES = {"CAPT", "FO", "FA"}


def validate_crew(crew: Sequence[CrewMember]) -> None:
    ids = [c.crew_id for c in crew]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate crew_id found in crew.json")
    
    for c in crew:
        if c.role not in ALLOWED_ROLES:
            raise ValueError(f"Invalid role for crew {c.crew_id}: {c.role}")
        if c.max_minutes <= 0:
            raise ValueError(f"max_minutes must be > 0 for crew {c.crew_id}")
        if not c.qualified_types:
            raise ValueError(f"qulified_types empty for crew {c.crew_id}")
        
def validate_duties(duties: Sequence[Duty], horizon_days: int) -> None:
    ids = [d.duty_id for d in duties]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate crew_id found in crew.json")
    
    for d in duties:
        if not (1<= d.day <= horizon_days):
            raise ValueError(f"Duty {d.duty_id} has day {d.day} outside 1..{horizon_days}")
        if not (0 <= d.start_min < 24 * 60) or not (0 <= d.end_min <= 24 * 60):
            raise ValueError(f"Duty {d.duty_id} has invalid start/end minutes")
        if d.end_min <= d.start_min:
            raise ValueError(f"Duty {d.duty_id} end_min must be > start_min")
        if d.duration_min > 24 * 60:
            raise ValueError(f"Duty {d.duty_id} duration too long")
        if not d.coverage:
            raise ValueError(f"Duty {d.duty_id} has empty required roles")
        for role, k in d.coverage.items():
            if role not in ALLOWED_ROLES:
                raise ValueError(f"Duty {d.duty_id} requires unknown role: {role}")
            if k <= 0:
                raise ValueError(f"Duty {d.duty_id} requires non-positive count for {role}")