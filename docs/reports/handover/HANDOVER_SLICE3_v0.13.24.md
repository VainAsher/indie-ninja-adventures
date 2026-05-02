---
doc_type: handover
status: complete
slice: 3
version: v0.13.24
date: 2026-05-01
blockers_addressed: P0-G0-02, P0-G0-03
next_slice: 4
---

# Handover — Slice 3 (v0.13.24)

## What was done

Wired the Tai intro cutscene to fire automatically on campaign start, chained `act1_social_grounding` to start after it completes, rewrote `tutorial_elder.yarn` to Tai's authored voice, and stripped siren day-one gameplay actions.

| File | Change |
|------|--------|
| `CutsceneTriggerType.java` | Added `CAMPAIGN_START` enum value |
| `CutsceneTrigger.java` | `matches()` short-circuits on `CAMPAIGN_START` (no id needed); `fromMap()` allows absent `id` field for `campaign_start` event |
| `CutsceneTriggerRouter.java` | Added `onCampaignStart()` method |
| `GameScreen.java` | Wired `onCompleteCallback` → auto-starts `act1_social_grounding` when `act1_aen_of_lantern_heights` completes; calls `onCampaignStart()` after save restore (non-replay only); siren handlers stripped to flag-only |
| `act1_aen_of_lantern_heights.json` | Trigger changed: `npc_interact:instructor_tai` → `campaign_start` |
| `tutorial_elder.yarn` | Full rewrite to Instructor Tai's authored voice (calm mentor, resident-to-resident) |

## Behaviour after this slice

- On first campaign start: Tai cutscene plays immediately — player does not need to find or interact with him.
- Cutscene completion auto-starts `act1_social_grounding` mission.
- Subsequent Tai interactions use `tutorial_elder.yarn` (calm mentor fallback dialogue).
- `siren_start_first_trial` and `siren_open_mission_board` dialogue events now only store story flags; no `startMissionFlow` or `openMissionSelectOverlay` fires from them.

## Extending campaign_start for future cutscenes

Any cutscene with trigger `{ "event": "campaign_start" }` and an appropriate `start_conditions` block (e.g. a flag check) will fire in sequence. `CutsceneTriggerRouter.onCampaignStart()` returns on the first matching cutscene — order determined by iteration over `manager.definitions().values()`.

## Released

- Tag: `v0.13.24`
- Commit: `50d0e14`

## Remaining open P0 blockers

| ID | Status | Next action |
|----|--------|-------------|
| P0-G0-01 | Fixed (Slice 2) | — |
| P0-G0-02 | **Fixed** | — |
| P0-G0-03 | **Fixed** | — |
| P0-G0-04 | Open | Slice 4 — handleSoloPortalTravel mission_return |
| P0-G0-05 minimum | Fixed (Slice 1) | Full ghost entity in Slice 6 |
| P0-G0-06 data | Fixed (Slice 1) | NPC spawn gate (code) in Slice 5 |

## To resume Slice 4

**Problem:** After completing a mission (e.g. `samson_q1_dojo`), the portal home calls `handleSoloPortalTravel()` with `transition_type=mission_return`. The current code generates a new world instead of returning to `lantern_heights`.

**Files to read first:**

- `java/client/src/main/java/com/indieniinja/client/GameScreen.java` — grep `handleSoloPortalTravel` and `mission_return`
- `java/client/src/main/java/com/indieniinja/client/game/cutscene/` — no changes needed here

**Changes required:**

1. **`GameScreen.java` — `handleSoloPortalTravel()`**: When `transition_type` equals `"mission_return"`, reinitialize the simulation at `lantern_heights` using the original `soloSeed` (not a new seed). Re-enter the hub at the home spawn point instead of generating a new procedural world.
   - The method currently calls `initializeSoloSimulation(...)` with a hub-derived seed — that path is already there for hub transitions. The `mission_return` case needs to explicitly route to `lantern_heights` using `HubRegistry.hubSeed(soloSeed, "lantern_heights")`.
   - Preserve player state (abilities, position near hub entry portal).
2. No data changes needed.
3. No new enum/type additions needed.

Read `handleSoloPortalTravel` in full before starting — confirm whether `soloSeed` is accessible in that method's scope, and check if `restorePlayerStateForHubReturn()` or similar already exists for the hub-travel path.
