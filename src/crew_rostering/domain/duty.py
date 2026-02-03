from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Duty:
    """
    Represents a single flight duty to be covered.

    A Duty is a task that must be staffed by a specific combination
    of crew roles (CAPT / FO / FA), depending on the aircraft type.
    Each duty occurs on a single day and has a fixed start and end time.

    Attributes
    ----------
    duty_id : str
        Unique identifier of the duty.
    day : int
        Day index within the planning horizon (1-based).
    start_min : int
        Duty start time in minutes since midnight.
    end_min : int
        Duty end time in minutes since midnight.
    base : str
        Base airport from which the duty departs.
        Must match the crew member's base.
    aircraft_type : str
        Aircraft type operated by the duty.
        Determines crew eligibility and coverage requirements.
    coverage : Dict[str, int]
        Required number of crew per role.
        Example: {"CAPT": 1, "FO": 1, "FA": 4}
    """   
    duty_id: str
    day: int                 # 1..horizon_days
    start_min: int           # minutes from 00:00 that day
    end_min: int
    base: str
    aircraft_type: str
    coverage: Dict[str, int] 

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min

