from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Duty:
    """
    Duty Class

    Attributes
    ----------
    duty_id : str
        Unique identifier of the class instance.
    day: float
        Days needed for the duty.
    start_min: float
        Duty start time.
    end_min: float
        Duty end time.
    base: str
        Airport base
    aircraft_type: str
        aircraft type
    coverage: Dict[str, int]
        required coverage for each duty, you need K crew (e.g., 1 Captain + 1 FO))
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

