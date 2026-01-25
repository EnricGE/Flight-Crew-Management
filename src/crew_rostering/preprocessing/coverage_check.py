from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty


@dataclass(frozen=True)
class CoverageIssue:
    duty_id: str
    day: int
    role: str
    required: int
    eligible_count: int
    eligible_crew_ids: List[str]


def check_coverage_feasibility(
    crew: List[CrewMember],
    duties: List[Duty],
    eligible: Dict[Tuple[str, str], bool],
) -> List[CoverageIssue]:
    """
    For each duty and each required role, verify there are at least `required`
    eligible crew members of that role.
    Returns a list of issues (empty => coverage feasible).
    """
    crew_by_id = {c.crew_id: c for c in crew}

    issues: List[CoverageIssue] = []

    for d in duties:
        for role, required_n in d.coverage.items():
            eligible_crew = [
                c.crew_id
                for c in crew
                if c.role == role and eligible.get((c.crew_id, d.duty_id), False)
            ]
            count = len(eligible_crew)

            if count < int(required_n):
                issues.append(
                    CoverageIssue(
                        duty_id=d.duty_id,
                        day=d.day,
                        role=role,
                        required=int(required_n),
                        eligible_count=count,
                        eligible_crew_ids=sorted(eligible_crew),
                    )
                )

    # Sort: most severe first (largest gap), then by day/duty/role
    issues.sort(
        key=lambda x: ((x.eligible_count - x.required), x.day, x.duty_id, x.role)
    )
    return issues
