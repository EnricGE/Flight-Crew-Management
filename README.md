# ✈️ Flight Crew Rostering — CP-SAT Optimization

This project implements a **realistic airline crew rostering problem** using **OR-Tools CP-SAT**, including hard operational constraints, soft preferences, and multi-criteria optimization.

The goal is **not just feasibility**, but to **balance fairness, preferences, and regulatory rules** under tight resources.

---

## 1. Problem Overview

Given:

* A set of **crew members** (Captains, First Officers, Flight Attendants)
* A set of **flight duties** across multiple days
* Aircraft-specific **crew coverage requirements**
* Operational rules (rest, duty conflicts, base, qualifications)

We compute a **weekly roster** that:

* Covers all duties
* Respects hard constraints
* Minimizes penalties from soft constraints

---

## 2. Data Schema

All input data is JSON-based.

### `crew.json`

```json
{
  "crew": [
    {
      "crew_id": "FA1",
      "role": "FA",
      "base": "CDG",
      "qualified_types": ["A320", "A321"],
      "max_minutes": 2000
    }
  ]
}
```

**Fields**

* `crew_id`: unique identifier
* `role`: `CAPT`, `FO`, `FA`
* `base`: home airport (e.g. `CDG`, `ORY`)
* `qualified_types`: aircraft types crew can operate
* `max_minutes`: max duty minutes over horizon

---

### `duties.json`

```json
{
  "duties": [
    {
      "duty_id": "D01",
      "day": 1,
      "start_min": 360,
      "end_min": 600,
      "base": "CDG",
      "aircraft_type": "A321",
      "coverage": { "CAPT": 1, "FO": 1, "FA": 4 }
    }
  ]
}
```

**Fields**

* `day`: 1-based day index
* `start_min`, `end_min`: minutes since midnight
* `coverage`: required crew by role (aircraft dependent)

---

### `scenario.json`

```json
{
  "horizon_days": 7,
  "min_rest_minutes": 60,
  "max_consecutive_work_days": 5,
  "min_rest_days_per_week": 4,
  "late_end_threshold_min": 1200,
  "early_start_threshold_min": 480,
  "weights": {
    "fairness_spread": 10,
    "worked_days": 10,
    "off_request": 1,
    "weekly_rest_shortfall": 4,
    "late_to_early": 10
  }
}
```

---

### `preferences.json` (optional)

```json
{
  "off_requests": [
    { "crew_id": "FA1", "day": 1, "penalty": 60 }
  ]
}
```

If the file is missing, preferences are ignored.

---

## 3. Decision Variables

| Variable               | Meaning                       |
| ---------------------- | ----------------------------- |
| `x[c,d]`               | Crew `c` assigned to duty `d` |
| `work[c,day]`          | Crew `c` works on day         |
| `total_minutes[c]`     | Total duty minutes            |
| `late_work[c,day]`     | Crew ends late that day       |
| `early_work[c,day]`    | Crew starts early that day    |
| `late_to_early[c,day]` | Late → early violation        |

---

## 4. Constraints

### Hard Constraints (must be satisfied)

1. **Duty coverage**
   Each duty must have required CAPT / FO / FA

2. **Eligibility**

   * Matching base
   * Qualified aircraft type
   * Matching role

3. **Duty conflicts**
   Overlapping duties forbidden

4. **Max workload**
   `total_minutes[c] ≤ max_minutes`

5. **Max consecutive work days**
   Sliding window constraint

---

### Soft Constraints (penalized)

| Constraint      | Description                               |
| --------------- | ----------------------------------------- |
| Fairness spread | Minimize max–min workload                 |
| Worked days     | Penalize total worked days                |
| OFF requests    | Working on requested-off day              |
| Weekly rest     | Missing minimum rest days per week        |
| Late → Early    | Late duty followed by early duty next day |

All soft constraints contribute linearly to the objective.

---

## 5. Objective Function

The solver minimizes:

```
Σ weight_i × violation_i
```

Specifically:

```
10 × fairness_spread
+ 10 × worked_days
+ 1 × off_request_penalty
+ 4 × weekly_rest_shortfall
+ 10 × late_to_early_violations
```

The full **objective breakdown** is exported to JSON.

---

## 6. How to Run

### Install dependencies

```bash
uv sync
```

### Run the model

```bash
python scripts/run_rostering_model.py \
  --instance-dir data/generated/v3 \
  --time-limit 10
```

---

## 7. Outputs

### Terminal summary

* Solver status
* KPIs
* Objective breakdown

Example:

```
Status: OPTIMAL
objective: 13106
late_to_early_total: 1
```

---

### JSON outputs

```
outputs/solutions/rostering_solution.json
outputs/report/objective_breakdown.json
```

---

### CSV reports

```
outputs/report/work_matrix.csv
outputs/report/workloads.csv
outputs/report/weekly_rest.csv
outputs/report/off_requests.csv
```

---

### Visualizations

```
outputs/report/work_calendar.png
outputs/report/workloads.png
```

The **heatmap highlights**:

* Grey: rest
* Green: work
* Orange: OFF request violated
* Purple: late → early violation
* Red: weekly rest violation

---

## 8. Design Choices

* CP-SAT chosen for:

  * Logical constraints
  * Indicator variables
  * Soft constraints via penalties
* No metaheuristics required — CP-SAT efficiently explores feasible schedules
* Model structured to scale to:

  * Longer horizons
  * More bases
  * Additional rules

---

## 9. Possible Extensions

* Pairing / multi-day rotations
* Base change penalties
* Crew preference fairness
* Aircraft-dependent duty durations
* Interactive dashboards (Plotly)

---

## 10. Author Notes

This project focuses on **decision quality**, not prediction.
It demonstrates **operations research modeling**, **constraint design**, and **trade-off analysis** under competing operational objectives.
