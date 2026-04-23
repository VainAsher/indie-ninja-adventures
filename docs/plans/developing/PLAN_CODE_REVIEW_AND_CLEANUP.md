---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-23
version_anchor: v0.12.04
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
- [ ] Commit with scope/reason/risk

Cleanup categories:
- [x] Correctness fixes found during review
- [x] Naming/readability cleanup
- [x] Method extraction and de-duplication
- [ ] Dead code/path removal
- [x] Null safety and guard-rail hardening
- [ ] Logging clarity for debugging and support

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
- [ ] Run release checklist for release-facing loops
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
- [ ] dead or unreachable code

Performance:
- [ ] hot-path allocations
- [ ] expensive loops in per-tick or per-frame paths
- [ ] avoidable map/list churn in core loops

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
