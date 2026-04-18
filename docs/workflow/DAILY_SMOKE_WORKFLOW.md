---
doc_type: workflow
status: living
owner: qa-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Daily Smoke Workflow

Reference documents:
- [SPRINT_WORKFLOW.md](SPRINT_WORKFLOW.md)
- [PLAYTEST_PACKET_WORKFLOW.md](PLAYTEST_PACKET_WORKFLOW.md)
- [GOLDEN_PATH_REGRESSION.md](GOLDEN_PATH_REGRESSION.md)

Short-form daily verification workflow for confirming the game still boots, plays, and routes correctly.

## Rules

1. A passing unit test suite does not replace a passing smoke run.
2. Smoke scope must cover launcher/runtime reality, not only IDE execution.
3. Smoke runs should stay short, repeatable, and focused on core path survivability.
4. Failures must capture version, session ID, and replay/log bundle where available.

## Canonical Route

1. Boot launcher.
2. Boot server.
3. Boot client.
4. Enter the hub.
5. Interact with Siren or mission board.
6. Confirm the objective tracker is visible.
7. Travel into a mission.
8. Confirm one room transition.
9. Confirm at least one stance change.
10. Confirm one Flow activation or expected Flow-ready state.
11. Confirm death/respawn or quit/reload path.
12. Record pass/fail.

## Smoke Report Minimum

- Build/version
- Mode tested (`launcher`, `client+server`, `offline`)
- Route used
- Pass/fail
- First failure point
- Replay/log path if captured

## Done Criteria

- [ ] Launcher boot verified
- [ ] Runtime boot verified
- [ ] Hub entry verified
- [ ] Mission handoff verified
- [ ] Mission entry verified
- [ ] Room transition verified
- [ ] One critical state transition verified
- [ ] Result recorded

## Failure Path

If smoke fails:

1. Stop cutting tags or test builds.
2. Capture logs/replay immediately.
3. Classify whether the failure is boot, routing, mission, traversal, state, or persistence.
4. Fix and rerun the same route before resuming feature work.

## Related Workflows

- [PLAYTEST_PACKET_WORKFLOW.md](PLAYTEST_PACKET_WORKFLOW.md)
- [GOLDEN_PATH_REGRESSION.md](GOLDEN_PATH_REGRESSION.md)
