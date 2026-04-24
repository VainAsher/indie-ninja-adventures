---
doc_type: design-reference
status: living
owner: design-team
last_updated: 2026-04-24
version_anchor: v0.12.07
---

# Gameplay KPI Targets — Stance Readability and Flow Clarity

Numeric precision layer for the qualitative stance/Flow goals in `PLAN_SHADOW_ASCENT.md` addendum and `GDD.md §3.3`.

This document is the **Phase 2 measurement contract**. Every tuning loop must reference it. Targets are working hypotheses — update them after each loop if the data demands it, but do not change them without a logged reason.

**Source goals this document operationalises:**
- PLAN_SHADOW_ASCENT.md §Addendum — stance/Flow playtest focus questions
- PLAN_SHADOW_ASCENT.md §Metric guardrails — initial target bands
- GDD.md §3.3 — Passive/Aggressive stance identity, Flow as mastery state

---

## 1. Stance Readability KPIs

### 1.1 Passive / Aggressive Distinction Comprehension

> Does Passive stance feel distinct from Aggressive stance in movement, silhouette, and combat outcome?

| Metric | Target | Fail signal |
|--------|--------|-------------|
| After completing Act I, playtesters who can describe (unprompted) what makes Passive different from Aggressive | ≥ 80% | < 60% = stances are not communicating their identity; escalate to design |
| Playtesters who describe Roll as "stealthy / low-profile / controlled" | ≥ 70% | < 50% = Roll fantasy is not landing |
| Playtesters who describe Dash as "fast / forceful / aggressive" | ≥ 70% | < 50% = Dash fantasy is not landing |

**G4 gate:** Before any renderer or stance change ships, G4 must pass — both stances correct in all five movement states (idle, walk, jump, crouch, attack). See `GOLDEN_PATH_REGRESSION.md`.

### 1.2 Roll vs Dash Preference Skew

> Does the Roll vs Dash split signal stance-mobility imbalance?

| Metric | Target | Fail signal |
|--------|--------|-------------|
| Roll share of all traversal actions in a mixed session | ≥ 15% | < 10% = Roll is being skipped; one stance invalidating the other |
| Dash share of all traversal actions in a mixed session | ≥ 15% | < 10% = Dash is being skipped; Roll too dominant or Dash cost too high |

**Pre-telemetry measurement:** Estimate from session observation notes — observer counts Roll and Dash uses at defined checkpoints (one per room transition). Record as `roll_n / total_traversal_n`.

### 1.3 Stance Switch Engagement

> Are players actively switching stances or locking to one?

| Metric | Target | Fail signal |
|--------|--------|-------------|
| Successful runs where both stances are used (≥ 1 action each) | ≥ 90% | < 75% = one stance ignored; dominance problem or switch UX barrier |
| Runs where player never switches stance after Act I intro | < 15% | > 25% = stance switching is not understood or not rewarded clearly enough |

---

## 2. Flow Activation Clarity KPIs

### 2.1 Flow Activation Frequency

> Is Flow achievable without becoming background noise?

| Metric | Target | Fail signal |
|--------|--------|-------------|
| Flow activations per mainline mission in a skilled session | 1 – 3 | < 1 = Flow is unreachable or unreadable; > 5 = Flow is trivial, loses meaning |
| Sessions where player never activates Flow across a full mainline mission | < 20% | > 40% = Flow entry is too opaque or too punishing to pursue |

### 2.2 Balance Indicator Comprehension

> Is the balance indicator clear without cluttering play?

| Metric | Target | Fail signal |
|--------|--------|-------------|
| First-hour playtesters who can explain what the balance indicator does (unprompted) | ≥ 70% | < 50% = indicator is not communicating; needs visual or placement rework |
| Playtesters who can explain how to trigger Flow after one session | ≥ 65% | < 45% = Flow entry mechanic is opaque |

### 2.3 Flow Pursuit Intent (Observable)

> Do players consciously adjust their stance to chase Flow?

| Metric | Target | Observation method |
|--------|--------|-------------------|
| Playtest sessions where player explicitly shifts stance at least twice to pursue Flow | ≥ 50% of sessions | Noted by observer: "player switched stance deliberately when balance leaning heavy to one side" |
| Player reports Flow felt "earned" vs "random" | ≥ 65% of respondents | Post-session question: "Did Flow feel earned or did it happen unexpectedly?" |

### 2.4 Flow Feel Quality

> Does Flow feel smoother and more masterful rather than simply stronger?

| Metric | Target | Fail signal |
|--------|--------|-------------|
| Playtesters who describe Flow as "smooth / masterful / earned" | ≥ 60% | < 40% = Flow is reading as a pure stat burst; rethink visuals or duration |
| Playtesters who describe Flow as "confusing / random / not useful" | < 20% | > 35% = Flow benefit is not landing; investigate readability and reward clarity |

---

## 3. Unfair-Death Rate

> Deaths that feel unjust erode mastery trust faster than any balance issue.

| Metric | Target | Fail signal |
|--------|--------|-------------|
| Deaths where player self-reports "I didn't understand why I died" in first 2 hours | < 20% of deaths | > 30% = too many deaths are invisible or unfair-feeling; triage cause before tuning damage |
| Same metric after 4+ hours of play | < 10% of deaths | > 20% = game not teaching its own rules even with experience |

**How to capture:** Post-death micro-question in playtest notes — "Did you understand why you died? Y / N / Partially." Count N+Partially as "unfair-feeling."

---

## 4. Pre-Telemetry Measurement Method

These targets were written before P1-02 telemetry is built. Until telemetry is in place, capture manually during structured playtest sessions.

### 4.1 Required observer notes per session

For every Phase 2 playtest session, the observer records:

```
Session: [date] [player-id] [version]
Stances used: Passive_n=[n] Aggressive_n=[n]
Roll_traversal_n=[n] Dash_traversal_n=[n] Total_traversal_n=[n]
Flow_activations=[n]
Unfair_deaths=[n] Total_deaths=[n]
Stance_switch_to_chase_flow=[n]
```

### 4.2 Post-session questions (required per session)

From PLAN_SHADOW_ASCENT.md §Addendum — ask directly after play, no coaching:

1. "Without looking at the controls screen, what does Passive stance feel like vs Aggressive stance?"
2. "What is the balance indicator showing you?"
3. "How do you trigger Flow?"
4. "Did Flow feel earned or did it happen unexpectedly?"
5. "Were there deaths that felt unfair or confusing?"

### 4.3 When telemetry (P1-02) is ready

Replace manual counts with session bundle metrics. The KPI target numbers stay the same — only the measurement source changes. Review this document and confirm targets are still valid at that point.

---

## 5. Tuning Loop Protocol

Each Phase 2 tuning loop must produce:

1. **Hypothesis** — what you expect to change and why (reference a specific KPI)
2. **Change** — the specific code/data/parameter changed (with commit reference)
3. **Evidence** — session notes from at least one playtest run using §4.1 observer template
4. **Decision** — did the KPI move? What's next?

Record outcomes in `BALANCE_LOG.md` (create if not yet present). One entry per loop.

Change-control rules from PLAN_SHADOW_ASCENT.md §Change-control apply:
- Do not merge unmeasured balance changes
- Each commit must reference a hypothesis ID
- Freeze 48h before any release candidate

---

## 6. Phase 2 Exit Gate

Phase 2 is done when **all three** hold simultaneously:

- [ ] ≥ 80% stance comprehension rate across two consecutive tuning loops (§1.1)
- [ ] ≥ 65% Flow comprehension rate across two consecutive tuning loops (§2.2)
- [ ] G4 pass on the current build (both stances, all five movement states)

Until all three are met, Phase 3 (Content Depth) does not open.

---

## 7. Target Refinement Policy

These targets are **working hypotheses as of v0.12.07**. Update them when:
- Two consecutive loops produce data clearly above the target (target may be too easy)
- A target is structurally unmeasurable without telemetry (defer with note, don't delete)
- Post-external-playtest data contradicts the internal baseline

Always log the reason for a target change in a commit message referencing this file.
