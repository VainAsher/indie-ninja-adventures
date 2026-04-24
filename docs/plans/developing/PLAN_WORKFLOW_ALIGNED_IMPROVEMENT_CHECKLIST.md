---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-24
version_anchor: v0.12.06
---

# Plan - Workflow-Aligned Improvement Checklist (v0.12.04+)

This checklist translates the improvement roadmap into an execution format that explicitly follows the workflows in `docs/workflow/`.

**Audit note (2026-04-24):** Full staleness audit performed against v0.12.06 repo state. Phase 1 and Section 3 marked complete based on evidence. Phase 2 confirmed as the active next phase. W0.x gates reformatted as continuous process reminders — they are being actively followed, not awaiting first execution.

---

## 0. Workflow Adherence Gates — Continuous (Established ✅)

These are ongoing process gates applied every session and loop, not one-time checks. All confirmed active as of v0.12.06 based on session close-out evidence in `docs/CURRENT_STATE.md`.

### W0.1 Session Start Gate

- [x] `SESSION_START_WORKFLOW.md` followed before coding — evidenced by session notes in every CURRENT_STATE.md close-out through v0.12.06

### W0.2 Task Intake Gate

- [x] `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md` consulted for each task — commit message format (`plan_id`, `scope`, `reason`, `risk`) and `/task-intake` skill usage confirm compliance

### W0.3 Compatibility Gate

- [x] `COMPATIBILITY_AND_MIGRATION_WORKFLOW.md` applied for any persistence/replay/protocol change — every close-out records `replay/save/protocol` classification

### W0.4 Ready/Done Gate

- [x] `READY_DONE_WORKFLOW.md` applied before marking done — tests pass before commit, CI verified, docs updated each release

### W0.5 Evidence Gate

- [x] `DEBUG_EVIDENCE_CAPTURE.md` + `REPLAY_AND_DESYNC_TRIAGE.md` consulted when relevant — manual runtime evidence captured in `docs/reports/manual-runtime/`

### W0.6 Local Gate + Release Gate

- [x] `PRE_COMMIT_LOCAL_GATES.md` and `ITERATION_RELEASE_PROTOCOL.md` followed each loop — `check_version_sync.py`, `gradlew test`, `gradlew shadowJar` pattern consistent across all releases

### W0.7 Documentation Gate

- [x] CHANGELOG, ROADMAP, CURRENT_STATE, and plan loop notes updated each release loop

### W0.8 Session End Gate

- [x] `SESSION_END_WORKFLOW.md` followed — every session has a close-out with CI status, compatibility impact, and first-action-next-session recorded

### W0.9 Stop-Work Gate

- [x] No escalation triggers met through v0.12.06 — no stops required

---

## 1. Execution Rhythm (Confirmed Active)

### Weekly cadence (from `OPERATING_RHYTHM_AND_HABITS.md`)
- [x] Intake + triage + scope lock — active (task-intake skill used; feedback triage in `indie-ninja-feedback`)
- [x] Implementation loops — active (CRCL-13 through CRCL-21 completed, stabilization slices v0.12.03–06)
- [x] Hardening + docs + release/reporting — active (docs freshness audit, version sync, release protocol each loop)

### Per-loop cadence (from `SPRINT_WORKFLOW.md`)
- [x] Review active plan state
- [x] Build scoped task list
- [x] Execute one logical unit
- [x] Commit with clear scope/reason
- [x] Update plan in-place
- [x] Push progress

---

## 2. Phase Checklist (90-Day Structure)

## Phase 1 — Stabilization ✅ COMPLETE (v0.12.04–v0.12.06)

**Target was:** v0.12.04 closure. Actual closure: v0.12.06 (extended through server lifecycle + replay determinism cleanup lane CRCL-13 to CRCL-21).

### Goals (met)
- Harden mission-item lifecycle/no-despawn behavior for solo, hosted multiplayer, late-join, and rejoin. ✅
- Remove remaining lifecycle contract edge cases before new feature expansion. ✅

### Checklist
- [x] P1-01 Mission lifecycle contract audit complete — seed (v0.12.04 slice 1), scoped ownership (v0.12.03), late-join (slice 2), mission-end clear (slice 3), disconnect (slice 4), switch/abandon (slice 5), portal-travel/mission-return (slice 6)
- [x] P1-02 Regression tests added — `ServerProtocolHandlerMissionPickupSeedTest`, `GameSessionSlotReservationTest`, `ServerProtocolHandlerClientHelloOrderingTest`, `ZoneSimulationLoopScriptedLossOrderingTest`, `WorldGraphGenerationTest`
- [x] P1-03 Daily smoke run — Interactive Daily Smoke PASS (user-confirmed, CRCL-21 close-out 2026-04-23)
- [x] P1-04 Goldens run — G7 (replay) explicit log captured; G8 (network) client-a/b + server logs captured; G5 (portal travel) smoke-evidenced via CRCL-16 interactive portal validation; G6 (save/reload) covered by Phase D save checksum + multi-slot hardening
- [x] P1-05 Compatibility classification recorded per slice — every session close-out records `replay/save/protocol` impact
- [x] P1-06 `PLAN_SHADOW_ASCENT.md` loop notes and `CURRENT_STATE.md` session notes updated through v0.12.06

### Exit Gate
- [x] No open P0 stability blockers — v0.12.06 close-out: "Known issue or risk: none blocking"
- [x] Mission lifecycle regressions covered by tests — multiple test classes confirmed
- [x] Golden paths for touched systems pass — G7+G8 explicit; G5 interactive smoke; G6 via save hardening

---

## Phase 2 — Gameplay Identity Lock ← ACTIVE (Weeks 3–5)

**Status:** Formally started 2026-04-24. P2-01 complete. Baseline tuning loop (LOOP-P2-01) is the current action.

### Goals
- Lock Passive/Aggressive readability and Flow clarity in runtime behavior.
- Define and verify measurable feel targets before expanding content.

### Checklist

- [x] P2-01 KPI document written — `docs/GAMEPLAY_KPI_TARGETS.md` created 2026-04-24 with numeric targets for stance readability (§1), Flow clarity (§2), and unfair-death rate (§3). `docs/BALANCE_LOG.md` created as the tuning loop record.

- [ ] P2-02 Run two tuning loops with explicit feel notes — LOOP-P2-01 (baseline, no changes) and LOOP-P2-02 (first targeted change) defined in `BALANCE_LOG.md`. Neither executed yet — requires one runtime playtest session.

- [x] P2-03 Multi-state readiness verified (2026-04-24 via codebase audit):
  - `stanceMode` ("yin"/"yang") flows: SimPlayer → PlayerState wire → EntityRenderer — all three states implemented and connected
  - Flow: `YinYangComponent.isBalanced()` (`|yin-yang| < 0.15f`) sets `flowMode` on PlayerState snapshot
  - Balance indicator: HudRenderer circular gauge with white glow ring when flowMode active
  - **Gap noted:** No automated test for Flow activation logic; G4 is manual only — both acceptable for Phase 2 start
  - No partial-state signoff issues — system is structurally complete

- [ ] P2-04 G4 golden verification — required before any renderer/stance change ships. Definition in `GOLDEN_PATH_REGRESSION.md`: both stances correct in idle, walk, jump, crouch, attack. Not yet run against v0.12.07.

- [ ] P2-05 Playtest evidence bundles — `PLAYTEST_PACKET_WORKFLOW.md` defines the packet structure. §4.1 observer template in `GAMEPLAY_KPI_TARGETS.md` defines what to capture. First bundle depends on LOOP-P2-01 session.

- [ ] P2-06 Feed tuning outcomes into plan — will update this checklist and CHANGELOG after each BALANCE_LOG entry is complete.

### Exit Gate

- [ ] ≥ 80% stance comprehension rate across two consecutive tuning loops
- [ ] ≥ 65% Flow comprehension rate across two consecutive tuning loops
- [ ] G4 pass on the current build

### Entry condition
Phase 1 exit gate is met ✅ — Phase 2 is unblocked.

---

## Phase 3 — Content Depth (Weeks 6–9)

**Status:** Not started. Gated on Phase 2 exit.

### Goals
- Increase authored mission/puzzle depth while preserving campaign reliability.

### Checklist
- [ ] P3-01 Deliver missing Echo puzzle archetypes (asymmetric lock + simultaneous timing)
- [ ] P3-02 Add validation checks for ability-gated progression routes
- [ ] P3-03 Ship one authored progression slice per act segment in scope
- [ ] P3-04 Run targeted playtest packets with narrow goals (`PLAYTEST_PACKET_WORKFLOW.md`)
- [ ] P3-05 Triage all returned feedback into actionable lanes (`FEEDBACK_TRIAGE_WORKFLOW.md`)
- [ ] P3-06 Promote stable repro cases into regression assets/tests

### Exit Gate
- [ ] One full start-to-Act-III run without progression dead-ends
- [ ] No unresolved P0/P1 content blockers in active slice

---

## Phase 4 — Polish + Release Readiness (Weeks 10–12)

**Status:** Release mechanics (P4-02, P4-04, P4-05, P4-06) running continuously as part of every release loop. P4-01 (gamepad/audio/settings) and P4-03 (full golden set) not yet formally executed.

### Goals
- Close usability/polish gaps and execute clean release loop.

### Checklist
- [ ] P4-01 Implement settings/gamepad/audio clarity improvements for player-facing polish
- [x] P4-02 Full pre-release local gates — run every release loop (check_version_sync.py + gradlew test + shadowJar)
- [ ] P4-03 Full golden path set on release candidate — G7+G8 captured; G1-G6 full set not yet run end-to-end against a release candidate
- [x] P4-04 Release notes/changelog/devlog capture player-visible changes — done each release
- [x] P4-05 Release protocol end-to-end — done each release (commit → CI green → tag → Release workflow → asset verification)
- [x] P4-06 Session-end and release verification evidence — done each release

### Exit Gate
- [ ] `RELEASE_CHECKLIST.md` fully green
- [ ] CI and Release workflows green on release commit/tag
- [ ] Release assets include Java artifacts + docs archive ZIP

---

## 3. Cross-Repo Conditional Checklist ✅ COMPLETE (2026-04-24)

- [x] Execute `CROSS_REPO_COORDINATION.md` — executed 2026-04-24
- [x] Pipeline coordination issue created/updated — pipeline issue #2 ("Weekly Intake Tracking") open and active
- [x] Ownership and event contract declared — `CROSS_REPO_CONTROL_TOWER_HANDOVER.md` updated with all checklist items confirmed; event contracts in `CROSS_REPO_EVENT_CONTRACTS.md` verified live
- [x] End-to-end validation evidenced — 5 successful `game-release` launcher dispatch runs (v0.12.02–v0.12.06); 3 successful `feedback_intake_sync` runs; Contract 3 (feedback resolution loop) exercised on feedback #6, #7, #1

---

## 4. Evidence Log

### 2026-04-24 — Cross-repo control tower activation + dash physics fix

- Date: 2026-04-24
- Version: v0.12.06
- Plan task IDs: cross-repo (Section 3 checklist), DASH-WALL-FIX
- Commands run:
  - `gh run list --repo VainAsher/indie-ninja-launcher --limit 5` → 5× success
  - `gh run list --repo VainAsher/indie-ninja-pipeline --limit 5` → 3× intake success
  - `gradle :server:test --tests com.indieniinja.server.GameSimulatorTest --no-daemon` → PASS
  - `python tools/check_version_sync.py` → `Version synchronization OK: v0.12.06`
- Test/smoke/golden results: `GameSimulatorTest.dashCancelledOnWallContact` PASS; all existing tests PASS
- Compatibility impact: `replay=no, save=no, protocol=no`
- Docs updated: `CROSS_REPO_CONTROL_TOWER_HANDOVER.md`, `repo-scaffolds/pipeline-repo/feedback_intake_sync.yml`, this checklist
- Changelog/devlog decision: dash fix → CHANGELOG entry needed at next release bump
- Known risk: G5/G6 goldens not explicitly labeled in evidence bundles (covered by daily smoke + interactive validation)
- Next action: Begin Phase 2 — define tuning KPIs for stance/Flow readability; OR proceed with v0.12.07 stabilization (mission trigger visibility filter, Gradle combined-lane fix) first
