---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Pull Request and Review Workflow

Reference documents:
- [docs/workflow/BRANCHING.md](BRANCHING.md)
- [docs/workflow/ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)
- [docs/workflow/READY_DONE_WORKFLOW.md](READY_DONE_WORKFLOW.md)

Workflow for consistent pull requests, self-review, and merge discipline in a small engineering team or solo-with-review environment.

## Rules

1. Every PR must be scoped to one logical change set.
2. Draft PRs are required for incomplete work, risky work, or work needing early visibility.
3. Review evidence must exist before review is requested.
4. Merge method must preserve readable project history.
5. Large mixed-purpose PRs are forbidden.

## Branch Naming

Use a readable scope-first convention:

- `feature/<area>-<short-topic>`
- `fix/<area>-<short-topic>`
- `docs/<topic>`
- `refactor/<area>-<short-topic>`
- `chore/<topic>`

## Required PR Sections

- summary
- why this change exists
- player-facing impact
- systems touched
- risks
- validation performed
- docs updated
- rollback notes

## PR Size Expectations

Preferred:
- one task or bug
- one bounded feature slice
- one refactor with no behavior change

Escalate or split when a PR mixes:
- content + architecture
- protocol + UI + refactor
- dependency changes + major gameplay changes

## Evidence Requirement

Attach as relevant:
- test output
- smoke result
- screenshot/video
- replay id/path
- log excerpt
- save/seed/session id

## Review and Merge Rules

- request review only after ready/done conditions pass
- use draft when feedback is needed before completion
- squash merge for small linear task branches
- merge commit only when preserving meaningful intermediate commits matters
- do not merge with unresolved known risk that lacks a follow-up record

## Done Criteria

- [ ] Branch name follows convention
- [ ] PR sections complete
- [ ] Evidence attached
- [ ] Validation complete
- [ ] Review state correct (`draft` or `ready`)
- [ ] Merge method chosen deliberately

## Failure Path

If review reveals missing scope, evidence, or mixed concerns:

1. Convert back to draft if needed.
2. Split the work or tighten the PR description.
3. Add missing evidence.
4. Re-request review only after the PR tells a clean story.

## Related Workflows

- [READY_DONE_WORKFLOW.md](READY_DONE_WORKFLOW.md)
- [DEBUG_EVIDENCE_CAPTURE.md](DEBUG_EVIDENCE_CAPTURE.md)
