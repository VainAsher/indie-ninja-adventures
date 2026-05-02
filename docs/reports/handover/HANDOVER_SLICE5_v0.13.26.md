---
doc_type: handover
status: complete
slice: 5
version: v0.13.26
date: 2026-05-02
blockers_addressed: P0-G0-06 code
next_slice: 6
---

# Handover — Slice 5 (v0.13.26)

## What was done

Gated Linzi's NPC spawn behind completion of all four villager q1 missions.

| File | Change |
|------|--------|
| `GameSimulator.java` | Added `removeNpcsByCharacterId(String)` — removes all live NPCs with a matching `characterId` from the sim roster |
| `GameScreen.java` | Added `gateLinziSpawnBehindVillagerQuests()` — called after save restore on every hub load; removes Linzi if any of the four q1_complete flags are unset |

## Behaviour after this slice

- On first session (no q1 flags set): Linzi is removed from the sim immediately after spawn. She does not appear in the hub.
- After any single q1 completion: still absent.
- After all four (`samson_q1_complete`, `sophia_q1_complete`, `marcel_q1_complete`, `hazel_q1_complete` all `"true"`): Linzi spawns normally on the next hub load (triggered by the mission_return portal from the final q1 mission).

## Extending to other story-gated NPCs

Add a check in `gateLinziSpawnBehindVillagerQuests()` or create a sibling method. The same `localSim.removeNpcsByCharacterId(characterId)` call works for any authored NPC.

## Released

- Tag: `v0.13.26`

## Remaining open P0 blockers

| ID | Status | Next action |
|----|--------|-------------|
| P0-G0-01 | Fixed (Slice 2) | — |
| P0-G0-02 | Fixed (Slice 3) | — |
| P0-G0-03 | Fixed (Slice 3) | — |
| P0-G0-04 | Fixed (Slice 4) | — |
| P0-G0-05 minimum | Fixed (Slice 1) | Full ghost entity — Slice 6 |
| P0-G0-06 data | Fixed (Slice 1) | — |
| P0-G0-06 code | **Fixed** | — |

## To resume Slice 6

**Problem:** Samson sparring (`samson_q1_dojo`) uses a static boss enemy. The authored design calls for a two-phase ghost entity:
- Phase 1: ghost runs the critical path ahead of the player via scripted waypoints (AI leader, not recording playback)
- Phase 2: on reaching the arena / exit room, ghost switches to melee combat AI
- Resolution: at ≤1/3 HP, explicit "good enough" cutscene fires, sets `samson_q1_complete`, spawns exit portal

**New files needed:**

1. **`data/cutscenes/samson_sparring_complete.json`** — cutscene with:
   - Trigger: `{ "event": "flag_change", "id": "samson_ghost_low_hp" }`
   - Steps: lock player, Samson dialogue ("Good enough. You're ready."), set `samson_q1_complete = true`, unlock player, spawn exit portal
2. **`data/dialogues/samson_sparring.yarn`** — Samson's voice in the sparring cutscene (gruff, direct, impressed reluctantly)

**Code changes needed:**

1. **`java/shadowascent/src/main/java/com/indieniinja/sim/SimGhost.java`** — new class. Phase 1: waypoint list + move-toward logic. Phase 2: melee combat AI (can reuse `SimBoss` attack pattern). HP threshold field.
2. **`GameSimulator.java`** — when `samson_q1_dojo` is the active mission, spawn `SimGhost` in the boss room instead of (or alongside) the existing boss entity. Wire HP-threshold check → `setFlag("samson_ghost_low_hp", "true")`.
3. **`GameScreen.java`** — handle `samson_ghost_low_hp` flag change triggering the cutscene via `cutsceneTriggerRouter.onFlagChange("samson_ghost_low_hp")`.

**Read first:**
- `java/shadowascent/src/main/java/com/indieniinja/sim/SimBoss.java` — existing boss AI to reuse for Phase 2
- `java/shadowascent/src/main/java/com/indieniinja/sim/GameSimulator.java` — how `SimBoss` is spawned and stepped, to mirror for `SimGhost`
- `data/missions.json` entry for `samson_q1_dojo` — confirm `guaranteed_boss_exit: true` is present (added Slice 1)
