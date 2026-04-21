---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Content and Schema Change Workflow

Use this workflow for authored data, schema, and content-contract changes.

## Canonical Loop

1. Define the contract change and impacted loaders.
2. Classify compatibility via `COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`.
3. Update runtime/spec docs in the same work loop.
4. Capture migration and rollback behavior.

## Related Workflows

- [COMPATIBILITY_AND_MIGRATION_WORKFLOW.md](COMPATIBILITY_AND_MIGRATION_WORKFLOW.md)
- [ARCHITECTURE_AND_SPEC_SYNC.md](ARCHITECTURE_AND_SPEC_SYNC.md)
