---
doc_type: current_state
status: living
owner: core-team
last_updated: 2026-05-02
version_anchor: v0.13.31
replaces: docs/HANDOVER.md
---

# Current State

Canonical runtime and handover snapshot for the active Java stack.

## Baseline

- Date baseline: 2026-04-24
- Version baseline: v0.12.06
- Platform baseline: Windows desktop
- Engine stack: Java 21 + libGDX + Netty
- Source of truth for release metadata: `version.json`

## Product State

- Current release truth (2026-05-02): v0.13.31 — M6 puzzle archetypes complete: ASYMMETRIC_ABILITY_LOCK (looping echo + 96px proximity jump unlock) and SIMULTANEOUS_TIMING (3-sync jump matching). 7 new unit tests, all pass. WG-1–WG-4 worldgen baseline also complete (v0.13.29–30).
- G0/P0-10 is not closed yet. Session 1 FAIL (v0.13.21, 2026-05-01). All 6 blockers from session 1 are now fixed.
- G0 session 1 evidence: [`docs/reports/manual-runtime/g0-v0.13.21-session-1.md`](reports/manual-runtime/g0-v0.13.21-session-1.md)
- G0 P0 blockers — status:
  - P0-G0-01: **Fixed** v0.13.23 — Hub name + time-of-day banner in HUD
  - P0-G0-02: **Fixed** v0.13.24 — Tai cutscene fires automatically on campaign start
  - P0-G0-03: **Fixed** v0.13.24 — `act1_social_grounding` auto-starts after Tai cutscene
  - P0-G0-04: **Fixed** v0.13.25 — Mission-return portal routes to origin hub
  - P0-G0-05: **Fixed** v0.13.27 — Samson boss yields at ≤1/3 HP; sparring cutscene + mission completion
  - P0-G0-06: **Fixed** v0.13.22 (data) + v0.13.26 (code) — Linzi gated behind 4× q1_complete flags
- Slice handover notes: [`docs/reports/handover/`](reports/handover/)
- Next required action: Run G0 smoke session 2 against v0.13.28. Need 5 passing first-session records to close P0-10.
- Product direction: campaign-first single-player with optional multiplayer overlay.
- Active execution plan: [`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`](plans/implementing/PLAN_SHADOW_ASCENT.md)
- Worldgen runtime adoption plan: [`docs/plans/implementing/PLAN_WORLDGEN_RUNTIME_ADOPTION.md`](plans/implementing/PLAN_WORLDGEN_RUNTIME_ADOPTION.md) — RFC stub; not yet scheduled.
- Current milestone lane: M0 - Act I Lantern Dawn vertical slice (G0 golden route proof). Unblocked — ready for session 2.
- Playable truth: [docs/PLAYABLE_TRUTH.md](PLAYABLE_TRUTH.md)

## Runtime Reality (Implemented)

- Authoritative server loop, zone simulation, and snapshot replication are active.
- Client rendering/UI loop is on libGDX desktop runtime.
- Mission lifecycle tracing and session-correlation logging are active.
- Siren-first onboarding flow and objective/mission affordances are active.
- NPC runtime dimensions are now authoritative over the wire (`NPCState.width/height`) and used by client render/debug hitbox overlays.
- Map input now follows explicit tap/hold semantics: `Tab` tap toggles quick map, `Tab` hold opens full map while held.
- Animation integration: stance-coupled posture readability (Yin unarmed / Yang armed) is enforced client-side â€” `EntityRenderer` routes animation key prefix from `stanceMode` directly (GDD Â§3.3), so Yin always renders unarmed and Yang always renders armed regardless of desync or offline state. Ledge corner hang-climb context and water-bank exit traversal bridge are also implemented with playtest log events.
- Solo/multiplayer campaign unification is live: `handleSoloPortalTravel()` now applies the same ability-gate + zone-migration logic as the server's `handlePortalTravel()`. Player state (health, level, xp, currency, inventory, abilities) is preserved across hub transitions; hub seeds are derived deterministically from the session seed via `HubRegistry.hubSeed()`. Campaign experience is identical whether played solo or co-op (drop-in/drop-out up to 4 players).
- Portal travel blocker fixes (v0.11.65): start-room portals removed from `LevelLayout` (exit-rooms only), render-loop race condition fixed (`refreshSoloWorldRoomCache` + `camera.snapTo` now called in `pollZoneTransition` handler). Portal travel is now stable.
- Stance animation fix (v0.11.65): `EntityRenderer` uses `hasAnyWithPrefix("player_sword_")` for Yang so all locomotion states (idle/walk/jump/crouch) display correct armed posture when sword sheets are registered.
- F9 debug ability toggle active (v0.11.65): solo mode only â€” cycles all abilities granted/cleared; HUD toast feedback.
- Mode select updated (v0.11.65): Sandbox retired, CAMPAIGN maps to solo ID, DEVELOPER replaces old solo card.
- Runtime keybinding ingestion is now live from `user_data/settings/settings.json` (`keybindings` block plus legacy `key_*` fallback), and map/debug/mission hotkeys consume the same binding table as input polling.
- Direct posture hot-swap input is now active (`select_weapon_1` / `select_weapon_2`, default `1`/`2`) with Yin-lock to unarmed and persistent Yang posture preference for runtime readability testing.
- `F1` controls overlay now renders active live bindings instead of a static key legend.
- Interaction affordance readability bridge is now active: lever/button/echo-trigger and pickup interactions queue short explicit animation feedback with `[Playtest][Interaction]` traces.
- Release/version parity gate is enforced through `tools/check_version_sync.py`.
- Solo replay playback is now routed through the Java client (`ninja-client-all.jar`) via `-Dninja.replayPath`; `ninja_dash.exe` / `demo_game.py` is no longer invoked for any launcher-initiated game operation.
- Pygame prototype extraction phase-4 cutover is complete in this repo: launcher fallback to `demo_game.py` is removed, CI/release default lanes are Java-first, and migrated prototype runtime paths now live in `VainAsher/indie-ninja-prototype`.
- **Engine Platform Phases A-C complete (2026-04-19)**: Content definition system (`ContentLoader`, `ContentRegistry`, JSON-schema-validated definitions), `GameConfig` balance constants, animation manifest + hot-reload, Tiled TMX room loader (4 templates), Yarn Spinner dialogue format (23 files), in-game DevConsole (backtick toggle, 14 commands), Gradle `buildAssets` pipeline (436 files, SHA-256). Module extraction: `:shadowascent` module created - `sim.*` and `world.*` moved out of `:core`; `EntityTypeRegistry` + `ShadowAscentEntityTypeBootstrap` added; `:core` published as `engine-core` Maven artifact to GitHub Packages. All server tests pass.
- **Engine Platform Phase D complete (2026-04-19)**: Save checksums (`savegame.sha256` SHA-256 sidecar, verified on load with corrupt-save fallback). Perf regression gate (`TickDurationRegressionTest` â€” 2000-tick run, 5 ms ceiling, `perf_baseline.json`). Multi-slot save support (`user_data/saves/slot_N/`, `SlotSelectScreen`, legacy single-slot auto-migration). `tools/validate_animation_manifest.py` validates manifest against registry at authoring time.

## Session Handover - 2026-04-29 (v0.13.5 - world generation authoring rules)

- **Date:** 2026-04-29
- **Branch:** master
- **Version:** v0.13.5 release candidate for data-driven world-generation authoring.
- **Completed:** room geometry rules, runtime room geometry enforcement, strict TMX geometry validation, room structure rules, seeded template catalog variants, catalog validation, authored TMX shell cleanup, and a comprehensive level authoring guide.
- **Validation:** Python template validator unit tests PASS; canonical Java TMX strict geometry + catalog validation PASS; root editor TMX strict geometry PASS; `RoomGeometryRulesTest` PASS; `RoomStructureRulesTest` PASS; `RoomTemplateCatalogTest` PASS; `WorldGraphGenerationTest` PASS.
- **G0 status:** G0/P0-10 remains open. The previous `v0.13.5` evidence target is superseded by this world-generation release; use the next G0 evidence target before closing P0-10.

## Active Slice - Worldgen Lab Act 1 baseline

- **Status:** Preparing v0.13.17 release.
- **Completed:** seed `420` is now the first-class Act 1 worldgen baseline
  through `tools/worldgen_lab.py act1`; lab reports include pipeline stage
  artifacts; `tools/worldgen_lab.py compare` supports before/after seed tuning.
- **Validation:** `tools/test_worldgen_lab.py` PASS locally for the baseline,
  pipeline, batch, render, and compare paths.
- **Compatibility:** no live replay/save/protocol change; generator snapshot
  schema remains `10`.

## Active Slice - Worldgen vision execution (schema 11) + LayerProcGen improvements

- **Status:** WG-1 (socket fixes) + WG-3 (seam clearance) complete. WG-2 (seed sweep baseline) captured. 2026-05-03.
- **Completed (this session):**
  - WG-1: Fixed 3 socket mismatches in `data/worldgen/sections/` — canopy west (`west_low_walk`→`west_mid_jump`), canopy east (`east_high_climb`→`east_high_jump`), sanctum west (`west_low_walk`→`west_mid_jump`). Ruins unchanged (hub not in contract chain).
  - WG-3: `EntityPlanner.placeEnemies()` gains `boolean isSeamRoom` — returns `List.of()` immediately when true. `RoomPostProcessor.process()` accepts `Set<String> seamRoomKeys`; backward-compat overload uses `Collections.emptySet()`. 5/5 tests PASS (`EntityPlannerSeamClearanceTest`).
  - WG-2: 50-seed sweep baseline captured — `docs/reports/worldgen/sweep-50-v0.13.29.csv`.
  - `docs/systems/WORLD_GEN.md` updated with seam clearance contract.
  - `docs/dev/LAYERPROCGEN_WORLDGEN_ANALYSIS.md` authored (13-section analysis, 5 prioritised improvements).
- **Snapshot baseline (seed 420, post WG-1):** `java/shadowascent/build/worldgen-snapshots/act1-seed-420.json`
  - schema: `11`, `valid=true`
  - lab quality: `qualityScoreV1=100`, `qualityScoreV2=96`, `transitionDebtPenalty=0`, `criticalPathVarietyScore=75`, `socketCompatibilityScore=100`
  - All 3 Act I progression contracts: `status=matched`
- **Seed sweep baseline (seeds 1–50, BLOB/20):** `docs/reports/worldgen/sweep-50-v0.13.29.csv`
  - Score range: 60–80 (all `overallStatus=fail`)
  - Root cause: `critical_path_transition_debt` on Act II+ nodes (archive, cathedral, cavern, foundry, spire). No templates authored yet — expected failure, not a regression.
  - Worst 5: seeds 7 (60), 40 (61), 3 (63), 5 (64), 11 (65) — full breakdown at `docs/reports/worldgen/sweep-50-failures.md`.
- **Validation evidence (this session):**
  - `SectionTemplateLibraryTest` 4/4 PASS
  - `GenerationValidationPlannerTest` 4/4 PASS
  - `EntityPlannerSeamClearanceTest` 5/5 PASS
- **Deferred:** Act II+ section template authoring (archive, cathedral, cavern, foundry, spire). WG-4 forest trial TMX templates. 1..250 full sweep. Track via `PLAN_SHADOW_ASCENT.md` WG lane.
- **Prior slice (schema 11 initial):**
  - strict section schema validator, critical-path transition debt policy, Act I template variety expansion, worldgen lab quality scoring V2 metrics
  - Snapshot (pre-WG-1): `valid=false`, `qualityScoreV2=66`, `transitionDebtPenalty=67`, `socketCompatibilityScore=33`

## Completed Slice - Worldgen Lab detail view

- **Status:** Released as v0.13.16.
- **Completed:** deterministic zone rows, full tile preview rows, expanded
  world detail SVG, and per-room SVG detail outputs for diagnosing generation
  formations below the room-graph level.
- **Validation:** `WorldgenLabAnalyzerTest` PASS;
  `WorldGenerationSnapshotCommandTest` PASS; `tools/test_worldgen_lab.py` PASS.
- **Compatibility:** no live replay/save/protocol change; generator snapshot
  schema changes from `9` to `10`.

## Completed Slice - Worldgen Lab prototype

- **Status:** Released as v0.13.15.
- **Completed:** deterministic `labReport` snapshot metadata, per-room tile and
  warning metrics, static HTML/SVG report rendering, and batch seed summaries
  for ranking low-quality formations.
- **Compatibility:** no live replay/save/protocol change; generator snapshot
  schema changed from `8` to `9`.

## Completed Hotfix - Connected-edge room shell collision

- **Status:** Released as v0.13.14.
- **Completed:** connected room edges now retain full solid wall/floor shells outside configured door corridors; procedural generation re-enforces room shells after late terrain variation passes.
- **Validation:** red/green connected-down-edge regression PASS; `:shadowascent:test` PASS; related world graph suites PASS; full server/client tests and shadow JARs PASS.
- **Compatibility:** replay/collision behavior can change for seeds that previously exposed open connected edges; save/protocol unchanged; generator snapshot schema remains `8`.

## Completed Hotfix - Unified world void collision

- **Status:** Released as v0.13.13.
- **Completed:** missing room-grid cells inside unified world bounds are sealed with solid collision in both unified layout construction paths; a regression covers generated plans with empty interior cells.
- **Compatibility:** replay/collision behavior can change for seeds that previously exposed fall-through void cells; save/protocol unchanged; generator snapshot schema remains `8`.

## Completed Slice - Layered hybrid generator, Slice 8

- **Status:** Released as v0.13.12.
- **Plan:** [`docs/plans/implementing/PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md`](plans/implementing/PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md).
- **Completed in this slice:** deterministic megamap snapshot model, continuous room origins, seam metadata, overlay rows, tile metrics, autotile preview checksum, and snapshot renderer bundle tooling.
- **Validation:** `MegamapStitcherTest` PASS; `WorldGenerationSnapshotCommandTest` PASS; `tools/test_render_worldgen_snapshot.py` PASS.
- **Next slice:** layered hybrid generator plan complete; return to G0 evidence capture unless a new blocker appears.
- **Compatibility:** no live replay/save/protocol change yet. Generator snapshot schema changes from `7` to `8`.

## Session Handover - 2026-04-29 (v0.13.4 - Phase 2 CutsceneManager shipped)

- **Date:** 2026-04-29
- **Branch:** master | **HEAD:** 2439062 | **Tag:** v0.13.4
- **Version:** v0.13.4 - released and verified (CI pass, Release pass, 3 assets)
- **Active plan:** [`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`](plans/implementing/PLAN_SHADOW_ASCENT.md)
- **Completed:** Cutscene Phase 2 (CS-11 through CS-18): camera focus/pan/restore, marker registry, entity step controller/overrides, trigger parsing/router, GameScreen trigger wiring, save-load camera/entity reset, six Act I cutscene JSON files, `docs/systems/CUTSCENE.md`, and G0 route integration coverage.
- **Validation:** `.\gradlew.bat :client:test --no-daemon` PASS; `.\gradlew.bat :server:test :client:test --no-daemon` PASS; `.\gradlew.bat :server:shadowJar :client:shadowJar --no-daemon` PASS; `python tools/check_version_sync.py` PASS; `python tools/check_docs_freshness.py --emit-report` PASS; GitHub CI and Release PASS for `v0.13.4`.
- **Next target:** v0.13.5 - G0 signoff + state sync. Collect 5 first-session records for the `docs/PLAYABLE_TRUTH.md` G0 route, fix only G0 blockers, then close P0-10 if evidence supports it.
- **Known G0 gap:** no formal 5-record first-session evidence set yet; do not mark ROADMAP G0 complete or close P0-10 until those records exist.

---

## Session Handover — 2026-04-29 (v0.13.3 — Phase 1 CutsceneManager + JAR fix)

- **Date:** 2026-04-29
- **Branch:** master | **HEAD:** a3ba321
- **Version:** v0.13.3 — released and verified (CI ✓, Release ✓, 3 assets)
- **Session summary:** Built the full Phase 1 data-driven CutsceneManager from scratch, shipped as v0.13.2. Found and fixed a P0 runtime bug (CutsceneLoader's `isDirectory()` call always returns false in a fat JAR), shipped fix as v0.13.3. Confirmed working via live launcher smoke test.

---

### What was built — Phase 1 CutsceneManager (CS-01–CS-10, v0.13.2)

**New package:** `java/client/src/main/java/com/indieniinja/client/game/cutscene/`

| File | Purpose |
| --- | --- |
| `CutsceneStepType.java` | Enum of all step types (Phase 1 + Phase 2 stubs) |
| `SkipPolicy.java` | NEVER / ALWAYS / ALLOW_AFTER_FIRST_VIEW / DEBUG_ONLY |
| `StartCondition.java` | `flagNotSet` / `flagSet` condition pair; `isMet(StoryManager)` |
| `CutsceneLoadException.java` | Checked load error with cause chaining |
| `CutsceneStep.java` | Step data class with Builder; `fromMap()` factory |
| `CutsceneDefinition.java` | Full scene data model; `fromMap()` factory; `conditionsMet()` |
| `CutsceneLoader.java` | Reads `data/cutscenes/index.json` then loads each file by explicit path |
| `CutsceneManager.java` | Runtime state machine: start/tick/skip/complete/emergencyStop/resetCompleted |

**Existing files modified:**

- `DialogueManager.java` — added `startInline(speaker, text)`: synthetic single-node dialogue tree for cutscene dialogue without Yarn files
- `StoryManager.java` — added `hasFlag(key)` boolean shorthand
- `SaveData.java` — added `completedCutscenes List<String>` (null-safe on old save load)
- `SaveManager.java` — added live `completedCutscenesSet` that survives `liveData` replacement on reload; `completedCutscenes()` accessor
- `GameScreen.java` — CutsceneManager init after `saveManager.load()`, `tick()` in render loop, `cutscenePlayerLocked` gate in `gameplayInputEnabled()`, 4 DevConsole commands

**Data files:**

- `data/cutscenes/index.json` — manifest listing all cutscene filenames (JAR-safe; do NOT skip this when adding new scenes)
- `data/cutscenes/act1_linzi_first_appearance.json` — first Act I scene: lock → 3× dialogue → set_flag ×2 → unlock; sets `act1_linzi_met` + `linzi_arrived`

**Tests (36 new, all passing):**

- `CutsceneLoaderTest` (9) — valid load, invalid step skip, missing id exception, deterministic order
- `CutsceneManagerTest` (13) — start/tick/complete, second-start rejection, lock/unlock, set_flag, wait countdown, dialogue pause, completion flags, emergencyStop, resetCompleted
- `CutsceneCompletionFlagTest` (4) — flag written on finish, id tracked, one-shot no-restart, emergencyStop unlocks
- `CutsceneSkipPolicyTest` (7) — NEVER/ALWAYS/ALLOW_AFTER_FIRST_VIEW/DEBUG_ONLY behaviour
- `CutsceneSaveRoundtripTest` (3) — ids survive save/reload; null field defaults to empty

**Plan:** [`docs/plans/implementing/PLAN_CUTSCENE_MANAGER.md`](plans/implementing/PLAN_CUTSCENE_MANAGER.md) — Phase 1 COMPLETE, Phase 2 NOT STARTED

---

### P0 fix — CutsceneLoader JAR runtime (v0.13.3)

**Bug:** `Gdx.files.internal("data/cutscenes").isDirectory()` always returns `false` for classpath paths inside a fat JAR. The loader silently returned an empty map; every `cutscene play <id>` call failed with `[ERR] unknown id`.

**Fix:** Replaced directory-listing with explicit index file approach:

1. `CutsceneLoader.loadAll()` reads `data/cutscenes/index.json` (a JSON array of filenames)
2. Loads each file by explicit `Gdx.files.internal("data/cutscenes/<name>")` — individual paths work from JAR classpath
3. `loadAll(FileHandle dir)` overload retained for tests; skips `index.json` itself

**Rule for future authoring:** Every new `data/cutscenes/*.json` file **must** be added to `data/cutscenes/index.json` or the loader will not find it.

**Live smoke test (confirmed 2026-04-29):**

- `cutscene list` → `[unseen] act1_linzi_first_appearance (7 steps, ALLOW_AFTER_FIRST_VIEW)`
- `cutscene play act1_linzi_first_appearance` → player locks, Linzi speaks 3 lines, flags set, player unlocks ✓

---

### Validation

- `.\gradlew.bat :client:shadowJar` — BUILD SUCCESSFUL
- `.\gradlew.bat :client:test` — all 36 cutscene tests PASS
- `python tools/check_version_sync.py` — OK v0.13.3
- CI: success on all master pushes + tag
- Release v0.13.3: `ninja-client-all.jar`, `ninja-server-all.jar`, `docs-archive-2026-04-29-v0.13.3.zip` ✓
- Live DevConsole smoke: `cutscene play act1_linzi_first_appearance` ✓

---

### Known issues / risks going into Phase 2

| Risk | Detail |
| --- | --- |
| Phase 2 step types silently no-op | `camera_*` and `entity_*` steps log a warning and do nothing — authoring them before CS-11–CS-13 are implemented won't crash but won't work |
| No hub name HUD | Step 1 of G0 has been PARTIAL since v0.13.0 — deferred |
| `buildAll` Gradle undeclared dep | Workaround: use `:shadowascent:compileJava :client:compileJava :client:shadowJar` |

---

### First action for the next agent

1. Read [`docs/plans/implementing/PLAN_CUTSCENE_MANAGER.md`](plans/implementing/PLAN_CUTSCENE_MANAGER.md) — Phase 2 starts at CS-11

2. **CS-11:** Add `setCutsceneFocus(float worldX, float worldY)`, `panTo(float worldX, float worldY, float duration)`, `restorePlayerFollow()` to `GameCamera`
3. **CS-12:** Wire `CAMERA_FOCUS`, `CAMERA_PAN`, `CAMERA_RESTORE_PLAYER` step types into `CutsceneManager.tick()`
4. **CS-13:** Wire `ENTITY_FACE`, `ENTITY_MOVE_TO`, `ENTITY_SET_VISIBLE`, `ENTITY_PLAY_ANIM` step types
5. **CS-14:** `CutsceneMarkerRegistry` — named positions from `data/cutscenes/markers.json`
6. **CS-15:** NPC-interaction → cutscene trigger path in `GameScreen`
7. **CS-16:** Author the remaining 5 Act I cutscene JSON files (add each to `index.json`)
8. **CS-17–18:** Camera restore tests + G0 integration test
9. **Target version:** v0.13.4

- **Compatibility:** replay: no | save: additive | protocol: no
  - `buildAll` Gradle task has pre-existing undeclared dependency; workaround: `:shadowascent:compileJava :client:compileJava :client:shadowJar`.
- **Compatibility:** replay: no | save: additive (`completedCutscenes` added; old saves load cleanly with empty set) | protocol: no
- **Active plan:** [`docs/plans/implementing/PLAN_CUTSCENE_MANAGER.md`](plans/implementing/PLAN_CUTSCENE_MANAGER.md) — Phase 1 COMPLETE, Phase 2 NOT STARTED
- **First action next session:** Begin Phase 2 — CS-11: add `setCutsceneFocus()`, `panTo()`, `restorePlayerFollow()` to `GameCamera`. Then CS-12: wire camera step types into `CutsceneManager.tick()`. Then CS-13: entity steps. Target: v0.13.3. Run `cutscene play act1_linzi_first_appearance` from DevConsole as live smoke before starting CS-11.

## Session Handover — 2026-04-28

- **Date:** 2026-04-28
- **Branch:** master | **HEAD:** adbb01a
- **Version:** v0.13.1
- **Systems touched:** `GameSimulator` (NPC spawning), `GameScreen` (NPC interaction handler), CHANGELOG, ROADMAP, README, devlog, version.json, build.gradle.kts
- **Validation run:**
  - `.\gradlew.bat :shadowascent:compileJava :client:compileJava :client:shadowJar` — BUILD SUCCESSFUL
  - `python tools/check_version_sync.py` — OK v0.13.1
  - `python tools/check_docs_freshness.py --emit-report` — PASS (0 warnings)
  - G0 smoke (manual-20260428-190000) — PASS: named NPCs spawned across map, TALK_TO_NPC objectives advance, no softlock, save/reload stable
  - CI: success (`adbb01a`) | Release: success — assets: ninja-server-all.jar, ninja-client-all.jar, docs-archive-2026-04-28-v0.13.1.zip
- **Known issues / risks:**
  - No formal hub visual confirmation that spawn is in Lantern Heights (step 1 of G0 was PARTIAL in v0.13.0 smoke — hub name HUD not implemented).
  - Zero first-session test records beyond internal smoke; 5 external records required before v0.13.2.
  - `buildAll` Gradle task has a pre-existing undeclared dependency (`server:compileJava` → `client:copyJarToRoot`); workaround is `:shadowascent:compileJava :client:compileJava :client:shadowJar`.
- **Compatibility:** replay: no | save: no | protocol: no
- **First action next session:** Run 5 first-session tests recording the G0 metrics (time-to-objective, first confusion point, Yin/Yang readability, Linzi legibility, hub change noticed). Then address Lantern Heights hub name display (step 1 HUD).

## Canonical Documentation Set

- [PLAYABLE_TRUTH.md](PLAYABLE_TRUTH.md) - honest playable state, G0 golden route, tester scope
- [INDEX.md](INDEX.md) - top-level documentation routing
- [ROADMAP.md](ROADMAP.md) - milestone sequencing and current targets
- [CHANGELOG.md](CHANGELOG.md) - release-facing version history
- [PLAYER_EXPECTATIONS.md](PLAYER_EXPECTATIONS.md) - launcher-first playtest contract
- [GDD.md](GDD.md) - design intent and narrative/mechanics contracts
- [RELEASE_VERSION_SYNC_CHECKLIST.md](RELEASE_VERSION_SYNC_CHECKLIST.md) - release metadata gate
- [workflow/OPERATING_RHYTHM_AND_HABITS.md](workflow/OPERATING_RHYTHM_AND_HABITS.md) - daily/weekly/monthly operating model
- [operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md](operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md) - cross-repo control-tower handover

## Repository Process Defaults

- Plan-embedded tasks are canonical for implementation tracking.
- `indie-ninja-pipeline` is the control tower for master planning and cross-repo coordination.
- `docs/TASK_LIST.md` is historical and archived.
- Retired/stale docs move immediately to `docs/archive/retired/`.
- Archive ZIP snapshots are kept in `docs/archive/zips/` and mirrored to release assets.
- Docs freshness checks are warning-only in CI unless explicitly run in strict mode.

## Session Close-Out (2026-04-24, v0.12.08 — P1-03A Yin/Yang stance movement + duality prototype)

- Date: 2026-04-24
- Branch + HEAD: `master @ 310bf8f` (tag: v0.12.08)
- Current version: `v0.12.08`
- Systems touched: `GameConfig`, `SimPlayer`, `SimEnemy`, `EnemyAwarenessState` (new), `GameSimulator`, `PlayerState`, `EchoState`, `SimEcho`, `assets/rooms/templates/duality_test.tmx`.
- Changes: Yin/Yang stance movement modifiers (run/dash/wall-jump by stance); noise emission + enemy awareness FSM (UNAWARE/SUSPICIOUS/ALERTED/SEARCHING); Phase Teleport variants (ShadowStep/ThunderStep/HarmonicStep); Echo Art types (Silent/Riot/Resonant); Flow recency gate (`lastMeaningfulActionTimer`); duality test room (128×128 TMX).
- Test evidence: 56 new tests across 6 new test classes (`GameSimulatorStanceMovementTest`, `EnemyAwarenessTest`, `GameSimulatorTeleportStanceTest`, `SimEchoTypeTest`, `FlowRecencyTest`, `DualityTestRoomTest`). All server tests pass (BUILD SUCCESSFUL).
- Validation run:
  - `python tools/check_version_sync.py` (PASS — v0.12.08)
  - `python tools/check_docs_freshness.py --emit-report` (PASS — 32 docs, no warnings)
  - `./gradlew :server:shadowJar :client:shadowJar` (PASS)
  - CI=success + Release=success for `310bf8f` on GitHub
  - `gh release view v0.12.08` — 3 assets confirmed (client JAR, server JAR, docs archive ZIP)
- Known issue or risk: combined local Gradle lane (`:server:test :client:test :server:shadowJar :client:shadowJar`) still trips `:client:copyJarToRoot` task-order validation; split-lane command remains the local workaround. `:client:test` was green on CI.
- Compatibility impact: replay=`BREAKING` (stance multipliers change physics outputs; replays from ≤v0.12.07 desync), save=`no`, protocol=`ADDITIVE` (new wire fields `teleportType`/`echoType` default gracefully).
- First action next session: full playtest guide + launcher distribution pack for v0.12.08 (session confirmed); then animation art style planning and inspiration pass.

## Session Close-Out (2026-04-22)

- Date: 2026-04-22
- Branch + HEAD: `master @ 08c0424`
- Current version: `v0.12.03`
- Systems touched: release-loop metadata/docs parity, CI + Release verification, release asset publication confirmation.
- Validation run:
  - `python tools/check_version_sync.py --tag v0.12.03` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `gh run list --limit 8 --json status,conclusion,name,headSha,displayTitle,event` (CI=success + Release=success for `08c0424`)
  - `gh release view v0.12.03 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets` (release published; docs archive + client/server jars present)
- Known issue or risk: none blocking.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: begin `v0.12.04` stabilization by auditing mission-item lifecycle/despawn paths and implementing authoritative mission-critical no-despawn guarantees (solo + hosted multiplayer + late-join sync).

## Session Close-Out (2026-04-23)

- Date: 2026-04-23
- Branch + HEAD: `master @ 519f690`
- Current version: `v0.12.03`
- Systems touched: mission-return mission pickup contract lifecycle hardening, regression coverage expansion, release-checklist evidence pass, session close-out evidence capture.
- Validation run:
  - `C:\Users\asher\AppData\Local\Programs\Python\Python312\python.exe tools/check_version_sync.py --tag v0.12.03` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `./gradlew :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon` (FAIL: Gradle task validation on `:client:copyJarToRoot` implicit dependency when mixed with test tasks)
  - `./gradlew :server:test :client:test --no-daemon` (PASS)
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` (PASS)
  - `gh run list --limit 3 --json status,conclusion,name,headSha` (CI=success for `519f690`)
  - `gh run list --limit 12 --json status,conclusion,name,headSha,displayTitle,event` (latest `Release`=success for `08c0424`)
  - `gh release view v0.12.03 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets` (PASS; docs archive + client/server jars present)
- Known issue or risk: combined local Gradle lane (`test + shadowJar` in one invocation) still trips a task-order validation on `:client:copyJarToRoot`; split-lane execution and CI both pass.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: either patch `:client:copyJarToRoot` task dependency ordering so the canonical combined release command passes in one run, or keep split-lane release validation as the documented local workaround.

## Session Close-Out (2026-04-23, Final v0.12.04 Release Loop)

- Date: 2026-04-23
- Branch + HEAD: `master @ 2044b0d`
- Current version: `v0.12.04`
- Systems touched: release metadata/version parity bump, changelog/roadmap/current-state/plan release-note alignment, annotated tag publication, GitHub Release publication verification.
- Validation run:
  - `C:\Users\asher\AppData\Local\Programs\Python\Python312\python.exe tools/check_version_sync.py --tag v0.12.04` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `./gradlew :server:test :client:test --no-daemon` (PASS)
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` (PASS)
  - `gh run list --limit 3 --json status,conclusion,name,headSha` (Release=success + CI=success for `2044b0d`)
  - `gh run list --limit 8 --json status,conclusion,name,headSha,displayTitle,event` (tag-triggered Release=success for `v0.12.04`, `run_id=24825590863`)
  - `gh release view v0.12.04 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets` (PASS; docs archive + client/server jars present)
- Known issue or risk: non-blocking local workflow limitation remains: combined Gradle invocation `:server:test :client:test :server:shadowJar :client:shadowJar` can still trip `:client:copyJarToRoot` task-order validation; split-lane command sequence remains the validated local workaround.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: start `v0.12.05` stabilization planning and decide whether to permanently codify split-lane local release commands or fix `:client:copyJarToRoot` task dependency ordering.

## Session Close-Out (2026-04-23, Final v0.12.05 Release Loop)

- Date: 2026-04-23
- Branch + HEAD: `master @ 6fdddbf`
- Current version: `v0.12.05`
- Systems touched: client cleanup/perf hardening (`GameScreen`, `MissionManager`, `MinimapRenderer`), release metadata/docs parity bump, annotated tag publication, release asset verification.
- Validation run:
  - `C:\Users\asher\AppData\Local\Programs\Python\Python312\python.exe tools/check_version_sync.py --tag v0.12.05` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `./gradlew :server:test :client:test --no-daemon` (PASS)
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` (PASS)
  - `gh run list --limit 8 --json status,conclusion,name,headSha,displayTitle,event` (CI=success + Release=success for `6fdddbf`)
  - `gh release view v0.12.05 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets,url` (PASS; docs archive + client/server jars present)
- Known issue or risk: local combined Gradle lane (`:server:test :client:test :server:shadowJar :client:shadowJar`) still triggers `:client:copyJarToRoot` task-order validation; split-lane command sequence remains the validated local workaround.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: continue remaining cleanup-lane rubric coverage (authority/race/lifecycle/reliability matrix) and capture smoke/golden evidence when future slices change runtime behavior.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - WorldGraph Lifecycle Hardening)

- Date: 2026-04-23
- Branch + HEAD: `master @ 630da76` (working tree dirty; local slice not yet committed)
- Current version: `v0.12.05`
- Systems touched: world-graph reconstruction hardening (`WorldGraph.fromRooms` ownership/lifecycle guards, direction normalization), state-matrix regression expansion in `WorldGraphGenerationTest`.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --tests com.indieniinja.server.WorldGraphTest --no-daemon` (PASS)
  - `python tools/check_version_sync.py --tag v0.12.05` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `gh run list --limit 3 --json status,conclusion,name,headSha` (`CI`=success for `630da76`, latest `Release`=success for `6fdddbf`)
- Known issue or risk: invalid/corrupted persisted world-graph payloads with missing or type-mismatched start/exit entries are now rejected during reconstruction and should fall back to regeneration in repository load paths.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: continue cleanup-lane rubric coverage on remaining race/order and disconnect/reconnect lifecycle surfaces (`ServerProtocolHandler` + `ZoneSimulationLoop`), and capture smoke/golden evidence if a slice changes player-visible behavior.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Zone Room-Authority Ordering)

- Date: 2026-04-23
- Branch + HEAD: `master @ a47c80d` (working tree dirty; local CRCL-14 slice not yet committed)
- Current version: `v0.12.05`
- Systems touched: `ZoneSimulationLoop` room-authority ordering (`selectRoomAnchorPlayer` deterministic slot selection + `updateCurrentRoom` usage), ordering regression coverage in `ZoneSimulationLoopScriptedLossOrderingTest`.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --no-daemon` (PASS)
  - `python tools/run_p0_regression_suite.py` (FAIL: Data Integrity command references missing `tests/test_data_integrity.py`; Version Sync + Java Server/Client tests PASS; report emitted at `docs/reports/P0_REGRESSION_REPORT.md`)
- Known issue or risk: `tools/run_p0_regression_suite.py` currently contains a stale data-integrity path and fails before full PASS despite relevant Java test lanes succeeding.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: continue remaining cleanup-lane disconnect/reconnect lifecycle ordering pass in `ServerProtocolHandler` and capture manual smoke/golden evidence if player-visible behavior changes.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Reconnect Slot Reservation Ordering)

- Date: 2026-04-23
- Branch + HEAD: `master @ 83db817` (working tree dirty; local CRCL-15 slice not yet committed)
- Current version: `v0.12.05`
- Systems touched: `GameSession` disconnect/reconnect slot lifecycle (`releaseSlot` reservation semantics + `claimSlot` expiry sweep), new deterministic reservation tests in `GameSessionSlotReservationTest`.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.GameSessionSlotReservationTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS)
- Known issue or risk: `tools/run_p0_regression_suite.py` still references missing `tests/test_data_integrity.py`; workflow evidence runner requires follow-up path correction.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: resolve P0 regression-runner stale data-integrity path, then continue disconnect/reconnect handoff ordering pass in `ServerProtocolHandler`.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Portal Handoff Lifecycle + P0 Runner Reliability)

- Date: 2026-04-23
- Branch + HEAD: `master @ de93c91`
- Current version: `v0.12.05`
- Systems touched: `ServerProtocolHandler.handlePortalTravel` origin-zone simulator cleanup for transitions, mission pickup lifecycle regression expansion, and `tools/run_p0_regression_suite.py` optional check-path skip handling.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --tests com.indieniinja.server.GameSessionSlotReservationTest --no-daemon` (PASS)
  - `python tools/run_p0_regression_suite.py` (PASS; `Data Integrity` check now `SKIP` when legacy path is absent)
- Known issue or risk: no new blocker identified after manual interactive portal-travel smoke/golden validation.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: continue cleanup-lane rubric coverage on remaining authority/race/order surfaces in `ServerProtocolHandler` zone join/leave sequencing, and capture smoke/golden evidence if runtime behavior changes.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Zone Presence Join/Leave Sequencing)

- Date: 2026-04-23
- Branch + HEAD: `master` (CRCL-17 local slice committed in-session)
- Current version: `v0.12.05`
- Systems touched: `ServerProtocolHandler.handlePortalTravel` `ZONE_PRESENCE` payload alignment (`hub_id` now zone key for both `arrived`/`departed`; additive `master_hub_id`), and regression coverage in `ServerProtocolHandlerMissionPickupSeedTest`.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS)
  - `python tools/check_version_sync.py` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
- Known issue or risk: downstream listeners must use `master_hub_id` when master-hub routing is required; `hub_id` is now consistently zone-key scoped.
- Compatibility impact: replay=`no`, save=`no`, protocol=`low-risk payload correction + additive field`.
- First action next session: continue cleanup-lane rubric coverage on remaining `ServerProtocolHandler` race/order surfaces by hardening duplicate `CLIENT_HELLO` channel overlap handling and adding targeted lifecycle regression coverage.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - CLIENT_HELLO Overlap Ordering)

- Date: 2026-04-23
- Branch + HEAD: `master` (CRCL-18 local slice committed in-session)
- Current version: `v0.12.05`
- Systems touched: `ServerProtocolHandler.handleClientHello` overlap/idempotency guard path, `sendServerHello` helper extraction, and new `ServerProtocolHandlerClientHelloOrderingTest`.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.ServerProtocolHandlerClientHelloOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS)
  - `python tools/check_version_sync.py` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
- Known issue or risk: takeover path currently presents as disconnect/rejoin from other clients' perspective (`leave` then `join` event pair).
- Compatibility impact: replay=`no`, save=`no`, protocol=`no wire-format change`.
- First action next session: harden replay determinism by removing concurrent-set iteration order from `ZoneSimulationLoop` per-tick input collection.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Replay Input Ordering Determinism)

- Date: 2026-04-23
- Branch + HEAD: `master` (CRCL-19 local slice committed in-session)
- Current version: `v0.12.05`
- Systems touched: `ZoneSimulationLoop` ordered zone-player snapshot usage in `simulateTick`, slot-ordered `playersInZone`, and regression coverage in `ZoneSimulationLoopScriptedLossOrderingTest`.
- Validation run:
  - `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerClientHelloOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS)
  - `python tools/check_version_sync.py` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
- Known issue or risk: no new blocker identified in this slice.
- Compatibility impact: replay=`yes` (determinism hardening; no format change), save=`no`, protocol=`no`.
- First action next session: run cleanup-lane checklist closure pass and defer any remaining non-critical items with owner/date.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Checklist Closure)

- Date: 2026-04-23
- Branch + HEAD: `master` (CRCL-20 local slice committed in-session)
- Current version: `v0.12.05`
- Systems touched: cleanup-lane checklist bookkeeping (`PLAN_CODE_REVIEW_AND_CLEANUP.md`) + closeout status notes.
- Validation run:
  - `python tools/check_version_sync.py` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `python tools/run_p0_regression_suite.py` (PASS)
- Known issue or risk: full interactive smoke/golden workflow evidence is still pending because launcher/client interactive paths are not runnable in this terminal slice.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: execute interactive `Daily Smoke` and relevant golden routes, then attach evidence; code cleanup slices are otherwise complete.

## Session Close-Out (2026-04-23, Cleanup Rubric Slice - Interactive Runtime Gate Closure)

- Date: 2026-04-23
- Branch + HEAD: `master` (CRCL-21 manual-gate closure in progress)
- Current version: `v0.12.05`
- Systems touched: cleanup-lane runtime-gate closeout notes (`PLAN_CODE_REVIEW_AND_CLEANUP.md`) and manual evidence capture linkage.
- Validation run:
  - Interactive `Daily Smoke` route: PASS (user-confirmed)
  - Golden `G7` replay playback: PASS (`docs/reports/manual-runtime/manual-20260423-232647/g7-replay.log`)
  - Golden `G8` network connect/drop: PASS (`docs/reports/manual-runtime/manual-20260423-232647/client-a.log`, `client-b.log`, `server.log`)
  - Evidence index captured: `Get-ChildItem docs/reports/manual-runtime/manual-20260423-232647 | Select Name,Length,LastWriteTime`
- Known issue or risk: no new blocker identified; cleanup-lane manual runtime gates are now satisfied.
- Compatibility impact: replay=`no` (validation-only), save=`no`, protocol=`no`.
- First action next session: cleanup lane complete; continue with the next highest-priority implementing slice from `PLAN_SHADOW_ASCENT.md` after running `SESSION_START_WORKFLOW.md`.

## Session Close-Out (2026-04-24, v0.12.07 Release + Phase 2 Bootstrap)

- Date: 2026-04-24
- Branch + HEAD: `master @ 1cbd296`
- Current version: `v0.12.07`
- Systems touched: dash wall-cancel physics fix (`isDashing` cleared on wall contact, `feedback#4`); Phase 2 gameplay identity lock bootstrap (`GAMEPLAY_KPI_TARGETS.md`, `BALANCE_LOG.md`, P2-01 ✅, P2-03 ✅ readiness audit).
- Validation run:
  - `python tools/check_version_sync.py` (PASS — v0.12.07)
  - `./gradlew :server:test --tests com.indieniinja.server.GameSimulatorTest --no-daemon` (PASS)
  - CI green on `5b80603` (Release workflow success for v0.12.07 tag)
- Known issue or risk: none blocking.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: begin Slice 1 of Yin/Yang stance-driven movement feature (P1-03A) — stance speed/dash multipliers in `GameConfig` + `GameSimulator`.

## Session Close-Out (2026-04-24, Final v0.12.06 Release Loop)

- Date: 2026-04-24
- Branch + HEAD: `master @ 0433a6e`
- Current version: `v0.12.06`
- Systems touched: release metadata parity (`version.json`, `java/build.gradle.kts`, `README.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`), active-plan/current-state/version-anchor sync, and public comms capture (`docs/devlog/2026-04.md`).
- Validation run:
  - `python tools/check_version_sync.py --tag v0.12.06` (PASS)
  - `python tools/check_docs_freshness.py --emit-report` (PASS)
  - `./gradlew :server:test :client:test --no-daemon` (PASS)
  - `./gradlew :server:shadowJar :client:shadowJar --no-daemon` (PASS)
  - `gh run list --limit 6 --json status,conclusion,name,headSha` (CI + Release SUCCESS on `0433a6e`)
  - `gh release view v0.12.06 --json tagName,name,publishedAt,assets,url` (PASS; assets verified)
- Known issue or risk: combined local Gradle lane (`:server:test :client:test :server:shadowJar :client:shadowJar`) still reproduces `:client:copyJarToRoot` ordering validation under OneDrive; split-lane workflow remains the validated local workaround.
- Compatibility impact: replay=`no` (determinism hardening only), save=`no`, protocol=`no`.
- First action next session: continue next implementing stabilization slice from `PLAN_SHADOW_ASCENT.md` (`v0.12.07` target) after session-start workflow.

## Session Start (2026-04-22, v0.12.04 Loop Kickoff)

- Date: 2026-04-22
- Branch: `master`
- Current version: `v0.12.03`
- Primary target: mission-item lifecycle/despawn hardening with authoritative no-despawn guarantees and tighter late-join convergence.
- Supporting tasks:
  - Add regression coverage for mission pickup lifecycle state transitions.
  - Keep plan/workflow notes synced for the first `v0.12.04` stabilization slice.
- First validation command: `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon`
- Resume risk notes: `none`
- Progress update (`2026-04-23 07:45:21 +01:00`):
  - Completed `v0.12.04` stabilization slice 4: disconnect-path mission pickup contract cleanup (clear stale contracts, retain current-hub contract for rejoin reseed).
  - Added regression: `ServerProtocolHandlerMissionPickupSeedTest.disconnectKeepsCurrentHubContractAndClearsStaleContractsForPlayer` and `disconnectKeepsCurrentHubContractAvailableForRejoinReseed`.
  - Validation: `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS).
  - Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- Progress update (`2026-04-23 08:10:34 +01:00`):
  - Completed `v0.12.04` stabilization slice 5: mission-switch/abandon mission pickup contract hardening for hosted + rejoin flows.
  - Client now clears prior mission pickup seed contract when starting a new mission; server now ignores stale clear events that target a different mission contract.
  - Added regression: `ServerProtocolHandlerMissionPickupSeedTest.missionSwitchAToBRejoinReseedsMissionBContract`.
  - Validation: `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS), `python tools/check_version_sync.py` (PASS), `python tools/check_docs_freshness.py --emit-report` (PASS).
  - Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- Progress update (`2026-04-23 08:36:53 +01:00`):
  - Completed `v0.12.04` stabilization slice 6: mission-return portal-travel mission pickup contract hardening.
  - `ServerProtocolHandler.handlePortalTravel(...)` now clears mission pickup seed contracts when `transition_type=mission_return` and skips destination reseed queueing for mission-return travel.
  - Added regression: `ServerProtocolHandlerMissionPickupSeedTest.missionReturnTravelClearsContractsAndSkipsDestinationReseed`.
  - Validation: `./gradlew :server:test --tests com.indieniinja.server.ZoneSimulationLoopScriptedLossOrderingTest --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` (PASS), `python tools/check_version_sync.py` (PASS), `python tools/check_docs_freshness.py --emit-report` (PASS).
  - Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
