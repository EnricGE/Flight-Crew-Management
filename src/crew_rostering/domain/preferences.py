from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class OffRequest:
    crew_id: str
    day: int
    penalty: int
