---
doc_type: handover
status: complete
slice: 1
version: v0.13.22
date: 2026-05-01
blockers_addressed: P0-G0-05 (minimum), P0-G0-06 (data)
next_slice: 2
---

# Handover — Slice 1 (v0.13.22)

## What was done

Pure data fixes to `data/missions.json`. No Java code changed.

| Change | File | Detail |
|--------|------|--------|
| `guaranteed_boss_exit: true` on `samson_q1_dojo` | missions.json | P0-G0-05 minimum fix — player cannot be stranded in sparring mission |
| `requires` gate added to `linzi_q1` | missions.json | P0-G0-06 — gates Linzi's mission behind all four villager q1 completions |
| Sophia + Marcel added to `act1_social_grounding` objectives | missions.json | P0-G0-06 — greet mission now covers all four named NPCs |

## Key discovery during this slice

`unlock_requirements` in missions.json is **not read by `MissionDefinition.parse()`** — the Java parser reads `requires`. All NPC quest missions (samson_q1_dojo etc.) and linzi_q1 used `unlock_requirements`, making them silently available from the start with no prerequisites. This is how Linzi's mission appeared at day one. The fix uses `requires` which is the canonical parsed field.

## Released

- Tag: `v0.13.22`
- CI: success
- Release: success
- Commit: `57b7566`

## Remaining open P0 blockers (after this slice)

| ID | Status | Next action |
|----|--------|-------------|
| P0-G0-01 | Open | Slice 2 — HudRenderer hub name + time-of-day |
| P0-G0-02 | Open | Slice 3 — Tai cutscene auto-trigger |
| P0-G0-03 | Open | Slice 3 — auto mission flow from spawn |
| P0-G0-04 | Open | Slice 4 — handleSoloPortalTravel mission_return |
| P0-G0-05 minimum | **Fixed (data)** | Full ghost entity in Slice 6 |
| P0-G0-06 data | **Fixed** | NPC spawn gate (code) in Slice 5 |

## To resume from here

1. Confirm on `master` at `v0.13.22`.
2. Read `docs/reports/manual-runtime/g0-v0.13.21-session-1.md` for the full blocker list.
3. Read `docs/plans/implementing/PLAN_SHADOW_ASCENT.md` latest loop note for active work queue.
4. Start Slice 2: `HudRenderer.java` — add `setHubIdentity(String hubName, String timeOfDay)` method called from `GameScreen` on hub entry; render hub name top-centre in campaign mode and a small time-of-day label. Read from `HubRegistry.HubDef.displayName()` and a new `timeOfDay()` field (or derive from `WorldSnapshot.hubId`).
5. Follow `docs/workflow/ITERATION_RELEASE_PROTOCOL.md` for each slice.
