---
doc_type: plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.4
---
# PLAN â€” Shadow Ascent: The Hollowed Ninja
## GDD Alignment & Implementation Roadmap
**Created:** 2026-04-10 | **Last updated:** 2026-04-29 | **Codebase version:** v0.13.4 | **Next release target:** v0.13.5

---

## PIVOT — Act I Lantern Dawn Vertical Slice
**Pivot effective from:** 2026-04-28
**Pivot type:** product scope focus — from broad systems expansion to Act I vertical slice proof

Stop building the whole game at once.
Build the first 20-30 minutes so well that a player who knows nothing about the developer,
the GDD, or internal systems still understands:

- Aen has a home.
- Yin and Yang matter.
- Lantern Heights is alive.
- Linzi's praise feels good before it becomes dangerous.
- The first signs of isolation are beginning.

**Active golden path: G0 — Act I Lantern Dawn first-session route.**
See `docs/PLAYABLE_TRUTH.md` for the approved route and tester scope.

**Freeze in effect (until G0 is verified playable and emotionally legible):**
Arcade mode, co-op expansion, boss roster, biome variety, Echo Art, Traversal Art,
Proof Tokens, Labyrinth Court, Ember Monastery, Winding Skyroad, advanced Lantern recovery.

**Core campaign truth to preserve:**
The game is not about defeating a villain and getting back what was taken.
It is about becoming whole while still living with absence.
Yin and Yang are never reclaimed. Aen lights the Beacon of Return and waits.
This slice exists to make that future loss matter.

---

## PLAN STATUS â€” UPDATED IN PLACE
**Pivot effective from:** 2026-04-14 12:00:00 +01:00  
**Pivot type:** gameplay identity realignment on top of an existing campaign-first roadmap

This plan remains the active execution roadmap for Shadow Ascent.  
It has been **updated in place**, not replaced.

### Why this pivot exists
Since earlier versions of this plan were written, the gameâ€™s implemented movement, combat, animation, boss, HUD, and simulation foundations have made the intended player experience much clearer. The campaign-first product direction remains correct, but parts of the gameplay framing in this document still reflect an older Yin/Yang interpretation centered on abstract meter behavior, hidden-platform revelation, and threshold bonuses.

The current design direction is tighter and more legible:

- Passive / Aggressive stance gameplay
- Roll vs Dash movement identity
- Armed / Unarmed posture readability
- Shared combo/parry system with lethal vs non-lethal differentiation
- Aerial directional attacks and throws
- Flow as an earned mastery state reached through balanced stance use
- Lantern as a mastery amplifier
- Balance readability as a core UX requirement

### What this pivot changes
This update pivots the plan toward:
- movement-first stealth-action combat feel
- stance-driven moment-to-moment decision-making
- Flow as the primary mastery reward
- Trials as mastery extensions of the same combat/movement language
- clearer co-op stance synergy expectations

### What this pivot does not change
This pivot does **not** change:
- Campaign-first product direction
- Sandbox removal
- Trials as the repurposing of useful Arcade scaffolding
- Raids as later, subordinate challenge content
- Solo as an access path, not a separate flagship product
- Preservation of the current Java architecture
- The value of the existing implementation work loop and milestone discipline

### Interpretation rule from this point forward
Where older sections of this plan describe Yin/Yang primarily as abstract meter thresholds, hidden-platform gating, or raw stat-expression systems, those sections should now be interpreted through the newer stance-driven model unless explicitly preserved for historical implementation context.

---

## 0A. Feedback Workloop Operating Model (Mandatory)

This plan now uses the Implementation Work Loop from:
`C:\\Users\\asher\\.claude\\projects\\c--Users-asher-Vain-Asher-Gaming\\memory\\feedback_work_loop.md`

Every implementation cycle must follow this exact order:

| Step | Action | Required artifact |
|------|--------|-------------------|
| 1 | Review plan and current phase state | Plan status read and acknowledged in work notes |
| 2 | Create phase-specific todo list | Todo list mapped to current plan IDs |
| 3 | Execute tasks one by one | Task state moved to done in checklist/todo |
| 4 | Commit after each logical unit | Detailed commit message with plan ID references |
| 5 | Update plan | Completed items marked, decisions and next step captured |
| 6 | Push to remote | Branch updated on GitHub |
| 7 | Loop | Start next cycle from step 1 |

### Workloop rules

- Never batch all work into one end-of-day commit.
- Every meaningful implementation unit must map to at least one checklist ID below.
- Commit messages should include: `plan_id`, `scope`, `reason`, `risk`.
- Plan updates happen each loop, not only at milestone boundaries.
- Unknown scope discovered mid-loop becomes a new checklist row, not ad-hoc drift.
- All plan updates and loop notes must use full timestamps: `YYYY-MM-DD HH:mm:ss Â±HH:MM` (not date-only).

### Added rule from this pivot
**Added:** 2026-04-14 12:00:00 +01:00

Any loop that changes movement, combat, stance, Flow, Lantern readability, or Trials feel must also record:
- the intended player-facing feel change
- whether the change affects Passive play, Aggressive play, or both
- whether the change affects Flow entry, Flow maintenance, or Flow readability

**Why added:**  
The original workloop is excellent for implementation discipline, but the new direction introduces a stronger feel-first design layer. Without this addition, core combat/stealth tuning could drift while still appearing operationally complete.

### Latest loop note

`2026-05-01 00:00:00 +01:00`

- G0 session 1 ran against v0.13.21 (launcher install, CAMPAIGN, clean slot 1). Result: **FAIL**.
  - Evidence: `docs/reports/manual-runtime/g0-v0.13.21-session-1.md`
  - Steps 1–3 pass; steps 4–14 fail or are blocked by 6 P0 blockers.
  - Route cannot be re-run until all 6 P0-G0-01 through P0-G0-06 are resolved.
  - 4 sessions remaining to close G0/P0-10 (must use clean save each time).
- **Design clarification (critical):** Linzi and the Siren are the same character at different campaign phases.
  - `siren_phase1-4` NPC IDs are Linzi's later evolution — Linzi = Siren, not two characters.
  - Linzi/Siren must not appear in the Act I hub until a specific campaign beat has passed.
  - The correct gate: Linzi spawns only after `samson_q1_complete AND sophia_q1_complete AND marcel_q1_complete AND hazel_q1_complete` are all set.
  - **GDD §1.5 Runtime Alignment Addendum is incorrect.** Its claim "Siren is the explicit first quest giver in Act I" contradicts this. Addendum must be corrected before any further implementation work on Linzi/Siren.
  - `siren_start_first_trial` and `siren_open_mission_board` event handlers in `GameScreen` (currently fire `demo_coin_run` on day one) are incorrectly wired and must be removed or rewritten.
  - `siren_first_quest.yarn` is written as a day-one reveal; belongs to a far-future beat and must be removed from Act I routing.
- **Data discovery during triage:** All four villager q1 missions already exist in `data/missions.json`:
  - `samson_q1_dojo`, `sophia_q1_cartography`, `marcel_q1_forge`, `hazel_q1_gentle` — dialogue events wired in `*_act0.yarn` files.
  - **Gap:** `linzi_q1` only requires `act1_social_grounding`, not the four individual completions.
  - **Gap:** `act1_social_grounding` lists only Tai, Samson, Hazel — Sophia and Marcel are missing.

**Active work queue for P0-10 G0 blockers:**

- **P0-G0-01** Hub visual identity — Add hub name + time-of-day to `HudRenderer`; read from `HubRegistry`. No design gate.
- **P0-G0-02** Tai onboarding auto-trigger — Change cutscene trigger to `campaign_start`; rewrite `tutorial_elder.yarn` to Tai voice. No design gate.
- **P0-G0-03** Auto mission flow from spawn — Wire social grounding auto-trigger after Tai cutscene; remove siren day-one event handlers. No design gate.
- **P0-G0-04** Exit portal to wrong world — Fix `handleSoloPortalTravel` for `transition_type=mission_return` to return to hub. No design gate.
- **P0-G0-05** Samson sparring soft-lock — Add `guaranteed_boss_exit` to `samson_q1_dojo`. **Design gate: decide sparring mechanic** (scripted ghost, dummy, or scripted loss — `samson_ghost` enemy type already defined in missions.json).
- **P0-G0-06** Linzi gate broken — Gate `linzi_q1` behind all four `*_q1_complete` flags; add Sophia + Marcel to `act1_social_grounding` objectives; remove siren from hub spawn until Linzi beat. No design gate.

- P0-G0-05 design escalation: `samson_q1_dojo` already defines `samson_ghost` as opponent (enemy type in missions.json). Decision needed: scripted ghost opponent, training dummy, or scripted loss? This is the only blocker with an open design gate.

`2026-04-29 11:30:00 +01:00`

- State sync after v0.13.4 release: CutsceneManager Phase 2 has shipped, and this document remains the active implementation plan.
- Current implementation lane remains `P0-10`: G0 signoff playtest pack, controls/readability traceability, blocker triage, and evidence-backed handoff to P1.
- v0.13.5 scope is intentionally narrow: collect 5 first-session G0 records, fix only G0 blockers, update `ROADMAP.md` only if evidence supports closing the G0 checkbox, then release.
- Do not start `P1-01` data-driven tuning until P0-10 is closed or explicitly accepted as blocked with owner/date.

`2026-04-24 00:13:12 +01:00`

- `v0.12.06` release loop completion (`ITERATION_RELEASE_PROTOCOL` step 7/8/9 closure).
  - Pushed release-prep commits `1a23671` and `0433a6e` to `master`.
  - Created/pushed annotated tag `v0.12.06`.
  - Verified `CI` success on `0433a6e` (`run_id=24863406100`).
  - Verified tag-triggered `Release` success for `v0.12.06` (`run_id=24863406970`).
  - Verified published assets include docs archive ZIP + `ninja-client-all.jar` + `ninja-server-all.jar`.
- Validation evidence:
  - `python tools/check_version_sync.py --tag v0.12.06` ✅
  - `python tools/check_docs_freshness.py --emit-report` ✅
  - `./gradlew :server:test :client:test --no-daemon` ✅
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` ✅
  - `gh run list --limit 6 --json status,conclusion,name,headSha,displayTitle,event` ✅
  - `gh release view v0.12.06 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets,url` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-23 14:42:16 +01:00`

- `v0.12.05` release loop completion (`ITERATION_RELEASE_PROTOCOL` step 7/8/9 closure).
  - Pushed release commit `6fdddbf` to `master`.
  - Waited for `CI` success on `6fdddbf` before tagging (`run_id=24838332894`).
  - Created/pushed annotated tag `v0.12.05`.
  - Verified tag-triggered `Release` success (`run_id=24838474542`).
  - Verified published assets include docs archive ZIP + `ninja-client-all.jar` + `ninja-server-all.jar`.
- Validation evidence:
  - `gh run list --limit 8 --json status,conclusion,name,headSha,displayTitle,event` ✅
  - `gh release view v0.12.05 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets,url` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-23 14:32:35 +01:00`

- `v0.12.05` release-prep loop (`ITERATION_RELEASE_PROTOCOL` steps 2-4).
  - Continued cleanup lane with minimap hot-path churn reductions and preserved runtime behavior.
  - Synced release parity docs and metadata targets to `v0.12.05`:
    - `version.json`
    - `java/build.gradle.kts`
    - `README.md`
    - `docs/ROADMAP.md`
    - `docs/CHANGELOG.md`
  - Executed release-grade local gates:
    - `./gradlew :server:test :client:test --no-daemon` ✅
    - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` ✅

`2026-04-23 09:45:01 +01:00`

- `v0.12.04` release loop completion (`ITERATION_RELEASE_PROTOCOL` step 8/9 closure).
  - Pushed final release commit `2044b0d` to `master`.
  - Created/pushed annotated tag `v0.12.04`.
  - Verified `CI` success on `2044b0d` (`run_id=24824540532`) before tag publication.
  - Verified tag-triggered `Release` success for `v0.12.04` (`run_id=24825590863`).
  - Verified published assets include docs archive ZIP + `ninja-client-all.jar` + `ninja-server-all.jar`.
- Validation evidence:
  - `gh run list --limit 3 --json status,conclusion,name,headSha` ✅
  - `gh release view v0.12.04 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-23 09:10:21 +01:00`

- `v0.12.04` release-loop metadata sync and gate pass (`ITERATION_RELEASE_PROTOCOL` step 8 prep).
  - Release parity targets updated to `v0.12.04`: `version.json`, `java/build.gradle.kts`, `README.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`.
  - Active plan + current-state anchors updated for `v0.12.04` baseline continuity.
- Validation:
  - `python tools/check_version_sync.py --tag v0.12.04` ✅
  - `python tools/check_docs_freshness.py --emit-report` ✅
  - `./gradlew :server:test :client:test --no-daemon` ✅
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-23 08:36:53 +01:00`

- `v0.12.04` stabilization slice 6: mission-return portal-travel contract lifecycle hardening for hosted mission pickup correctness.
  - `ServerProtocolHandler.handlePortalTravel(...)` now detects `transition_type=mission_return`, clears mission pickup seed contracts for the travelling player, and skips destination reseed queuing for that travel type.
  - This prevents mission-return path stale-contract carry-over and avoids reseeding mission pickups into return hubs.
- Added regression coverage:
  - `ServerProtocolHandlerMissionPickupSeedTest.missionReturnTravelClearsContractsAndSkipsDestinationReseed`.
- Validation:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` ✅
  - `python tools/check_version_sync.py` ✅
  - `python tools/check_docs_freshness.py --emit-report` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-23 08:10:34 +01:00`

- `v0.12.04` stabilization slice 5: mission-switch/abandon contract lifecycle hardening for hosted mission pickup correctness.
  - `GameScreen.startMissionFlow(...)` now clears any prior multiplayer mission pickup seed contract before starting the next mission (`mission_switch_start` / `mission_restart`).
  - `ServerProtocolHandler.clearMissionPickupSeedContract(...)` is now mission-aware and ignores stale clear events when `mission_id` does not match the currently stored contract.
  - This prevents cross-mission carry-over in consecutive mission starts while preserving rejoin reseed for the latest mission contract.
- Added regression coverage:
  - `ServerProtocolHandlerMissionPickupSeedTest.missionSwitchAToBRejoinReseedsMissionBContract`.
- Validation:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-23 07:45:21 +01:00`

- `v0.12.04` stabilization slice 4: disconnect-path contract clearing for mission pickup lifecycle correctness.
  - `ServerProtocolHandler.handleDisconnect(...)` now clears stale mission pickup seed contracts while retaining the player's current-hub contract.
  - Prevents stale cross-hub contract carry-over without breaking reconnect/late-join mission pickup reseed convergence for the active hub.
- Added regression coverage:
  - `ServerProtocolHandlerMissionPickupSeedTest.disconnectKeepsCurrentHubContractAndClearsStaleContractsForPlayer`.
  - `ServerProtocolHandlerMissionPickupSeedTest.disconnectKeepsCurrentHubContractAvailableForRejoinReseed`.
- Validation:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-22 22:03:12 +01:00`

- `v0.12.04` stabilization slice 3: mission-end contract clearing for hosted pickup lifecycle correctness.
  - Client now emits `entity_event` `mission_seed_pickups_clear` on mission complete/fail callbacks.
  - Server now handles `mission_seed_pickups_clear` by removing the per-player zone contract, preventing stale late-join reseeds after mission end.
  - Existing slice-2 late-join reconcile remains active for in-progress missions.
- Added regression coverage:
  - `ServerProtocolHandlerMissionPickupSeedTest.missionPickupSeedClearEventPreventsLateJoinReseed`.
- Validation target:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon`
- Compatibility classification (expected):
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-22 21:24:31 +01:00`

- `v0.12.04` stabilization slice 2: late-join/rejoin mission-pickup reconcile and no-dup top-up seeding.
  - `ServerProtocolHandler` now persists latest mission pickup seed contracts per `player_id + zone_id`.
  - `bootstrapLateJoiner(...)` now queues a server-authoritative mission pickup reseed request when a contract exists (no client re-send required).
  - `handlePortalTravel(...)` now clears stale source-zone mission seed contracts and queues reconcile requests for destination zones when applicable.
  - `ZoneSimulationLoop.seedMissionObjectivePickups(...)` now reconciles using existing alive scoped pickups plus owner inventory count, spawning only missing supply instead of duplicating full requested counts.
- Added regression coverage:
  - `ServerProtocolHandlerMissionPickupSeedTest.bootstrapLateJoinerQueuesMissionPickupReseedWhenContractExists`.
- Validation:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

### v0.12.04 Implementation Brief (Mission Pickup Lifecycle / No-Despawn)

- goal: harden authoritative mission-pickup lifecycle so mission-critical pickups do not silently disappear from late-join/reconnect views.
- player-facing impact: hosted co-op mission item state converges faster for joiners/rejoiners; fewer stale/ghost pickup windows.
- systems touched: `ZoneSimulationLoop` mission pickup lifecycle + snapshot forcing; server mission pickup regression tests.
- risks: excessive forced full snapshots if mission-pickup change detection is noisy.
- required tests:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon`
- required docs to update:
  - `docs/CURRENT_STATE.md`
  - `docs/plans/implementing/PLAN_SHADOW_ASCENT.md`
- rollback plan: revert mission-pickup snapshot forcing hook in `ZoneSimulationLoop` and its new regression case; keep prior owner-scoping behavior intact.

`2026-04-22 20:32:40 +01:00`

- `v0.12.04` stabilization slice 1: mission-scoped pickup lifecycle sync hardening for hosted multiplayer + late-join convergence.
  - Added mission-scoped pickup hash tracking in `ZoneSimulationLoop` and now force `zone.forceNextFullSnapshot` when mission-scoped pickup state changes (seeded or collected).
  - This tightens cache/broadcast convergence so late joiners do not wait for periodic full-snapshot cadence after mission pickup lifecycle transitions.
- Added regression coverage:
  - `ZoneSimulationLoopScriptedLossOrderingTest.missionScopedPickupSeedAndCollectionForceNextFullSnapshot`.
- Validation:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-22 18:44:56 +01:00`

- `v0.12.03` stabilization slice: mission-seeded pickup ownership hardening for hosted multiplayer.
  - Added mission-owner scoping on `SimPickup` (`missionOwnerSlot`) so mission-seeded objective pickups are collectible only by the requesting player slot.
  - `GameSimulator.stepPickups()` now enforces ownership gating before collection to prevent non-owner pickup consumption/despawn.
  - `ZoneSimulationLoop.seedMissionObjectivePickups(...)` now uses `addPersistentPickupForPlayer(...)` so authoritative mission seeds are owner-scoped by default.
- Added regression coverage:
  - `ZoneSimulationLoopScriptedLossOrderingTest` now verifies mission-seeded pickups carry owner-slot scoping and cannot be consumed by other players.
- Validation:
  - `./gradlew :server:test` ✅
- Compatibility classification:
  - replay=`no`, save=`no`, protocol=`no`.

`2026-04-22 17:25:00 +01:00`

- Release loop execution for `v0.12.02` (docs/workflow closure + release metadata sync):
  - Updated release-sync canonical files: `version.json`, `java/build.gradle.kts`, `README.md`, `docs/ROADMAP.md`, `docs/CURRENT_STATE.md`, `docs/CHANGELOG.md`.
  - Refreshed docs freshness evidence report for current release anchor.
- Validation:
  - `C:\Users\asher\AppData\Local\Programs\Python\Python312\python.exe tools/check_version_sync.py --tag v0.12.02` ✅
  - `C:\Users\asher\AppData\Local\Programs\Python\Python312\python.exe tools/check_docs_freshness.py --emit-report` ✅
  - `./gradlew :server:test :client:test --no-daemon` with local `GRADLE_USER_HOME` ✅
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` with local `GRADLE_USER_HOME` + Python312 on `PATH` ✅

`2026-04-22 09:20:00 +01:00`

- Multiplayer mission objective pickup hard guarantee (v0.12.01):
  - Client now emits `entity_event` `mission_seed_pickups` when a mission starts in multiplayer-hosted runs.
  - Server queues seed requests on `ZoneInstance.pendingMissionPickupSeeds` from the Netty thread and applies them on the authoritative sim thread in `ZoneSimulationLoop`.
  - Request-id dedupe now prevents duplicate seed bursts on retries/replays.
  - Seeded mission pickups are restricted to persistent `quest_item`/`key_*` types; coin and non-objective entries are ignored.
- Solo mission objective seeding remains active and now shares the same objective item-count extraction path used by multiplayer requests.
- Validation:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest` ✅
  - `./gradlew :client:test --tests com.indieniinja.client.game.MissionAuthoringProgressionCoverageTest` ✅

`2026-04-18 14:00:00 +01:00`

- Playtest blocker fixes (v0.11.65):
  - **[P0] Portal travel**: start-room portals removed from `LevelLayout` (exit-rooms only). Render-loop race condition fixed — `pollZoneTransition()` now calls `refreshSoloWorldRoomCache()` + `camera.snapTo()` after clearing the megamap. Portal travel is stable.
  - **[P1] Stance animation**: `EntityRenderer` now uses `hasAnyWithPrefix("player_sword_")` for Yang — all locomotion states (idle/walk/jump/crouch) display armed posture when sword sheets are registered. `AnimationRegistry.hasAnyWithPrefix()` added.
  - **[P1] Spurious ability toasts**: `handleSoloPortalTravel()` now restores `prevLocalAbilities` from `snapAbilities` before zone transition so no spurious "new unlock" toasts appear after portal travel.
  - **[P2] Mode select**: Sandbox retired, CAMPAIGN maps to "solo" ID (spawns world), DEVELOPER replaces old solo card. All hardcoded card-count references updated to `MODE_COUNT = 3`.
  - **[P3] F9 debug ability toggle**: solo mode only — cycles all abilities granted/cleared; HUD toast feedback; no effect in multiplayer.
- Validation: `./gradlew buildAll test` — BUILD SUCCESSFUL, all tests green.
- Docs updated: `CHANGELOG.md`, `CURRENT_STATE.md`, `README.md`, `version.json`, `build.gradle.kts`.

`2026-04-18 12:00:00 +01:00`

- Solo/multiplayer campaign unification (v0.11.64):
  - **Portal unification**: `GameScreen.handleSoloPortalTravel()` replaced. Solo portal travel now applies the same ability-gate + zone-migration logic as `ServerProtocolHandler.handlePortalTravel()`. Player state (health, level, xp, currency, inventory, abilities) is snapshotted, hub seed derived via `HubRegistry.hubSeed()`, simulation re-initialised for destination hub, state restored. `stateBuffer.resetForZoneTransition()` triggers megamap rebuild. Save marked dirty on travel.
  - **Hub ID threading**: `initializeSoloSimulation()` 5-param overload added; `localSim.hubId` is now correct per hub for save/restore and zone tracking.
  - **Versus/race mode**: Registered as backlog idea `P1-11` (concept only, no implementation).
  - **Test added**: `SoloPortalTravelTest` — ability gate denial, open-hub entry, player state preservation, hub seed uniqueness.
- Animation posture readability pass (same release):
  - **Task A — Yin/Yang sprite prefix routing**: `EntityRenderer.renderPlayer()` routes from `stanceMode` (GDD §3.3).
  - **Task C — Minimap compass**: Pass 5d directional arrows + waypoint diamond POI.
  - **Task B — Combo system (backlog only)**: `P1-03B` registered, no implementation.
- Docs updated: `CHANGELOG.md`, `CURRENT_STATE.md`, plan loop note.
- Validation: `./gradlew test` — BUILD SUCCESSFUL.

`2026-04-18 00:00:00 +01:00`

- Animation posture readability pass (v0.11.64 prep):
  - **Task A — Yin/Yang sprite prefix routing**: `EntityRenderer.renderPlayer()` now routes animation key prefix from `stanceMode` (GDD §3.3 identity signal) instead of `weaponState` alone. Yin always renders unarmed prefix; Yang or unset renders sword prefix when sheets registered; pistol path unchanged. Client re-enforces the server-side stance lock so offline/desync players also read correctly.
  - **Task C — Minimap compass edge indicators**: `MinimapRenderer.render()` new Pass 5d: directional triangle arrows appear on minimap panel border when an active objective's room is outside the current zoom window. Arrows are colour-coded per marker type (reach=gold, switch=red, exit=cyan). Waypoint POI type added (diamond shape) to ObjectiveMarker Pass 4.
  - **Task B — Combo system (backlog only)**: 5-hit combo chains registered as `P1-03B` in plan. Assets are in `AnimationRegistry` (all slash/punch/kick keys loaded). No implementation started — `COMPATIBILITY_AND_MIGRATION_WORKFLOW` pre-flight required before any code change (InputCommand + SimPlayer + replay risk).
- Docs updated: `CHANGELOG.md`, `CURRENT_STATE.md`, plan loop note.
- Validation:
  - `./gradlew :client:compileJava` — BUILD SUCCESSFUL

`2026-04-15 21:11:43 +01:00`

- Closed the `v0.11.48` release workflow end to end after the NPC/map usability fix pass:
  - verified remote `CI` success on `master` (`run_id=24475744315`)
  - verified remote `Release` success on tag `v0.11.48` (`run_id=24475751960`)
  - verified published release assets include:
    - `ninja_dash.exe`
    - `ninja_dash_launcher.exe`
    - `ninja-client-all.jar`
    - `ninja-server-all.jar`
    - `docs-archive-2026-04-15-v0.11.48.zip`
- Plan status impact:
  - M8 polish evidence pass remains in-progress but now includes closed runtime baselines for NPC scale/hitbox parity and map tap/hold readability.
  - next implementation target remains `v0.11.49` onboarding/system-guidance follow-up under `P0-10`.

`2026-04-15 21:10:00 +01:00`

- Completed P0 playtest usability fix pass for solo launcher runs:
  - NPC runtime dimensions normalized to `48x72` across simulation spawn paths and wire payloads (`NPCState.width/height`) so rendered NPC scale and debug hitboxes no longer depend on stale `32x48` client constants.
  - client NPC rendering and hitbox overlay now read authoritative `NPCState.width/height` values instead of hardcoded dimensions.
  - map input behavior hardened to explicit GDD-intended split:
    - `Tab` tap = quick-map toggle
    - `Tab` hold (>=280 ms) = full-map mode while held, closes on key release
  - minimap now surfaces explicit key/mode guidance text so first-run players can understand quick vs full-map paths without external instruction.
- Added regression coverage:
  - `NPCStateTest` verifies width/height roundtrip and legacy-map default fallback behavior.
- Validation:
  - `./gradlew :client:compileJava :core:compileJava :server:compileJava --no-daemon` ✅

`2026-04-15 18:48:00 +01:00`

- Fresh-test onboarding blocker resolved for `demo_coin_run`:
  - mission `collect_items: coin` now progresses from `inventory.currency` deltas in `GameScreen.tickMissionProgress(...)`.
  - added inventory/currency baseline seeding so first snapshot after load/rebuild does not miscount historical totals as newly collected items.
- Added regression coverage:
  - `GameScreenSaveRestoreTest.tickMissionProgressCountsCurrencyGainAsCoinObjectiveProgress`.
- Release loop alignment for this patch:
  - preparing `v0.11.47` parity/docs updates and CI post-push stability by restoring Black formatting compliance for known failing files.

`2026-04-15 17:38:02 +01:00`

- Launcher pass aligned to canonical release naming + live playtest contract distribution:
  - launcher branding now uses `Shadow Ascent: The Hollowed Ninja` as primary window/splash title.
  - internal codename retained as secondary caption (`Code name: Indie Ninja Adventures`) for dev/internal continuity.
  - launcher version bumped to `v1.8.0`.
  - launcher update/install workers now sync `docs/PLAYER_EXPECTATIONS.md` from the selected release tag and replace local live copy.
- Workflow gates executed per `docs/workflow` before release cut:
  - `python run_tests.py` ✅
  - `python tools/check_docs_freshness.py --emit-report` ✅
  - `python tools/check_version_sync.py` ✅

`2026-04-15 17:01:30 +01:00`

- Documentation cleanup and freshness pipeline reset executed in a dedicated implementation loop:
  - moved active plan files into `docs/plans/{developing,implementing,completed}` with normalized plan statuses
  - created canonical `docs/CURRENT_STATE.md`; converted `docs/HANDOVER.md` to redirect; split devlog to rolling `docs/devlog/YYYY-MM.md`
  - retired first-wave stale docs into `docs/archive/retired/2026-04-15_v0.11.45/` with manifest
  - introduced freshness/reporting automation:
    - `tools/check_docs_freshness.py` (`--strict`, `--emit-report`, `--version`)
    - `tools/build_docs_archive_zip.py` and generated `docs/archive/zips/docs-archive-2026-04-15-v0.11.45.zip`
  - updated workflow/process contracts:
    - CI soft gate and report artifact (`.github/workflows/ci.yml`)
    - scheduled/manual docs audit workflow (`.github/workflows/docs_freshness_audit.yml`)
    - release docs-archive ZIP asset publish path (`.github/workflows/release.yml`)
    - PR template contract now includes `docs_impact`, `plan_id`, `archive_action`
- Validation:
  - `.\\.venv\\Scripts\\python.exe tools/check_version_sync.py` ✅
  - `.\\.venv\\Scripts\\python.exe tools/check_docs_freshness.py --emit-report --strict` ✅

`2026-04-15 15:47:50 +01:00`

- Executed milestone bundle pass (`M5 close-out + M8 playtest logging/controls evidence + M6 authored trigger slice`):
  - `M5`: immediate boss-defeat runtime queue now drains in `ZoneSimulationLoop.simulateTick()` and applies `HubStateMachine.onBossDefeated(...)` in the same tick.
  - `M5`: client scripted-loss receive path now applies local collapse readability state (`collapse` with renderer fallback to death sheets when needed).
  - `M6`: added authored `ECHO_TRIGGER` puzzle type, planner allocation/fallback, post-process stamping, unified layout spawn mapping, and runtime interact behavior (`echo_trigger_<pid>` unlocks `echo_door_<pid>` + spawns echo).
  - `M8`: added playtest evidence logs for controls preset signature and mission lifecycle (`start/progress/exit-unlock/complete/fail/restore`).
- Added regression coverage:
  - `GameSimulatorScriptedLossSignalTest.pendingBossDefeatIdsDrainIsSingleUseAfterLootSpawn`
  - `ZoneSimulationLoopScriptedLossOrderingTest.immediateBossDefeatQueueAdvancesHubStateInSameTick`
  - `WorldGraphTest.puzzlePlanAlwaysIncludesEchoTriggerAndMapsToInteractableNpcSpawn`
- Validation:
  - `./gradlew :server:test` âœ…
  - `./gradlew :client:compileJava` âœ…

`2026-04-15 14:47:10 +01:00`

- Completed release execution for the logging hardening pass:
  - pushed `master` commit `1360aa9` (`plan_id=P0-10 scope=logging-hardening+release-sync reason=playtest-traceability risk=low`)
  - cut + pushed tag `v0.11.44`
  - published release `v0.11.44`: https://github.com/VainAsher/indie-ninja-adventures/releases/tag/v0.11.44
- Remote CI monitoring results:
  - `CI` on `master` passed (`24457896928`)
  - `Release` on `v0.11.44` passed (`24457935321`)
- Noted non-blocking workflow warnings to backlog:
  - Node 20 action deprecation notices in release workflow
  - Gradle cache save/restore service outages during run
  - launcher-repo notify step annotation (`Parameter token or opts.auth is required`) despite overall green run

`2026-04-15 14:37:00 +01:00`

- Completed dedicated playtest logging hardening pass across client/core/server:
  - added client/server session correlation via `session_id` wire field on `CLIENT_HELLO` + `SERVER_HELLO`
  - server join/travel/disconnect logs now include `player_id` + `session_id` for end-to-end traceability
  - added low-noise runtime transition logs:
    - `[Playtest][Stance]`
    - `[Playtest][Flow]`
    - `[Playtest][Lantern]`
    - `[Playtest][Room]`
    - `[Playtest][Boss]`
    - `[Playtest][Player]`
  - dialogue event processing now logs key/arg/count for onboarding and authored mission handoff traces
- Validation:
  - `./gradlew :server:test` âœ…
  - `./gradlew :client:compileJava` âœ…
- Documentation alignment:
  - updated `PLAYER_EXPECTATIONS.md` instrumentation audit to reflect session-correlation and transition tracing
  - updated `GDD.md` with runtime observability contract (`10.4`)

`2026-04-15 14:06:38 +01:00`

- Completed release recovery and metadata parity closure for the Siren onboarding asset pass:
  - pushed `master` with Siren-first onboarding/dialogue/asset integration
  - cut and pushed tags `v0.11.42` then `v0.11.43`
  - resolved release gate mismatch by syncing version metadata in:
    - `version.json`
    - `java/build.gradle.kts`
    - `README.md`
    - `docs/ROADMAP.md`
    - `docs/CHANGELOG.md`
- Remote CI status:
  - `Release` workflow for `v0.11.43` passed (`24455868898`)
  - `CI` workflow on `master` passed (`24455833128`)
- Documentation alignment pass completed:
  - updated plan metadata and loop trail to `v0.11.43`
  - updated `PLAYER_EXPECTATIONS.md` controls/onboarding guidance to current runtime
  - updated `GDD.md` onboarding + mission-scale + lantern/Flow alignment notes

`2026-04-15 04:36:18 +01:00`

- Imported provided placeholder art into the client resource tree:
  - generated NPC `idle_spritesheet.png` / `walk_spritesheet.png` for:
    - `lore`, `shop`, `mission_giver`, `tutorial`
  - generated `siren_phase1..4` NPC idle/walk sheets from `veiled_siren_phases_transparent.png`
  - copied Siren boss phase source to `assets/sprites/bosses/siren/phases_spritesheet.png`
- Extended runtime loading/rendering to consume the imported boss art:
  - added `AnimationRegistry.loadBossSprites(...)` with `boss_siren_phase1..4` keys
  - client startup now loads boss sprites from `assets/sprites/bosses`
  - boss renderer now uses phase-specific keys for Siren (`boss_siren_phase{n}`) instead of AI-state placeholders
- Result:
  - Siren NPC onboarding chain now has authored phase visuals
  - Siren boss now renders authored placeholder phase art directly per phase state

`2026-04-15 04:22:10 +01:00`

- Implemented Siren-first quest-giver pass (onboarding chain + mission handoff + phase readability):
  - START-room required quest-giver now spawns as `siren` (SHOP retains `mission_giver`)
  - added dedicated Siren onboarding dialogue tree (`siren_first_quest`) with direct handoff events:
    - `siren_start_first_trial` â†’ starts `demo_coin_run`
    - `siren_open_mission_board` â†’ opens mission board overlay
  - dialogue state flags added for repeat-pass behavior:
    - `siren_intro_seen`
    - `siren_onboarding_complete`
- Implemented Siren phase sprite routing support:
  - NPC animation registry now loads/aliases `siren_phase1..4` keys
  - runtime render mapping now resolves `siren` by hub state:
    - `FULL` â†’ `siren_phase1`
    - `CORRUPTED` â†’ `siren_phase2`
    - `EMPTY` â†’ `siren_phase3`
  - phase-4 keys are registered for transformation path wiring in follow-up boss-transition work
- Feel-first impact note:
  - Affects Passive/Aggressive onboarding readability equally (quest entry clarity)
  - Improves Flow readability indirectly by ensuring stance/mission onboarding is delivered by one canonical NPC path in Act I

`2026-04-15 03:48:50 +01:00`

- Implemented mission onboarding and objective readability hardening pass:
  - added direct mission board hotkey (`O`) for discoverability without dialogue dependency
  - added persistent mission tracker panel in HUD (objective checklist + timer + exit lock state)
  - added onboarding toasts for first-session guidance (`F1` controls, `O` mission board, objective/minimap cues)
- Implemented mission world-scaling bridge for solo campaign starts:
  - unified mission start flow (`overlay` + `dialogue_event`) through `startMissionFlow(...)`
  - solo mission starts now regenerate world using mission-authored shape and act-aware room-count clamps:
    - Act I/II: clamp to `4..9` rooms
    - Act III+: clamp to `12..60` rooms
- Implemented mission affordance visibility upgrades:
  - minimap now renders active objective markers (reach/switch/exit) from mission contact volumes
  - tile detail now defaults ON for clearer zoom/readability behavior
- Implemented gameplay feedback fixes:
  - guaranteed `mission_giver` NPC spawn in START/SHOP onboarding rooms
  - slime-family facing corrected via enemy-type sprite orientation override
  - Flow now restores Lantern over time (`FLOW_LANTERN_RESTORE_PER_SECOND`) as an additional recharge avenue
  - tutorial dialogue key prompts updated to current control scheme
- Validation:
  - `./gradlew :client:compileJava` âœ…
  - `./gradlew :server:test` âœ…

`2026-04-13 22:41:01 +01:00`

- Implemented enemy/platform reliability pass:
  - one-way platform landing regression fix for stacked platform/terrain layouts
  - enemy AI now updates before physics tick so horizontal intent is collision-resolved same frame
  - archer kiting/range-reposition behavior tuned to avoid melee-style pressure
  - skeleton shield bearer now uses directional guard checks and retreating guard posture
- Implemented first-boss rewrite baseline:
  - Siren now runs a 3-phase combat pattern (ranged -> ranged+teleport -> volley bursts)
  - phase-based red-slime add waves (`slime_red`) spawn within boss-room bounds
  - boss-room confinement clamp added for boss movement
  - scripted-loss message now broadcasts end-to-end (sim -> server -> client) with continue-overlay handling
- Follow-up required in next loop:
  - finalize slime wall-crawl behavior (all-side surface traversal) as dedicated movement system
  - tune Siren vulnerability window and add-wave pacing via playtest metrics

`2026-04-13 23:17:46 +01:00`

- P0 workloop audit pass completed against current GDD + code:
  - confirmed `P0-06` scripted-loss pipeline is fully wired in sim/server/client flow
  - identified objective-system drift: only kill/boss hooks were wired at runtime
- Implemented `P0-01` build baseline quality-of-life closure:
  - added repo-root Gradle wrappers (`gradlew`, `gradlew.bat`) delegating to `java/gradlew`
  - validated root command path: `./gradlew.bat test` and `./gradlew.bat :server:test :client:compileJava`
- Implemented `P0-02` objective-normalization pass (partial integration closure):
  - normalized objective key handling (case-insensitive) in `MissionManager`
  - fixed objective requirement bug: `activate_switches` now honors `count` (with `target` fallback)
  - added runtime adapters (`onEnemyKilled`, `onBossDefeated`, `onItemCollected`, `onSwitchActivated`, `onReachLocation`)
  - wired `GameScreen` inventory-diff tracking to feed `collect_items` objective progress
- Implemented `P0-04` dialogue-event routing hardening:
  - removed silent drops by handling all currently-authored dialogue events
  - unknown dialogue events now emit telemetry and are persisted as story flags
- Follow-up required in next loop:
  - define canonical runtime sources for `reach_location` and `activate_switches` mission objectives
  - add objective coverage tests for mixed missions (collect/reach/switch/time)

`2026-04-13 23:38:32 +01:00`

- Applied user decisions for mission flow and objective semantics:
  - `reach_location` now uses explicit contact-volume IDs (portal and falling-platform derived volumes)
  - `activate_switches` now only counts mission-tagged activations (`<missionId>:<switchId>`)
  - mission completion now happens on exit-contact after objectives unlock (not immediately on objective completion)
  - `open_mission_menu` now opens a dedicated mission-select overlay
- Implemented `P0-03` mission lifecycle wiring (partial):
  - portal interaction blocks mission exit when objectives are incomplete
  - exit contact completes active mission and then allows portal travel
  - mission progress state reset/cleanup handled on mission start/complete and room transitions
- Implemented `P0-02` reach/switch integration expansion:
  - `MissionManager.onSwitchActivated` enforces current mission tag contract
  - `GameScreen` emits mission-tagged switch events when interacting with `btn_` / `lever_` NPCs
  - contact-volume trigger system resolves `reach_location` objectives via explicit IDs, with temporary exit-volume alias fallback when no authored volume exists
- Implemented dedicated mission selection UI:
  - new `MissionSelectOverlay` with navigation and mission start callbacks
  - dialogue event `open_mission_menu` now opens the overlay and suspends conflicting overlays
- Validation:
  - `./gradlew.bat test` âœ…
  - `./gradlew.bat :server:test :client:compileJava` âœ…
- Follow-up required in next loop:
  - remove temporary `reach_location` exit-alias fallback once authored location volume maps are present per mission
  - add automated objective lifecycle tests (reach/switch/exit-complete)

`2026-04-14 03:07:54 +01:00`

- Implemented `P0-02` / `P0-03` follow-up closure for mission objective runtime mapping:
  - added authoritative authored trigger map file: `data/mission_location_triggers.json`
  - added `MissionLocationTriggerRegistry` and wired `GameScreen` to load mission/location keyed trigger defs
  - removed temporary `reach_location` fallback alias to mission exit volume
  - added runtime snapping/clamping for authored trigger volumes to reachable in-room ground cells
  - validated trigger coverage: `15/15` `reach_location` objectives mapped (`missing=0`)
- Added objective lifecycle regression tests scaffold:
  - `MissionManager` now supports injected definitions via test-friendly constructor
  - new `MissionManagerObjectiveLifecycleTest` covers:
    - mission-tagged `activate_switches` contract
    - `reach_location` + switch completion unlocking exit
    - explicit completion call requirement after objective unlock
- Validation:
  - `./gradlew :server:test` pass
  - `./gradlew :client:compileJava` pass
  - `./gradlew :client:test --tests "*MissionManagerObjectiveLifecycleTest"` blocked in this environment by Gradle cache file lock (`gdx-jnigen-loader-2.3.1.jar` access denied)
- Next loop:
  - stabilize client test cache path for reliable `:client:test` execution in CI/local
  - continue `P0-05` save/load parity hardening after objective lifecycle suite expands

`2026-04-14 03:19:52 +01:00`

- Implemented `P0-05` save/load parity hardening pass (phase 1):
  - `MissionManager` now supports restore of full mission states plus active mission id/timer/objective progress
  - `SaveData` now persists/rehydrates full story snapshot booleans (`veil_maiden_defeated_*`, `yin_yang_present`) and active-mission objective progress
  - `StoryManager.restoreSnapshot(...)` added to restore saved story internals deterministically (act + legacy condition fields + flags)
  - fixed story-act migration clamp to use full act range (`0..6`) instead of truncating to `0..4`
  - `SaveManager` now deep-copies loaded save into `liveData` and writes saves from `liveData` baseline overlaid with fresh manager-owned state
  - added pre-save sync hook; `GameScreen` wires `syncSaveState()` into every save path (including auto-save)
- Added regression tests for this loop:
  - `SaveDataParityTest` (story snapshot + active mission restore behavior)
  - `SaveManagerMigrationTest` (act clamp bounds)
- Validation:
  - `./gradlew :server:test :client:compileJava` âœ…
  - `./gradlew :client:test --tests "*SaveDataParityTest" --tests "*SaveManagerMigrationTest"` blocked by existing local Gradle cache lock (`gdx-jnigen-loader-2.3.1.jar` access denied)
- Next loop:
  - close remaining `P0-05` parity gaps around full runtime world/player rehydrate-on-load behavior
  - stabilize local client-test cache path to unblock `:client:test` regression execution

`2026-04-14 03:35:37 +01:00`

- Continued `P0-05` runtime rehydrate implementation in `GameScreen`:
  - extracted solo bootstrapping into `initializeSoloSimulation(...)`
  - added `restoreSoloRuntimeStateFromSave()` to:
    - reinitialize solo world from saved `worldSeed` when present
    - restore visited room fog state (`visitedRoomKeys`)
    - restore solo player inventory/equipment/abilities and saved hub position
    - rebuild active mission reach-location one-shot cache from restored objective progress
  - added save-context refresh after load (`dialogueManager.setStoryContext(...)`) so restored story flags are active immediately
  - expanded `syncSaveState()` to persist `currentHubId/currentHubX/currentHubY` and fallback world seed from snapshots
- Added mission restore regression coverage:
  - `MissionManagerObjectiveLifecycleTest.restoreActiveMissionRestoresObjectiveProgressAndExitLock`
- Validation:
  - `./gradlew :server:test :client:compileJava` âœ…
  - targeted `:client:test` remains blocked in this environment (same local cache lock on `gdx-jnigen-loader`; compileTest then fails symbol resolution)
- Next loop:
  - continue `P0-05` with direct save/load roundtrip harness assertions for `SaveManager` liveData overlay path
  - either isolate `:client:test` dependency/cache issue or run client test stage in CI-only validation mode

`2026-04-14 04:22:46 +01:00`

- Started `P0-07` mission/item contract normalization pass:
  - normalized mission boss IDs in `data/missions.json` to canonical lowercase snake_case wire format
  - aligned `tests/test_data_integrity.py` boss validation to the real authored contract surface:
    - legacy boss wires from `entities/boss.py`
    - campaign boss IDs from `entities/boss_manager.py` normalized via enum name
  - added explicit lowercase-canonical assertion for mission boss objective IDs to prevent future case drift
- Validation:
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass
  - `./gradlew :server:test :client:compileJava --console=plain --no-daemon` pass
- Next loop:
  - continue `P0-07` by adding explicit runtime-boss compatibility validation so authored mission boss objectives cannot target non-emitted boss wires silently
  - begin `P0-08` version source-of-truth consolidation once P0-07 validation coverage is complete

`2026-04-14 07:25:41 +01:00`

- Reassessed P0 execution order for current pivot:
  - prioritized completion of `P0-07` runtime contract safety before further system expansion
  - kept `P0-05` marked in-progress, but moved immediate next critical gate to release metadata parity (`P0-08`)
- Completed remaining `P0-07` runtime compatibility check:
  - extended Java runtime boss wire catalog in `java/core/.../BossType.java` to include campaign-authored boss IDs used by mission objectives
  - added explicit data-integrity gate in `tests/test_data_integrity.py` that parses Java runtime boss wires and fails if mission `defeat_boss` objectives (or mission-level `boss`) target non-emitted IDs
- Validation:
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass (`test_mission_boss_ids_runtime_compatible` added)
  - `./gradlew :server:test :client:compileJava --console=plain --no-daemon` pass
- Next loop:
  - start `P0-08` version/document source-of-truth consolidation (`version.json`, tag policy, release metadata sync)
  - keep `P0-05` stabilization items queued behind release metadata parity closure

`2026-04-14 07:34:53 +01:00`

- Completed `P0-08` version/document source-of-truth consolidation:
  - added `tools/check_version_sync.py` with `version.json` as authoritative source
  - validator now checks parity across:
    - `version.json`
    - `java/build.gradle.kts`
    - `README.md` version banner
    - `docs/ROADMAP.md` metadata line
    - latest `docs/CHANGELOG.md` heading
  - added release parity checklist: `docs/RELEASE_VERSION_SYNC_CHECKLIST.md`
  - wired sync check into CI (`.github/workflows/ci.yml`)
  - replaced release metadata inline checks with validator call in `.github/workflows/release.yml`
  - refreshed release docs metadata to `0.11.34` (`README.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`)
- Validation:
  - `python tools/check_version_sync.py` pass
  - `python tools/check_version_sync.py --tag v0.11.34` pass
  - `./gradlew :server:test :client:compileJava --console=plain --no-daemon` pass
- Next loop:
  - start `P0-09` critical integration test suite expansion for campaign loop
  - continue residual `P0-05` client test-path stabilization in parallel with integration coverage

`2026-04-14 17:10:17 +01:00`

- Continued `P0-09` critical campaign integration-suite expansion:
  - added `CampaignCriticalFlowTest` for mission start/progress/save-load/complete coverage across objective adapters (`activate_switches`, `reach_location`, `collect_items`, `kill_all_enemies`, `defeat_boss`, `time_challenge`)
  - added `ScriptedLossMessageFlowTest` for client network scripted-loss message handling (`NetworkClientThread` -> `GameStateBuffer`) and one-shot consume behavior
  - added `GameSimulatorScriptedLossSignalTest` for scripted-loss one-shot drain contract in Java sim
- Continued `P0-04` dialogue parity hardening:
  - expanded `tests/test_data_integrity.py` with dialogue-event contract checks:
    - authored event keys must map to supported runtime router keys
    - argument-required event keys must include payloads
- CI hardening for `P0-09` exit gate:
  - updated `.github/workflows/ci.yml` Java job to run `:server:test` + `:client:test`
  - expanded Java test artifact upload to include both server and client reports
- Validation:
  - `./gradlew :server:test --console=plain --no-daemon` pass
  - `./gradlew :client:test --console=plain --no-daemon` pass
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass
- Next loop:
  - close remaining `P0-05` save/load parity items with full-world runtime restore assertions
  - finish `P0-06` scripted-loss consequence parity checks (story/hub post-overlay transitions)
  - move `P0-10` playtest pack/blocker triage once `P0-09` CI results confirm stability

`2026-04-14 17:26:10 +01:00`

- Continued `P0-05` save/load parity hardening:
  - added explicit `hubState` persistence in `SaveData` capture/restore path
  - removed duplicate `hub_state` leakage into generic `storyFlags` during capture
  - added migration sanitation for invalid/blank saved hub state values in `SaveManager.migrate(...)`
  - ensured `SaveManager` write overlay includes manager-captured `hubState`
- Continued `P0-06` scripted-loss consequence parity:
  - fixed `StoryManager.onVeilMaidenDefeatedAct1()` to actually enforce intended consequence contract:
    - collapse hub state to `EMPTY`
    - clamp hub degradation to collapse level
    - enforce minimum narrative progression to Act III
  - added server regression test proving scripted loss drains player Yin/Yang and collapses hub FSM state
  - added client regression tests for scripted-loss story consequences and hub-state restore from save
- Validation:
  - `./gradlew :server:test :client:test --console=plain --no-daemon` pass
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass
- Next loop:
  - finish remaining `P0-05` world/runtime rehydrate edge assertions (cross-hub position semantics + inventory overflow edge cases)
  - complete `P0-06` end-to-end multiplayer scripted-loss consequence checks against live snapshot ordering
  - continue toward `P0-10` signoff pack once P0 criticals are marked done

`2026-04-14 17:39:30 +01:00`

- Continued `P0-05` save/load edge hardening:
  - added migration regression coverage for invalid saved `hubState` values (`SaveManagerMigrationTest.invalidSavedHubStateIsSanitizedToFull`)
  - added roundtrip guard that reserved story context key `hub_state` does not leak into generic `storyFlags` (`SaveManagerRoundtripTest`)
- Continued `P0-06` multiplayer scripted-loss consequence checks:
  - added `ZoneSimulationLoopScriptedLossOrderingTest` to verify:
    - `SCRIPTED_LOSS` is broadcast when pending scripted loss is drained during sim tick
    - hub collapse consequence (`EMPTY`) is visible in subsequent world snapshot hub-state
    - broadcast is one-shot (no duplicate scripted-loss events across ticks)
- Validation:
  - `./gradlew :server:test :client:test --console=plain --no-daemon` pass
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass
- Next loop:
  - finish remaining `P0-05` runtime rehydrate edge assertions tied to `GameScreen.restoreSoloPlayerFromSave(...)` semantics
  - reassess `P0-02/P0-03/P0-04` status against now-expanded regression evidence and promote to done where exit gates are satisfied
  - stage `P0-10` signoff playtest pack skeleton once P0 in-progress items are either closed or explicitly blocked

`2026-04-14 17:53:17 +01:00`

- Completed final `P0-05` runtime rehydrate edge assertions around `GameScreen.restoreSoloPlayerFromSave(...)`:
  - added `GameScreenSaveRestoreTest` coverage for:
    - cross-hub saved-position semantics (saved coordinates do not override current player position when hub IDs differ)
    - same-hub position clamping to world bounds with velocity reset
    - currency clamp and inventory overflow capping against slot/stack limits
    - equipment + ability rehydrate parity (`equippedWeapon`, `equippedArmor`, `weaponState`, unlocked ability set)
- Reassessed `P0-02/P0-03/P0-04` and closed exit gates on regression evidence:
  - added `MissionAuthoringProgressionCoverageTest` proving `30/30` authored missions can progress objectives via runtime adapters and unlock exits
  - confirmed mission lifecycle matrix remains green via `MissionManagerObjectiveLifecycleTest` + `CampaignCriticalFlowTest`
  - confirmed dialogue parity lint remains green via `tests/test_data_integrity.py` (`test_dialogue_events_supported_by_runtime_router`)
- Validation:
  - `./gradlew :server:test :client:test --console=plain --no-daemon` pass
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass
- Next loop:
  - close remaining `P0-05` runtime/world rehydrate parity edges outside player restore (if any are discovered in playtest)
  - continue `P0-06` + `P0-09` final closure pass and prepare `P0-10` signoff playtest pack skeleton

`2026-04-14 18:53:17 +01:00`

- Continued in-progress P0 closure pass (`P0-05`/`P0-06`/`P0-09`):
  - expanded scripted-loss multiplayer consequence coverage in `ZoneSimulationLoopScriptedLossOrderingTest`:
    - verifies `SCRIPTED_LOSS` is broadcast to all zone members
    - verifies non-zone player channels do not receive the event
    - verifies post-loss authoritative snapshot carries collapsed hub state and drained Yin/Yang values for affected players
  - stabilized `P0-09` CI blocker found in latest CI run history:
    - identified failing step (`black --check`) from CI run `24411277310`
    - reformatted `tools/check_version_sync.py` to Black-compatible layout to remove formatting gate failure
- Reassessed status gates:
  - marked `P0-05` done based on migration + roundtrip + runtime rehydrate regression coverage
  - marked `P0-06` done based on single-player + multiplayer scripted-loss network/state transition coverage
  - kept `P0-09` in progress pending fresh remote CI confirmation after push
- Validation:
  - `./gradlew :server:test :client:test --console=plain --no-daemon` pass
  - `.venv\\Scripts\\python.exe tests/test_data_integrity.py` pass
  - `.venv\\Scripts\\python.exe tools/check_version_sync.py` pass
  - `gh run view 24411277310 --repo VainAsher/indie-ninja-adventures --log-failed` reviewed (Python Black gate root cause captured and fixed)
- Next loop:
  - push current branch and confirm CI green status for `P0-09` exit gate
  - stage `P0-10` signoff playtest pack + blocker triage scaffold once CI confirms

`2026-04-14 18:55:13 +01:00`

- Continued `P0-09` regression-suite deliverable hardening:
  - added `tools/run_p0_regression_suite.py` to execute core P0 gates in one command:
    - version sync (`tools/check_version_sync.py`)
    - data integrity (`tests/test_data_integrity.py`)
    - Java campaign-critical regressions (`:server:test` + `:client:test`)
  - report artifact now generated automatically at `docs/reports/P0_REGRESSION_REPORT.md`
  - executed runner locally and captured passing report (`Overall: PASS`)
- Validation:
  - `.venv\\Scripts\\python.exe tools/run_p0_regression_suite.py` pass
- Next loop:
  - commit/push this P0 closure batch and confirm remote CI turns green
  - move directly into `P0-10` playtest signoff scaffold after CI confirmation

`2026-04-14 20:15:00 +01:00`

- Closed `P0-09` exit gate on confirmed remote CI and release parity:
  - latest `master` CI run passed (`24416458487`)
  - latest release run for `v0.11.36` passed (`24416474476`)
- Started `P0-10` signoff scaffold:
  - rewrote `docs/PLAYER_EXPECTATIONS.md` into launcher-only end-to-end solo + multiplayer playtest packs
  - added explicit tester instructions for controls, lore framing, logs, debug overlays, and reporting templates
  - added instrumentation audit section (logging/debug/settings) to separate implemented tooling from current gaps
- Multiplayer identity persistence hardening (playtest reliability):
  - fixed client identity churn by resolving stable `player_id` from launcher profile property or persisted file fallback
  - launcher now assigns per-profile `player_id` and passes `-Dninja.playerId=<uuid>` to Java client
  - added in-game `F1` controls overlay and `F3` telemetry overlay for first-time tester support
  - enriched mission contact logs with hub, room, and coordinates for human-readable repro trails
- Validation target for next loop:
  - run `:server:test` + `:client:compileJava`, verify stable UUID across reconnect in `server.log`
  - execute first full P0-10 playtest cycle and triage blocker list

`2026-04-14 21:52:31 +01:00`

- Reviewed new GDD controls spec (`docs/GDD.md` section `10.3`) for P0/P1 alignment:
  - confirmed movement-profile vs stance separation, context-priority routing, and launcher-first input discoverability are now explicit design gates
  - mapped controls goals into P0-10 signoff so first external playtest pack validates onboarding, default input readability, and debug discoverability before P1 tuning lock
- Release prep for first P0-10 build:
  - staged runtime support for launcher-only testers (`F1` controls overlay, `F3` telemetry overlay, richer mission location logging)
  - staged identity persistence hardening to stop per-session UUID churn across reconnects
- Next loop:
  - execute first full P0-10 run and log blockers against GDD `10.3` controls requirements
  - start P1 handover only after control baseline and remaining P0 gates are signed off

`2026-04-15 03:18:26 +01:00`

- Continued P0-10 blocker remediation against latest playtest feedback:
  - implemented runtime guard/parry schema end-to-end:
    - added `InputCommand.block` wire field with input/replay parity (`InputPoller`, `InputRecorder`, `ReplayPlayer`)
    - added `SimPlayer` guard/parry runtime state (`isBlocking`, `isParrying`, block-hit reaction timers)
    - added directional front-facing guard resolution and parry stun path in `GameSimulator` (`applyIncomingDamage(...)`)
  - fixed Time Leech boss minion stability issues:
    - `time_leech` now spawns with canonical enemy type wire instead of mistyped slime fallback
    - capped active Time Leech adds (`MAX_ACTIVE_LEECHES=5`) in boss arena to prevent infinite runaway wave pressure
    - renderer/geometry mapping now explicitly supports `time_leech` collision and animation routing
  - hardened Siren shield/add interaction scope:
    - Siren shield immunity now checks red-slime adds inside arena bounds only
    - scripted-loss cleanup for spawned red slimes now scopes to the active boss arena
  - enforced solo campaign runtime mode in local sim startup (`GameScreen.initializeSoloSimulation`)
- Validation:
  - `./gradlew :server:test` pass
  - `./gradlew :client:compileJava` pass
- Next loop:
  - cut fresh testable build/tag for this runtime stability pass
  - execute targeted P0-10 playtest sweep on controls readability + boss fight clarity before P1 handoff gating

### Branch and commit format

- Branch naming: `feature/shadow-ascent-<phase>-<topic>`
- Commit subject format: `<type>(<plan_id>): <summary>`
- Commit body template:
  - `What changed`
  - `Why now`
  - `Risks`
  - `Validation`
  - `Next checklist item`

### Status legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done
- `[!]` Blocked

---

## 0B. Execution-Ordered Checklist (P0/P1/P2)

### Sprint map

- `S1-S4`: P0 (ship blockers)
- `S5-S9`: P1 (balance, tuning, content throughput)
- `S10-S14`: P2 (release hardening and full release)

Owner roles:

- `ENG-CORE`: Core sim/physics/systems
- `ENG-CLIENT`: Client/UI/rendering/input/save UX
- `ENG-NET`: Protocol/server/client message flow
- `ENG-DATA`: Missions/dialogue/items/data validation
- `DESIGN`: Balance, pacing, playtest interpretation
- `QA`: Test plans/regression/verification
- `PROD`: Planning, release process, dependency tracking

### Interpretation update from pivot date
**Added:** 2026-04-14 12:00:00 +01:00

From this point onward:
- P0 remains primarily about structural campaign reliability.
- P1 is no longer only â€œgeneral balance and content throughput.â€ It is now also the phase where **core combat feel, stealth readability, stance distinction, and Flow usability are locked**.
- P2 should only harden and scale systems whose moment-to-moment identity has already been proven in P1.

**Why added:**  
The earlier checklist assumed game feel would emerge naturally from structural stability plus broad tuning. The current design direction is more specific than that: the game now depends on a tight stance/Flow feel model that must be explicitly validated as a deliverable.

---

## P0 - Core Campaign Loop Stabilization

Goal: make campaign progression complete, testable, and safe to iterate.

| Status | ID | Task | Owner | Sprint | Depends on | Deliverable | Balance / ideation hook | Exit gate |
|--------|----|------|-------|--------|------------|-------------|--------------------------|-----------|
| [x] | P0-01 | Restore build/test baseline (fix Gradle wrapper path, ensure `./gradlew.bat test` works) | ENG-CORE + QA | S1 | None | Reproducible local test command and CI run | Enables rapid tuning safely | All existing tests run from clean checkout |
| [x] | P0-02 | Mission objective integration for all objective types (`collect_items`, `activate_switches`, `reach_location`, `time_challenge`, `defeat_boss`, `kill_all_enemies`) | ENG-CLIENT + ENG-CORE | S1 | P0-01 | Objective event adapters and mission progress hooks | Exposes full mission pacing for tuning | 30/30 missions can progress objectives in playtest harness |
| [x] | P0-03 | Mission completion and exit-lock behavior wiring | ENG-CLIENT | S1 | P0-02 | Mission completion trigger + unlock/lock lifecycle | Supports mission difficulty tuning | Mission state transitions pass lifecycle test matrix |
| [x] | P0-04 | Dialogue event routing parity (handle all emitted events or remove dead authored events) | ENG-DATA + ENG-CLIENT | S1-S2 | P0-02 | Event router map + unknown-event telemetry | Enables narrative pacing experiments | Zero silent event drops in dialogue lint output |
| [x] | P0-05 | Save/load parity hardening (active mission restore, story-act clamp fix, full liveData restore symmetry) | ENG-CLIENT + ENG-CORE | S2 | P0-03 | Migration rules + roundtrip integrity tests | Preserves tuning experiments across sessions | Save/load roundtrip loses no critical progression fields |
| [x] | P0-06 | Scripted-loss full network pipeline (`GameSimulator` emit -> server broadcast -> client handling -> story/hub consequences) | ENG-NET + ENG-CLIENT | S2 | P0-04, P0-05 | End-to-end scripted-loss flow in MP and solo | Stabilizes narrative boss balancing | Siren sequence completes with consistent state transitions |
| [x] | P0-07 | Mission/item contract normalization (canonical IDs, reward/item schema checks) | ENG-DATA | S2-S3 | P0-02 | Validation script and cleaned mission data | Prevents fake rewards and invalid progression tuning data | Zero missing mission-referenced item IDs |
| [x] | P0-08 | Version/document source-of-truth consolidation (`version.json`, build file, README/changelog sync policy) | PROD + ENG-CORE | S3 | P0-01 | Release metadata sync checklist | Keeps test/balance results attributable to exact build | One authoritative version source reflected in all release docs |
| [x] | P0-09 | Critical integration test suite for campaign loop (mission start/progress/complete, save/load, dialogue events, scripted-loss) | QA + ENG-CORE | S3-S4 | P0-06, P0-07 | Regression suite with pass/fail report | Locks in baseline before heavy balance iteration | Green suite in CI for all P0 critical flows |
| [~] | P0-10 | P0 signoff playtest pack, controls-spec traceability, and blocker triage | DESIGN + QA + PROD | S4 | P0-09 | Structured playtest report plus GDD 10.3 control-resolution matrix | Establishes tuning baseline for P1 | No open P0 blockers, controls baseline validated against GDD 10.3, and approved handoff to P1 |

---

## P1 - Balance, Tuning, and Content Throughput

Goal: make gameplay feel coherent and tunable while increasing mission/story output safely.

### Added interpretation from pivot date
**Added:** 2026-04-14 12:00:00 +01:00

P1 is now the phase where the following must be explicitly proven:

- Passive and Aggressive stances feel meaningfully different
- Roll and Dash each support their intended fantasy
- shared combat language feels tight
- lethal/non-lethal split is readable and satisfying
- Flow is understandable, reachable, and rewarding
- the balance indicator teaches players how to lean and rebalance
- Trials inherit the same gameplay language cleanly

| Status | ID | Task | Owner | Sprint | Depends on | Deliverable | Balance / ideation hook | Exit gate |
|--------|----|------|-------|--------|------------|-------------|--------------------------|-----------|
| [ ] | P1-01 | Data-driven tuning layer (movement/combat/economy/mission timing/boss parameters) | ENG-CORE + ENG-DATA | S5 | P0-10 | Config-driven tuning files and loader | Fast hypothesis testing without code churn | Core balance constants removed from hardcoded logic path |
| [ ] | P1-02 | Telemetry instrumentation (mission fail reasons, death causes, DPS in/out, completion times, economy curves) | ENG-CORE + ENG-CLIENT | S5 | P1-01 | Session telemetry logs and aggregation scripts | Quantifies tuning changes | Every playtest produces comparable metrics bundle |
| [ ] | P1-03 | Balance dashboard and target bands | DESIGN + QA | S5-S6 | P1-02 | KPI sheet with min/max target bands | Converts feel goals into measurable thresholds | Targets defined for TTK, fail-rate, mission duration, resource pressure |
| [~] | P1-03A | Stance/Flow combat-feel lock (Roll vs Dash tuning, Passive/Aggressive readability, block/parry/combo feel, balance indicator clarity, Flow usability) | DESIGN + ENG-CORE + ENG-CLIENT + QA | S5-S7 | P1-01, P1-02 | Locked stance/combat/Flow tuning notes and validated playtest results | Converts broad combat/stealth goals into a shippable gameplay identity | Playtesters can distinguish stances, understand Flow pursuit, and report tighter combat feel consistently |
| | | **P1-03A Progress (v0.12.08):** Simulation layer complete — stance movement multipliers, noise/awareness FSM, ShadowStep/ThunderStep/HarmonicStep teleport, Silent/Riot/Resonant Echo Art, Flow recency gate, duality test room. 56 new tests. **Remaining:** animation/VFX pass (client-side expression), balance tuning pass, validated playtest results. Playtest guide at `docs/reports/manual-runtime/v0.12.08-playtest-guide.md`. | | | | | | |
| [ ] | P1-03B | Weapon combo chain system: `ComboManager`, 5-hit unarmed (punch/kick) and sword (slash1→slash2→slash3 + aerial/crouch/dash) chains, `InputCommand` wire extension, `SimPlayer` combo-window state, `EntityRenderer` per-hit key routing. **Requires COMPATIBILITY_AND_MIGRATION_WORKFLOW pre-flight before any implementation** (touches InputCommand, SimPlayer persistence, replay determinism). | ENG-CORE + ENG-CLIENT | S5-S6 | P1-03A | `ComboManager` class, `InputCommand.comboTrigger` wire field, `SimPlayer.comboHit` state, per-hit anim routing | Enables lethal/non-lethal combo feel differentiation per GDD §3.3 | Player can chain 5-hit standing, aerial, crouch, and dash combos; unarmed = non-lethal, sword = lethal |
| [ ] | P1-04 | Weekly balance loop (hypothesis -> change -> playtest -> metrics review -> decision log) | DESIGN + ENG-CORE | S6-S9 (recurring) | P1-03 | Weekly balance notes linked to commits | Structured ideation and tuning rhythm | 4 consecutive loops completed with logged decisions |
| [ ] | P1-05 | Story pacing pass (mission unlock cadence, act transition timing, hub evolution rhythm) | DESIGN + ENG-DATA | S6-S7 | P1-02 | Progression pacing matrix | Supports narrative ideation against measurable flow | No dead-end progression in scripted path tests |
| [ ] | P1-06 | Enemy and boss tuning pass (difficulty curves by act and mission tier) | DESIGN + ENG-CORE | S7-S8 | P1-04 | Tuning table per archetype and phase | Core combat feel iteration | Difficulty spikes within target fail-rate bands |
| [ ] | P1-07 | Economy and rewards pass (currency sinks, reward fairness, fragment pacing) | DESIGN + ENG-DATA | S8 | P1-04, P0-07 | Economy model and reward audit | Sustains long-term progression motivation | Economy inflation/shortage outside target band eliminated |
| [ ] | P1-08 | Content authoring guardrails (mission lint, dialogue event lint, schema CI) | ENG-DATA + QA | S8-S9 | P0-07 | CI content validation gates | Enables safe ideation at higher throughput | Invalid mission/dialogue content blocked pre-merge |
| [ ] | P1-09 | Client integration tests for gameplay-facing systems | QA + ENG-CLIENT | S9 | P1-08 | Expanded automated regression tests | Prevents tuning regressions from UI/client side | Critical client gameplay regressions detected in CI |
| [ ] | P1-10 | P1 signoff and release candidate criteria lock | PROD + DESIGN + QA | S9 | P1-09 | Approved P2 entry criteria | Freezes design pillars before hardening | P1 targets met and signed off by leads |
| [ ] | P1-11 | **[BACKLOG IDEA]** Versus / Race multiplayer mode: up to 4 players racing to objectives or to the zone exit. Separate mode from campaign co-op — no shared story progression. Potential variants: race-to-exit (fastest to clear a generated dungeon), objective-race (compete for POI captures), kill-race (score via enemies defeated). Requires dedicated server-side mode flag, score/ranking state, timeout/finish conditions, and UX flows (lobby, result screen). Full COMPATIBILITY_AND_MIGRATION_WORKFLOW pre-flight required (protocol, SimPlayer mode state, replay). **No implementation scheduled — concept only.** | ENG-CORE + ENG-CLIENT + DESIGN | TBD | P1 campaign stability | Mode design, protocol spec, lobby UX | Adds competitive replayability orthogonal to the campaign | Player can enter a versus lobby, complete a timed run against peers, and see a ranked result screen |

---

## P2 - Full Release Hardening and Launch

Goal: content-complete, performance-stable, release-managed build to ship and maintain.

### Added rule from pivot date
**Added:** 2026-04-14 12:00:00 +01:00

P2 should assume:
- the core stance/Flow combat identity is already proven
- the balance indicator and Flow readability are already adequate
- Trials already feel like the same game
- Echo/advanced systems already support, rather than obscure, the core loop

Do not let P2 become a hidden design-discovery phase for core combat feel. That work belongs in P1.

| Status | ID | Task | Owner | Sprint | Depends on | Deliverable | Balance / ideation hook | Exit gate |
|--------|----|------|-------|--------|------------|-------------|--------------------------|-----------|
| [ ] | P2-01 | Complete remaining roadmap systems (Echo, Act IV depression mechanics, final-act integrations) | ENG-CORE + ENG-CLIENT + DESIGN | S10-S11 | P1-10 | Feature-complete release branch | Final thematic tuning and identity cohesion | GDD must-have systems marked implemented |
| [ ] | P2-02 | Performance and stability optimization (long session, load times, memory, frame pacing) | ENG-CORE + ENG-CLIENT + QA | S11-S12 | P2-01 | Profiling reports and optimizations | Maintains feel under stress | Meets performance budgets on target hardware |
| [ ] | P2-03 | UX/accessibility and onboarding pass | ENG-CLIENT + DESIGN + QA | S12 | P2-01 | UX polish checklist and options validation | Reduces friction in first-hour tuning insights | New-player completion funnel improves vs P1 baseline |
| [ ] | P2-04 | Release candidate process (code freeze, blocker-only merges, triage SLA, rollback plan) | PROD + QA + ENG-CORE | S13 | P2-02, P2-03 | RC protocol and signoff artifacts | Locks tuned state for launch quality | RC passes full regression + playtest signoff |
| [ ] | P2-05 | Launch prep and post-launch loop setup (telemetry review cadence, hotfix path, backlog triage rules) | PROD + DESIGN + QA | S13-S14 | P2-04 | Live ops handbook | Keeps ideation alive post-launch without destabilizing game | Day-0 and Day-7 post-launch review process approved |
| [ ] | P2-06 | Final release signoff and shipping checklist | PROD + all leads | S14 | P2-05 | Final release decision record | Final confirmation of tuned and stable experience | No critical or high-severity blockers remain |

---

## 0C. Balancing, Tweaking, and Ideation Cadence (Runs Through All Phases)

### Weekly cadence

| Day | Activity | Owner | Artifact |
|-----|----------|-------|----------|
| Mon | Set hypotheses for week | DESIGN + ENG leads | `balance_hypotheses.md` |
| Tue-Wed | Implement targeted changes | ENG roles | Commits linked to plan IDs |
| Thu | Structured playtest sessions (baseline/challenge/new-player) | QA + DESIGN | Playtest observations + telemetry bundle |
| Fri | Review metrics, accept/reject hypotheses, queue next loop | DESIGN + PROD + ENG | Decision log + updated checklist status |

### Mandatory balance artifacts

- `BALANCE_LOG.md`: each parameter change, why it changed, expected effect, observed result.
- `IDEATION_BACKLOG.md`: candidate ideas with `impact`, `effort`, `risk`, `thematic_fit`.
- `PLAYTEST_REPORT_<date>.md`: qualitative notes plus quantitative telemetry.
- `RISK_REGISTER.md`: known risks, mitigations, owner, due sprint.

### Addendum â€” stance / Flow playtest focus
**Added:** 2026-04-14 12:00:00 +01:00

All future balance and ideation loops must explicitly track at least these gameplay questions:

- Does Passive stance feel distinct from Aggressive stance in movement, silhouette, and combat outcome?
- Does Roll feel stealthy, low-profile, and controllable?
- Does Dash feel fast, forceful, and aggressive?
- Is the lethality split between unarmed and armed play readable and satisfying?
- Are block/parry timings readable and rewarding in both stances?
- Do aerial directional attacks and throws preserve the stance fantasy?
- Can players understand how close they are to Flow?
- Is the balance indicator clear without cluttering play?
- Does Flow feel smoother and more masterful rather than simply stronger?

**Why added:**  
The original cadence was broad enough for system tuning, but the realigned design depends on a set of very specific experiential goals. These now need to be explicit test criteria.

### Metric guardrails (initial targets, refine during P1)

| Metric | Target band | Usage |
|--------|-------------|-------|
| Mission completion rate (mainline) | 65% to 85% | Detects overtuned or undertuned progression |
| Mission fail due to unclear objective | < 10% | Signals objective readability issues |
| Average retries per boss (story path) | 2 to 6 | Controls frustration vs mastery |
| Median mission duration | 8 to 18 min | Maintains pacing consistency |
| Economy reserve at act transitions | Positive but constrained | Prevents inflation and hard-lock scarcity |
| Severe spike encounters per session | 0 to 1 | Keeps difficulty ramps intentional |
| Flow activation frequency (mainline missions) | Regular but not constant | Ensures Flow is achievable without becoming background noise |
| Passive vs Aggressive usage spread | Neither stance ignored in successful runs | Detects dominance of one stance over the intended rebalance loop |
| Balance indicator comprehension rate | High in first-hour tests | Detects whether players understand how to reach Flow |
| Parry success readability | Improvement across sessions | Measures whether combat timing communicates well |
| Roll vs Dash preference skew | No single movement identity invalidates the other | Detects stance-mobility imbalance |

### Change-control rules for tuning

- Do not merge unmeasured balance changes.
- Each balance commit must reference a hypothesis ID.
- Freeze tuning 48 hours before any release candidate.
- After freeze, only blocker fixes are allowed.
- Do not merge major movement/combat feel changes without a short before/after note in `BALANCE_LOG.md`.
- Any change to Roll, Dash, Parry, stance readability, Flow entry, or Flow visuals must reference a gameplay hypothesis, not only a bug fix.

---

## 0. Situation Summary

### Project history in brief

The full 296-commit git history tells a clear story of four technology pivots over ~101 days:

| Period | Technology | Version | What happened |
|--------|-----------|---------|---------------|
| Dec 31 2025 | Python/Pygame monolith | v0.4.0-dev | Initial commit |
| Jan 1 2026 | Python modular | v0.7.0 | Refactor into modules, 85-day silence follows |
| Mar 27â€“Apr 3 2026 | Python full-featured | v0.7.xâ€“v0.9.16 | Animation, bosses, multiplayer, launcher, zones, delta encoding â€” all built in 8 days |
| Apr 4â€“10 2026 | Java (Netty + libGDX) | v0.10.0â€“v0.10.83 | Complete rewrite: server, simulator, client, all features ported, post-audit hardening |

The Java codebase landed on Apr 4 and reached v0.10.83 by Apr 10 â€” **6 days to rebuild everything**. The Apr 7 sprint alone was 53 commits.

**The fourth pivot is Shadow Ascent.** It exists in the GDD and these planning documents â€” not yet in a single line of game-specific Java code. The infrastructure is the most complete it has ever been. The game itself has not started.

### Current codebase state (v0.11.5)

The Phase 0 audit (Apr 9) identified ~30 structural issues. All resolved. Milestones 1â€“3 shipped. Infrastructure bugs discovered in the first playable sessions and fixed.

| Area | Resolved | Still open |
|------|----------|-----------|
| ECS | EntityLifecycleListener, SerializableComponent, auto-tag index, concrete components | ECS-4 (no auto-registration, low risk) |
| Physics | TileType decoupling, GAS tile, abilityFlags, dynamicTiles in candidates, raycast API; lava ceiling trigger test; swept non-tunnel test | PHYS-4/6 (documented contracts) |
| World gen | Back-edges (Metroidvania loops ready), Redis tile cache, PostgreSQL, deterministic biomes | WORLD-5/6/7 (low risk) |
| Networking | Schema version, frameHash desync detection, Redis zone cache, no boxing; NET-1 spawn default | NET-4/5 (no NPC/inventory delta, low) |
| Inventory | DB-backed items/recipes, player_inventory persistence, ability type, coin recipe fix, item Redis cache | â€” |
| Tests | 13 test files; all gaps closed including lava ceiling trigger + swept non-tunnel | â€” |
| Solo mode | In-process GameSimulator; no server required; unified world layout; 12-room megamap | â€” |
| Hub system | HubState FSM, HubStateMachine, NPC spawn/despawn, Act.java FSM, player_progress persistence | â€” |
| Save state | Full save (currency, inventory, abilities, world seed, visited rooms) via syncSaveState() | â€” |
| Logging | logback.xml in shadow JAR (Gradle resource-filter bug fixed); client.log written on disk | â€” |
| Replays | Solo InputRecorder wired into GameScreen; .ndjson files in user_data/replays/ | â€” |
| Launcher | cwd fixed for server Popen; replay viewer handles .ndjson; record flag wired to -Dninja.record | â€” |

### What shipped since plan was written (v0.11.0 â†’ v0.11.6)

| Version | What shipped |
| ------- | ------------ |
| v0.11.0 | M1: test gaps closed, version sync; M2: solo mode in-process GameSimulator |
| v0.11.1 | M3: HubStateMachine, Act FSM, NPC roster sync, player_progress persistence |
| v0.11.2 | fix: solo multi-room world; hub NPC authority; overlay null-guards |
| v0.11.3 | fix: portal NPE in solo (networkClient null-guard); full save state (currency/inventory/abilities) |
| v0.11.4 | fix: logback.xml stripped by Gradle resource filter; server cwd missing in launcher |
| v0.11.5 | feat: solo InputRecorder + .ndjson replay files; launcher replay viewer updated |
| v0.11.6 | M4: YinYangComponent + LanternComponent + vignette + HUD bars + weapon-state animation routing; 171 player sprite sheets extracted |
| v0.11.7 | fix: vignette in solo mode (setDarkArea flag); crouch_walk + swim animation states; companion orbs scale with Yin/Yang; HUD redesign (merged stamina, lantern bottom-left) |
| v0.11.8 | fix(vignette): smoother gradient (20 layers, quadratic curve), corner overlap fix, base dim layer; build.gradle.kts version resync (0.10.83 â†’ 0.11.8) |
| v0.11.9 | fix(vignette): critical GL blend state bug â€” SpriteBatch.end() disables GL_BLEND; ShapeRenderer did not re-enable it; all vignette rectangles drew as solid opaque black covering the game world. Fix: explicit glEnable(GL_BLEND) before shapes.begin() |
| v0.11.10 | feat(m5): Shadow Ascent boss AI â€” BossPatternLibrary (Siren/EchoWarden/TimeLechLord/MemoryEater); SCRIPTED_LOSS MessageType; enemy FLEE+GUARD states; loadEnemySheets() + stitch_enemy_frames.py; climb/ledge animation FSM routing |
| v0.11.11 | fix(m3): hub NPC authority; overlay null-guards |
| v0.11.12 | fix(m3): skip hub NPC sync at frame 0; fix CME when despawning NPCs |
| v0.11.13â€“15 | fix: log files, save-on-exit, save-on-room-entry; launcher black formatting CI fix |
| v0.11.16 | feat(pickups): PickupSlot respawn system (30â€“60 s lifetime, 15â€“30 s cooldown) |
| v0.11.17 | fix(rendering): bottom-anchor enemy sprites to physics feet; ENEMY_LIFT formula |
| v0.11.18 | fix(dialogue): bundle data/ into fat JAR so NPC dialogues load from classpath |
| v0.11.19 | feat(minimap): 860Ã—680 panel; zoom 1x/2x/4x (+/-); arrow pan; per-pickup-type colours; room labels when zoomed; hitbox debug overlay (H); terrain density boost; fragments in all loot pools; pickup Y-spawn fix |

### What the GDD requires that doesn't exist

Four interlocking pillars define Shadow Ascent. Two are shipped:

| Pillar | GDD section | Status |
|--------|-------------|--------|
| Yin/Yang system | Â§3.3 | **Done** â€” `YinYangComponent`, decay/sight/surge, bars in HUD (v0.11.6) |
| Lantern system | Â§3.4 | **Done** â€” `LanternComponent`, vignette overlay, lantern meter (v0.11.6) |
| Hub evolution state machine | Â§4 | **Done** â€” `HubState`, `HubStateMachine`, NPC roster sync, `player_progress` (v0.11.1) |
| Narrative Act FSM | Â§5 | **Done** â€” `Act.java` FSM Acts Iâ€“VI, `StoryManager` wired to hub state (v0.11.1) |

Secondary systems â€” boss AI behavioral patterns, Echo mechanic, puzzle archetypes, Act IV depression mechanics â€” not yet built.

### Pivot interpretation update
**Added:** 2026-04-14 12:00:00 +01:00

The earlier reading of this section focused on whether the Java codebase had caught up to the original GDD pillars. That was the correct question at the time.

The current question is different:

**which parts of the original GDD are already materially present, which parts now need reinterpretation through the stance/Flow model, and which parts remain genuinely unbuilt?**

### Updated current status by gameplay identity

The architecture is mature enough to support the intended game.
Core campaign-critical systems are substantially wired.
Yin/Yang, Lantern, hub, act, boss, and mission foundations all exist.

The biggest remaining product risk is not infrastructure absence, but gameplay cohesion.

The codebase now supports the following as the intended active gameplay direction:

- Passive stance with low-profile, stealth-leaning movement and non-lethal control
- Aggressive stance with burst movement and lethal pressure
- shared combat language across stances
- directional aerial combat and throws
- Flow as the reward for balanced play
- Lantern as a Flow amplifier
- player-readable balance feedback as a required UX layer

These are no longer speculative design notes. They are now the intended interpretation layer for all future campaign, Trials, and polish work.

**Why added:**  
The live plan records shipped systems well, but it does not yet establish the new stance/combat/Flow direction as the active lens through which those systems should be developed.

### The multiplayer vs. single-player decision

The GDD is single-player first with optional co-op. The codebase is multiplayer first.

**Decision:** Keep the networked architecture. Add an **in-process solo mode** where `GameSimulator` runs locally on the client, no socket required. The same rendering pipeline serves both paths. Multiplayer co-op becomes an optional overlay â€” Yin/Yang and Lantern work identically in both modes.

### Three game modes (as of v0.11.3)

The game ships **three distinct modes** with separate loops, tones, and world structures. The milestones below cover Campaign/Solo. Arcade and Sandbox are separate roadmap tracks.

| Mode | Loop | World | Player identity | Status |
|------|------|-------|-----------------|--------|
| **Campaign / Solo** | Narrative Metroidvania; hub â†’ portal â†’ mission level | Instanced; procedurally generated interconnected rooms; hub world | The Hallowed Ninja | **Active â€” this roadmap** |
| **Arcade** | Roguelike run; no hub; loadout + powerup/modifier builds; death ends run | Per-run generated dungeon; smaller rooms; no persistence | Unnamed Ninja (cosmetic) | Planned â€” separate Arcade roadmap |
| **Sandbox** | Open-ended survival/construction; player-set goals; persistent server world | Endless interconnected world; no instancing; destructible | Disciples / Acolytes (NOT the Hallowed Ninja) | Planned â€” separate Sandbox roadmap |

**Key design constraints that follow from this:**
- Arcade must NOT use the Metroidvania hub system â€” it is a separate loop entirely
- Sandbox players are not the protagonist; the world is the canvas, not the story
- Solo/Campaign can share network code with Arcade for co-op lobby, but the world generation, persistence, and narrative systems are campaign-only

---

## 1. What to Keep

| System | Why it stays |
|--------|-------------|
| ECS (`EntityManager`, `EventBus`, `GameClock`) | New systems plug in as `Component` types and `EventBus` subscribers |
| `PhysicsSystem` + `CollisionSystem` | GDD movement (wall-jump, dash, grapple) already gated by `abilityFlags` |
| `SpatialHash` (including `dynamicTiles` + `raycast`) | `raycast` is ready for boss line-of-sight |
| `WorldGraph` (with back-edges) | Metroidvania loops are ready |
| `WorldGenerator` tile pipeline | GAS, LAVA, ICE, WATER, PLATFORM map directly to GDD mechanics |
| `RoomPostProcessor` pipeline (AbilityLayer, PuzzleLayer, EntityPlanner) | Foundation for all puzzle archetypes |
| `WireCodec`, `MessageType`, delta encoding | No protocol changes needed for new systems |
| `ZoneSimulationLoop` 60 Hz loop | Unchanged |
| `ZoneStateCache` + `RoomTileCache` + `ItemCache` | Unchanged |
| `InventoryRepository` + `WorldGraphRepository` (JDBC implemented) | Unchanged |
| `ItemDatabase` / `RecipeBook` (DB-backed) | Extend with new item types |
| libGDX rendering pipeline | Extend, not replace |
| `InputRecorder` / `ReplayPlayer` | Foundation for the Echo system |
| `DialogueManager` / `DialogueTree` | GDD NPC dialogue is minimal-symbolic; existing system is sufficient |
| `MissionManager` | Maps to "Accept mission / access level" in GDD core loop |

### Interpretation note from pivot date
**Added:** 2026-04-14 12:00:00 +01:00

The main lesson remains:

**extend and reinterpret; do not rewrite.**

However, â€œreinterpretâ€ now matters more than earlier versions of this plan acknowledged. Several systems that were previously mapped as abstract GDD equivalents now need to be **re-centered around combat feel, stance clarity, and Flow readability** rather than left in their earlier meter-first framing.

---

## 2. Historical lessons that shape the plan

**Lesson 1 â€” Boss tuning is always iterative.** The Python boss received 5 successive HP/damage commits in a single day (Mar 29) to go from unkillable to playable. Plan for boss AI behavioral patterns to need the same treatment â€” ship a working loop first, tune in follow-up commits.

**Lesson 2 â€” Physics onGround is hard.** It took 5 commits to stabilize Java `onGround` detection (Apr 5â€“6). The lava-ceiling trigger and swept non-tunnel test gaps are the same class of problem. Close them before building on top of the physics.

**Lesson 3 â€” The Apr 7 sprint produced foundations, not designs.** 53 commits built a complete game in a day. The save system, hub registry, crafting, and puzzle system all exist â€” but they weren't designed for Shadow Ascent. Each needs to be extended, not replaced. The instinct to rewrite will be wrong.

**Lesson 4 â€” Version numbers drift.** `version.json` is at 0.10.70, `build.gradle.kts` is at `0.10.7`, commit messages reference v0.10.83. Fix this immediately and keep it in sync going forward. A single `chore(release)` commit should keep all three in agreement.

**Lesson 5 â€” The Loop system was an effective sprint tool.** The numbered Loop system (Loop 3, Loop 7, etc.) drove rapid feature delivery during the Java rebuild. For Shadow Ascent milestones, use numbered **Milestone** labels in commit messages (`feat(m3):`, `feat(m4):`) to preserve the same traceability.

---

## 3. What to Build New

### Interpretation addendum â€” what â€œbuild newâ€ means now
**Added:** 2026-04-14 12:00:00 +01:00

This section now needs to be read in three categories:

1. systems that already exist and should be reinterpreted
2. systems that remain incomplete and must be extended
3. systems that are still genuinely new work

**Why added:**  
The live file still contains several â€œbuild newâ€ subsections for systems that are already shipped or substantially wired. That creates confusion and makes the plan look less honest than it really is.

### 3.1 In-Process Solo Mode (pre-requisite for everything)

`GameScreen` gets an `offlineMode` path: instantiates `GameSimulator` locally, skips `NetworkClientThread`. Input feeds directly to local `sim.step()` each render frame. `WorldSnapshot` assembled locally and consumed by the same rendering pipeline.

**Files to modify:** `ModeSelectScreen.java`, `GameScreen.java`

No server code changes. Solo and networked clients use identical rendering paths.

---

### 3.2 Yin/Yang System (GDD Â§3.3)

**Yin (Emotion):** Reveals hidden platforms, slows time, environmental awareness  
**Yang (Discipline):** Attack strength, movement precision, stamina  
**Balance (`|yin âˆ’ yang| < 0.15`):** Flow Mode â€” smooth animation blending + enhanced traversal + combat

```java
// core/src/main/java/com/indieniinja/sim/YinYangComponent.java
public final class YinYangComponent extends Component implements SerializableComponent {
    float yin;   // 0.0 â€“ 1.0
    float yang;  // 0.0 â€“ 1.0

    boolean isBalanced()          { return Math.abs(yin - yang) < 0.15f; }
    void absorbYin(float amount)  { yin = Math.min(1.0f, yin + amount); }
    void absorbYang(float amount) { yang = Math.min(1.0f, yang + amount); }

    @Override public Map<String, Object> toMap() { return Map.of("yin", yin, "yang", yang); }
    public static YinYangComponent fromMap(int id, Map<String, Object> m) { â€¦ }
}
```

**Server effects** in `GameSimulator.step()`:
- `yin > 0.7f` â†’ set `ABILITY_YIN_SIGHT` on `PhysicsState.abilityFlags`; hidden-platform tiles become solid for this entity
- `yang > 0.7f` â†’ attack damage multiplier 1.5Ã—; dash stamina cost âˆ’30%
- `isBalanced()` â†’ set `FLOW_MODE` flag on `PlayerState`

**Client effects** in `GameScreen.render()`:
- `yin > 0.7f` â†’ `EntityRenderer` renders hidden-platform tiles with alpha âˆ Yin value
- `yang > 0.7f` â†’ denser hit particles, sharper attack animations
- `FLOW_MODE` â†’ lerp-based animation state blending
- `HudRenderer` Yin/Yang bar (currently stubbed â€” replace)

`PlayerState` gains: `yinValue`, `yangValue`, `flowMode`.
`WorldSnapshot.SCHEMA_VERSION` increments to 2.

**Files to create:** `core/sim/YinYangComponent.java`

**Files to modify:** `network/PlayerState.java`, `network/WorldSnapshot.java`, `sim/GameSimulator.java`, `physics/CollisionSystem.java`, `physics/PhysicsConstants.java`, `client/rendering/EntityRenderer.java`, `client/rendering/HudRenderer.java`

#### Pivot note â€” updated interpretation of Yin/Yang
**Added:** 2026-04-14 12:00:00 +01:00

The implementation foundation described below remains valuable, but the player-facing interpretation has evolved.

From this point forward, Yin/Yang should be read primarily as support for a stance-driven gameplay model:

- Passive stance = stealth/control/non-lethal bias
- Aggressive stance = pressure/lethality/burst bias
- balance between those stances = Flow access

The earlier meter-first interpretation remains useful as historical implementation context, but it is no longer the clearest primary gameplay description.

---

### 3.3 Lantern System (GDD Â§3.4)

Per-player float (0.0â€“1.0) persisted to `player_progress`. Global modifier for world clarity and physics.

```java
// core/src/main/java/com/indieniinja/sim/LanternComponent.java
public final class LanternComponent extends Component implements SerializableComponent {
    float value;  // 0.0 â€“ 1.0

    void decay(float dt)      { value = Math.max(0f, value - 0.01f * dt); }
    void restore(float amount){ value = Math.min(1f, value + amount); }

    @Override public Map<String, Object> toMap() { return Map.of("lantern", value); }
    public static LanternComponent fromMap(int id, Map<String, Object> m) { â€¦ }
}
```

| Value | Physics effect | Visual |
|-------|---------------|--------|
| < 0.3 | Some PLATFORM tiles treated as SOLID | Full vignette |
| 0.3â€“0.7 | Normal | Partial shadow |
| > 0.7 | Jump height +20%, coyote time 4â†’8 ticks | Clear, warm |

**Server:** Decay âˆ’0.01/s in dark areas or on damage. Restore +0.05 per NPC interaction, +0.2 per Lantern fragment.  
**Client:** `ChunkRenderer` vignette intensity âˆ `1.0 - lanternValue`. At low Lantern, re-rasterize PLATFORM as SOLID visually (matches server physics).

`PlayerState` gains: `lanternValue`.

**Files to create:** `core/sim/LanternComponent.java`

**Files to modify:** `network/PlayerState.java`, `sim/GameSimulator.java`, `client/rendering/ChunkRenderer.java`, `client/rendering/HudRenderer.java`

#### Pivot note â€” updated interpretation of Lantern
**Added:** 2026-04-14 12:00:00 +01:00

Lantern remains implemented and valid, but its priority meaning shifts.

From this point forward, Lantern should be read primarily as:
- a mastery amplifier
- a clarity modifier
- a scaler for the quality, duration, and confidence of Flow expression

It should not replace stance mastery as the main player skill loop.

---

### 3.4 Fragment System

Three new `ItemDef` records in `ItemDatabase` (type `"ability"`, non-stackable):
- `"yin_fragment"` â€” calls `YinYangComponent.absorbYin(0.25f)` on pickup
- `"yang_fragment"` â€” calls `YinYangComponent.absorbYang(0.25f)` on pickup
- `"lantern_fragment"` â€” calls `LanternComponent.restore(0.2f)` on pickup

`EntityPlanner` places fragments in BOSS and TREASURE rooms.  
Three new `ObjectiveType` values: `COLLECT_YIN_FRAGMENT`, `COLLECT_YANG_FRAGMENT`, `COLLECT_LANTERN_FRAGMENT`.

**Files to modify:** `sim/ItemDatabase.java`, `client/game/MissionManager.java`, `world/postprocess/EntityPlanner.java`

---

### 3.5 Hub Evolution System (GDD Â§4)

```java
// core/src/main/java/com/indieniinja/world/HubState.java
public enum HubState {
    FULL,       // Act I: All NPCs, stable environment
    CORRUPTED,  // Act II: NPCs disappearing, prices rise, areas close
    EMPTY,      // Act II end: Only Siren remains
    FRACTURED,  // Hub 2 initial state (Chasm of Still Shadows)
    RECOVERING, // Act V: NPCs return one by one
    WHOLE       // Act VIâ€“VII: Full NPC roster, all abilities
}
```

```java
// core/src/main/java/com/indieniinja/world/HubStateMachine.java
public final class HubStateMachine {
    HubState state = HubState.FULL;
    int bossesDefeated = 0;
    Set<String> fragmentsCollected = new LinkedHashSet<>();

    public void onBossDefeated(String bossId)      { /* advance state */ }
    public void onFragmentCollected(String fragId) { /* may advance state */ }
    public HubState getState()                      { return state; }
    public List<String> activeNpcIds()             { /* NPC roster for current state */ }
    public List<String> openAreaIds()              { /* accessible areas */ }
    public Map<String, Object> toMap()             { /* for player_progress JSON */ }
    public static HubStateMachine fromMap(Map<String, Object> m) { â€¦ }
}
```

**NPC presence:** Each NPC definition in `HubRegistry` carries `visibleFromState` / `hiddenFromState`. `ZoneSimulationLoop` calls `hub.activeNpcIds()` once per second and spawns/despawns `SimNPC` via `EntityLifecycleListener`.

**`WorldSnapshot`** gains `hubState` field (bundled into SCHEMA_VERSION 2 increment with Yin/Yang fields).

**Hub 1 (Bamboo Courtyard) NPC rosters:**
- `FULL`: vendors, mentors, allies, training dummies
- `CORRUPTED`: vendors disappear, mentor dialogue shifts, prices rise
- `EMPTY`: only Siren NPC remains

**Persistence:** `HubStateMachine.toMap()` stored as JSONB in `player_progress.hub_state`. Loaded on connect.

**Files to create:** `world/HubState.java`, `world/HubStateMachine.java`

**Files to modify:** `world/HubRegistry.java`, `network/WorldSnapshot.java`, `server/ZoneSimulationLoop.java`, `server/InventoryRepository.java` (add `player_progress` table), `client/game/StoryManager.java`

---

### 3.6 Narrative Act FSM (GDD Â§5)

```java
// client/src/main/java/com/indieniinja/client/game/Act.java
public enum Act {
    ACT_I_RISE       (1.0f, 1.0f),  // (lanternDefault, hudAlpha)
    ACT_II_FALL      (0.6f, 1.0f),
    ACT_III_LABYRINTH(0.4f, 0.8f),
    ACT_IV_BREAK     (0.2f, 0.1f),  // near-invisible HUD, heavy world
    ACT_V_HEARTH     (0.5f, 0.7f),
    ACT_VI_ASCENT    (0.7f, 1.0f),
    ACT_VII_UPPER    (1.0f, 1.0f);

    public final float lanternDefault;
    public final float hudAlpha;
}
```

Transitions driven by: boss defeats, fragment milestones, hub state changes.

**Act IV depression mechanics** (GDD Â§5):
- `hudAlpha = 0.1f` â†’ near-invisible HUD
- Gravity multiplier `0.7Ã—` â€” `PlayerState` carries `gravityMult`; `PhysicsSystem` applies it
- Dash disabled, jump reduced â€” gated via `AbilityComponent`
- Act V: gradual mechanical restoration

**Files to create:** `client/game/Act.java`

**Files to modify:** `client/game/StoryManager.java`, `client/rendering/HudRenderer.java`, `network/PlayerState.java` (add `gravityMult`), `sim/GameSimulator.java`

---

### 3.7 Boss AI â€” Psychological Patterns (GDD Â§7)

**Note from history:** Boss tuning required 5 successive commits in the Python phase. Design for iteration, not perfection. Ship a working FSM first, tune in follow-up commits.

| Boss | Act | Psychological theme | Core mechanic |
|------|-----|--------------------|--------------||
| Siren of the Veiled Vale | II | Scripted loss | Invincible; triggers on dialogue end; strips Yin/Yang to 0 |
| Echo Warden | III | Self-doubt | Mirrors player movement with 0.5 s delay; walks into hazards if player stops |
| Time Leech Lord | IV | Burnout | Drains Lantern each tick; spawns `TIME_LEECH` enemies; speed burst at 30% HP |
| Memory Eater | VI | Identity loss | Resets platform positions each phase; erases DOOR_LOCKED unlocks |

**Siren:** Not a traditional fight. Server sends new `SCRIPTED_LOSS` `MessageType` when Siren's dialogue sequence completes. Server sets `yin = 0`, `yang = 0` on `YinYangComponent`, calls `HubStateMachine.onBossDefeated("siren")` â†’ hub transitions to `EMPTY`.

**Files to modify:** `sim/SimBoss.java`, `sim/BossAIState.java`, new `sim/BossPatternLibrary.java`, `network/MessageType.java`

### Gameplay identity lock from this point forward
**Added:** 2026-04-14 12:00:00 +01:00

All roadmap and implementation decisions should now be interpreted through the following gameplay identity lock:

Shadow Ascent is being aligned as:
- a campaign-first stealth-action precision platformer
- where players balance Passive and Aggressive playstyles
- to enter Flow
- and master movement, combat, and advanced integration systems

Core identity components:
- Passive stance
- Aggressive stance
- Roll vs Dash mobility identity
- shared combat language
- lethal vs non-lethal differentiation
- aerial directional attacks and throws
- Flow as a mastery state
- Lantern as a mastery amplifier
- readable balance guidance for the player
- Echo and later advanced traversal/combat systems as integration layers

---

### 3.8 Echo System (GDD Â§6)

```java
// core/src/main/java/com/indieniinja/sim/EchoRecorder.java
// 10-second (600-tick) ring buffer of InputCommand per SimPlayer.
public final class EchoRecorder {
    private static final int BUFFER = 600;
    private final InputCommand[] ring = new InputCommand[BUFFER];
    private int head = 0;
    public void record(InputCommand cmd) { ring[head++ % BUFFER] = cmd; }
    public List<InputCommand> snapshot() { /* ordered copy */ }
}

// core/src/main/java/com/indieniinja/sim/SimEcho.java
// Driven by ReplayPlayer (already exists), not InputCommand.
// recallable flag: recalling before echo completes its role fails the puzzle.
```

`WorldSnapshot` gains `echoes` list. `EntityPlanner` places echo trigger zones in PUZZLE rooms.

---

### 3.9 Proof Token Mechanic (Act III â€” GDD Â§5)

- New item: `"proof_token"` (type `key_item`, non-consumable)
- New `AbilityGate` variant: `TOKEN_GATE(n)` â€” requires N tokens
- New `RoomType.LABYRINTH` â€” Act III room archetype
- At `yin < 0.5f`: some PLATFORM tiles rendered as AIR in Act III rooms (intentionally "unfair" â€” server physics unchanged)

---

## 4. File Creation Checklist

Files that must be created (âœ“ = already exists):

```
core/src/main/java/com/indieniinja/
â”œâ”€â”€ world/
â”‚   â”œâ”€â”€ HubState.java          âœ“ (v0.11.1)
â”‚   â””â”€â”€ HubStateMachine.java   âœ“ (v0.11.1)
â””â”€â”€ sim/
    â”œâ”€â”€ YinYangComponent.java  âœ“ (v0.11.6)
    â”œâ”€â”€ LanternComponent.java  âœ“ (v0.11.6)
    â”œâ”€â”€ SimEcho.java           â† M6
    â””â”€â”€ EchoRecorder.java      â† M6

client/src/main/java/com/indieniinja/client/game/
â””â”€â”€ Act.java                   âœ“ (v0.11.1)
```

Files requiring significant modification:

```
core/src/main/java/com/indieniinja/
â”œâ”€â”€ network/
â”‚   â”œâ”€â”€ PlayerState.java          â† yinValue, yangValue, lanternValue, flowMode, gravityMult
â”‚   â””â”€â”€ WorldSnapshot.java        â† hubState, echoes; SCHEMA_VERSION â†’ 2
â”œâ”€â”€ world/
â”‚   â”œâ”€â”€ WorldGraph.java           â† RoomType.LABYRINTH
â”‚   â””â”€â”€ HubRegistry.java          â† store HubStateMachine per hub
â”œâ”€â”€ sim/
â”‚   â”œâ”€â”€ GameSimulator.java         â† Yin/Yang, Lantern, Echo ticking, gravityMult
â”‚   â”œâ”€â”€ SimBoss.java               â† 4 boss behavioral patterns
â”‚   â””â”€â”€ ItemDatabase.java          â† yin/yang/lantern fragments, proof_token
â””â”€â”€ physics/
    â”œâ”€â”€ PhysicsConstants.java      â† ABILITY_YIN_SIGHT flag constant
    â””â”€â”€ CollisionSystem.java       â† ABILITY_YIN_SIGHT hidden platform check

server/src/main/java/com/indieniinja/server/
â”œâ”€â”€ ZoneSimulationLoop.java       â† hub state machine ticking, NPC spawn/despawn
â”œâ”€â”€ InventoryRepository.java      â† player_progress table
â””â”€â”€ (WorldGraphRepository â€” no changes needed)

client/src/main/java/com/indieniinja/client/
â”œâ”€â”€ GameScreen.java               â† offline/solo mode path
â”œâ”€â”€ game/StoryManager.java        â† Act FSM
â”œâ”€â”€ rendering/HudRenderer.java    â† Yin/Yang bar, Lantern meter, act-alpha
â”œâ”€â”€ rendering/ChunkRenderer.java  â† vignette
â””â”€â”€ rendering/EntityRenderer.java â† hidden platform reveal pass
```

---

## 5. Milestone Plan

Commit prefix convention: `feat(m1):`, `feat(m2):`, etc. â€” mirrors the Loop system from the Java rebuild sprint.

### Milestone interpretation update
**Added:** 2026-04-14 12:00:00 +01:00

From this point onward, a milestone may be considered:
- technically shipped
- partially design-complete
- or design-complete

Shipped infrastructure milestones must now also be reviewed for:
- stance clarity
- movement identity
- combat feel
- Flow readability
- campaign-facing usability

**Why added:**  
The live milestone history accurately records shipping progress, but the new gameplay direction makes it important to distinguish â€œimplementedâ€ from â€œfully aligned.â€

---

### Milestone 1 â€” Foundation Close (v0.11.0)
*Fix the two remaining test gaps and the version chaos before anything else.*

- [x] `CollisionEdgeCaseTest`: `lava_upwardContactSetsOnLavaFlag` (`lavaCeilingSetsOnLavaFlag`)
- [x] `CollisionEdgeCaseTest`: `dash_speed_doesNotTunnelThinWall` (`wallStopsEntityAtDashSpeed`)
- [x] Fix `version.json` â†’ `0.10.83`, `build.gradle.kts` â†’ `0.10.83`
- [x] Fix `NET-1`: remove `zone.spawnX != 0` fallback in `ZoneSimulationLoop` (grid-0,0 spawn was silently wrong)

**Deliverable:** Physics is regression-proof. Version numbers are honest. No known correctness bugs.

---

### Milestone 2 â€” In-Process Solo Mode (v0.11.0, same release)
*The entire game must be playable without a running server.*

- [x] `ModeSelectScreen`: add "Solo" option (4th card, purple, passes `"solo"` gameMode)
- [x] `GameScreen`: offline path â€” local `GameSimulator`, no `NetworkClientThread`
- [x] Input fed directly to local sim via `sim.step(Map.of(0, cmd))`; `WorldSnapshot` pushed to `GameStateBuffer`
- [x] Solo and multiplayer share the same rendering pipeline (single-room tile fallback + `stampSoloFields`)

**Deliverable:** Can start a game with no server. Multiplayer remains unchanged.

---

### Milestone 3 â€” Hub Evolution (v0.11.1)
*The hub breathes. NPCs appear and disappear. Acts Iâ€“II are playable.*

- [x] `HubState.java` + `HubStateMachine.java`
- [x] `HubStateMachine` stored per `ZoneInstance`; server ticks FSM at 1 Hz in `ZoneSimulationLoop`
- [x] `SimNPC` spawned/despawned via `GameSimulator.addNpc/removeNpc` driven by `activeNpcTypes()`
- [x] `WorldSnapshot.hubState` field
- [x] `Act.java` FSM â€” Acts Iâ€“VI wired (hub state transition triggers act change)
- [x] `StoryManager` reads `hubState` â†’ drives act FSM; `GameScreen` wires it on every snapshot
- [x] Hub 1 (Bamboo Courtyard): FULL / CORRUPTED / EMPTY roster; Hub 2: FRACTURED / RECOVERING / WHOLE
- [x] `player_progress` table with `hub_state JSONB` column (persisted on zone leave)

**Deliverable:** Playable Acts Iâ€“II. Enter full hub, watch it corrupt, Siren trigger, hub collapses.

---

### Milestone 4 â€” Yin/Yang & Lantern (v0.11.6) âœ“ SHIPPED

*The core emotional mechanics are functional and visible.*

- [x] `YinYangComponent` (server tick: decay, yin_sight flag, balanced check)
- [x] `LanternComponent` (server decay/restore, dark-room check, jump bonus)
- [x] `PlayerState` + `WorldSnapshot` updated (SCHEMA_VERSION â†’ 2, 5 new fields)
- [x] `HudRenderer` Yin/Yang bars + Lantern meter (glow states, Flow Mode indicator)
- [x] `ChunkRenderer` vignette (12-layer screen-edge overlay, red-tint at low lantern)
- [x] `ABILITY_YIN_SIGHT` bitmask in `PhysicsConstants`; set/cleared in `GameSimulator.tickYinYang()`
- [x] Fragment items in `ItemDatabase` + placed by `EntityPlanner` in BOSS/TREASURE rooms
- [x] Weapon-state animation routing in `EntityRenderer` (`player_sword_*` prefix)
- [x] 171 player sprite sheets extracted: 81 unarmed, 90 sword (tools/extract_animations.py)
- [x] `AnimationRegistry.loadUnarmedSheets()` + `loadSwordSheets()` â€” 130+ animation keys
- [x] Siren: scripted loss â†’ Yin/Yang â†’ 0 â†’ hub state â†’ EMPTY

**Deliverable:** Yin/Yang bars and Lantern meter render live. Low Lantern creates oppressive vignette. Fragments spawn in boss/treasure rooms. Full player animation set loaded from template sheets.

#### Pivot interpretation note
**Added:** 2026-04-14 12:00:00 +01:00

Milestone 4 remains shipped and important. However, its original interpretation should now be treated as foundational rather than final.

Milestone 4 should now be read as:
- the data and presentation foundation for the later stance/Flow system
- not the final design definition of Passive/Aggressive stance gameplay

What remains to be aligned on top of M4:
- Passive vs Aggressive stance readability
- Roll vs Dash movement expression
- balance indicator refinement
- Flow UX refinement
- reinterpretation of Yin/Yang values as stance/balance support rather than the core fantasy themselves

---

### Milestone 5 â€” Boss AI (v0.11.10) âœ“ SHIPPED

*Four bosses, each with a distinct psychological pattern. Ship working FSMs first, tune after.*

- [x] Shadow Ascent `BossType` values: SIREN, ECHO_WARDEN, TIME_LEECH_LORD, MEMORY_EATER
- [x] `BossPatternLibrary.java` â€” 4 psychological patterns (ScriptedLoss, EchoMirror, LanternDrain, PhaseReset)
- [x] `SCRIPTED_LOSS` `MessageType` added; `GameSimulator.drainPendingScriptedLoss()` poll method
- [x] `GameSimulator.setHub()` injection point; narrative patterns wired in `stepBosses()`
- [x] Siren: invincible; after 6 s song sequence â†’ zero all Yin/Yang â†’ `hub.onSirenDefeated()` â†’ `SCRIPTED_LOSS`
- [x] Echo Warden: 30-tick ring buffer mirrors player movement with 0.5 s delay
- [x] Time Leech Lord: drains Lantern each tick; spawns `time_leech` enemies every 8 s; speed burst at 30% HP
- [x] Memory Eater: `boss.platformReset` flag set on phase transition; `ZoneSimulationLoop` reads and acts on it
- [x] Client collapse animation on `SCRIPTED_LOSS` receive (runtime collapse state + renderer fallback path)
- [x] Boss defeat â†’ fragment drop â†’ `HubStateMachine.onBossDefeated()` (immediate queue drain in `ZoneSimulationLoop`)

**What shipped:** All 4 psychological patterns are live server-side. Siren scripted loss fires correctly. Echo Warden mirrors movement. Time Leech Lord drains lantern and spawns minions. Memory Eater signals platform reset per phase. Client collapse readability and immediate boss-defeat hub progression wiring are now integrated and regression-covered.

Loop note (2026-04-13 21:27:17 +01:00): Enemy combat tuning pass shipped after M5:
slime attack hitbox now lunges one body-length forward, skeleton attack range is
extended by 15%, and archers now fire projectile attacks that damage players.

**Note:** Boss tuning (HP, timings, difficulty) will need iteration after first playtests â€” Lesson 1 from project history.

#### Pivot tuning note
**Added:** 2026-04-14 12:00:00 +01:00

Bosses should now be tuned not only for:
- difficulty
- pacing
- pattern readability

but also for:
- stance-switching opportunities
- Passive vs Aggressive expression
- Flow entry pressure and payoff
- movement chaining opportunities
- multiplayer stance synergy where relevant

---

### Milestone 6 â€” Echo System & Puzzles (v0.11.11)

*Solo play feels co-op through echoes. Puzzle rooms are distinct.*

- [x] `EchoRecorder` (600-tick ring buffer on `SimPlayer`)
- [x] `SimEcho` (`ReplayPlayer`-driven, `recallable` flag)
- [x] Authored echo trigger puzzle markers placed by `PuzzleLayer` and mapped as interactable NPC markers in unified layout
- [ ] Puzzle archetype: **Asymmetric Ability Lock** (echo holds position)
- [ ] Puzzle archetype: **Simultaneous Timing** (echo replicates past actions)
- [ ] Proof token mechanic (`RoomType.LABYRINTH`, `TOKEN_GATE`)
- [ ] `ValidationLayer` verifies all puzzles solvable with current ability set

Loop note (2026-04-13 19:36:16 +01:00): `EchoRecorder` added in `core/sim`, integrated on `SimPlayer`,
and sampled each tick in `GameSimulator.step()`; covered by `EchoRecorderTest`.
Loop note (2026-04-13 20:03:24 +01:00): `SimEcho` added as a `ReplayPlayer`-driven entity with
`recallable` fail semantics; `GameSimulator` now supports echo spawn/tick/recall
hooks (`spawnEchoFromPlayer`, `addEcho`, `stepEchoes`, `recallEcho`), and behavior
is covered by `SimEchoTest`.

**Deliverable:** Puzzle rooms are mechanically interesting solo. Act III "unfair" platforms work.

#### Pivot scope-control note
**Added:** 2026-04-14 12:00:00 +01:00

Echo should first ship as:
- authored, testable, understandable puzzle support
- optional late combat support only where readability remains high
- a solo/co-op coordination language

Echo should not expand into broad systemic complexity until:
- stance feel is locked
- Flow readability is locked
- campaign pacing is stable

---

### Milestone 7 â€” Act IV & Narrative Arc (v0.11.12)

*The 7-act emotional arc is playable end-to-end.*

- [ ] Full `Act.java` FSM â€” all 7 acts with `hudAlpha` and `lanternDefault`
- [ ] `HudRenderer` alpha driven by `currentAct.hudAlpha` (Act IV â†’ 0.1)
- [ ] `gravityMult` on `PlayerState`; `PhysicsSystem` applies it (Act IV â†’ 0.7Ã—)
- [ ] Dash/jump restricted in Act IV
- [ ] Act V: gradual mechanical restoration per tick
- [ ] Act VII: full abilities, full HUD, complete hub
- [ ] Hub 2 (Chasm of Still Shadows): FRACTURED â†’ RECOVERING â†’ WHOLE wired

**Deliverable:** A player can experience the full emotional arc from Act I through Act VII in one session.

---

### Milestone 8 â€” Polish (v0.11.13+)

- [ ] Music / BGM hooks (Lantern-dynamic music system)
- [ ] Gamepad support (`InputPoller` extension)
- [ ] Act-based palette shifts and fog density in `ChunkRenderer`
- [ ] New game+ (remixed hub progression)
- [ ] Alternate endings based on Yin/Yang balance at Act VII
- [x] Playtest logging + controls evidence baseline (`[Playtest][*]`, `[Mission]`, controls preset signature in startup logs)
- [x] NPC runtime scale/hitbox parity baseline (`NPCState.width/height` wired end-to-end; removed hardcoded `32x48` client assumptions)
- [x] Map tap/hold readability baseline (`Tab` tap quick map toggle, `Tab` hold full map while held, explicit on-map key guidance text)
- [ ] Fix `version.json`, `build.gradle.kts`, and `README.md` in sync after each release

#### Added polish targets from this pivot
- balance indicator refinement
- stance silhouette refinement
- Roll vs Dash readability refinement
- Flow visual/audio refinement
- combat hit feedback refinement
- aerial attack/throw readability refinement

---

## 6. Design Decisions

| Question | Decision |
|----------|----------|
| Solo mode | `GameScreen` offline path: local `GameSimulator`, no socket. Toggle via `ModeSelectScreen`. |
| Co-op Yin/Yang | Each player has own Yin/Yang. Flow Mode requires both balanced. Zone Lantern = average. |
| Hub state persistence | `HubStateMachine.toMap()` in `player_progress.hub_state JSONB`. Loaded on connect. |
| Siren encounter | Not a traditional fight. `SCRIPTED_LOSS` message sent when dialogue completes. |
| Act III hidden platforms | Server treats tiles as PLATFORM (authoritative). Client hides sprite when `yin < 0.5f`. Intentional. |
| Echo moral tension | `recallable` flag. Recalling before completion fails the puzzle. Player chooses. |
| SCHEMA_VERSION timing | Increment to 2 when Milestone 4 fields land. Bundle all new `PlayerState` fields in one bump. |
| Commit prefix | `feat(m1):`, `feat(m2):` etc. â€” mirrors Loop system, maintains git traceability. |
| Version discipline | After every milestone release: `version.json`, `build.gradle.kts`, and `README.md` must match. |

### Design decisions added by pivot
**Added:** 2026-04-14 12:00:00 +01:00

| Question | Decision |
|----------|----------|
| Core stance split | Passive and Aggressive are the active gameplay stances from this point forward |
| Mobility identity | Passive centers on Roll; Aggressive centers on Dash |
| Combat posture | Passive defaults to Unarmed readability; Aggressive defaults to Armed readability |
| Combat language | Both stances share block, parry, 5-hit combo, aerial attacks, and aerial throws |
| Lethality split | Passive play is primarily non-lethal/control oriented; Aggressive play is primarily lethal/pressure oriented |
| Throw behavior | Same input, stance-dependent outcome: smoke/distraction in Passive, weapon projectile in Aggressive |
| Flow readability | Balance indicator is required and uses a combined solution: player ring + stance glow + Flow afterimage/pulse |
| Flow feel | Flow should primarily improve smoothness, chaining, responsiveness, and clarity rather than acting as a raw stat spike |
| Trials identity | Trials must reinforce the same stance/Flow/movement/combat language as Campaign |

### Co-op interpretation note from pivot date
**Added:** 2026-04-14 12:00:00 +01:00

The earlier co-op Yin/Yang framing should now be read more flexibly:

- Each player maintains their own local balance state.
- Flow should remain primarily readable and earnable at the per-player level.
- Co-op design should reward Passive/Aggressive synergy, but one playerâ€™s imbalance should not trivially hard-lock another playerâ€™s ability to understand or access their own Flow.
- Shared team-level modifiers may still exist where appropriate, but local readability must come first.

---

## 7. Success Criteria

### Success-criteria addendum from pivot date
**Added:** 2026-04-14 12:00:00 +01:00

In addition to the structural campaign criteria already listed below, this plan now also succeeds when the following are true:

1. A player can read the gameâ€™s identity quickly:
   - Passive feels stealthy/control-oriented
   - Aggressive feels forceful/pressure-oriented

2. The player can distinguish and use:
   - Roll vs Dash
   - smoke throw vs weapon throw
   - unarmed vs armed posture
   - non-lethal vs lethal combat outcomes

3. The player can perform and understand:
   - block
   - parry
   - 5-hit combo
   - aerial directional attacks
   - aerial directional throws

4. The player can understand how to reach Flow:
   - balance indicator is readable
   - stance leaning is understandable
   - Flow activation feels intentional rather than accidental

5. Flow feels like mastery:
   - smoother
   - cleaner
   - more confident
   - not merely overpowered

6. Trials feel like extensions of the same game:
   - not a detached arcade ruleset
   - but a mastery surface for the same movement/combat/Flow language

7. Echo and later advanced systems deepen the core loop rather than replacing it.

Complete when a player can, in a single session:

1. Start solo mode with no server
2. Play Act I in the Bamboo Courtyard with the full NPC roster
3. Collect a Yin fragment â€” watch hidden platforms materialise
4. Collect a Yang fragment â€” watch attack strength increase
5. Encounter the Siren, lose in a scripted sequence, watch the hub collapse
6. Enter Hub 2 (Chasm of Still Shadows) and watch NPCs return through Acts IIIâ€“V
7. Solve a puzzle room using an echo of their own past movement
8. Collect enough fragments in Act VI to trigger Flow Mode
9. Reach Act VII with full abilities, a populated final hub
10. Receive a narrative resolution that was felt, not told

---

## Current Priority Order From Pivot Date
**Added:** 2026-04-14 12:00:00 +01:00

### Priority 1 â€” Campaign structural reliability
Includes:
- mission lifecycle
- save/load parity
- scripted-loss integrity
- hub progression correctness
- solo and co-op campaign stability

### Priority 2 â€” Stance / Flow gameplay identity lock
Includes:
- Passive vs Aggressive distinction
- Roll vs Dash feel
- armed/unarmed readability
- block/parry/combo feel
- aerial directional combat readability
- smoke vs weapon throw clarity
- balance indicator usability
- Flow readability and satisfaction

### Priority 3 â€” Trials integration under the new gameplay language
Trials should be replayable mastery spaces built from the same stance/Flow language.

### Priority 4 â€” Content throughput and authored depth
Includes:
- mission breadth
- puzzle breadth
- boss encounter tuning
- authored Trials buckets
- Echo-authored content
- advanced traversal/combat integration

### Priority 5 â€” Raids and late prestige challenge content
Keep this late and subordinate.

---

## Do-Not-Regress Rules
**Added:** 2026-04-14 12:00:00 +01:00

### Do not regress product clarity
Do not reintroduce framing that makes the project appear to be:
- multiple equal flagship games
- a sandbox-led roadmap
- an arcade-first identity
- a mechanically generic platformer with abstract meters

### Do not regress stance readability
Do not allow ongoing tuning to collapse Passive and Aggressive into cosmetic variations of the same playstyle.

### Do not regress movement identity
Roll and Dash must remain clearly differentiated in:
- feel
- silhouette
- use case
- audio/visual feedback

### Do not regress combat clarity
The gameâ€™s combat language should remain simple to understand and deep to master.

Shared:
- block
- parry
- 5-hit combo
- aerial directionals
- aerial throws

Differences should come from:
- lethality
- mobility identity
- posture/readability
- Flow interaction

### Do not regress Flow readability
Players must continue to be able to understand:
- which way they are leaning
- how to rebalance
- when Flow has activated
- why Flow feels different

### Do not regress campaign-first discipline
Trials, Raids, Echo complexity, and advanced systems must not destabilize:
- campaign readability
- campaign pacing
- solo/co-op parity
- save/load reliability
- boss consequence loops

---

## Plan Maintenance Rule After Pivot
**Added:** 2026-04-14 12:00:00 +01:00

Any future update to `docs/plans/implementing/PLAN_SHADOW_ASCENT.md` that changes:
- stance interpretation
- Flow interpretation
- combat identity
- Trials purpose
- co-op Flow rules
- balance indicator/readability requirements

must include:
1. timestamp
2. what changed
3. why it changed
4. whether it changes product direction, gameplay identity, or only implementation detail

---

## Updated Final Statement of Scope
**Added:** 2026-04-14 12:00:00 +01:00

Shadow Ascent remains:
- one campaign-first game,
- with solo play and first-class drop-in/drop-out co-op in Campaign,
- plus repeatable Trials,
- and optional future Raids.

That product direction does not change.

What has changed is the gameplay identity lock inside that structure.

From this point forward, Shadow Ascent should be interpreted and built as:
- a movement-first stealth-action platformer,
- with Passive and Aggressive stance play,
- Roll and Dash as distinct mobility identities,
- shared combat language differentiated by lethality and posture,
- Flow as the primary mastery reward for balanced play,
- Lantern as a mastery amplifier,
- and Trials as replayable mastery extensions of the same gameplay language.

Sandbox remains removed.  
Trials remain subordinate to Campaign.  
The codebase remains directed toward finishing the game it has already become.

---

## Maintainer Note
**Added:** 2026-04-14 12:00:00 +01:00

This document should now be read as having three layers:

1. Operational roadmap  
2. Implementation history  
3. Gameplay identity alignment  

Do not strip out the implementation history unless it is first archived elsewhere, because it remains useful for milestone traceability.  
Do not treat the gameplay identity sections as optional commentary, because they now define how the roadmap should be interpreted.

---

*Living document. Update milestone checkboxes as work progresses. Archive completed milestones to `docs/archive/`.*

---

## Worldgen Improvement Lane — LayerProcGen-Informed Act I Layout Quality

**Added:** 2026-05-02 — sourced from `docs/dev/LAYERPROCGEN_WORLDGEN_ANALYSIS.md`

### Task Intake Brief

**Goal:** Reduce Act I worldgen `critical_path_transition_debt` to zero and produce level layouts that match the narrative beat sequence, using principles derived from the LayerProcGen framework.

**Player-facing impact:** Act I layouts will always be traversable from hub to boss without requiring bridge rooms the engine cannot yet insert. Critical path rooms will have correct environmental transitions — forest trial rooms lead naturally into lantern approach rooms without abrupt geography mismatch.

**Systems touched:**
- `data/worldgen/sections/*.json` — authored socket compatibility
- `java/shadowascent/.../world/validation/GenerationValidationPlanner.java` — `critical_path_transition_debt` check
- `java/shadowascent/.../world/postprocess/EntityPlanner.java` — seam clearance for entity placement
- `docs/systems/WORLD_GEN.md` — seam clearance contract documentation

**Risks:**
- Socket changes are snapshot-schema-visible but not replay-breaking (worldgen changes only affect newly generated worlds).
- EntityPlanner clearance is a placement-behaviour change — entity counts near section boundaries will change. This is intentional.
- Any socket change that reduces the candidate pool for a given progression node must be verified not to block layout planning (HybridLayoutPlanner must still find a valid section assignment).

**Required tests:**
- `GenerationValidationPlannerTest` — verify `critical_path_transition_debt` count ≤ 0 for Act I after socket fixes
- `SectionTemplateLibraryTest` — verify patched sections still load in strict mode
- `WorldGenSnapshotCommand` — regenerate seed 420, capture `qualityScoreV2` delta
- `EntityPlanner` seam clearance test — new test asserting no enemies in boundary rooms

**Required docs to update:**
- `docs/CURRENT_STATE.md` — new active slice entry + snapshot quality delta
- `docs/systems/WORLD_GEN.md` — seam clearance zone contract description
- `docs/CHANGELOG.md` — per-version entries
- `PLAN_SHADOW_ASCENT.md` loop note — this document

**Rollback plan:**
- Socket fixes: revert the three JSON edits; regenerate snapshot. No code changes.
- EntityPlanner clearance: feature-flag via `-Dninja.entityPlanner.seamClearanceRooms=0` (default 2).

**Escalation conditions:**
- If socket fix reduces template candidate pool to 0 for any `(biome, kind)` required by Act I progression, stop and author a new section variant before continuing.
- If seed sweep shows 20%+ seeds produce `valid=false` after fixes (regression), escalate before tagging.

---

### Implementation Queue

#### WG-1 — Fix socket mismatches in authored section templates *(data-only)*

Root cause of `socketCompatibilityScore=33` and `critical_path_transition_debt x2`:

| Section | Field | Old value | New value | Reason |
| ------- | ----- | --------- | --------- | ------ |
| `forest_key_trial_ruins` | `requiredSockets` | `["west_mid_jump","east_mid_jump"]` | *(unchanged)* | Hub (`hub_home` kind) is not in connectionContracts — ruins↔ruins mission chain already compatible. |
| `forest_key_trial_canopy` | `requiredSockets[0]` | `west_low_walk` | `west_mid_jump` | Mission chain requires mid-jump entry to match ruins→canopy contract. |
| `forest_key_trial_canopy` | `requiredSockets[1]` | `east_high_climb` | `east_high_jump` | climb-exit has no compatible boss-approach entry; high_jump↔mid_jump is one-step valid. |
| `lantern_boss_approach_sanctum` | `requiredSockets[0]` | `west_low_walk` | `west_mid_jump` | All forest trials exit at `east_mid_jump`; sanctum entry must accept mid-jump. |

Compatibility check after fix:

| Chain | Hub→Trial | Trial→Boss | Valid? |
| ----- | --------- | ---------- | ------ |
| hub → ruins → ascension | `east_low_walk`↔`west_low_walk` ✓ | `east_mid_jump`↔`west_mid_jump` ✓ | ✓ |
| hub → canopy → ascension | `east_low_walk`↔`west_low_walk` ✓ | `east_high_jump`↔`west_mid_jump` (band one-step, same traversal) ✓ | ✓ |
| hub → trial → sanctum | `east_low_walk`↔`west_low_walk` ✓ | `east_mid_jump`↔`west_mid_jump` ✓ | ✓ |
| hub → riverbank → ascension | `east_low_walk`↔`west_low_walk` ✓ | `east_mid_jump`↔`west_mid_jump` ✓ | ✓ |

- [x] Apply the three JSON edits (canopy west+east, sanctum west). Ruins unchanged — hub not in contract chain.
- [x] Seed 420 snapshot regenerated: `qualityScoreV2=96`, `transitionDebtPenalty=0`, `socketCompatibilityScore=100` (all 3 contracts matched) — 2026-05-02.
- [x] `SectionTemplateLibraryTest` (4/4 PASSED) — 2026-05-02.
- [x] `GenerationValidationPlannerTest` (4/4 PASSED) — 2026-05-02.
- [x] Update `docs/CURRENT_STATE.md` with new snapshot quality numbers — 2026-05-03.
- [x] Bump version to v0.13.29, commit, tag, push — 2026-05-03.

**Compatibility:** replay=no | save=no | protocol=no | snapshot schema=11 (unchanged)

---

#### WG-2 — Seed sweep quality baseline *(tooling-only)*

- [x] Run `python tools/worldgen_lab.py batch --seeds 50 --rooms 20 --shape BLOB --out build/worldgen-lab/sweep-50 --failures 5` — 2026-05-03.
- [x] Save summary: `docs/reports/worldgen/sweep-50-v0.13.29.csv` — 2026-05-03.
- [x] Capture worst 5 seeds and their failure modes to `docs/reports/worldgen/sweep-50-failures.md` — 2026-05-03.
- [ ] Update `PLAN_WORLDGEN_RUNTIME_ADOPTION.md` with sweep evidence (deferred 1..250 partial).

**Compatibility:** tooling-only, no code/data change.

---

#### WG-3 — EntityPlanner seam clearance *(Java + test)*

Apply the LayerProcGen effect-distance principle: no enemy spawns or hazard tiles within the outermost 2 rooms of a section boundary.

**Mechanism:** `SocketAnchorPlan.resolvedAnchors` already records section world-space bounds. `EntityPlanner.computeSpawn()` can check whether a candidate spawn room is within `seamClearanceRooms` distance of any section-boundary room and skip enemy placement there.

- [x] Add `isSeamRoom` boolean to `EntityPlanner.placeEnemies()` — early-returns `List.of()` when true.
- [x] `RoomPostProcessor.process()` accepts `Set<String> seamRoomKeys`; backward-compat overload passes `Collections.emptySet()`.
- [x] 5 unit tests in `EntityPlannerSeamClearanceTest` — all PASSED (2026-05-02).
- [x] Update `docs/systems/WORLD_GEN.md` with seam clearance contract description.
- [x] Bumped with WG-1 as v0.13.29 (single combined release) — 2026-05-03.

**Compatibility:** replay=breaking for worlds where boundary-room enemy placement would have changed | save=no | protocol=no

---

#### WG-4 — Forest trial authored room templates *(content authoring)*

Add TMX templates for forest trial rooms that match the narrative beat: platforming challenge that reads as "forest ruin" or "canopy path" to ground the player's location emotionally before they reach the boss approach.

- [x] Author `java/assets/rooms/templates/platform_ascent_forest.tmx` — 128×128, staggered ascending platforms with climbable vine strips (tile 8). 2026-05-03.
- [x] Author `java/assets/rooms/templates/combat_standard_forest_ruins.tmx` — 128×128, broken stone floor with ruin ledges, pillar rubble, irregular platform heights. 2026-05-03.
- [x] Register both in `data/room_template_catalog.json` as weighted variants: `platform_ascent` (base w=2, forest w=1), `combat_standard` (base w=2, forest w=1). Note: catalog does not support biome filter field — variants are weighted globally. 2026-05-03.
- [x] `validate_room_templates.py --strict-geometry --catalog` — all 12 templates OK. 2026-05-03.
- [x] Seed 420 snapshot regenerated — `qualityScoreV2=96`, `valid=true`, `socketCompatibilityScore=100` (stable). `RoomTemplateCatalogTest` 3/3 PASS. 2026-05-03.
- [ ] Bump version to v0.13.30, commit, tag, push.

**Compatibility:** replay=breaking (template selection changes for forest rooms) | save=no | protocol=no

---

### Loop Note

`2026-05-02 00:00:00 +01:00` — WorldGen improvement lane opened.

- LayerProcGen analysis complete: `docs/dev/LAYERPROCGEN_WORLDGEN_ANALYSIS.md`
- Root cause of `critical_path_transition_debt x2` identified: 3 socket mismatches in authored section JSON data.
- `socketCompatibilityScore=33` → expected to rise to 100 after WG-1 socket fixes (all Act I chains become compatible).
- Implementation priority order: WG-1 (data-only, immediate) → WG-2 (tooling sweep) → WG-3 (seam clearance) → WG-4 (room templates).
- WG-3 and WG-4 are decoupled; either can proceed after WG-1.
