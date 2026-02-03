from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class OffRequest:
    """
    Represents a crew preference to not work on a specific day.

    OffRequests are modeled as soft constraints.
    If a crew member is assigned to work on a requested-off day,
    a penalty is incurred in the objective function.

    Attributes
    ----------
    crew_id : str
        Identifier of the crew member making the request.
    day : int
        Day for which the crew member requests to be off.
    penalty : int
        Cost incurred if the request is violated.
        Higher values indicate stronger preferences.
    """
    crew_id: str
    day: int
    penalty: int
