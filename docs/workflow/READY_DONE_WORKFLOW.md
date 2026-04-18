---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.65
---

# Ready / Done Workflow

Reference documents:

- [docs/workflow/TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md](TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md)
- [docs/workflow/DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
- [docs/CHANGELOG.md](../CHANGELOG.md)
- [docs/DEVLOG.md](../DEVLOG.md)

Workflow for defining when a task is allowed to start and what must be true before it is considered complete.

## Ready Definition

A task is ready only when all of the following are true:

- desired behavior is clear
- canonical doc is identified
- dependencies are known
- target branch is known
- acceptance test is known

## Done Definition

A task is done only when all of the following are true:

- code compiles
- tests passed
- smoke path checked where relevant
- docs updated or explicitly marked not needed
- changelog/devlog decision made
- logs/replay attached if behavior changed

## Rules

1. “Code written” is not done.
2. Ambiguous acceptance means not ready.
3. Missing documentation decisions mean not done.
4. Runtime behavior changes require evidence, not memory.
5. **Partial-state verification is not done.** Testing one state of a multi-state system is not evidence that the system is correct. Every state must be named and checked.

## Canonical Loop

1. Check ready state before branching or coding.
2. Refuse to start if any ready condition is missing.
3. Implement the smallest complete scope.
4. Validate with compile, tests, and smoke path as needed.
5. Update docs and change history decisions.
6. Attach evidence for behavior changes.
7. Mark done only after the checklist is complete.

## Done Criteria Checklist

- [ ] Compile/build passed
- [ ] Required tests passed
- [ ] Smoke validation completed when relevant
- [ ] Canonical docs updated
- [ ] Changelog/devlog decision recorded
- [ ] Evidence attached for runtime changes

## Surface-Specific Done Criteria

Generic "smoke checked" is not sufficient for these systems. If the task touched any of the following, the named checklist must be completed before done is declared.

### Animation / Rendering / Stance Posture

Touched: `EntityRenderer`, animation sheets, stance system, posture, locomotion states

Must verify in **both Yin and Yang stance** across **all five movement states**:

- [ ] idle — correct posture
- [ ] walk — correct posture
- [ ] jump — correct posture
- [ ] crouch — correct posture
- [ ] attack — correct posture

"Works in combat" covers one of five. All five are required.

### Hub Travel / Zone Migration

Touched: `GameScreen.pollZoneTransition`, `handleSoloPortalTravel`, `LevelLayout`, portal placement, `initializeSoloSimulation`, ability restoration

Must verify all six:

- [ ] No portal at spawn (start-room portals absent — exit-rooms only)
- [ ] World renders fully after travel (no blank screen)
- [ ] Camera centred on player after travel (not at world origin)
- [ ] Locked portal blocked with toast — no unintended transit
- [ ] No spurious "new ability" toasts for abilities already held pre-travel
- [ ] Player state (health, inventory, abilities) preserved across transition

### Notification / Toast System

Touched: ability unlock toasts, HUD notification queue, `prevLocalAbilities` tracking

Must verify:

- [ ] Toast fires for genuinely new unlocks only
- [ ] Restoring an existing ability does not fire a new-unlock toast
- [ ] Multiple toasts do not fire simultaneously for already-known abilities

### Version / Docs Parity

Touched: `version.json`, CHANGELOG, ROADMAP, PLAN, CURRENT_STATE

Must verify:

- [ ] `python tools/check_version_sync.py` passes cleanly
- [ ] ROADMAP, CHANGELOG, PLAN, and CURRENT_STATE all reflect the new version

## Failure Path

If a task reaches review with missing ready or done conditions:

1. Move it back out of ready-for-review state.
2. Fill the missing condition.
3. Re-run validation if the gap affected scope or behavior.
4. Only then resume review or merge.

## Related Workflows

- [TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md](TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md)
- [DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
