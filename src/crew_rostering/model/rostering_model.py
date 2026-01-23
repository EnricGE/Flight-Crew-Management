from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty
from crew_rostering.domain.preferences import OffRequest


@dataclass(frozen=True)
class RosteringModel:
    model: cp_model.CpModel
    x: Dict[Tuple[str, str], cp_model.IntVar]  # (crew_id, duty_id) -> var
    total_minutes: Dict[str, cp_model.IntVar]
    work: Dict[Tuple[str, int], cp_model.IntVar] # (crew_id, day) -> BoolVar
    max_load: cp_model.IntVar
    min_load: cp_model.IntVar
    worked_days: cp_model.IntVar
    preference_cost: cp_model.IntVar


def build_rostering_model(
        crew: List[CrewMember],
        duties: List[Duty],
        eligible: Dict[Tuple[str, str], bool],
        conflicts: List[Tuple[str, str]],
        horizon_days: int,
        max_consecutive_work_days:int,
        min_rest_days_per_week: int,
        weights: Dict[str, int],
        off_requests: List[OffRequest],
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

    # --- Workday indicator variables ---
    work: Dict[Tuple[str, int], cp_model.IntVar] = {}

    # Pre-group duties by day for fast linking
    duties_by_day: Dict[int, List[str]] = {day: [] for day in range(1, horizon_days + 1)}
    for d in duties:
        duties_by_day[d.day].append(d.duty_id)

    for c_id in crew_ids:
        for day in range(1, horizon_days + 1):
            w = model.NewBoolVar(f"work[{c_id},{day}]")
            work[(c_id, day)] = w

            # If any assignment that day => work=1
            day_vars = []
            for d_id in duties_by_day[day]:
                var = x.get((c_id, d_id))
                if var is not None:
                    day_vars.append(var)

            if day_vars:
                # w >= each assignment var
                for v in day_vars:
                    model.Add(w >= v)
                # w <= sum(assignments)  (so w can't be 1 if no assignment)
                model.Add(w <= sum(day_vars))
            else:
                # no eligible duties on that day for that crew
                model.Add(w == 0)

    # --- Max consecutive work days (hard constraint) ---
    K = max_consecutive_work_days
    if K < horizon_days:
        for c_id in crew_ids:
            for start_day in range(1, horizon_days - K + 1):
                window = [work[(c_id, d)] for d in range(start_day, start_day + K + 1)]
                model.Add(sum(window) <= K)

    # --- Weekly minimum rest days (hard constraint) ---
    WEEK_LEN = 7
    R = int(min_rest_days_per_week)

    if R > 0:
        num_weeks = (horizon_days + WEEK_LEN - 1) // WEEK_LEN  # ceil
        for c_id in crew_ids:
            for w in range(num_weeks):
                start = w * WEEK_LEN + 1
                end = min((w + 1) * WEEK_LEN, horizon_days)
                days_in_week = end - start + 1

                worked_in_week = [work[(c_id, day)] for day in range(start, end + 1)]
                # worked_days <= days_in_week - rest_min
                model.Add(sum(worked_in_week) <= days_in_week - R)

    # --- Objective: minimize spread and worked days, maximise fairness ---
    fairness_w = int(weights.get("fairness_spread", 100))
    worked_days_w = int(weights.get("worked_days", 1))
    pref_w = int(weights.get("off_request", 1))

    # --- KPI vars ---
    max_cap = max(c.max_minutes for c in crew) if crew else 0
    spread = model.NewIntVar(0, max_cap, "spread")
    model.Add(spread == max_load - min_load)

    worked_days = model.NewIntVar(0, len(crew_ids) * horizon_days, "worked_days")
    model.Add(worked_days == sum(work.values()))

    # Preference cost: sum penalty * work[c,day] for OFF requests
    pref_terms = []
    for r in off_requests:
        w = work.get((r.crew_id, r.day))
        if w is not None:
            pref_terms.append(r.penalty * w)

    preference_cost = model.NewIntVar(0, sum(r.penalty for r in off_requests), "preference_cost")
    model.Add(preference_cost == sum(pref_terms) if pref_terms else 0)

    model.Minimize(fairness_w * spread + worked_days_w * worked_days + pref_w * preference_cost)

    return RosteringModel(
        model=model,
        x=x,
        total_minutes=total_minutes,
        work=work,
        max_load=max_load,
        min_load=min_load,
        worked_days=worked_days,
        preference_cost=preference_cost,
    )

