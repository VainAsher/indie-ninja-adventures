---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Session Start Workflow

Reference documents:
- [SPRINT_WORKFLOW.md](SPRINT_WORKFLOW.md)
- [SESSION_END_WORKFLOW.md](SESSION_END_WORKFLOW.md)
- [WORKFLOW_AUDIT_2026-04-17.md](WORKFLOW_AUDIT_2026-04-17.md)

Start-of-session workflow for preventing stale context, version-anchor mistakes, and unfocused implementation.

## Rules

1. Read `version.json` before implementing anything.
2. Treat `docs/CURRENT_STATE.md` as the runtime truth source for the current session.
3. Review the active implementation plan before selecting work.
4. Compare intended work against recent commits before re-implementing any feature.
5. Write a short session intent note before coding.
6. If session context and repo state disagree, perform a scope review before changing code.

## Canonical Loop

1. Sync `master`.
2. Read:
   - `version.json`
   - `docs/CURRENT_STATE.md`
   - active implementation plan
   - latest `git log --oneline -10`
3. Confirm current version anchor and active milestone.
4. Identify one risky target and supporting safe tasks.
5. Write a 3-line session note:
   - target
   - reason
   - stop condition
6. Begin implementation only after the note reflects the real repo state.

## Session Note Minimum

- Date
- Branch
- Current version
- Primary target
- Supporting tasks
- First validation command
- Resume risk notes (`none/stale-context/runtime/env`)

## Failure Path

If `version.json`, the active plan, and the session summary do not align:

1. Stop implementation.
2. Record the mismatch in the session note.
3. Audit recent commits and docs.
4. Re-scope the task against the actual repo HEAD.

## Related Workflows

- [SESSION_END_WORKFLOW.md](SESSION_END_WORKFLOW.md)
- [SPRINT_WORKFLOW.md](SPRINT_WORKFLOW.md)
