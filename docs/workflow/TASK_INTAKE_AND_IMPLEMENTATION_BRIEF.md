---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Task Intake and Implementation Brief Workflow

Reference documents:
- [docs/production/backlog.md](../production/backlog.md)
- [docs/production/roadmap.md](../production/roadmap.md)
- [docs/production/decisions.md](../production/decisions.md)
- [docs/workflow/READY_DONE_WORKFLOW.md](READY_DONE_WORKFLOW.md)

Pre-implementation workflow for forcing scope clarity before code changes begin.

## Rules

1. No task starts without a written implementation brief.
2. The brief must be small enough to read in under two minutes.
3. If the brief cannot identify the canonical doc and acceptance test, the task is not ready.
4. Scope creep discovered during implementation requires a brief update before coding continues.

## Brief Minimum

Every implementation brief must answer:

- goal
- player-facing impact
- systems touched
- risks
- required tests
- required docs to update
- rollback plan

## Canonical Loop

1. Pull the task from backlog, bug list, playtest report, or plan.
2. Write the brief in the issue, PR description draft, or task note.
3. Identify the canonical documents and runtime systems touched.
4. Define acceptance validation before implementation.
5. Confirm the rollback path.
6. Start coding only after the brief is complete.

## Scope Guardrails

A brief must explicitly call out when a task touches any of the following:

- persistence or schema
- networking or protocol
- mission/content formats
- replay determinism
- player-facing tuning
- public documentation or release notes

## Done Criteria

- [ ] Goal stated in one sentence
- [ ] Player-facing impact identified
- [ ] Systems touched listed
- [ ] Risks called out
- [ ] Tests named
- [ ] Docs update list named
- [ ] Rollback plan written

## Failure Path

If implementation reveals hidden systems or risk not captured in the brief:

1. Stop broadening the change silently.
2. Update the brief.
3. Reconfirm acceptance tests and rollback plan.
4. Re-scope or split the task before continuing.

## Related Workflows

- [READY_DONE_WORKFLOW.md](READY_DONE_WORKFLOW.md)
- [PR_AND_REVIEW_WORKFLOW.md](PR_AND_REVIEW_WORKFLOW.md)
