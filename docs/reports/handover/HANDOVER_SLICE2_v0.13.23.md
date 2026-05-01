---
doc_type: handover
status: complete
slice: 2
version: v0.13.23
date: 2026-05-01
blockers_addressed: P0-G0-01
next_slice: 3
---

# Handover — Slice 2 (v0.13.23)

## What was done

Added hub name + time-of-day banner to HUD for campaign mode. No data changes.

| File | Change |
|------|--------|
| `HudRenderer.java` | Added `hubDisplayName`/`hubTimeOfDay` fields, `setHubIdentity()` setter, campaign-mode banner render (gold hub name + amber subtitle, top-centre) |
| `GameScreen.java` | Added `prevHubIdForBanner` tracking field, hub-change detection in snap loop calling `setHubIdentity()`, static `hubTimeOfDay()` mapping |

## Render behaviour

- `LANTERN HEIGHTS` rendered at top-centre in warm gold (scale 1.3×) whenever `snap.hubId = "lantern_heights"`
- `At Dawn` rendered below in muted amber (scale 0.85×)
- Other hubs show display name with no time-of-day subtitle until authored
- Banner updates on every hub transition automatically

## Extending time-of-day for new hubs

Add a `case` to `GameScreen.hubTimeOfDay(String hubId)`. No other files needed.

## Released

- Tag: `v0.13.23`
- CI: success
- Release: success
- Commit: `df199fd`

## Remaining open P0 blockers

| ID | Status | Next action |
|----|--------|-------------|
| P0-G0-01 | **Fixed** | — |
| P0-G0-02 | Open | Slice 3 — Tai cutscene trigger change + yarn rewrite |
| P0-G0-03 | Open | Slice 3 — auto mission flow after Tai cutscene |
| P0-G0-04 | Open | Slice 4 — handleSoloPortalTravel mission_return |
| P0-G0-05 minimum | Fixed (Slice 1) | Full ghost entity in Slice 6 |
| P0-G0-06 data | Fixed (Slice 1) | NPC spawn gate (code) in Slice 5 |

## To resume Slice 3

Changes required:

1. **`data/cutscenes/act1_aen_of_lantern_heights.json`** — change trigger from `{ "event": "npc_interact", "id": "instructor_tai" }` to `{ "event": "campaign_start" }`.
2. **`CutsceneTriggerType.java`** — add `CAMPAIGN_START` to enum.
3. **`CutsceneTriggerRouter.java`** — add `onCampaignStart()` method calling `startFirst(CAMPAIGN_START, "")`.
4. **`CutsceneLoader.java`** — handle `"campaign_start"` event string → `CAMPAIGN_START` type when loading triggers.
5. **`GameScreen.java`** — after `initializeSoloSimulation` on campaign start, call `cutsceneTriggerRouter.onCampaignStart()`. Also wire `act1_social_grounding` auto-trigger on cutscene complete via the `onCompleteCallback`.
6. **`data/dialogues/tutorial_elder.yarn`** — rewrite to match Tai's authored voice. Current content is generic placeholder ("Elder Guardian", "Welcome young ninja"). Tai's authored lines are in `act1_aen_of_lantern_heights.json` steps already; the yarn file is the fallback for subsequent interactions. Use Tai's voice: calm, mentor, speaks to Aen as someone who belongs here.
7. **`GameScreen.java`** — remove `siren_start_first_trial` and `siren_open_mission_board` event handlers (lines ~2462–2471). Replace with story-flag-only storage (fall through to `default`).

Read `java/client/src/main/java/com/indieniinja/client/game/cutscene/CutsceneTrigger.java` and `CutsceneLoader.java` before starting — confirm how triggers are parsed from JSON to understand where to add `campaign_start` string handling.
