---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Repo Hygiene and Archive Workflow

Use this workflow for cleanup, archive, and deprecation operations.

## Canonical Loop

1. Classify targets: active, archived, quarantined, delete-candidate.
2. Confirm no active runtime references are broken.
3. Move stale docs/assets to archive paths with explicit notes.
4. Update index/routing docs after structure changes.

## Related Workflows

- [PROTOTYPE_QUARANTINE_AND_RETIREMENT.md](PROTOTYPE_QUARANTINE_AND_RETIREMENT.md)
- [DECISION_RECORD_WORKFLOW.md](DECISION_RECORD_WORKFLOW.md)
