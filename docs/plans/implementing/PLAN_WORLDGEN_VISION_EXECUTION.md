# Worldgen Vision Execution Plan (Act I -> Runtime Integration)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn current worldgen planning metadata into production-trustworthy gameplay constraints by enforcing strict section authoring contracts, raising traversal correctness, improving pacing variety, and upgrading QA scoring so `valid` means playable.

**Architecture:** Keep deterministic seed flow unchanged while hardening authored data contracts and validation semantics. Execute four disjoint parallel lanes (schema, traversal contracts, content variety, lab scoring), then merge through a single integrator lane that runs full regression and documents replay-impact changes.

**Tech Stack:** Java 21, Gradle 8.7, JSON authored worldgen data, Python worldgen lab scripts, JUnit 5 + AssertJ.

---

## Success Criteria (Program-Level)

1. Mandatory progression edges in Act I no longer all downgrade to `needs_transition`.
2. Authored section files are schema-complete and CI-failing when malformed.
3. Act I critical path shows measurable template variety across seed sweep.
4. Worldgen quality metrics include traversal/pacing risk, not only shell-edge geometry.
5. Runtime integration path is documented with safe feature flags and replay-risk notes.

## Non-Negotiable Constraints

1. Seed determinism must remain stable for unchanged inputs.
2. No hidden defaults for required authored fields in strict mode.
3. Existing passing tests stay green unless intentionally replaced by stricter checks.
4. All new validation failures must be actionable (`issue kind` + `repair action`).
5. Every lane must publish verification evidence before merge.

## Branching and Ownership

1. One feature branch per lane: `wg/lane-a-schema`, `wg/lane-b-contracts`, `wg/lane-c-variety`, `wg/lane-d-quality`.
2. Each lane has exclusive write scope until integration.
3. Integrator lane rebases and resolves conflicts; no lane force-push to another lane.

## Shared Verification Baseline

```powershell
cd java
./gradlew.bat :shadowascent:test --tests com.indieniinja.world.sections.SectionTemplateLibraryTest --tests com.indieniinja.world.layout.HybridLayoutPlannerTest --tests com.indieniinja.world.validation.GenerationValidationPlannerTest --tests com.indieniinja.world.progression.WorldProgressionGeneratorTest --tests com.indieniinja.world.progression.AuthoredProgressionLoaderTest --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --no-daemon
./gradlew.bat :shadowascent:worldgenSnapshot -Pseed=420 -Prooms=20 -Pshape=BLOB -PcampaignId=act1 "-Pout=build/worldgen-snapshots/act1-seed-420.json" --no-daemon
cd ..
python tools/worldgen_lab.py render java/shadowascent/build/worldgen-snapshots/act1-seed-420.json --out build/worldgen-lab/act1-seed-420
```

---

## Parallel Lane Matrix

| Lane | Owner | Focus | Write Scope | Conflict Risk |
| --- | --- | --- | --- | --- |
| A | Agent A | Section schema hardening | `world/sections/*`, section schema tests, docs | Low |
| B | Agent B | Traversal contract semantics | `world/contracts/*`, `world/validation/*`, contract tests | Low |
| C | Agent C | Authored variety expansion | `data/worldgen/sections/*.json`, progression/selection data tests | Low |
| D | Agent D | Quality scoring v2 | `world/lab/*`, lab tests, compare output fields | Low |
| E | Integrator | Merge + release gates | docs + integration glue + full regression | Medium |

---

## Ticket Pack A (Schema Hardening)

### WG-A1: Add Strict Section Schema Validator

**Files:**
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/sections/SectionTemplateValidationIssue.java`
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/sections/SectionTemplateValidator.java`
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/sections/SectionTemplateLibrary.java`
- Create: `java/shadowascent/src/test/java/com/indieniinja/world/sections/SectionTemplateValidatorTest.java`

**Out of scope:** contracts, validation planner, lab scoring, section JSON content.

**Kind-level exemptions (decided, do not re-litigate):**
- `hub_home` and `boss_approach` kinds do NOT require `nodeKinds`, `edgeRules`, or `requiredSockets`.
- All other kinds (e.g. `key_trial`, `shop_save_loop`) require all navigation fields.
- This keeps `lantern_heights_hub.json` and `summit_shrine_boss.json` valid under strict mode without Lane C backfill, so lanes A and C are not sequentially dependent.

- [ ] Define strict required fields by template `kind` (including `footprint`, `nodeKinds`, `edgeRules`, `requiredSockets`, `anchors` minimums where applicable) — apply kind-level exemptions above.
- [ ] Add a non-throwing validator that emits structured issues (file, field, severity, message).
- [ ] Wire library load to collect and expose validation issues.
- [ ] Add opt-in strict mode (`-Dninja.sectionTemplateStrict=true`) that fails load when errors exist.
- [ ] Add deterministic sort of issue output for stable CI logs.
- [ ] Add tests for valid template, missing field, malformed socket id, empty anchors on required kinds.
- [ ] Run lane verification tests.

**Acceptance:** strict mode fails malformed templates with explicit issue list and deterministic ordering.

### WG-A2: Document Schema Contract

**Files:**
- Modify: `docs/systems/WORLD_GEN.md`

- [ ] Add section-level schema table with required vs optional fields.
- [ ] Document strict-mode property and CI usage.
- [ ] Document migration policy for legacy partial templates.

**Acceptance:** docs explain how designers avoid silent fallback behavior.

---

## Ticket Pack B (Traversal Contracts)

### WG-B1: Raise `needs_transition` to Critical-Path Policy

**Files:**
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/contracts/SocketAnchorPlanner.java`
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/validation/GenerationValidationPlanner.java`
- Create: `java/shadowascent/src/test/java/com/indieniinja/world/contracts/SocketAnchorPlannerPolicyTest.java`
- Modify: `java/shadowascent/src/test/java/com/indieniinja/world/validation/GenerationValidationPlannerTest.java`

**Out of scope:** section schema and lab scoring.

- [ ] Introduce policy config: mandatory edges may only use `needs_transition` when explicit transition strategy exists.
- [ ] Add issue kind `critical_path_transition_debt` when mandatory edge violates policy.
- [ ] Ensure `validationReport.valid=false` for unresolved mandatory transition debt.
- [ ] Keep optional branch behavior lenient but recorded.
- [ ] Add tests proving pass/fail behavior across required vs optional edges.
- [ ] Confirm snapshot export includes new issue kind and repair action details.
- [ ] Run lane verification tests.

**Acceptance:** Act I baseline cannot claim `valid=true` while mandatory links rely on unresolved transitions.

### WG-B2: Standardize Socket Compatibility Grammar

**Files:**
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/contracts/SocketAnchorPlanner.java`
- Modify: `docs/systems/WORLD_GEN.md`

- [ ] Formalize socket token grammar (`side_band_traversal[_modifier...]`).
- [ ] Reject unknown bands/sides in strict contract mode.
- [ ] Add compatibility matrix documentation for walk/jump/climb traversal tags.

**Acceptance:** parser behavior and docs are aligned and test-covered.

---

## Ticket Pack C (Authored Variety Expansion)

### WG-C1: Expand Template Pool for Act I Critical Path

**Files:**
- Create/Modify: `data/worldgen/sections/*.json` for additional `forest:key_trial` and `lantern:boss_approach` variants.
- Create: `java/shadowascent/src/test/resources/worldgen/sections/variety/*.json` (if needed by tests)
- Create: `java/shadowascent/src/test/java/com/indieniinja/world/sections/SectionTemplateVarietyDataTest.java`

**Out of scope:** Java generator logic and validation planner semantics.

- [ ] Add at least 3 distinct `forest key_trial` variants with differentiated node flow and sockets.
- [ ] Add at least 2 `lantern boss_approach` variants with complete sockets and anchors.
- [ ] Backfill full schema fields for hub/boss templates currently relying on defaults.
- [ ] Add test asserting minimum candidate counts per `(biome, kind)` for Act I-required combinations.
- [ ] Confirm templates remain deterministic-selectable by id sorting/seed modulus.
- [ ] Run lane verification tests plus snapshot generation.

**Acceptance:** generated plans across seed sweep show materially lower template repetition on critical path.

### WG-C2: Authoring Guardrails for Designers

**Files:**
- Create: `docs/guides/WORLDGEN_SECTION_AUTHORING.md`

- [ ] Provide copyable section template skeletons by kind.
- [ ] Include anti-patterns: mismatched sockets, empty required arrays, weak anchor semantics.
- [ ] Include pre-PR checklist for content-only contributors.

**Acceptance:** content creators can author templates without code-level guesswork.

---

## Ticket Pack D (Quality Scoring v2)

### WG-D1: Extend Lab Metrics Beyond Shell Geometry

**Files:**
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabAnalyzer.java`
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabReport.java`
- Modify: `java/shadowascent/src/test/java/com/indieniinja/world/lab/WorldgenLabAnalyzerTest.java`

**Out of scope:** section schema, socket parser behavior.

**Schema bump decision (decided, do not re-litigate):**

- V2 quality scores go INTO the worldgen snapshot JSON (not lab-report-only), so old snapshots can be compared by score retrospectively.
- This requires bumping `GeneratorSchemaVersion` from `10` to `11`.
- Lane E (integrator) must regenerate the Act I baseline snapshot at seed 420 after merge and update `docs/CURRENT_STATE.md` with the new schema version.
- Replay impact: snapshot format change is `BREAKING` for any tooling that reads schema version 10 snapshots directly — document in WG-E1 integration note.

- [ ] Add score dimensions: `transitionDebtPenalty`, `criticalPathVarietyScore`, `socketCompatibilityScore` (or equivalent names).
- [ ] Preserve old warning counters for backward trend continuity.
- [ ] Emit both `qualityScoreV1` and `qualityScoreV2` during migration window.
- [ ] Bump `GeneratorSchemaVersion` from `10` to `11`.
- [ ] Add deterministic tests for score computation with fixed synthetic inputs.
- [ ] Ensure no NaN/negative overflow in edge cases.
- [ ] Run lane verification tests.

**Acceptance:** score reflects traversal/pacing risk even when shell warnings are zero.

### WG-D2: Compare Output Compatibility

**Files:**
- Modify: `tools/worldgen_lab.py`
- Modify: `tools/test_worldgen_lab.py`

**Out of scope:** runtime generation internals.

- [ ] Surface V2 metrics in compare JSON/CSV output.
- [ ] Keep existing compare consumers unbroken.
- [ ] Add tests confirming new fields and stable schema.

**Acceptance:** compare reports can gate both old and new quality signals.

---

## Integrator Lane E (Post-Parallel Merge)

**Canonical workflow references (read before starting this lane):**
- [`docs/workflow/ITERATION_RELEASE_PROTOCOL.md`](../../workflow/ITERATION_RELEASE_PROTOCOL.md) — canonical commit/tag/push/release loop
- [`docs/workflow/RELEASE_CHECKLIST.md`](../../workflow/RELEASE_CHECKLIST.md) — pre-tag and post-push gates
- [`docs/workflow/READY_DONE_WORKFLOW.md`](../../workflow/READY_DONE_WORKFLOW.md) — done definition

### WG-E1: Merge, Reconcile, and Gate

**Files:**
- Modify: conflict resolution files from A-D only as needed.
- Modify: `docs/systems/WORLD_GEN.md`
- Modify: `docs/CURRENT_STATE.md` — include schema version bump 10→11 and snapshot regeneration note
- Modify: `docs/CHANGELOG.md`

- [ ] Rebase A-D lanes onto latest mainline and resolve conflicts with no behavior loss.
- [ ] Run full shared verification baseline.
- [ ] Run additional seed sweep (`1..250`) and capture failure deltas.
- [ ] Regenerate Act I baseline snapshot (seed 420) and compare against pre-change baseline.
- [ ] Publish final integration note: deterministic changes, replay-impact (snapshot schema 10→11), migration risk.

**Acceptance:** one consolidated commit with green tests, documented behavior changes, and explicit rollback plan.

### WG-E2: Release Loop

**Canonical reference:** Follow `ITERATION_RELEASE_PROTOCOL.md` exactly for every step below.

**Files:**
- Modify: `version.json` — bump patch version
- Modify: `README.md` — update version banner
- Modify: `docs/ROADMAP.md` — mark worldgen vision lane complete
- Modify: `docs/CURRENT_STATE.md` — add session handover entry

- [ ] Bump `version.json` patch version (e.g. v0.13.20 → v0.13.21).
- [ ] Run pre-tag gates:
  - `python tools/check_version_sync.py`
  - `python tools/check_docs_freshness.py --emit-report`
  - `cd java && ./gradlew.bat :server:test :client:test --no-daemon`
  - `cd java && ./gradlew.bat :server:shadowJar :client:shadowJar --no-daemon`
  - `python tools/test_worldgen_lab.py`
  - `cd java && ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon`
- [ ] Commit version bump. Push feature commit (no tag yet). Wait for CI `java-build` green.
- [ ] Create annotated tag: `git tag v0.<minor>.<patch>`
- [ ] Push: `git push origin master && git push origin v0.<minor>.<patch>`
- [ ] Confirm CI workflow passes and Release workflow passes.
- [ ] Confirm release assets: `ninja-client-all.jar`, `ninja-server-all.jar`, `docs-archive-*.zip`.

**Acceptance:** `gh release view v0.<minor>.<patch>` shows 3 assets and no draft/prerelease flag.

### WG-E3: Player Testability and Manual Smoke

**Files:**
- Modify: `docs/PLAYABLE_TRUTH.md` — add worldgen changes section
- Modify: `docs/CURRENT_STATE.md` — add manual smoke result

**What to update in `PLAYABLE_TRUTH.md`:**
- Add a note under "What is working well enough to judge" that worldgen validation is now stricter — `valid=true` from the lab means the Act I critical path is traversable, not just geometrically complete.
- Add new template variety note: the Act I critical-path (forest trial rooms, lantern approach rooms) now has multiple authored variants; repetition across seeds should be lower.
- Do NOT change the G0 golden route — the player-visible route is unchanged.

**Manual smoke after release (run from launcher — never raw JARs):**
1. Launch `python launcher/launcher.py` → click Play → choose CAMPAIGN.
2. Complete steps 1–13 of the G0 golden route in `docs/PLAYABLE_TRUTH.md`.
3. Confirm: no crash, no softlock, all NPCs present, Linzi mission advances, hub change visible after Linzi accepted.
4. Open DevConsole (backtick `` ` ``) and run: `worldgen info` — confirm snapshot schema version shows `11`.
5. Save the manual smoke result to `docs/reports/manual-runtime/` using the naming convention from existing files.

- [ ] G0 golden route smoke passed and recorded.
- [ ] `PLAYABLE_TRUTH.md` updated with worldgen change notes.
- [ ] Smoke report saved to `docs/reports/manual-runtime/`.

**Acceptance:** You can follow the G0 route start to finish from the launcher with no instructions beyond `PLAYABLE_TRUTH.md`, and the route behaves exactly as before — worldgen changes are invisible to the player at the G0 level.

### WG-E4: Runtime Adoption RFC Stub

**Files:**
- Create: `docs/plans/implementing/PLAN_WORLDGEN_RUNTIME_ADOPTION.md`

- [ ] Define feature-flag strategy for consuming `hybridLayout` and `socketAnchorPlan` in live placement.
- [ ] Define rollout phases and kill-switch behavior.
- [ ] Define telemetry to validate runtime parity vs snapshot expectations.

**Acceptance:** runtime adoption has a controlled, measurable implementation path.

---

## Agent Prompt Templates (Copy/Paste)

### Prompt for Agent A

```text
You own lane A (WG-A1, WG-A2). Stay strictly inside world/sections + docs contract updates. Do not edit contracts, validation planner, lab scoring, or section content JSON. Deliver code, tests, verification command output summary, and a concise risk note.
```

### Prompt for Agent B

```text
You own lane B (WG-B1, WG-B2). Stay strictly inside contracts/validation + related tests/docs. Do not edit section schema implementation or lab scoring. Make validation semantics stricter for mandatory critical-path transition debt.
```

### Prompt for Agent C

```text
You own lane C (WG-C1, WG-C2). Stay strictly in data/worldgen/sections + authoring docs + data tests. Do not modify generator logic unless required for deterministic data loading tests. Focus on variety and schema completeness of authored templates.
```

### Prompt for Agent D

```text
You own lane D (WG-D1, WG-D2). Stay strictly in lab analyzer/report and worldgen_lab tooling/tests. Do not modify progression, section schema, or socket policy logic. Deliver V2 quality metrics while preserving V1 outputs.
```

### Prompt for Integrator

```text
You own lane E (WG-E1, WG-E2). Merge outputs from A-D, run full gates, resolve only required conflicts, and produce final release-quality integration documentation including rollback strategy.
```

---

## Final Exit Criteria

1. All lane deliverables merged.
2. All verification gates green.
3. Act I baseline snapshot regenerated and reviewed.
4. `validationReport.valid` semantics aligned with playable critical path reality.
5. Docs updated for designers, engineers, QA, and release owners.
