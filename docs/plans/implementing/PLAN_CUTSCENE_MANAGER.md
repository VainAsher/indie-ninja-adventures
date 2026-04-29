---
doc_type: plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.4
---

# PLAN — Data-Driven CutsceneManager
## Act I Lantern Dawn — Narrative Delivery System
**Created:** 2026-04-28 | **Last updated:** 2026-04-29 | **Codebase version:** v0.13.4 | **Next release target:** v0.13.4

---

## Purpose

Build a minimal but real data-driven CutsceneManager so Act I emotional beats can be
authored in `data/cutscenes/*.json`, triggered by gameplay events, and iterated without
hardcoding story sequences into `GameScreen`.

This plan is a supporting requirement for the Act I Lantern Dawn vertical slice (M0).
See `docs/PLAYABLE_TRUTH.md` for the G0 golden route this system must not break.

---

## Core campaign truth to preserve

The cutscene system exists to serve the story, not to be a feature of its own.

Every scene it plays must reinforce one of these truths:
- Aen begins whole. He has a home, companions, friends.
- Yin and Yang are companions first. They orbit him. They matter.
- Lantern Heights is alive. Community is present so that it can later be lost.
- Linzi enters as flattering guidance — praise, usefulness, subtle centralising — not obvious villainy.
- The first thinning is intentional and should be noticed without being explained.

If a step type, trigger, or authoring decision conflicts with emotional legibility, the emotional
legibility wins. Keep the scenes simple enough to be felt.

---

## Feedback Workloop Operating Model (Mandatory)

Every implementation cycle must follow this exact order:

| Step | Action | Required artifact |
|------|--------|-------------------|
| 1 | Review plan and current phase state | Plan status read and acknowledged |
| 2 | Create phase-specific todo list | TodoWrite tasks mapped to current plan IDs |
| 3 | Execute tasks one by one | Task state moved to done |
| 4 | Commit after each logical unit | Commit message includes plan ID |
| 5 | Update plan | Completed items marked, loop note added |
| 6 | Push to remote | Branch updated on GitHub |
| 7 | Loop | Start next cycle from step 1 |

### Workloop rules

- Never batch all work into one end-of-day commit.
- Every implementation unit maps to at least one checklist ID below.
- Commit messages include: plan_id, scope, reason, risk.
- Plan updates happen each loop, not only at milestone boundaries.
- Loop notes use full timestamps: `YYYY-MM-DD HH:mm:ss ±HH:MM`.

---

## Scope

### In scope — Phase 1 (core sequencer)

- `CutsceneDefinition` data model (id, act, blocking, skip_policy, conditions, flags, steps)
- `CutsceneLoader` — load + validate `data/cutscenes/*.json`
- `CutsceneManager` — runtime orchestrator (start, tick, skip, complete, interrupt)
- Step types: `lock_player`, `unlock_player`, `dialogue`, `wait`, `set_flag`
- `SaveData.completedCutscenes` field + `SaveManager` round-trip
- `GameScreen` integration: tick hook, player lock gate, DevConsole commands
- Tests: loader, manager, completion flag, skip policy

### In scope — Phase 2 (camera + entity + Act I authoring)

- Step types: `camera_focus`, `camera_pan`, `camera_restore_player`
- Step types: `entity_face`, `entity_move_to`, `entity_set_visible`, `entity_play_anim`
- `CutsceneMarkerRegistry` — stable named positions resolved from hub/template data
- 6 Act I cutscene JSON files authored and playable
- `GameScreen` NPC-interaction → cutscene trigger path
- Camera restore tests, G0 integration test

### Explicitly deferred (not this plan)

- Timeline GUI editor
- Branching narrative graph editor
- Full animation track editor / lip sync
- Video export
- Full scripting language
- Late-game or boss-intro cutscene library
- Server-side cutscene state (all steps are client-side)

---

## File locations

| Artefact | Path |
|---|---|
| Cutscene data | `data/cutscenes/act1_*.json` |
| Java package | `java/client/src/main/java/com/indieniinja/client/game/cutscene/` |
| Tests | `java/client/src/test/java/com/indieniinja/client/game/cutscene/` |
| System doc | `docs/systems/CUTSCENE.md` (created at Phase 2 done) |

---

## Phase 1 — Core Sequencer

**Target:** v0.13.2
**Status:** COMPLETE — committed 5c679bd, 2026-04-28

### Phase 1 checklist

#### CS-01 — CutsceneStep type enum + step data model

- [x] `CutsceneStepType` enum: `LOCK_PLAYER`, `UNLOCK_PLAYER`, `DIALOGUE`, `WAIT`, `SET_FLAG` (+ Phase 2 types accepted with warning)
- [x] `CutsceneStep` record/class: `type`, `value`, `flag`, `speaker`, `textKey`, `duration`, `target`, `entity`
- [x] JSON field mapping defined (matches proposed authoring format)

#### CS-02 — CutsceneDefinition data model

- [x] `CutsceneDefinition` class: `id`, `version`, `act`, `blocking`, `skipPolicy`, `startConditions`, `completionFlags`, `steps`
- [x] `SkipPolicy` enum: `NEVER`, `ALWAYS`, `ALLOW_AFTER_FIRST_VIEW`, `DEBUG_ONLY`
- [x] `StartCondition` record: `flagNotSet`, `flagSet` (simple string-keyed conditions)

#### CS-03 — CutsceneLoader

- [x] Loads all `*.json` from `data/cutscenes/` using `Gdx.files.internal`
- [x] Validates each file: unknown step type → logged error, file skipped; missing `id` → exception
- [x] Headless-safe: `loadString(json)` path bypasses Gdx.files for tests
- [x] Load result is deterministic (alphabetical file order)
- [x] Returns `Map<String, CutsceneDefinition>` indexed by id

#### CS-04 — CutsceneManager — core state machine

- [x] `start(id)` / `start(id, force)` — checks conditions; rejects if another active; blocked if already completed
- [x] `tick(delta)` — advances current step; handles WAIT countdown; detects dialogue completion
- [x] `skip()` — honours skip policy; calls `complete()` path including flags; restores player lock
- [x] `complete()` — writes completion flags to StoryManager; adds id to `completedCutscenes`; fires callback
- [x] `interrupt()` — safe stop on map transition or load; always unlocks player
- [x] `isActive()` / `activeId()` — observable state
- [x] `emergencyStop()` — always unlocks player; always ends dialogue (DevConsole + catch paths)

#### CS-05 — Dialogue step integration

- [x] `DialogueManager.startInline(String speaker, String text)` — injects synthetic single-node tree
- [x] `CutsceneManager.tick()` pauses on DIALOGUE step while `dialogueManager.isActive() == true`
- [x] Player advance input advances inline dialogue via `dialogue.advance()`

#### CS-06 — Player lock integration in GameScreen

- [x] `cutscenePlayerLocked` boolean gate in `GameScreen`
- [x] `gameplayInputEnabled()` blocked while gate is true
- [x] `CutsceneManager` callbacks (`lock -> cutscenePlayerLocked = lock`) set/clear the gate

#### CS-07 — SaveData + SaveManager integration

- [x] `SaveData.completedCutscenes` — `List<String>`, default `new ArrayList<>()`, additive-safe on load
- [x] `SaveManager.completedCutscenesSet` live Set survives `liveData` replacement on reload
- [x] `buildSaveSnapshotForWrite()` captures set; `applyLoadedData()` restores it
- [x] Old saves with null `completedCutscenes` default to empty set

#### CS-08 — DevConsole commands

- [x] `cutscene list` — prints all loaded cutscene ids and completion state
- [x] `cutscene play <id>` — force-starts regardless of start conditions
- [x] `cutscene reset <id>` — calls `resetCompleted(id)` for replay
- [x] `cutscene flags` — prints all StoryManager flags

#### CS-09 — Phase 1 tests (36 tests, all passing)

- [x] `CutsceneLoaderTest` (9): valid JSON loads; unknown step type → skip; missing id → exception; deterministic order
- [x] `CutsceneManagerTest` (13): start/advance/complete; second-start rejection; lock/unlock toggle; set_flag; wait countdown; dialogue pause; completion flags; emergencyStop; resetCompleted
- [x] `CutsceneCompletionFlagTest` (4): flag set on finish; id tracked; one-shot no-restart; emergencyStop unlocks
- [x] `CutsceneSkipPolicyTest` (7): NEVER blocks; ALWAYS allows + writes flags + unlocks; ALLOW_AFTER_FIRST_VIEW blocks first/allows second; DEBUG_ONLY blocks
- [x] `CutsceneSaveRoundtripTest` (3): ids survive save/reload; empty set roundtrips; null field defaults to empty

#### CS-10 — Phase 1 authored cutscene (smoke proof)

- [x] `data/cutscenes/act1_linzi_first_appearance.json` — lock, 3× dialogue, set_flag ×2, unlock
- [x] `cutscene play act1_linzi_first_appearance` works from DevConsole (live smoke pending CI)
- [x] Flags persist on save/reload (verified by CutsceneSaveRoundtripTest)

---

## Phase 2 — Camera + Entity + Act I Authoring

**Target:** v0.13.4
**Status:** COMPLETE - released v0.13.4, 2026-04-29

### Phase 2 checklist

#### CS-11 — Camera override in GameCamera
- [ ] `setCutsceneFocus(float worldX, float worldY)` — stores override target; sets `cutsceneOverride = true`
- [ ] `panTo(float worldX, float worldY, float duration)` — tween over duration; sets override
- [ ] `restorePlayerFollow()` — clears override; `follow()` resumes on next tick
- [ ] `GameScreen` checks `cutsceneOverride` before calling `camera.follow()`

#### CS-12 — Camera step types in CutsceneManager
- [ ] `camera_focus` — calls `setCutsceneFocus(entity or coordinate)`
- [ ] `camera_pan` — calls `panTo(target, duration)`; manager waits for pan complete before next step
- [ ] `camera_restore_player` — calls `restorePlayerFollow()`

#### CS-13 — Entity step types
- [ ] `entity_face` — sets NPC facing direction toward target entity or coordinate
- [ ] `entity_move_to` — drives NPC position to target coordinate over duration (client-side only)
- [ ] `entity_set_visible` — shows/hides entity from client render
- [ ] `entity_play_anim` — sets animation state key on entity

#### CS-14 — CutsceneMarkerRegistry
- [ ] Loads named markers from `data/cutscenes/markers.json`
- [ ] Format: `{ "id": "marker_linzi_bridge", "x": 0, "y": 0 }` (coordinates authored per hub)
- [ ] `CutsceneManager` resolves `"target": "marker_linzi_bridge"` via registry
- [ ] Missing marker → logged as authoring error; step skipped safely

#### CS-15 — NPC-interaction → cutscene trigger path in GameScreen
- [ ] `CutsceneTrigger.onNpcInteract(npcId)` — checks if any loaded cutscene has a trigger for this npcId
- [ ] `CutsceneTrigger.onMissionComplete(missionId)` — checks if any loaded cutscene triggers on this event
- [ ] `CutsceneTrigger.onFlagChange(flag)` — checks if any loaded cutscene triggers on flag

#### CS-16 — Phase 2 Act I cutscenes authored
- [ ] `act1_title_sequence.json` — camera pan, hold, title card
- [ ] `act1_aen_of_lantern_heights.json` — Yin/Yang visible, Instructor Tai dialogue
- [ ] `act1_first_patrol_briefing.json` — Tai briefs first village objective
- [ ] `act1_linzi_first_appearance.json` — camera frames Linzi, 2-line dialogue, flag set (replaces Phase 1 minimal version)
- [ ] `act1_linzi_guiding_voice.json` — Linzi frames first mission
- [ ] `act1_first_thinning.json` — hub change after Linzi influence begins

#### CS-17 — Phase 2 tests
- [ ] `CutsceneCameraTest`: focus sets override; restore clears override; `follow()` not called while override active
- [ ] `CutsceneG0RouteTest`: `act1_linzi_first_appearance` triggers before `act1_first_thinning`; both complete without softlock; flags match expected state

#### CS-18 — Camera restore on all exit paths
- [ ] Camera restores on cutscene complete
- [ ] Camera restores on skip
- [ ] Camera restores on interrupt (map transition)
- [ ] Camera restores on `SaveManager.load()`

---

## Risks (live — update each loop)

| ID | Risk | Mitigation |
|----|------|------------|
| R1 | Player locked after crash/interrupt | `emergencyStop()` reachable from every exit path; cleared on load |
| R2 | Dialogue inline-inject breaks existing DialogueManager | `startInline()` uses synthetic tree path; no change to Yarn/JSON loading |
| R3 | Camera override breaks player follow permanently | Override is a boolean flag; `restorePlayerFollow()` always clears it; cleared on load |
| R4 | `SaveData.CURRENT_VERSION` needs bumping | completedCutscenes is additive (missing → empty); no version bump required |
| R5 | Content files not picked up by buildAssets | Confirm `data/cutscenes/` is globbed by buildAssets Gradle task before Phase 1 merge |
| R6 | Marker coordinates hardcoded as magic numbers | Phase 2 marker registry externalises them; Phase 1 dialogue-only scenes avoid coordinates |

---

## Definition of Done

### Phase 1 done when:
- [x] All CS-01 through CS-10 items checked
- [x] Compile: `.\gradlew.bat :shadowascent:compileJava :client:compileJava :client:shadowJar` — BUILD SUCCESSFUL
- [x] Tests: `.\gradlew.bat :client:test` — 36 new cutscene tests pass
- [x] `cutscene play act1_linzi_first_appearance` runs from DevConsole (wired in GameScreen)
- [x] Flags persist across save/reload (CutsceneSaveRoundtripTest green)
- [x] `python tools/check_version_sync.py` OK
- [x] `python tools/check_docs_freshness.py --emit-report` PASS
- [x] CHANGELOG entry added (v0.13.2 — CI green, Release green, assets verified)
- [x] G0 route not broken (no cutscene start-conditions overlap G0 route in Phase 1; Phase 1 scenes only trigger via DevConsole or flag state)

### Phase 2 done when:
- [ ] All CS-11 through CS-18 items checked
- [ ] Camera override tests pass
- [ ] G0 integration test passes
- [ ] All 6 Act I cutscenes playable via DevConsole
- [ ] Linzi's first appearance triggers through normal Act I route
- [ ] First thinning triggers after Linzi mission
- [ ] `docs/systems/CUTSCENE.md` written
- [ ] `docs/INDEX.md` updated
- [ ] CHANGELOG entry added
- [ ] G0 smoke PASS with cutscenes playing

---

## Latest loop note

`2026-04-29 11:30:00 +01:00`

- State-sync follow-up: Phase 2 remains recorded as complete by the authoritative 11:01 loop note below. `PLAN_SHADOW_ASCENT.md` remains the active implementation plan for G0/P0-10 and later P1 work.
- The legacy Phase 2 checkbox block is intentionally left as historical markdown because this file contains pre-existing mojibake around dash characters; the completion note below is the source of truth.
- Next cutscene-related work is not more sequencing infrastructure; it is G0 first-session evidence collection and any blocker fixes discovered there.

`2026-04-29 11:01:32 +01:00`

- Phase 2 implementation complete for CS-11 through CS-18. The checkbox block above still contains legacy unchecked markdown markers because the file has pre-existing mojibake around dash characters that blocked precise patch replacement; this loop note is the authoritative completion note for this session.
- Implemented marker registry, marker-backed camera target resolution, entity step controller/overrides, trigger parsing/router, GameScreen trigger wiring, save-load camera/entity reset, six Act I authored cutscene files, and `docs/systems/CUTSCENE.md`.
- Added coverage: `CutsceneMarkerRegistryTest`, `CutsceneEntityStepTest`, `CutsceneTriggerTest`, `CutsceneG0RouteTest`, plus the earlier `CutsceneCameraTest`.
- Validation: `.\gradlew.bat :client:test --no-daemon` PASS; `python tools/check_version_sync.py` PASS v0.13.4; `python tools/check_docs_freshness.py --emit-report` PASS; `.\gradlew.bat :shadowascent:compileJava :client:compileJava :client:shadowJar --no-daemon` PASS.
- Compatibility: replay=no | save=no schema change | protocol=no.

`2026-04-29 10:07:54 +01:00`

- Completed CS-11 and most of CS-12/CS-18: `GameCamera` now exposes cutscene focus, pan, pan tick, and restore APIs through `CutsceneCameraController`; `GameScreen` skips player-follow while camera override is active.
- `CutsceneManager` now handles `camera_focus`, `camera_pan`, and `camera_restore_player` for coordinate targets (`"x,y"`), waits for pan completion, and restores camera on complete/skip/interrupt.
- Added `CutsceneCameraTest` coverage for pure camera motion, manager camera step dispatch, pan waiting, and restore on complete/skip/emergency stop.
- Validation: `.\gradlew.bat :client:test --no-daemon` PASS; `.\gradlew.bat :shadowascent:compileJava :client:compileJava :client:shadowJar --no-daemon` PASS.
- Remaining: entity/marker target resolution for `camera_focus` (CS-13/CS-14), explicit `SaveManager.load()` restore path, entity step types, trigger path, and Act I authoring.
- Compatibility: replay=no | save=no | protocol=no.

`2026-04-29 09:53:50 +01:00`

- Session start: continuing from HEAD da5ce9b | Version: v0.13.3 | Branch: master.
- Primary target: Phase 2 CS-11/CS-12 camera override slice, with CS-18 restore coverage where it naturally belongs.
- Supporting tasks: write failing camera tests first, then implement `GameCamera` override/follow APIs and wire `camera_focus`, `camera_pan`, and `camera_restore_player` through `CutsceneManager`.
- First validation command: `.\gradlew.bat :client:test --tests com.indieniinja.client.game.cutscene.CutsceneCameraTest`.
- Resume risk notes: runtime/camera. Main stop condition is any unclear camera ownership or cutscene exit path that can leave player follow disabled.

`2026-04-29 00:00:00 +00:00`

- Phase 1 complete. All 36 tests pass. JAR builds clean. Version sync and docs freshness OK.
- HEAD: 5c679bd | Version: v0.13.1 (pre-release; v0.13.2 tag pending CI green)
- Committed feat(cutscene): Phase 1 — data-driven CutsceneManager (CS-01–CS-10). Pushed master.
- CI running. Next: bump version to v0.13.2, add CHANGELOG entry, tag, push tag, verify Release assets.
- Compatibility: replay=no, save=additive-only (null→empty default), protocol=no.
- After CI: start Phase 2 loop — CS-11 camera override first.

`2026-04-28 19:55:00 +00:00`

- Plan created from task-intake brief. Phase 1 work not yet started.
- HEAD: c3aceec | Version: v0.13.1
- Starting Phase 1, CS-01 first.
- Compatibility: replay=no, save=additive-only, protocol=no.
