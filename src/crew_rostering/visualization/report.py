from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import pandas as pd
from ortools.sat.python import cp_model

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty
from crew_rostering.domain.preferences import OffRequest
from crew_rostering.preprocessing.loaders import Scenario
from crew_rostering.model.rostering_model import RosteringModel


WEEK_LEN = 7
cmap = ListedColormap([
    "#f2f2f2",  # 0 = rest (light grey)
    "#2ca02c",  # 1 = work (green)
    "#ff7f0e",  # 2 = off-request violated (orange)
    "#9467bd",  # 3 = late->early violated (purple)
    "#d62728",  # 4 = weekly rest violated (red)
])

@dataclass(frozen=True)
class ReportFrames:
    work_matrix: pd.DataFrame
    violation_matrix: pd.DataFrame
    workloads: pd.DataFrame
    weekly_rest: pd.DataFrame
    off_requests: pd.DataFrame


def build_report_frames(
    solver: cp_model.CpSolver,
    rm: RosteringModel,
    crew: List[CrewMember],
    duties: List[Duty],
    scenario: Scenario,
    off_requests: List[OffRequest],
) -> ReportFrames:
    crew_ids = [c.crew_id for c in crew]
    days = list(range(1, scenario.horizon_days + 1))

    # --- Work matrix (crew x day) ---
    work_data = {
        c_id: [solver.Value(rm.work[(c_id, day)]) for day in days]
        for c_id in crew_ids
    }
    work_matrix = pd.DataFrame(work_data, index=days).T
    work_matrix.index.name = "crew_id"
    work_matrix.columns = work_matrix.columns.astype(int)


    # --- Workloads ---
    workloads = pd.DataFrame(
        {
            "crew_id": crew_ids,
            "role": [next(c.role for c in crew if c.crew_id == c_id) for c_id in crew_ids],
            "total_minutes": [solver.Value(rm.total_minutes[c_id]) for c_id in crew_ids],
            "worked_days": [int(work_matrix.loc[c_id].sum()) for c_id in crew_ids],
        }
    ).sort_values(["role", "crew_id"])

    # --- Weekly rest shortfall (computed from work_matrix) ---
    R = int(getattr(scenario, "min_rest_days_per_week", 0) or 0)
    rows = []
    num_weeks = (scenario.horizon_days + WEEK_LEN - 1) // WEEK_LEN

    for c_id in crew_ids:
        for w in range(num_weeks):
            start = w * WEEK_LEN + 1
            end = min((w + 1) * WEEK_LEN, scenario.horizon_days)
            days_in_week = end - start + 1

            worked = int(work_matrix.loc[c_id, start:end].sum())
            rest = days_in_week - worked
            shortfall = max(0, R - rest) if R > 0 else 0

            rows.append(
                {
                    "crew_id": c_id,
                    "week": w + 1,
                    "start_day": start,
                    "end_day": end,
                    "worked_days": worked,
                    "rest_days": rest,
                    "required_rest_days": R,
                    "shortfall": shortfall,
                }
            )

    weekly_rest = pd.DataFrame(rows).sort_values(["crew_id", "week"])

    # --- OFF requests violations (worked on requested-off day) ---
    req_rows = []
    for r in off_requests:
        worked = solver.Value(rm.work.get((r.crew_id, r.day), 0))
        req_rows.append(
            {
                "crew_id": r.crew_id,
                "day": r.day,
                "penalty": r.penalty,
                "worked": int(worked),
                "cost": int(worked) * int(r.penalty),
            }
        )
    off_df = pd.DataFrame(req_rows).sort_values(["crew_id", "day"]) if req_rows else pd.DataFrame(
        columns=["crew_id", "day", "penalty", "worked", "cost"]
    )

    # --- Late->early violations computed from assignments ---
    duty_by_id = {d.duty_id: d for d in duties}

    late_thr = int(getattr(scenario, "late_end_threshold_min", 1080))
    early_thr = int(getattr(scenario, "early_start_threshold_min", 540))

    # For each crew/day: whether they have a late duty / early duty that day
    late_day = {(c_id, day): 0 for c_id in crew_ids for day in days}
    early_day = {(c_id, day): 0 for c_id in crew_ids for day in days}

    # Scan assigned duties
    for (c_id, d_id), var in rm.x.items():
        if solver.Value(var) != 1:
            continue
        d = duty_by_id[d_id]
        if d.end_min >= late_thr:
            late_day[(c_id, d.day)] = 1
        if d.start_min <= early_thr:
            early_day[(c_id, d.day)] = 1

    # Build a list of (crew_id, day_k) where violation happens between day_k and day_k+1
    late_to_early_pairs = []
    for c_id in crew_ids:
        for day in range(1, scenario.horizon_days):
            if late_day[(c_id, day)] == 1 and early_day[(c_id, day + 1)] == 1:
                late_to_early_pairs.append((c_id, day))


    violation_matrix = build_violation_matrix(
        work_matrix, weekly_rest, off_df, late_to_early_pairs
    )
    print("unique codes:", np.unique(violation_matrix.values))

    return ReportFrames(
        work_matrix=work_matrix,
        violation_matrix=violation_matrix,
        workloads=workloads,
        weekly_rest=weekly_rest,
        off_requests=off_df,
    )

def build_violation_matrix(
    work_matrix: pd.DataFrame,
    weekly_rest: pd.DataFrame,
    off_requests: pd.DataFrame,
    late_to_early_pairs: List[Tuple[str, int]],
) -> pd.DataFrame:
    """
    Returns a matrix with codes:
    0 = rest
    1 = work (ok)
    2 = work + off-request violated
    3 = work + weekly-rest violated
    4 = work late -> work early violated
    """
    vm = work_matrix.copy()
    vm.columns = vm.columns.astype(int)

    # Start: 0 or 1
    vm[:] = vm.values

    # --- OFF-request violations ---
    for _, r in off_requests.iterrows():
        if r["worked"] == 1:
            vm.loc[r["crew_id"], r["day"]] = 2

    # --- Late->early violations (purple = code 3) ---
    # We’ll mark the "early day" (day+1) as the problem day.
    for c_id, day in late_to_early_pairs:
        early_day = int(day) + 1
        if c_id in vm.index and early_day in vm.columns:
            if int(vm.loc[c_id, early_day]) >= 1:  # only if working that day
                vm.loc[c_id, early_day] = 3

    # --- Weekly rest violations (red = code 4) ---
    viol_weeks = weekly_rest[weekly_rest["shortfall"] > 0]
    for _, r in viol_weeks.iterrows():
        for day in range(r["start_day"], r["end_day"] + 1):
            if vm.loc[r["crew_id"], day] >= 1:
                vm.loc[r["crew_id"], day] = 4
    
    return vm


def save_plots(frames: ReportFrames, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Work "heatmap" (crew x day) using default matplotlib colormap
    plt.figure()
    plt.imshow(frames.violation_matrix.values, aspect="auto", cmap=cmap, vmin=0, vmax=4)
    plt.yticks(
        range(len(frames.violation_matrix.index)),
        frames.violation_matrix.index,
    )
    plt.xticks(
        range(len(frames.violation_matrix.columns)),
        frames.violation_matrix.columns,
    )
    plt.xlabel("Day")
    plt.ylabel("Crew")
    legend_patches = [
        mpatches.Patch(color="#f0f0f0", label="Rest"),
        mpatches.Patch(color="#2ca02c", label="Work"),
        mpatches.Patch(color="#ff7f0e", label="OFF request violated"),
        mpatches.Patch(color="#9467bd", label="Late → Early violated"),
        mpatches.Patch(color="#d62728", label="Weekly rest violated"),
    ]
    plt.legend(
        handles=legend_patches,
        loc="upper right",
        bbox_to_anchor=(1.25, 1.0),
    )
    plt.title("Work calendar with violations")
    plt.tight_layout()
    plt.savefig(out_dir / "work_calendar.png", dpi=160)
    plt.close()

    # 2) Workloads bar chart (minutes)
    plt.figure()
    plt.bar(frames.workloads["crew_id"], frames.workloads["total_minutes"])
    plt.xlabel("Crew")
    plt.ylabel("Total minutes")
    plt.title("Workload per crew")
    plt.tight_layout()
    plt.savefig(out_dir / "workloads.png", dpi=160)
    plt.close()


def save_tables(frames: ReportFrames, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames.work_matrix.to_csv(out_dir / "work_matrix.csv")
    frames.violation_matrix.to_csv(out_dir / "violation_matrix.csv")
    frames.workloads.to_csv(out_dir / "workloads.csv", index=False)
    frames.weekly_rest.to_csv(out_dir / "weekly_rest.csv", index=False)
    frames.off_requests.to_csv(out_dir / "off_requests.csv", index=False)
