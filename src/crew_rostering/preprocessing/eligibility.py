from __future__ import annotations

from typing import Dict, List, Tuple

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty


def compute_eligibility(
        crew: List[CrewMember],
        duties: List[Duty],
) -> Dict[Tuple[str, str], bool]:
    """
    Returns dict[(crew_id, duty_id)] = True/False.
    A crew is eligible if:
    - Has required roles
    - Has the same base
    - Are qualified for the aircraft type
    """
    eligible: Dict[Tuple[str, str], bool] = {}

    for c in crew:
        for d in duties:
            ok = (
                c.role in d.coverage
                and c.base == d.base
                and d.aircraft_type in c.qualified_types
            )
            eligible[(c.crew_id, d.duty_id)] = ok #T/F

    return eligible



