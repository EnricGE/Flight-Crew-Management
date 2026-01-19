from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty


@dataclass(frozen=True)
class FeasibilityModel:
    model: cp_model.CpModel
    x: Dict[Tuple[str, str], cp_model.IntVar]  # (crew_id, duty_id) -> var


def build_feasibility_model(
        crew: List[CrewMember],
        duties: List[Duty],
        eligible: Dict[Tuple[str, str], bool],
        conflicts: List[Tuple[str, str]],
) -> FeasibilityModel:
    """
    Build a feasibility-only CP-SAT model.

    Variables:
      x[c,d] = 1 if crew c is assigned to duty d

    Constraints:
      - Coverage: for each duty and each role, assign exactly coverage[role] crew with that role
      - Eligibility: only create (or force 0) for ineligible pairs
      - Conflicts: for each crew and conflicting duty pair, cannot take both
    """
    model = cp_model.CpModel()

    crew_ids = [c.crew_id for c in crew]
    duty_ids = [d.duty_id for d in duties]

    crew_by_id = {c.crew_id: c for c in crew}
    duty_by_id = {d.duty_id: d for d in duties}

    # --- Variables (only create x if eligible; else omit or force 0) ---
    x: Dict[Tuple[str, str], cp_model.IntVar] = {}
    for c_id in crew_ids:
        for d_id in duty_ids:
            if eligible.get((c_id, d_id), False):
                x[(c_id, d_id)] = model.NewBoolVar(f"x[{c_id},{d_id}]")

    # --- Coverage constraints: for each duty, each role ---
    for d_id in duty_ids:
        d = duty_by_id[d_id]
        for role, required_n in d.coverage.items():
            # all eligible crew with matching role
            vars_for_role = []
            for c_id in crew_ids:
                c= crew_by_id[c_id]
                if c.role != role:
                    continue
                var = x.get((c_id,d_id))
                if var is not None:
                    vars_for_role.append(var)

            # If there aren't enough eligible crew for this role, model will become infeasible
            model.Add(sum(vars_for_role) == required_n)

    # --- Conflict constraints: per crew, cannot take two conflicting duties ---
    for c_id in crew_ids:
        for d1, d2 in conflicts:
            v1 = x.get((c_id, d1))
            v2 = x.get((c_id, d2))
            if v1 is not None and v2 is not None:
                model.Add(v1 + v2 <= 1)

    return FeasibilityModel(model=model, x=x)


