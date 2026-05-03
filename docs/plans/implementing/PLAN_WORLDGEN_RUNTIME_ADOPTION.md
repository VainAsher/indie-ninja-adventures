---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-05-03
version_anchor: v0.13.30
---

# Plan: Worldgen Runtime Adoption

## Purpose

Define a safe path for consuming snapshot-era worldgen planning metadata
(`hybridLayout`, `socketAnchorPlan`, stricter `validationReport`) inside live
runtime placement without breaking G0 player flow.

## Scope

- Runtime feature-flag strategy
- Rollout phases with kill-switch behavior
- Telemetry for parity checks between runtime and snapshot expectations

Out of scope:

- New authored content creation
- Quality scoring model changes
- Release tagging workflow

## Feature Flags

| Flag | Default | Purpose | Kill switch behavior |
| ---- | ------- | ------- | -------------------- |
| `ninja.runtime.useHybridLayout` | `false` | Enables runtime consumption of `hybridLayout.assignments` for section placement hints. | Disable flag to immediately revert to legacy `WorldGraph` room placement only. |
| `ninja.runtime.useSocketContracts` | `false` | Enables corridor/transition decisions from `socketAnchorPlan.connectionContracts`. | Disable flag to bypass contract-driven joins and use existing deterministic corridor logic. |
| `ninja.runtime.enforceValidationDebt` | `false` | Prevents runtime publication of worlds with unresolved `critical_path_transition_debt`. | Disable flag to allow legacy publish semantics while logging debt. |
| `ninja.runtime.useProcgenRooms` | `false` | Replaces `WorldGenerator.generate()` with `RoomGenerator.generate()` (procgen-lab) as the tile grid source inside `buildProceduralLayout`. Spawn logic and enemy/pickup placement are unchanged. Seeds derive from `SaveData.worldSeed ^ roomId.hashCode()`. | Disable flag to revert to `WorldGenerator` grid with no save or layout change required. |

Flag precedence:

1. Config file override (`user_data/settings/settings.json` for dev profiles)
2. JVM property override (`-Dninja.runtime.*`)
3. Default false in production until rollout phase 3

## Rollout Phases

### Phase 0 — Shadow mode (no behavior change)

- Compute runtime candidate decisions from `hybridLayout` and `socketAnchorPlan`
  but do not apply them.
- Emit parity telemetry comparing legacy vs candidate decisions.

Exit criteria:

- 0 crashes/softlocks across internal seed sweep
- candidate-vs-legacy disagreement understood and classified

### Phase 1 — Dev-only opt-in

- Enable `useHybridLayout` in dev builds only.
- Keep socket contracts observational.

Exit criteria:

- G0 route manual smoke unchanged
- no regression in room connectivity assertions

### Phase 2 — Contract-assisted joins

- Enable `useSocketContracts` in dev and staging.
- Allow transition insertion only where explicit `transitionStrategy` exists.

Exit criteria:

- unresolved `critical_path_transition_debt` trends downward across seed sweep
- no increase in runtime softlock reports

### Phase 3 — Guarded production rollout

- Enable flags for controlled cohorts.
- Turn on `enforceValidationDebt` after at least one stable iteration with no
  G0 regressions.

Rollback:

- Disable all three flags to return immediately to legacy behavior.

## Telemetry and Parity Signals

Emit per-generation telemetry row:

- `worldSeed`
- `generatorSchemaVersion`
- `runtimeFlags` (`hybrid`, `socket`, `validationDebt`)
- `legacyPlacementHash`
- `candidatePlacementHash`
- `contractMatchedCount`
- `contractNeedsTransitionCount`
- `criticalPathTransitionDebtCount`
- `runtimeValidationAccepted` (bool)

Required dashboards:

- debt count trend by build version
- candidate/legacy hash divergence rate
- runtime generation failure rate

## Verification Gates

- Local:
  - `:shadowascent:test --tests com.indieniinja.world.validation.GenerationValidationPlannerTest`
  - `:shadowascent:test --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest`
- Tooling:
  - `python tools/test_worldgen_lab.py`
- Manual:
  - G0 launcher smoke route unchanged and documented

## Risks

- replay drift when runtime placement starts consuming hybrid metadata
- false-positive validation debt blocks on content still in migration
- contract strictness mismatch between snapshot generation and runtime parser

## Open Questions

- Should `enforceValidationDebt` block world publication hard, or downgrade to
  warning for one release window?
- Do we need per-campaign flag granularity (`act1` only) before phase 3?

## Seed Sweep Evidence (v0.13.29, 2026-05-03)

Partial 1..50 sweep (deferred from 1..250 target). Full data: `docs/reports/worldgen/sweep-50-v0.13.29.csv`.

- Score range: 60–80, all seeds `overallStatus=fail`
- Root cause: `critical_path_transition_debt` on Act II+ nodes (archive, cathedral, cavern, foundry, spire) — no templates authored
- Act I (seed 420): `qualityScoreV2=96`, `valid=true`, `socketCompatibilityScore=100` — fully resolved
- Phase 0 entry criteria not yet met: candidate vs legacy disagreement not yet classified; debt count only trending down for Act I scope
- Full 1..250 sweep and Phase 0 parity telemetry remain deferred until Act II+ templates reduce debt below target threshold
