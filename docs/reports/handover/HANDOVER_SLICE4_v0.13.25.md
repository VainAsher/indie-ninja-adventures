---
doc_type: handover
status: complete
slice: 4
version: v0.13.25
date: 2026-05-02
blockers_addressed: P0-G0-04
next_slice: 5
---

# Handover — Slice 4 (v0.13.25)

## What was done

Fixed `handleSoloPortalTravel()` so that `mission_return` portals route back to the hub the mission was launched from, not to the generated `destinationId` on the portal entity.

| File | Change |
|------|--------|
| `GameScreen.java` | Added `resolvedDestination` local variable in `handleSoloPortalTravel()` — when `normalizedTransitionType == "mission_return"`, uses `originHubId` instead of the passed `destinationId` |

## Root cause

Level generation stamps boss-exit portals with `destinationId = HubRegistry.nextHub(masterHubId)` — the *next* hub in progression, not the origin. When the player used the mission-return portal, `handleSoloPortalTravel` passed that next-hub ID to `HubRegistry.get()`, spawning the wrong world.

## Released

- Tag: `v0.13.25`
- Commit: pending (next commit after this file is staged)

## Remaining open P0 blockers

| ID | Status | Next action |
|----|--------|-------------|
| P0-G0-01 | Fixed (Slice 2) | — |
| P0-G0-02 | Fixed (Slice 3) | — |
| P0-G0-03 | Fixed (Slice 3) | — |
| P0-G0-04 | **Fixed** | — |
| P0-G0-05 minimum | Fixed (Slice 1) | Full ghost entity in Slice 6 |
| P0-G0-06 data | Fixed (Slice 1) | NPC spawn gate (code) in Slice 5 |

## To resume Slice 5

**Problem:** Linzi appears at Lantern Heights from day one regardless of story progress. She should only spawn once all four villager q1 missions are complete (`samson_q1_complete`, `sophia_q1_complete`, `marcel_q1_complete`, `hazel_q1_complete` all set to `"true"`).

The `requires` gate in `missions.json` prevents the *mission* from being offered early, but Linzi's NPC *entity* spawns unconditionally. The fix lives in GameScreen's NPC spawner.

**Files to read first:**

- `java/client/src/main/java/com/indieniinja/client/GameScreen.java` — grep `spawnNpc`, `linzi`, `npcId`, and how `activeNpcTypes()` or similar is used to decide which NPCs to render/spawn
- `java/shadowascent/src/main/java/com/indieniinja/world/HubRegistry.java` — check if `HubDef.activeNpcTypes()` already has a story-flag-aware gate mechanism, or if it's a static list
- `data/hub_templates/lantern_heights.tmx` — check if Linzi has a dedicated spawn point separate from the generic NPC list

**Changes required:**

1. **`GameScreen.java` NPC spawner / snap processing**: Before adding Linzi's entity to the active NPC list, check that all four story flags are set to `"true"` in `storyManager`. If any flag is missing, skip her spawn.
2. The story flags to check: `samson_q1_complete`, `sophia_q1_complete`, `marcel_q1_complete`, `hazel_q1_complete`.
3. No data changes expected. No HubRegistry changes unless the hub NPC roster already reads from story flags (in which case, extend that mechanism rather than adding a new check in GameScreen).

Confirm where NPCs are added to the world snapshot before starting — the gate must be in the right layer (world-gen / sim-step / render prep).
