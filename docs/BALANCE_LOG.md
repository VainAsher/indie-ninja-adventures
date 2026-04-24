---
doc_type: balance-log
status: living
owner: design-team
last_updated: 2026-04-24
version_anchor: v0.12.07
---

# Balance Log — Shadow Ascent

Record of every measurable tuning change. Each entry must reference a hypothesis ID and a KPI from `GAMEPLAY_KPI_TARGETS.md`.

Do not merge balance changes without a logged entry. See change-control rules in `PLAN_SHADOW_ASCENT.md §Change-control`.

---

## Template

```
### [LOOP-ID] [date] — [one-line description]

**Hypothesis:** What do you expect to change and which KPI it should move?
**KPI reference:** §X.X of GAMEPLAY_KPI_TARGETS.md
**Change:** Parameter/code changed + commit SHA
**Evidence:** Session notes using §4.1 observer template (or attach file path)
**Result:** Did the KPI move? What was observed?
**Decision:** Keep / revert / iterate — and why
```

---

## Phase 2 Tuning Loops

### LOOP-P2-01 [pending] — Establish Flow baseline

**Hypothesis:** Before any tuning, run one unmodified session to establish baseline KPI readings across §1–§3 of GAMEPLAY_KPI_TARGETS.md. Expected: stance comprehension and Flow comprehension will be below target (no tuning yet).

**KPI reference:** All — this is the baseline measurement loop.

**Change:** None. Baseline observation only.

**Evidence:** Run session using `docs/workflow/PLAYTEST_PACKET_WORKFLOW.md` packet structure. Fill in §4.1 observer notes from GAMEPLAY_KPI_TARGETS.md. Record here when complete.

```
Session: [date] [player-id] v0.12.07
Stances_used: Passive_n=[] Aggressive_n=[]
Roll_traversal_n=[] Dash_traversal_n=[] Total_traversal_n=[]
Flow_activations=[]
Unfair_deaths=[] Total_deaths=[]
Stance_switch_to_chase_flow=[]
Post-session Q1 (stance distinction): []
Post-session Q2 (balance indicator): []
Post-session Q3 (how to trigger Flow): []
Post-session Q4 (Flow felt earned?): []
Post-session Q5 (unfair deaths?): []
```

**Result:** [fill after session]

**Decision:** [fill after session — identify the lowest-scoring KPI as the focus for LOOP-P2-02]

---

### LOOP-P2-02 [pending] — First targeted tuning change

**Hypothesis:** [Define after LOOP-P2-01 baseline is complete — target the lowest-scoring KPI.]

**KPI reference:** [Fill from GAMEPLAY_KPI_TARGETS.md]

**Change:** [Parameter/code + commit SHA]

**Evidence:** [Session notes]

**Result:** [Observed KPI movement]

**Decision:** [Keep / revert / iterate]
