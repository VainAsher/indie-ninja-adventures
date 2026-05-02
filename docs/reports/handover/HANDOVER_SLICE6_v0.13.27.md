---
doc_type: handover
status: complete
slice: 6
version: v0.13.27
date: 2026-05-02
blockers_addressed: P0-G0-05 full
next_slice: none (all P0 G0 blockers resolved)
---

# Handover — Slice 6 (v0.13.27)

## What was done

Wired Samson sparring resolution: boss yields at ≤1/3 HP instead of dying, cutscene fires, mission completes via cutscene callback.

| File | Change |
|------|--------|
| `SimBoss.java` | Added `yielded` field; `takeDamage()` no-ops when `yielded = true` |
| `GameSimulator.java` | Added `setBossYieldCallback(Runnable)` + `bossYieldFired` flag; yield check fires in `stepBosses()` at ≤1/3 HP |
| `GameScreen.java` | Registers yield callback for `samson_q1_dojo` missions post-world-build; `onCompleteCallback` handles `samson_sparring_complete` → `completeActiveMissionWithCutsceneTrigger()` |
| `data/cutscenes/samson_sparring_complete.json` | New cutscene; trigger: `flag_change:samson_ghost_low_hp`; Samson concession dialogue + mission completion |
| `data/dialogues/samson_sparring.yarn` | Samson's authored voice for sparring resolution and follow-up interaction |

## Full resolution flow

1. Player damages boss in `samson_q1_dojo` to ≤1/3 HP
2. `GameSimulator.stepBosses()` sets `boss.yielded = true` and fires `bossYieldCallback`
3. Callback calls `setStoryFlagAndTriggerCutscene("samson_ghost_low_hp", "true")`
4. `CutsceneTriggerRouter.onFlagChange("samson_ghost_low_hp")` starts `samson_sparring_complete` cutscene
5. Cutscene plays Samson concession lines (blocking)
6. `CutsceneManager.onCompleteCallback` fires → `completeActiveMissionWithCutsceneTrigger()`
7. Mission completes → `samson_q1_complete` story flag set (via `story_trigger` in missions.json)
8. Exit portal (from `guaranteed_boss_exit: true`) available; player returns to `lantern_heights`

## What Phase 1 (scripted ghost leader) would require

Phase 1 (ghost running critical path ahead of player via waypoints) was intentionally deferred — the combat resolution and HP-threshold cutscene are what matter for G0 playtest. If Phase 1 is needed:

1. Add `List<float[]> waypoints` to a new `SimGhost` entity (or add to `SimBoss` for the SAMSON_GHOST boss type)
2. In Phase 1, ghost moves toward waypoints sequentially; no combat
3. Switch to Phase 2 (combat AI) on reaching the final waypoint (arena entrance)
4. This requires authored waypoint positions keyed to `samson_q1_dojo`'s room layout

## Released

- Tag: `v0.13.27`

## All P0 G0 blockers resolved

| ID | Status |
|----|--------|
| P0-G0-01 | Fixed (v0.13.23) |
| P0-G0-02 | Fixed (v0.13.24) |
| P0-G0-03 | Fixed (v0.13.24) |
| P0-G0-04 | Fixed (v0.13.25) |
| P0-G0-05 | Fixed (v0.13.27) |
| P0-G0-06 | Fixed (v0.13.22 data + v0.13.26 code) |

## Next step

Run G0 second smoke session against v0.13.27. Target: 5 passing first-session records to close P0-10 and unblock Milestone 0 sign-off.

Use `docs/PLAYABLE_TRUTH.md` for the approved G0 golden route and tester scope.
