---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Prototype Quarantine and Retirement Workflow

Use this workflow when prototype code diverges from active runtime direction.

## Canonical Loop

1. Classify prototype state: active, quarantined, retired.
2. Record ownership and migration/deprecation path.
3. Prevent new feature scope in quarantined paths unless explicitly approved.
4. Archive or extract prototype paths when retirement criteria are met.

## Related Workflows

- [REPO_HYGIENE_AND_ARCHIVE.md](REPO_HYGIENE_AND_ARCHIVE.md)
- [DECISION_RECORD_WORKFLOW.md](DECISION_RECORD_WORKFLOW.md)
