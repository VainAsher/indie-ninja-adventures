---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Debug Evidence Capture Workflow

Reference documents:
- [docs/templates/bug_template.md](../templates/bug_template.md)
- [docs/production/bugs.md](../production/bugs.md)
- [docs/workflow/BUG_REPRO_REPLAY_WORKFLOW.md](BUG_REPRO_REPLAY_WORKFLOW.md)

Workflow for turning bug reports and debugging notes into actionable engineering evidence.

## Rules

1. “It broke” is not a valid report.
2. Every bug or regression must include enough evidence for a second engineer to attempt reproduction.
3. Runtime claims must be tied to version and branch context.
4. UI and feel problems still require concrete evidence.

## Required Evidence

Capture all applicable items:

- version
- branch/commit
- reproduction steps
- log excerpt
- replay if available
- save file or seed if relevant
- expected behavior
- actual behavior
- screenshot/video if UI-related

## Canonical Loop

1. Reproduce the issue.
2. Record version, branch, and commit.
3. Write exact steps, not summary prose.
4. Collect logs and relevant runtime identifiers.
5. Attach replay, save, seed, screenshot, or video when available.
6. Compare expected vs actual behavior.
7. File or update the bug with the evidence bundle.

## Evidence Quality Rules

Good evidence is:
- reproducible
- time-bounded
- attached to a specific build/version
- readable without IDE access

Bad evidence is:
- vague memory
- “sometimes” without reproduction context
- screenshots without explanation
- logs with no indication of where to look

## Done Criteria

- [ ] Version captured
- [ ] Commit/branch captured
- [ ] Repro steps written
- [ ] Expected vs actual written
- [ ] Logs attached/excerpted
- [ ] Replay/save/seed included when relevant
- [ ] UI evidence included when relevant

## Failure Path

If the issue cannot be reproduced cleanly:

1. Mark it as partial evidence, not confirmed reproduction.
2. Preserve whatever logs/replays exist.
3. Record uncertainty explicitly.
4. Escalate only with the evidence currently available.

## Related Workflows

- [BUG_REPRO_REPLAY_WORKFLOW.md](BUG_REPRO_REPLAY_WORKFLOW.md)
- [REPLAY_AND_DESYNC_TRIAGE.md](REPLAY_AND_DESYNC_TRIAGE.md)
