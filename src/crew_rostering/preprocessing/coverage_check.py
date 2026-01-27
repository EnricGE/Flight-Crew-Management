from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
from collections import defaultdict

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

@dataclass(frozen=True)
class AggregateCoverageIssue:
    day: int
    base: str
    aircraft_type: str
    role: str
    required_total: int
    available_total: int
    duty_ids: List[str]
    available_crew_ids: List[str]


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


def check_aggregate_coverage_feasibility(
    crew: List[CrewMember],
    duties: List[Duty],
) -> List[AggregateCoverageIssue]:
    """
    For each (day, base, aircraft_type, role), verify that the total required
    coverage across ALL duties in that bucket can be met simultaneously by the
    available crew pool (role + base + qualification).
    """
    issues: List[AggregateCoverageIssue] = []

    # Group duties by (day, base, aircraft_type)
    duties_by_bucket: Dict[Tuple[int, str, str], List[Duty]] = defaultdict(list)
    for d in duties:
        duties_by_bucket[(d.day, d.base, d.aircraft_type)].append(d)

    for (day, base, aircraft_type), bucket_duties in duties_by_bucket.items():
        # Sum required per role across duties in this bucket
        required_by_role: Dict[str, int] = defaultdict(int)
        for d in bucket_duties:
            for role, n in d.coverage.items():
                required_by_role[role] += int(n)

        # For each role, compute available crew in this bucket
        for role, required_total in required_by_role.items():
            available_crew_ids = [
                c.crew_id
                for c in crew
                if c.role == role
                and c.base == base
                and aircraft_type in c.qualified_types
            ]
            available_total = len(available_crew_ids)

            if available_total < required_total:
                issues.append(
                    AggregateCoverageIssue(
                        day=day,
                        base=base,
                        aircraft_type=aircraft_type,
                        role=role,
                        required_total=required_total,
                        available_total=available_total,
                        duty_ids=sorted([d.duty_id for d in bucket_duties]),
                        available_crew_ids=sorted(available_crew_ids),
                    )
                )

    # Sort: biggest shortage first
    issues.sort(
        key=lambda x: (x.available_total - x.required_total, x.day, x.base, x.aircraft_type, x.role)
    )
    return issues