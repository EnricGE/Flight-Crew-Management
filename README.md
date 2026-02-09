# ✈️ Crew Rostering — Decision Under Operational Constraints

**Workforce planning, fairness trade-offs, and defensible scheduling decisions**
*Including hard operational constraints, soft preferences, and multi-criteria optimization.*

---

## 1. Context & Motivation

Crew rostering decisions are rarely about *finding any feasible schedule*.  
They are about **choosing an operational roster** that balances:

- coverage feasibility  
- regulatory and contractual constraints  
- fairness across crew members  
- fatigue and quality-of-life considerations  

This project studies a **realistic airline crew rostering decision problem under strict operational constraints**, using optimisation to support **transparent, defensible scheduling decisions**.

The goal is not to build a generic scheduling solver, but to answer:

> *“Given limited crew resources and hard operational rules, what roster should we operate — and what trade-offs does it imply?”*

---

## 2. Decision Problem

An airline must construct a crew roster over a fixed planning horizon.

The system includes:
- crew members with roles, bases, and qualifications  
- flight duties distributed across multiple days  
- regulatory and operational rules on rest and workload  

The roster determines:
- who works which duties  
- how workload is distributed  
- where fatigue and fairness risks appear  

All hard rules are **strictly enforced**.  
The decision-maker must choose **one roster**.

---

## 3. Operational Policies Considered

Each feasible roster corresponds to an **implicit operational policy**, defined by:

- assignment of crew to duties  
- distribution of worked days and duty minutes  
- exposure to fatigue patterns (late → early sequences)  

Different rosters represent different strategic choices, such as:
- prioritising workload balance  
- minimising total worked days  
- protecting rest patterns at the expense of fairness  

---

## 4. Modelling & Evaluation Approach

The problem is formulated as a **constraint-based optimisation model**:

- Binary assignment variables  
- Indicator variables for workload and fatigue patterns  
- Linear penalties for undesirable but acceptable patterns  

Key characteristics:
- Hard constraints ensure feasibility  
- Soft constraints express preferences and risk exposure  
- A single objective aggregates trade-offs  

Each candidate roster is evaluated on:
- feasibility  
- total penalty score  
- distribution of workload and rest  

---

## 5. Decision Variables & Constraints

### Decision Variables
- Assignment of crew to duties  
- Daily work indicators  
- Fatigue and rest pattern indicators  

### Hard Constraints
- Duty coverage by role  
- Qualification and base eligibility  
- Duty overlap prevention  
- Maximum workload limits  
- Maximum consecutive work days  

### Soft Constraints (penalised)
- Workload fairness  
- Total worked days  
- Day-off request violations  
- Weekly rest shortfall  
- Late → early fatigue patterns  

These constraints define the **decision trade-off space**.

---

## 6. Objective Function

The decision criterion is:

```
Minimise total weighted penalty
```

Where penalties reflect:
- fairness imbalance  
- excessive workload  
- violation of crew preferences  
- fatigue risk  

The weights encode **management priorities and risk tolerance**.

---

## 7. Decision Insights

Typical questions this model helps answer:

- Where are fairness and feasibility in conflict?  
- Which crew members carry disproportionate workload?  
- How do rest rules constrain flexibility?  
- What is the cost of protecting fatigue-sensitive patterns?  

The value lies in **understanding why a roster looks the way it does**, not just generating it.

---

## 8. Decision Recommendation

For a given scenario, the recommended decision is:

> **The feasible roster with the lowest total penalty, respecting all hard operational constraints while balancing fairness and fatigue risk.**

Because all assumptions and penalties are explicit, the recommendation is:
- transparent  
- auditable  
- adjustable to policy changes  

---

## 9. Limitations & Extensions

This is a **simplified planning model**.

Not included (yet):
- pairing or multi-day rotations  
- reserve crew dynamics  
- demand uncertainty  
- real-time recovery  

These extensions would enable richer operational decision support.

---

## 10. Takeaway

> **The value of crew rostering lies not in assigning duties, but in making explicit the trade-offs between fairness, feasibility, and fatigue.**

This project demonstrates how optimisation can be used as a **Decision Intelligence tool** to justify workforce scheduling decisions under real-world constraints.
