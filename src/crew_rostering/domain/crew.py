from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class CrewMember:
    """
    Crew Class

    Attributes
    ----------

    
    """
    crew_id: str
    role: str            # "CAPT" or "FO" for v0
    base: str            # e.g., "CDG"
    qualified_types: List[str]  # e.g., ["A320"]
    max_minutes: int     # monthly or horizon cap
