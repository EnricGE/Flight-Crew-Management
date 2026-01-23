from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from ortools.sat.python import cp_model

from crew_rostering.domain.crew import CrewMember
from crew_rostering.domain.duty import Duty
from crew_rostering.domain.preferences import OffRequest
from crew_rostering.preprocessing.loaders import Scenario
from crew_rostering.model.rostering_model import RosteringModel


WEEK_LEN = 7


@dataclass(frozen=True)
class ReportFrames:
    work_matrix: pd.DataFrame
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

    return ReportFrames(
        work_matrix=work_matrix,
        workloads=workloads,
        weekly_rest=weekly_rest,
        off_requests=off_df,
    )


def save_plots(frames: ReportFrames, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Work "heatmap" (crew x day) using default matplotlib colormap
    plt.figure()
    plt.imshow(frames.work_matrix.values, aspect="auto")
    plt.yticks(range(len(frames.work_matrix.index)), frames.work_matrix.index)
    plt.xticks(range(len(frames.work_matrix.columns)), frames.work_matrix.columns)
    plt.xlabel("Day")
    plt.ylabel("Crew")
    plt.title("Work calendar (1=works, 0=rest)")
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
    frames.workloads.to_csv(out_dir / "workloads.csv", index=False)
    frames.weekly_rest.to_csv(out_dir / "weekly_rest.csv", index=False)
    frames.off_requests.to_csv(out_dir / "off_requests.csv", index=False)
