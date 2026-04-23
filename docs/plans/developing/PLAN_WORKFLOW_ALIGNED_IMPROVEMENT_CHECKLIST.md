---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-23
version_anchor: v0.12.03
---

# Plan - Workflow-Aligned Improvement Checklist (v0.12.04+)

This checklist translates the improvement roadmap into an execution format that explicitly follows the workflows in `docs/workflow/`.

## 0. Workflow Adherence Gates (Non-Negotiable)

### W0.1 Session Start Gate
- [ ] Follow `SESSION_START_WORKFLOW.md` before coding:
  - [ ] Read `version.json`
  - [ ] Read `docs/CURRENT_STATE.md`
  - [ ] Read active implementing plan (`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`)
  - [ ] Review latest `git log --oneline -10`
  - [ ] Write session note (target/reason/stop condition)

### W0.2 Task Intake Gate
- [ ] Follow `TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md` for each task:
  - [ ] Goal
  - [ ] Player-facing impact
  - [ ] Systems touched
  - [ ] Risks
  - [ ] Required tests
  - [ ] Required docs updates
  - [ ] Rollback plan

### W0.3 Compatibility Gate
- [ ] For any persistence/replay/protocol/schema change, run `COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`:
  - [ ] save classification
  - [ ] replay classification
  - [ ] protocol classification
  - [ ] schema classification
  - [ ] migration/gate decision recorded

### W0.4 Ready/Done Gate
- [ ] Apply `READY_DONE_WORKFLOW.md` before marking done:
  - [ ] compile/build passed
  - [ ] required tests passed
  - [ ] smoke path run when relevant
  - [ ] canonical docs updated
  - [ ] changelog/devlog decision recorded
  - [ ] runtime evidence attached

### W0.5 Evidence Gate
- [ ] For regressions or unclear behavior, follow:
  - [ ] `DEBUG_EVIDENCE_CAPTURE.md`
  - [ ] `REPLAY_AND_DESYNC_TRIAGE.md` when replay/desync-related

### W0.6 Local Gate + Release Gate
- [ ] Run `PRE_COMMIT_LOCAL_GATES.md` for each loop
- [ ] Run `ITERATION_RELEASE_PROTOCOL.md` and `RELEASE_CHECKLIST.md` for release loops

### W0.7 Documentation Gate
- [ ] Follow:
  - [ ] `ARCHITECTURE_AND_SPEC_SYNC.md` for system/spec truth updates
  - [ ] `DOCUMENTATION_ROUTING_WORKFLOW.md` for route/index updates
  - [ ] `DECISION_RECORD_WORKFLOW.md` when long-tail decisions are made
  - [ ] `DEVLOG_AND_MARKETING_CAPTURE.md` for player-visible captures

### W0.8 Session End Gate
- [ ] Follow `SESSION_END_WORKFLOW.md`:
  - [ ] CI and Release status checked (`gh run list --limit 3 --json status,conclusion,name,headSha`)
  - [ ] validation evidence recorded
  - [ ] compatibility impact recorded
  - [ ] first action next session recorded

### W0.9 Stop-Work Gate
- [ ] If uncertainty/risk crosses stop triggers, execute `ESCALATION_AND_STOP_WORK.md` immediately.

---

## 1. Execution Rhythm (Required)

### Weekly cadence (from `OPERATING_RHYTHM_AND_HABITS.md`)
- [ ] Monday: intake + triage + scope lock
- [ ] Tuesday-Thursday: implementation loops
- [ ] Friday: hardening + docs + release/reporting

### Per-loop cadence (from `SPRINT_WORKFLOW.md`)
- [ ] Review active plan state
- [ ] Build scoped task list
- [ ] Execute one logical unit
- [ ] Commit with clear scope/reason
- [ ] Update plan in-place
- [ ] Push progress

---

## 2. Phase Checklist (90-Day Structure)

## Phase 1 - Stabilization (Weeks 1-2, target: v0.12.04 closure)

### Goals
- Harden mission-item lifecycle/no-despawn behavior for solo, hosted multiplayer, late-join, and rejoin.
- Remove remaining lifecycle contract edge cases before new feature expansion.

### Checklist
- [ ] P1-01 Complete mission lifecycle contract audit (seed, collect, clear, reconnect, mission switch/abandon, disconnect)
- [ ] P1-02 Add/complete regression tests for lifecycle transitions
- [ ] P1-03 Run daily smoke route (`DAILY_SMOKE_WORKFLOW.md`) each implementation day
- [ ] P1-04 Run relevant goldens (`G5`, `G6`, `G8`) before release candidate (`GOLDEN_PATH_REGRESSION.md`)
- [ ] P1-05 Record compatibility classification per slice (`save/replay/protocol/schema`)
- [ ] P1-06 Update `PLAN_SHADOW_ASCENT.md` loop notes and `CURRENT_STATE.md` session notes

### Exit Gate
- [ ] No open P0 stability blockers
- [ ] Mission lifecycle regressions covered by tests
- [ ] Golden paths for touched systems pass

## Phase 2 - Gameplay Identity Lock (Weeks 3-5)

### Goals
- Lock Passive/Aggressive readability and Flow clarity in runtime behavior.

### Checklist
- [ ] P2-01 Define measurable tuning KPIs (stance readability, Flow activation clarity, unfair-death rate)
- [ ] P2-02 Run two tuning loops with explicit feel notes (Passive/Aggressive/Flow impact)
- [ ] P2-03 Verify multi-state readiness requirements for touched systems (no partial-state signoff)
- [ ] P2-04 Run stance/animation golden verification (`G4`) whenever renderer/stance changes
- [ ] P2-05 Capture playtest evidence bundles for clarity issues (logs + replay + expected vs actual)
- [ ] P2-06 Feed tuning outcomes into plan and changelog/devlog decisions

### Exit Gate
- [ ] Testers can explain stance and Flow behavior without external explanation
- [ ] G4/G3 pass for touched movement/animation surfaces

## Phase 3 - Content Depth (Weeks 6-9)

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

## Phase 4 - Polish + Release Readiness (Weeks 10-12)

### Goals
- Close usability/polish gaps and execute clean release loop.

### Checklist
- [ ] P4-01 Implement settings/gamepad/audio clarity improvements for player-facing polish
- [ ] P4-02 Execute full pre-release local gates
- [ ] P4-03 Run full golden path set on release candidate
- [ ] P4-04 Ensure release notes/changelog/devlog capture player-visible changes
- [ ] P4-05 Run release protocol end-to-end (feature commit -> CI green -> version bump/tag -> release verification)
- [ ] P4-06 Complete session-end and release verification evidence with CI/Release success

### Exit Gate
- [ ] `RELEASE_CHECKLIST.md` fully green
- [ ] CI and Release workflows green on release commit/tag
- [ ] Release assets include Java artifacts + docs archive ZIP

---

## 3. Cross-Repo Conditional Checklist

Run only if this improvement loop touches more than one repo:

- [ ] Execute `CROSS_REPO_COORDINATION.md`
- [ ] Pipeline coordination issue created/updated
- [ ] Ownership and event contract impact declared
- [ ] End-to-end validation evidence recorded

---

## 4. Evidence Log Template (Use Per Loop)

- Date:
- Version:
- Plan task IDs:
- Commands run:
- Test/smoke/golden results:
- Compatibility impact (`replay/save/protocol/schema`):
- Docs updated:
- Changelog/devlog decision:
- Known risk:
- Next action:

