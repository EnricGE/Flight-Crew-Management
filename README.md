# ✈️ Crew Rostering — Defensible Scheduling Under Operational Constraints

Optimization tool for airlines to select a crew roster that explicitly balances coverage, fairness, and fatigue risk.

The goal is to produce a single, justifiable roster over a fixed planning horizon — not just any feasible schedule, but the one that best respects competing operational priorities. It enforces hard regulatory rules while surfacing the true trade-offs between workload equity, crew preferences, and fatigue exposure. The weights governing these trade-offs encode management policy and can be tuned per scenario.

## Problem Overview
Without structured optimization, crew scheduling risks:
- Uncovered flights due to eligibility or qualification mismatches
- Rest and consecutive-day violations that breach regulatory requirements
- Uneven workload distribution, exposing the airline to fairness grievances
- Fatigue patterns (late-to-early duty sequences) that increase operational risk
- Decisions that are opaque and difficult to defend to crew or regulators

## What the Model Does
- Enforces duty coverage by role (Captain, First Officer, cabin crew) as a hard constraint
- Respects crew eligibility: base assignment, aircraft qualification, and individual workload limits
- Prevents duty overlap and guarantees minimum rest between assignments
- Penalizes fairness imbalance, off-request violations, weekly rest shortfall, and late-to-early fatigue sequences
- Aggregates all soft trade-offs into a single weighted objective whose weights encode management priorities
- Supports robustness testing by solving across scenario variants — crew unavailability, duty shifts, preference changes

## Approaches
- **Feasibility model** — Confirms whether a legally compliant roster exists for a given instance; serves as a planning baseline
- **Optimization model** — Finds the best roster under a weighted multi-criteria objective; the primary decision tool
- **Scenario batch solver** — Runs the optimization across generated variants to quantify how solutions change under disruption

## Purpose
This project demonstrates:
- Constraint programming applied to a realistic workforce planning problem
- Multi-criteria optimization with explicit, auditable trade-off encoding
- Separation of hard feasibility from soft preference management
- Robustness analysis through systematic scenario generation and batch solving
- Decision-level reporting: objective breakdown, workload distribution, and fatigue exposure per crew member
