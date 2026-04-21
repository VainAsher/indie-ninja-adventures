---
doc_type: workflow
status: living
owner: production-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Decision Record Workflow

Reference documents:
- [docs/decisions/INDEX.md](../decisions/INDEX.md)
- [docs/templates/decision_record_template.md](../templates/decision_record_template.md)

Workflow for recording high-impact project decisions before their context is lost and the repo drifts into undocumented structure.

## Rules

1. Decisions with long-tail impact must be logged.
2. A decision record captures why a path was chosen, not only what changed.
3. Reversals and supersessions must be recorded, not silently overwritten.
4. Decision records should be brief, searchable, and linked from affected docs when relevant.
5. Implementation may proceed quickly, but high-impact choices may not remain undocumented.

## Required Triggers

Create or update a decision record when you:

- change core architecture
- change repo structure
- deprecate a system
- adopt or remove a dependency
- change branching or release process
- change canonical documentation paths
- introduce/archive a major prototype
- redefine milestone scope in a way that changes implementation order or ownership

## Canonical Loop

1. Identify whether the change has long-tail structural impact.
2. Write a decision entry using the template.
3. Include:
   - context
   - decision
   - why this path was chosen
   - rejected alternatives
   - consequences
   - follow-up docs needing updates
4. Link the decision from affected workflow/spec docs when useful.
5. Update the decision if it is later superseded.

## Decision Minimum

- Date
- Title
- Status (`proposed/accepted/superseded/deprecated`)
- Context
- Decision
- Consequences
- Related docs/systems

## Done Criteria

- [ ] High-impact change has a recorded decision
- [ ] Reasoning is preserved, not only the outcome
- [ ] Superseded decisions are marked
- [ ] Affected docs can trace back to the decision when needed

## Failure Path

If a cleanup, architecture shift, or process change is already merged without a decision record:

1. Backfill the record immediately.
2. Capture the real reason while context still exists.
3. Link it from the affected docs during the follow-up cleanup.

## Related Workflows

- [ARCHITECTURE_AND_SPEC_SYNC.md](ARCHITECTURE_AND_SPEC_SYNC.md)
- [TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md](TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md)
