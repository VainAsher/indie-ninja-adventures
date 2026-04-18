---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.65
---

# Session End Workflow

Reference documents:

- [SESSION_START_WORKFLOW.md](SESSION_START_WORKFLOW.md)
- [SPRINT_WORKFLOW.md](SPRINT_WORKFLOW.md)

End-of-session handover workflow for clean resumes and low-friction recovery.

## Rules

1. Every stopped session must leave a resumable note.
2. Record what changed, what remains, and the exact next action.
3. Record validation state, not just implementation state.
4. Record compatibility impact whenever save, replay, protocol, or content contracts changed.
5. Do not end a session with unresolved ambiguity about the next step.
6. **Do not close the session if CI is pending or failing.** Run `gh run list --limit 3 --json status,conclusion,name,headSha` before writing the handover note. If either `CI` or `Release` shows `"conclusion":"failure"`, fix on `master`, cut the next patch tag, and re-run the release loop before ending.

## Canonical Loop

1. Run `gh run list --limit 3 --json status,conclusion,name,headSha` — confirm both `CI` and `Release` are green.
2. Summarize what changed this session.
3. Record files or systems touched.
4. Record commands run and validation results.
5. Record known issues and blockers.
6. Record the next concrete action.
7. Update the active plan if the session completed a logical unit.
8. Commit or explicitly record why the work remains uncommitted.

## Handover Note Minimum

- Date
- Branch + HEAD commit
- Current version
- Systems touched
- Validation run
- Known issue or risk
- Compatibility impact:
  - replay (`yes/no`)
  - save (`yes/no`)
  - protocol (`yes/no`)
- First action next session

## Failure Path

If the session ends mid-debug or mid-refactor:

1. Record the last known good command.
2. Record the failing command or symptom.
3. Record whether the repo is safe to pull/build.
4. Record exactly what to avoid redoing next session.

## Related Workflows

- [SESSION_START_WORKFLOW.md](SESSION_START_WORKFLOW.md)
- [SPRINT_WORKFLOW.md](SPRINT_WORKFLOW.md)
