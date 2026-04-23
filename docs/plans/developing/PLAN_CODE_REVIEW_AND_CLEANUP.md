---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-23
version_anchor: v0.12.05
---

# PLAN - Code Review and Cleanup Lane (Workflow-First)

Reference workflows:
- `docs/workflow/SESSION_START_WORKFLOW.md`
- `docs/workflow/TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`
- `docs/workflow/READY_DONE_WORKFLOW.md`
- `docs/workflow/PRE_COMMIT_LOCAL_GATES.md`
- `docs/workflow/DAILY_SMOKE_WORKFLOW.md`
- `docs/workflow/GOLDEN_PATH_REGRESSION.md`
- `docs/workflow/COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`
- `docs/workflow/DEBUG_EVIDENCE_CAPTURE.md`
- `docs/workflow/REPLAY_AND_DESYNC_TRIAGE.md`
- `docs/workflow/SESSION_END_WORKFLOW.md`

## 0. Session-Start First Rule (Mandatory)

No review or cleanup work starts until `SESSION_START_WORKFLOW.md` is completed.

Required pre-work checklist:
- [x] Sync `master`
- [x] Read `version.json`
- [x] Read `docs/CURRENT_STATE.md`
- [x] Read active implementation plan (`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`)
- [x] Read `git log --oneline -10`
- [x] Write 3-line session note (target, reason, stop condition)

Session note minimum for this lane:
- [x] Date
- [x] Branch
- [x] Current version
- [x] Primary review/cleanup target
- [x] Supporting tasks
- [x] First validation command
- [x] Resume risk notes (`none/stale-context/runtime/env`)

## 1. Goal and Boundaries

Goal:
- Improve code quality, readability, and maintainability while protecting runtime behavior and release reliability.

In scope:
- Defect-focused code review
- Safe cleanup/refactor of low-risk internals
- Test coverage improvements for identified risk areas
- Removal of dead code or confusing paths when behavior is unchanged

Out of scope for this lane:
- Net-new gameplay features
- Unplanned schema/protocol changes without explicit compatibility review
- Broad architecture rewrites without decision record

## 2. Review and Cleanup Workflow

## Phase A - Intake and Review Map

### A1 Intake brief per review slice
- [x] Create a short implementation brief per slice (`TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
  - [x] Goal
  - [x] Player-facing impact (or explicit "none")
  - [x] Systems touched
  - [x] Risks
  - [x] Required tests
  - [x] Docs to update
  - [x] Rollback plan

### A2 Review map and risk tagging
- [x] Build review map by module:
  - [x] `java/core`
  - [x] `java/server`
  - [x] `java/client`
- [x] Tag each finding by severity:
  - [ ] `P0` crash, corruption, progression block, desync risk
  - [ ] `P1` core loop unreliability, repeated unfair behavior
  - [x] `P2` maintainability/readability issue with moderate risk
  - [x] `P3` low-impact cleanup

### A3 Evidence capture for runtime issues
- [ ] For behavior bugs, capture evidence bundle (`DEBUG_EVIDENCE_CAPTURE.md`)
- [ ] For replay/desync claims, run replay triage (`REPLAY_AND_DESYNC_TRIAGE.md`)

## Phase B - Fix and Cleanup Loops

Execute smallest complete unit each loop (`SPRINT_WORKFLOW.md` + `READY_DONE_WORKFLOW.md`):
- [x] Implement one logical fix or cleanup
- [x] Keep behavior change explicit: `behavior-change` or `no-behavior-change`
- [x] Add or update tests for each fixed bug or risky path
- [x] Run module-appropriate validation
- [x] Update plan loop notes
- [x] Commit with scope/reason/risk

Cleanup categories:
- [x] Correctness fixes found during review
- [x] Naming/readability cleanup
- [x] Method extraction and de-duplication
- [x] Dead code/path removal
- [x] Null safety and guard-rail hardening
- [x] Logging clarity for debugging and support

## Phase C - Quality Gates Per Loop

### C1 Local gates
- [x] `python tools/check_version_sync.py`
- [x] `python tools/check_docs_freshness.py --emit-report`
- [x] `cd java && ./gradlew :server:test :client:test --no-daemon` (or targeted test command for scoped slices)

### C2 Runtime gates
- [ ] Daily smoke route (`DAILY_SMOKE_WORKFLOW.md`) when runtime behavior was touched
- [ ] Golden pair/full golden run (`GOLDEN_PATH_REGRESSION.md`) for touched systems

### C3 Compatibility gates
- [x] If persistence/replay/protocol/schema touched, complete classification:
  - [x] save
  - [x] replay
  - [x] protocol
  - [x] schema
- [x] Record migration/version-gate decision (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`)

## Phase D - Docs and Release Discipline

### D1 Documentation sync
- [x] Update canonical docs for behavior or contract changes
- [x] Keep planned vs implemented status explicit
- [ ] Route new/updated docs in `docs/INDEX.md` when needed

### D2 Release and closeout
- [x] Run release checklist for release-facing loops
- [x] Verify CI and Release status before session close (`SESSION_END_WORKFLOW.md`)
- [x] Record:
  - [x] systems touched
  - [x] validation results
  - [x] known risks
  - [x] compatibility impact (`replay/save/protocol`)
  - [x] first action next session

## 3. Review Rubric (What to Look For)

Correctness:
- [ ] authority and ownership violations
- [ ] race/order assumptions in sim/network paths
- [ ] state lifecycle leaks across mission/hub transitions

Reliability:
- [x] null/guard handling in renderer and runtime paths
- [ ] disconnect/reconnect safety
- [ ] deterministic behavior requirements for replay surfaces

Maintainability:
- [x] repeated logic that should be centralized
- [ ] confusing method names or mixed responsibilities
- [x] dead or unreachable code

Performance:
- [x] hot-path allocations
- [x] expensive loops in per-tick or per-frame paths
- [x] avoidable map/list churn in core loops

Testing:
- [x] missing regression tests for known bug classes
- [ ] insufficient state-matrix coverage (partial-state verification is not done)

## 4. Exit Criteria for This Lane

- [ ] High-risk findings (`P0/P1`) resolved or explicitly deferred with owner and date
- [ ] Each completed slice has evidence (tests plus smoke/golden where needed)
- [ ] No compatibility-unknown changes merged
- [ ] Documentation reflects runtime truth
- [ ] Session closeout notes are resumable and specific

## 5. Loop Evidence Template

- Date:
- Branch + HEAD:
- Version:
- Slice ID:
- Finding class (`bug/cleanup/refactor/perf/logging/test`):
- Files touched:
- Validation commands:
- Smoke/golden result:
- Compatibility impact (`replay/save/protocol/schema`):
- Docs updated:
- Known risk:
- Next action:

## 6. Execution Log

### Loop ID: CRCL-2026-04-23-01

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: review mission pickup contract handling and land one safe cleanup/hardening fix with regression coverage
- Supporting tasks: build review map (`core/server/client`), classify compatibility impact, record close-out evidence
- First validation command: `./gradlew :server:test --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon`
- Resume risk notes: `env` (OneDrive/Gradle file-lock risk)

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: harden input normalization in `ServerProtocolHandler` for portal transition/session identifiers and add direct regression tests.
- Player-facing impact: none expected for normal flows; improved resilience for whitespace/case variant payloads and oversized session ids.
- Systems touched: `java/server` (`ServerProtocolHandler`), `java/server` tests (`ServerProtocolHandlerMissionPickupSeedTest`).
- Risks: low; protocol parsing path touched but change is permissive/defensive.
- Required tests: `:server:test --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `normalizePortalTransitionType` and `normalizeSessionId` changes plus the two new tests.

Review map and findings:
- `java/core`: no P0/P1 findings in this slice; no edits.
- `java/server`: P2 finding - strict portal transition normalization (`mission_return` case/whitespace handling) and unbounded session-id normalization.
- `java/client`: P3 observation - renderer/UI constructor guard coverage (`Gdx.app != null`) is uneven; deferred to separate cleanup slice.

Implemented cleanup (`behavior-change`: defensive-hardening, backwards-compatible):
- `ServerProtocolHandler.normalizePortalTransitionType(...)`
  - now trims + lowercases input before comparison
  - defaults unknown/null values to `inter_hub`
- `ServerProtocolHandler.normalizeSessionId(...)`
  - now trims, falls back to `missing`, and clamps to 128 chars

Regression coverage added:
- `normalizePortalTransitionTypeAcceptsCaseAndWhitespaceVariants`
- `normalizeSessionIdTrimsAndClampsLength`

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: compatible (more permissive parsing, no wire schema change)
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- evaluated trigger conditions; no cross-repo outputs required for this slice (`game repo only`).

Validation evidence:
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` runs are `success`.
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home`
  `./gradlew :server:test --tests com.indieniinja.server.ServerProtocolHandlerMissionPickupSeedTest --no-daemon` -> PASS.

Known issues/risks:
- Local OneDrive/Gradle lock contention still affects default local build paths; workaround required for deterministic local validation.
- Commit status: intentionally left uncommitted for user review before creating a scoped cleanup commit.

First action next session:
- Run next review/cleanup slice on client-side constructor guard consistency (`Gdx.app != null`) and add headless-safe tests where applicable.

### Loop ID: CRCL-2026-04-23-02

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: make client renderer/UI/screen constructor guard behavior consistent by applying `Gdx.app != null` checks to libGDX allocations and making dispose/render paths headless-safe.
- Player-facing impact: none (runtime behavior unchanged when libGDX is initialized).
- Systems touched: `java/client` rendering + UI screen constructors and disposal paths.
- Risks: low to moderate; broad file-touch footprint in client UI classes.
- Required tests: targeted guard regression test + full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert constructor/dispose guard edits and remove `ClientConstructorGuardTest`.

Review map and findings:
- `java/client`: P3 finding confirmed - constructor guard pattern was inconsistent (only `DevConsole` guarded `Gdx.app`).
- `java/core` / `java/server`: no additional findings in this slice.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Added constructor guard pattern (`Gdx.app != null`) and null-safe render/dispose gates to:
  - `HudRenderer`
  - `DialogueOverlay`
  - `InventoryOverlay`
  - `CraftingOverlay`
  - `ShopOverlay`
  - `MissionSelectOverlay`
  - `MinimapRenderer`
  - `ModeSelectScreen`
  - `SlotSelectScreen`
  - `MainMenuScreen`
  - `PauseScreen`
  - `UiStyle.build()` fallback for headless instantiation.
- Added headless constructor regression coverage:
  - `java/client/src/test/java/com/indieniinja/client/ui/ClientConstructorGuardTest.java`

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo work required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp3`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-3`
  `./gradlew :client:test --tests com.indieniinja.client.ui.ClientConstructorGuardTest --no-daemon` -> PASS.
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp3`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-3`
  `./gradlew :client:test --no-daemon` -> PASS.

Known issues/risks:
- OneDrive/Gradle lock contention on temp caches can intermittently produce `AccessDeniedException`; mitigated by isolated temp cache roots for test runs.
- Commit status: intentionally left uncommitted (user requested commit at end after multiple slices).

### Loop ID: CRCL-2026-04-23-03

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: extend headless guard-rail consistency to client managers that still hard-required `Gdx.files` in default constructors/utilities.
- Player-facing impact: none.
- Systems touched: `DialogueManager`, `MissionManager`, `SaveManager.listSlots`.
- Risks: low; runtime path unchanged where `Gdx` is initialized.
- Required tests: dedicated manager guard tests + full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert manager constructor/listSlots guards and remove `HeadlessManagerConstructorGuardTest`.

Implemented cleanup (`behavior-change`: no-behavior-change):
- `DialogueManager()` now returns an empty tree map when `Gdx.app`/`Gdx.files` is unavailable.
- `MissionManager()` now falls back to an empty definition map when `Gdx` runtime is unavailable.
- `SaveManager.listSlots()` now returns empty slot summaries when `Gdx` runtime is unavailable.
- Added regression coverage:
  - `java/client/src/test/java/com/indieniinja/client/game/HeadlessManagerConstructorGuardTest.java`

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact (runtime save format/serialization unchanged)
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo work required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp3`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-3`
  `./gradlew :client:test --tests com.indieniinja.client.game.HeadlessManagerConstructorGuardTest --tests com.indieniinja.client.ui.ClientConstructorGuardTest --no-daemon` -> PASS.
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp3`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-3`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` runs are `success`.

Known issues/risks:
- Default `python` shim (`WindowsApps`) was inaccessible in this environment; explicit Python path was used for `check_version_sync`.
- Commit status: intentionally left uncommitted pending user sign-off on full cleanup batch.

Session closeout note (per `SESSION_END_WORKFLOW.md`):
- Date: 2026-04-23
- Branch + HEAD: `master` @ `7f7dc73`
- Current version: `v0.12.04`
- Systems touched: `java/client` UI/rendering/screens + manager guards + client tests.
- Validation run: targeted guard tests, full `:client:test`, docs freshness check, version sync check, CI/Release status check.
- Compatibility impact: replay `no`, save `no`, protocol `no`.
- Known issue/risk: local temp-cache lock contention can require isolated `LOCALAPPDATA/GRADLE_USER_HOME` values.

First action next session:
- Run method-extraction/de-dup cleanup slice for client UI item/label formatting helpers (`InventoryOverlay` / `ShopOverlay`) with no behavior change and targeted tests.

### Loop ID: CRCL-2026-04-23-04

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: method-extraction/de-dup cleanup for client UI item/label formatting (`InventoryOverlay` + `ShopOverlay`)
- Supporting tasks: add targeted formatter regression tests, run full client test gate, refresh docs/version/CI evidence
- First validation command: `./gradlew :client:test --tests com.indieniinja.client.ui.ItemLabelFormatterTest --no-daemon`
- Resume risk notes: `env` (OneDrive/Gradle temp-cache lock contention)

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: centralize duplicated item-label/sell-price formatting logic used by inventory and shop overlays while preserving output strings.
- Player-facing impact: none (UI strings/prices are parity-preserved by regression tests).
- Systems touched: `java/client` UI overlays (`InventoryOverlay`, `ShopOverlay`) and new shared formatter utility.
- Risks: low; string formatting regression risk mitigated by explicit output tests.
- Required tests: `:client:test --tests com.indieniinja.client.ui.ItemLabelFormatterTest` plus full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: remove `ItemLabelFormatter`, restore original overlay helper methods, remove formatter test class.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Extracted shared formatting helper:
  - `java/client/src/main/java/com/indieniinja/client/ui/ItemLabelFormatter.java`
  - centralizes:
    - inventory abbreviation logic (`abbreviateForInventory`)
    - shop abbreviation logic (`abbreviateForShop`)
    - estimated sell-price table (`estimatedSellPrice`)
    - shop buy-line / inventory sell-line formatting helpers
- Updated overlays to consume shared helper:
  - `InventoryOverlay` now uses `ItemLabelFormatter.abbreviateForInventory(...)`
  - `ShopOverlay` now uses `ItemLabelFormatter.formatShopBuyLine(...)` and `formatInventorySellLine(...)`
- Added focused regression coverage:
  - `java/client/src/test/java/com/indieniinja/client/ui/ItemLabelFormatterTest.java`
  - verifies inventory/shop abbreviation parity, sell-price table parity, and exact formatted line outputs.

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp4`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-4`
  `./gradlew :client:test --tests com.indieniinja.client.ui.ItemLabelFormatterTest --no-daemon` -> PASS.
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp4`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-4`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- Default `python` shim remains unreliable in this environment; explicit Python path is still required for deterministic version-sync gate runs.
- OneDrive-backed temp cache lock contention remains an intermittent local risk; isolated `LOCALAPPDATA`/`GRADLE_USER_HOME` roots mitigate it.

First action next session:
- Run the dead-code/path-removal cleanup slice for unused UI fields/helpers and verify no render/input behavior changes.

### Loop ID: CRCL-2026-04-23-05

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: dead-code/path-removal cleanup for unused client UI/render helpers.
- Supporting tasks: verify symbol usage before deletion, run full client validation, refresh version/docs/CI evidence.
- First validation command: `./gradlew :client:test --no-daemon`
- Resume risk notes: `env` (sandbox network/cache constraints for Gradle wrapper/dependency fetch).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: remove unused helper/constant declarations in client visual code without changing render/input behavior.
- Player-facing impact: none.
- Systems touched: `java/client` (`DevConsole`, `EntityRenderer`).
- Risks: low; removed members were unreferenced.
- Required tests: full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: restore removed helper/constants in touched files.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Removed dead UI helper `DevConsole.logInfo(String)` (private, unreferenced).
- Removed dead renderer constants `EntityRenderer.FPS_HURT` and `EntityRenderer.FPS_WALL_SLIDE` (private, unreferenced).
- No call-path or runtime-behavior changes.

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp5`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-5`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- Initial in-sandbox Gradle run failed due blocked socket access while fetching wrapper; rerun outside sandbox succeeded.
- Commit status: intentionally left uncommitted (user requested batching and committing at end).

First action next session:
- Run the logging-clarity slice: tighten high-signal client runtime logs for debugging/support while keeping gameplay behavior unchanged.

### Loop ID: CRCL-2026-04-23-06

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: improve network-client logging clarity with structured, high-signal event labels.
- Supporting tasks: keep behavior unchanged, run full `:client:test`, refresh docs/version/CI evidence.
- First validation command: `./gradlew :client:test --no-daemon`
- Resume risk notes: `env` (encoding and sandbox/network constraints when editing/running local tooling).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: make `NetworkClientThread` logs easier to scan/correlate during support triage by standardizing event naming and key/value fields.
- Player-facing impact: none.
- Systems touched: `java/client` network runtime (`NetworkClientThread`).
- Risks: low; string-only log changes.
- Required tests: full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `NetworkClientThread` log-line edits.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Standardized network connection lifecycle logs to structured event-style forms:
  - `connect_start`, `connect_success`, `reconnect_scheduled`, `client_thread_stopped`.
- Standardized inbound message logs:
  - `server_hello`, `world_transition`, `scripted_loss_received`, `ignored_message`.
- Added host/port/backoff context to reconnect logs for support debugging.
- Encoding fix during implementation:
  - Removed accidental UTF-8 BOM introduced during intermediate file write (compile restored immediately).

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp5`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-5`
  `./gradlew :client:test --no-daemon` -> PASS.
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp5`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-5`
  `./gradlew :client:compileJava --no-daemon` -> PASS (outside sandbox rerun).
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- One intermediate compile failure was caused by an accidental UTF-8 BOM; fixed by rewriting file without BOM.
- In-sandbox `:client:compileJava` hit transient Gradle cache `AccessDeniedException`; outside-sandbox rerun passed.
- Commit status: intentionally left uncommitted (user requested batching and committing at end).

First action next session:
- Run a focused performance-review slice on client hot-path allocations (`GameScreen`/`HudRenderer`) and capture before/after evidence if any low-risk reductions are applied.

### Loop ID: CRCL-2026-04-23-07

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: performance slice on client hot-path allocations in `GameScreen` and `HudRenderer`.
- Supporting tasks: keep runtime behavior unchanged, validate full client tests, refresh docs/version/CI evidence.
- First validation command: `./gradlew :client:test --no-daemon`
- Resume risk notes: `env` (temp cache/network constraints and iterative compile/test loops).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: reduce avoidable per-frame/per-tick allocations in high-frequency render/sim paths without changing gameplay behavior.
- Player-facing impact: none expected (performance/readability cleanup only).
- Systems touched: `java/client` (`GameScreen`, `HudRenderer`).
- Risks: low; broad method-touch in frame loop but logic preserved.
- Required tests: full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `GameScreen`/`HudRenderer` changes for this loop.

Implemented cleanup (`behavior-change`: no-behavior-change):
- `GameScreen` hot-path allocation reductions:
  - Replaced repeated `players.stream().filter(...).findFirst()` calls with helper-based slot lookups (`findPlayerBySlot`, `findPlayerBySlotOrFirst`) across render/tick paths.
  - Added `inputForReplayTick(long)` to avoid eager `new InputCommand()` allocation on every replay tick.
  - Replaced per-tick `Map.of(0, cmd)` allocation in solo sim step with reusable `soloStepInputs` map (`clear` + `put`).
- `HudRenderer` hot-path allocation reductions:
  - Replaced per-frame boss-phase `new Color(...)` creation with static phase color constants.
  - Replaced per-frame `new float[]{0.75f, 0.50f, 0.25f}` divider array with static constant.
  - Replaced death-overlay stream/lambda check with loop helper (`isPlayerDead`).

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp6`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-6`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- One intermediate compile failure during the loop (`inputForReplayTick` parameter type mismatch) was fixed immediately (`int` -> `long`).
- Commit status: intentionally left uncommitted pending user direction after this performance slice.

First action next session:
- Run the next performance review slice on expensive per-frame loops and map/list churn in render/update paths, with targeted micro-optimizations only where behavior remains unchanged.

### Loop ID: CRCL-2026-04-23-08

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: continue performance lane with explicit map/list churn reduction in `GameScreen` runtime paths.
- Supporting tasks: keep behavior unchanged, validate full client tests, refresh docs/version/CI evidence.
- First validation command: `./gradlew :client:test --no-daemon`
- Resume risk notes: `env` (temp Gradle cache/bootstrap overhead in isolated local roots).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: remove avoidable per-frame/per-tick map/list allocations in mission tracker, minimap marker, and inventory-progress paths.
- Player-facing impact: none.
- Systems touched: `java/client` (`GameScreen`, `MissionManager`).
- Risks: low; data-flow/loop cleanup only, no gameplay contract change.
- Required tests: full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `GameScreen` and `MissionManager` edits in this loop.

Implemented cleanup (`behavior-change`: no-behavior-change):
- `GameScreen` map/list churn reductions:
  - Added reusable scratch collections:
    - `missionTrackerLinesScratch`
    - `minimapObjectiveMarkersScratch`
    - `inventoryTotalsScratch`
  - `syncMissionTrackerHud()` now reuses `missionTrackerLinesScratch` instead of allocating a new list each frame.
  - `buildMinimapObjectiveMarkers()` now reuses `minimapObjectiveMarkersScratch` instead of allocating a new list each frame.
  - `tickMissionProgress()` now reuses `inventoryTotalsScratch` instead of allocating a new hash map each tick.
- `MissionManager` progress-map churn reduction:
  - Added read-only live view accessor `getObjectiveProgressView()` backed by a single unmodifiable map wrapper.
  - `GameScreen.syncMissionTrackerHud()` now reads this view instead of requesting a per-frame snapshot copy.

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp7`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-7`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- No functional regressions observed in client test suite.
- Commit status: intentionally left uncommitted pending user direction.

First action next session:
- Continue performance lane with targeted expensive-loop reductions in `MinimapRenderer` world-to-minimap projection path (reuse scratch vectors / reduce per-marker temp allocations) while preserving draw behavior.

### Loop ID: CRCL-2026-04-23-09

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: execute the queued `MinimapRenderer` expensive-loop slice from CRCL-08 first action.
- Supporting tasks: preserve minimap draw behavior, validate full client tests, refresh docs/version/CI evidence.
- First validation command: `./gradlew :client:test --no-daemon`
- Resume risk notes: `env` (isolated Gradle cache bootstrap overhead in temp roots).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: remove avoidable per-frame allocations in `MinimapRenderer` world-to-minimap projection path.
- Player-facing impact: none expected (render-path allocation cleanup only).
- Systems touched: `java/client` (`MinimapRenderer`).
- Risks: low; projection helper contract changed from return-array to out-parameter.
- Required tests: full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `MinimapRenderer` changes in this loop.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Added reusable projection scratch buffer in `MinimapRenderer`:
  - `minimapProjectionScratch` (`float[2]`).
- Refactored `worldToMinimap(...)`:
  - from `float[]` allocation-return helper
  - to `boolean` helper that writes `{x,y}` into a caller-provided output array.
- Updated all minimap projection hot-path loops to reuse the same scratch output:
  - enemies, pickups, portals, NPCs, bosses, players, and mission objective markers.
- Result:
  - removes per-entity/per-marker `new float[]` churn in per-frame minimap render path while preserving coordinate math.

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp8`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-8`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- No functional regressions observed in client test suite.
- Commit status: intentionally left uncommitted pending user direction.

First action next session:
- Continue performance lane in `MinimapRenderer` by reducing remaining per-frame allocation churn (`roomColor`/`pickupTypeColor` object creation and repeated `roomKey` string construction in render loops) while preserving visual output.

### Loop ID: CRCL-2026-04-23-10

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: execute the queued `MinimapRenderer` churn slice from CRCL-09 first action.
- Supporting tasks: keep minimap visuals unchanged, validate full client tests, refresh docs/version/CI evidence.
- First validation command: `./gradlew :client:test --no-daemon`
- Resume risk notes: `env` (isolated Gradle cache bootstrap overhead in temp roots).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: remove remaining per-frame object churn in minimap color selection and room-key generation.
- Player-facing impact: none expected (render-path cleanup only).
- Systems touched: `java/client` (`MinimapRenderer`).
- Risks: low; helper return values now reference static color constants and room-key lookup now caches by packed grid coordinate.
- Required tests: full `:client:test`.
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `MinimapRenderer` changes in this loop.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Replaced per-call room color allocation in `roomColor(...)`:
  - switched from `new Color(...)` in switch branches to static room color constants.
- Replaced per-call pickup color allocation in `pickupTypeColor(...)`:
  - switched from `new Color(...)` in switch branches to static pickup color constants.
- Replaced transient room key string construction path:
  - added `LongMap<String> roomKeysByPackedCoord` cache keyed by packed `(gx, gy)`.
  - `roomKey(...)` now returns cached string keys and only builds once per coordinate.
  - `clearState()` now clears the room-key cache alongside minimap textures.
- Result:
  - eliminates per-frame `Color` and repeated `String` churn in minimap render loops while preserving draw logic.

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp9`
  `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-9`
  `./gradlew :client:test --no-daemon` -> PASS.
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.04` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `gh run list --limit 3 --json status,conclusion,name,headSha` -> latest `CI` and `Release` are `success`.

Known issues/risks:
- No functional regressions observed in client test suite.
- Commit status: intentionally left uncommitted pending user direction.

First action next session:
- Continue performance lane with a focused pass on remaining minimap loop overhead (e.g., repeated `visitedRooms.contains(...)` checks and repeated room-center arithmetic in multi-pass room loops) only if behavior remains unchanged.

### Loop ID: CRCL-2026-04-23-11

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.04`
- Primary target: execute CRCL-10 queued minimap overhead pass before release workflow execution.
- Supporting tasks: keep minimap behavior unchanged and collect release-grade local gate evidence.
- First validation command: `./gradlew :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`
- Resume risk notes: `env` (isolated Gradle cache/bootstrap overhead in temp roots).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: reduce remaining `MinimapRenderer` per-frame overhead from repeated visited-room lookups and repeated room-center arithmetic.
- Player-facing impact: none expected (render-path cleanup only).
- Systems touched: `java/client` (`MinimapRenderer`).
- Risks: low; loop condition/caching changes in draw passes.
- Required tests: release-grade local gates (`server/client tests`, `shadowJar` build outputs).
- Docs to update: this cleanup plan execution log.
- Rollback plan: revert `MinimapRenderer` changes in this loop.

Implemented cleanup (`behavior-change`: no-behavior-change):
- Added reused per-frame visible-room visited cache in `MinimapRenderer`:
  - `visibleVisitedRoomCoordsScratch` keyed by packed room coordinates.
- Updated multi-pass minimap loops to use cached visited-state checks instead of repeated `visitedRooms.contains(roomKey(...))` calls.
- Added `roomHalf` precompute for reused room-center arithmetic in connection-line pass.
- Preserved previous projection and color/room-key cache optimizations from CRCL-09/10 while tightening hot-path loop reuse.

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- Strict combined release lane attempted:
  - `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp10`
    `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-10`
    `./gradlew :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`
    -> FAIL (`:client:copyJarToRoot` task-order validation conflict with `:client:compileTestJava`).
- Deterministic split-lane workaround (`ITERATION_RELEASE_PROTOCOL` evidence capture):
  - `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp10c`
    `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-10c`
    `./gradlew :server:test :client:test --no-daemon` -> PASS.
  - `LOCALAPPDATA=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-localapp10d`
    `GRADLE_USER_HOME=C:\\Users\\asher\\AppData\\Local\\Temp\\codex-gradle-user-home-10d`
    `./gradlew :server:shadowJar :client:shadowJar --no-daemon` -> PASS.

Known issues/risks:
- Combined local release lane remains sensitive to Gradle task-order validation (`:client:copyJarToRoot`).
- Commit status: intentionally left uncommitted pending release-loop commit/tag execution.

First action next session:
- Execute release-loop closure: finalize release docs parity, commit scoped cleanup/release prep, push, verify CI green, then bump/tag/publish per `ITERATION_RELEASE_PROTOCOL`.

### Loop ID: CRCL-2026-04-23-12

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.05`
- Primary target: execute commit + tag + release closure for the cleanup batch using `ITERATION_RELEASE_PROTOCOL`.
- Supporting tasks: verify CI green on feature SHA before tagging; verify release assets after tag publication.
- First validation command: `gh run list --limit 8 --json status,conclusion,name,headSha,displayTitle,event`
- Resume risk notes: `env` (GitHub Actions async wait windows).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: publish a testable release for cleanup slices CRCL-08 through CRCL-11 with workflow-complete evidence.
- Player-facing impact: none expected (cleanup/perf hardening, no intended gameplay contract changes).
- Systems touched: release metadata/docs, plan logs, GitHub release/tag state.
- Risks: low; release discipline and metadata parity only.
- Required tests: version/docs gates + server/client tests + shadowJar gates + CI/Release success.
- Docs to update: cleanup plan log and release-facing docs.
- Rollback plan: cut next patch if post-tag regression is detected.

Implemented cleanup/release closure:
- Committed scoped batch with release metadata and cleanup slices:
  - commit: `6fdddbf`
  - message includes `plan_id/scope/reason/risk`.
- Pushed `master` and waited for CI success on feature SHA before tagging:
  - CI run: `24838332894` -> `success`.
- Created and pushed annotated tag:
  - `v0.12.05`.
- Verified tag-triggered Release workflow:
  - Release run: `24838474542` -> `success`.
- Verified published release assets:
  - `docs-archive-2026-04-23-v0.12.05.zip`
  - `ninja-client-all.jar`
  - `ninja-server-all.jar`

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `C:\\Users\\asher\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/check_version_sync.py --tag v0.12.05` -> PASS.
- `python tools/check_docs_freshness.py --emit-report` -> PASS.
- `./gradlew :server:test :client:test --no-daemon` -> PASS.
- `./gradlew :server:shadowJar :client:shadowJar --no-daemon` -> PASS.
- `gh run list --limit 8 --json status,conclusion,name,headSha,displayTitle,event` -> `CI` + `Release` success for `6fdddbf`.
- `gh release view v0.12.05 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets,url` -> PASS (assets present).

Known issues/risks:
- Combined local Gradle release lane (`test + shadowJar` in one invocation) still triggers task-order validation conflict on `:client:copyJarToRoot`; split-lane workaround remains required locally.
- Post-release follow-up should either codify split-lane local gate usage permanently or patch task dependency ordering.

First action next session:
- Resume remaining review rubric coverage (authority/race/lifecycle/reliability matrix) and run targeted smoke/golden evidence when a future slice changes runtime behavior.

### Loop ID: CRCL-2026-04-23-13

Session start note (per `SESSION_START_WORKFLOW.md`):
- Date: 2026-04-23
- Branch: `master`
- Current version: `v0.12.05`
- Primary target: continue cleanup-lane rubric coverage by hardening `WorldGraph` reconstruction ownership/lifecycle contracts used by persistence reload paths.
- Supporting tasks: add state-matrix regression coverage for reconstruction guardrails and direction-normalization intake safety.
- First validation command: `./gradlew :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --tests com.indieniinja.server.WorldGraphTest --no-daemon`
- Resume risk notes: `runtime` (must preserve valid persisted-world load behavior while hardening invalid-state handling).

Task intake brief (per `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`):
- Goal: remove authority/lifecycle leakage in `WorldGraph.fromRooms(...)` and harden direction intake for deserialized room neighbor data.
- Player-facing impact: none expected for valid data; corrupted world-graph payloads now fail fast instead of being accepted silently.
- Systems touched: `java/shadowascent` (`WorldGraph`), `java/server` tests (`WorldGraphGenerationTest`).
- Risks: low; constructor/reconstruction and direction normalization changes in world-graph internals.
- Required tests: `:server:test --tests com.indieniinja.server.WorldGraphGenerationTest --tests com.indieniinja.server.WorldGraphTest`.
- Docs to update: this cleanup plan execution log and `docs/CURRENT_STATE.md`.
- Rollback plan: revert `WorldGraph` reconstruction/intake changes and the added regression tests.

Review map and findings:
- `java/core`: no new P0/P1 findings in this slice; no edits.
- `java/server`: P2 finding - reconstruction accepted caller-owned mutable room maps and could be mutated after load boundaries.
- `java/shadowascent`: P2 finding - deserialized `neighborDirs` accepted null/invalid/case-variant entries without normalization.
- `java/client`: no new findings in this slice; no edits.

Implemented cleanup (`behavior-change`: defensive-hardening, no intended gameplay/runtime contract change for valid data):
- `WorldGraph` reconstruction ownership/lifecycle hardening:
  - `fromRooms(...)` now validates non-null inputs, snapshots the room map, resolves canonical start/exit by coordinates, and rejects missing/type-mismatched start/exit entries.
  - `WorldGraph` constructor now stores an unmodifiable room-map snapshot to prevent external map/view mutation after construction.
- `WorldGraph.RoomNode` deserialization constructor now normalizes direction strings (`trim + lowercase`) and drops null/unknown directions.
- `neighborRoom(...)` now uses normalized direction lookup so case/whitespace variants resolve safely.

Regression coverage added:
- `fromRooms_snapshotUnaffectedByCallerMapMutation`
- `fromRooms_rejectsMissingStartOrExitInRoomMap`
- `roomNodeDeserializationConstructorNormalizesDirectionsAndDropsInvalid`
- `neighborRoom_acceptsCaseAndWhitespaceDirection`

Smoke/golden result:
- Not run for this slice (`no player-path or mission-flow behavior change`; defensive reconstruction hardening only).

Compatibility classification (`COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`):
- save: no impact (valid persisted graphs unchanged; invalid graphs now fail fast)
- replay: no impact
- protocol: no impact
- schema: no impact
- migration/version gate: not required

Cross-repo coordination check (`CROSS_REPO_COORDINATION.md`):
- trigger conditions reviewed; no cross-repo changes required (`game repo only`).

Validation evidence:
- `./gradlew :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --tests com.indieniinja.server.WorldGraphTest --no-daemon` -> PASS.

Known issues/risks:
- Work remains intentionally uncommitted pending user direction for commit/release loop timing.
- Corrupted persisted graph payloads with missing/invalid start/exit entries now reject reconstruction; load path should regenerate safely via existing fallback behavior.

First action next session:
- Continue rubric pass on remaining `race/order` and `disconnect/reconnect safety` surfaces in world/zone transition lifecycle (`ServerProtocolHandler` + `ZoneSimulationLoop`), and run smoke/golden evidence if a slice changes player-visible behavior.
