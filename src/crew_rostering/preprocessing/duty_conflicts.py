from __future__ import annotations

from typing import List, Tuple

from crew_rostering.domain.duty import Duty

MINUTES_PER_DAY = 24 * 60


def _abs_start(d: Duty) -> int:
    return (d.day - 1) * MINUTES_PER_DAY + d.start_min


def _abs_end(d: Duty) -> int:
    return (d.day - 1) * MINUTES_PER_DAY + d.end_min


def duties_conflict(d1: Duty, d2: Duty, min_rest_minutes: int) -> bool:
    """
    True if the same crew cannot do both duties (overlap or insufficient rest).
    """
    s1, e1 = _abs_start(d1), _abs_end(d1)
    s2, e2 = _abs_start(d2), _abs_end(d2)

    # overlap
    if not (e1 <= s2 or e2 <= s1):
        return True
    
    # rest constraint: if d1 ends before d2 starts, need e1 + rest <= s2
    if e1 <= s2 and (e1 + min_rest_minutes > s2):
        return True
    
    # or if d2 ends before d1 starts
    if e2 <= s1 and (e2 + min_rest_minutes > s1):
        return True

    return False


def compute_conflict_pairs(
        duties: List[Duty],
        min_rest_minutes:int,
) -> List[Tuple[str, str]]:
    """
    Returns list of (duty_id1, duty_id2) with duty_id1 < duty_id2 that conflict.
    """
    pairs: List[Tuple[str, str]] = []
    n = len(duties)

    for i in range(n):
        for j in range(i + 1, n):
            if duties_conflict(duties[i], duties[j], min_rest_minutes):
                pairs.append((duties[i].duty_id, duties[j].duty_id))

    return pairs

