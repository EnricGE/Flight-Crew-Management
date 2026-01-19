from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty


@dataclass(frozen=True)
class RosteringModel:
    model: cp_model.CpModel
    x: Dict[Tuple[str, str], cp_model.IntVar]  # (crew_id, duty_id) -> var
    total_minutes: Dict[str, cp_model.IntVar]
    max_load: cp_model.IntVar
    min_load: cp_model.IntVar


def build_rostering_model(
        crew: List[CrewMember],
        duties: List[Duty],
        eligible: Dict[Tuple[str, str], bool],
        conflicts: List[Tuple[str, str]],
) -> RosteringModel:
    """
    Build a rostering CP-SAT model.
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

    # --- Workload variables and hard limits ---
    total_minutes: Dict[str, cp_model.IntVar] = {}
    total_vars_list = []

    for c_id in crew_ids:
        c = crew_by_id[c_id]
        t = model.NewIntVar(0, c.max_minutes, f"total_minutes[{c_id}]")
        total_minutes[c_id] = t
        total_vars_list.append(t)

        # Link t = sum_d x[c,d] * duration(d)
        terms = []
        for d_id in duty_ids:
            var = x.get((c_id, d_id))
            if var is None:
                continue
            dur = duty_by_id[d_id].duration_min  # constant int
            terms.append(var * dur)

        model.Add(t == sum(terms))

        # (Redundant due to domain upper bound, but explicit is nice)
        model.Add(t <= c.max_minutes)

    # --- Fairness variables ---
    # Upper bound for max_load can be the maximum max_minutes among crew
    max_cap = max(c.max_minutes for c in crew) if crew else 0
    max_load = model.NewIntVar(0, max_cap, "max_load")
    min_load = model.NewIntVar(0, max_cap, "min_load")

    model.AddMaxEquality(max_load, total_vars_list)
    model.AddMinEquality(min_load, total_vars_list)

    # --- Objective: minimize spread ---
    model.Minimize(max_load - min_load)

    return RosteringModel(
        model=model,
        x=x,
        total_minutes=total_minutes,
        max_load=max_load,
        min_load=min_load,
    )

