---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Documentation Routing Workflow

Use this workflow to keep canonical docs centralized and avoid duplicate truth.

## Rules

1. `docs/INDEX.md` is the routing layer.
2. Update the canonical owner doc first.
3. Link or archive duplicates; do not maintain parallel "current" docs.

## Canonical Loop

1. Identify subject and canonical owner.
2. Update canonical doc.
3. Update `docs/INDEX.md` when routes change.
4. Archive stale docs when replaced.

## Related Workflows

- [README_AND_INDEX_MAINTENANCE.md](README_AND_INDEX_MAINTENANCE.md)
- [DECISION_RECORD_WORKFLOW.md](DECISION_RECORD_WORKFLOW.md)
