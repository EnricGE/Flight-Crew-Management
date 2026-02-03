from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class CrewMember:
    """
    Represents a single crew member available for assignment.

    A CrewMember is an atomic decision entity in the rostering problem.
    The solver decides which duties this crew member is assigned to,
    subject to eligibility, workload limits, and rest constraints.

    Attributes
    ----------
    crew_id : str
        Unique identifier of the crew member.
    role : str
        Operational role (e.g. CAPT, FO, FA).
        Used to satisfy duty coverage requirements.
    base : str
        Home base airport of the crew member.
        Crew can only be assigned to duties departing from this base.
    qualified_types : List[str]
        Aircraft types the crew member is qualified to operate.
        Used for eligibility filtering.
    max_minutes : int
        Maximum total duty minutes allowed over the planning horizon.
        Enforced as a hard workload constraint.
    """
    crew_id: str
    role: str            # "CAPT" or "FO" for v0
    base: str            # e.g., "CDG"
    qualified_types: List[str]  # e.g., ["A320"]
    max_minutes: int     # monthly or horizon cap
