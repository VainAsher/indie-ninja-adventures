---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Escalation and Stop Work Workflow

Use this workflow when uncertainty or risk is high enough that continued implementation may cause regressions.

## Stop Triggers

- Canonical docs conflict on current truth.
- Save/replay/protocol compatibility cannot be classified.
- Cross-repo ownership is unclear for a release-facing change.
- Security/privacy/licensing concerns appear without resolution.

## Canonical Loop

1. Stop scope expansion.
2. Record known facts, unknowns, and impacted systems.
3. Preserve evidence (logs/replays/save data).
4. Define resume condition and owner for next action.

## Related Workflows

- [COMPATIBILITY_AND_MIGRATION_WORKFLOW.md](COMPATIBILITY_AND_MIGRATION_WORKFLOW.md)
- [SESSION_END_WORKFLOW.md](SESSION_END_WORKFLOW.md)
