---
doc_type: workflow
status: living
owner: design-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Gameplay Tuning Change Workflow

Use this workflow for feel-sensitive gameplay adjustments.

## Required Capture

- Exact values/behavior changed.
- Intended player-facing feel outcome.
- Validation path (replay/smoke/benchmark route).
- Regressions or tradeoffs observed.

## Canonical Loop

1. Record before/after values.
2. Run focused validation path.
3. Capture evidence and update relevant docs.
4. Re-check design alignment if identity-level feel changed.

## Related Workflows

- [GOLDEN_PATH_REGRESSION.md](GOLDEN_PATH_REGRESSION.md)
- [ARCHITECTURE_AND_SPEC_SYNC.md](ARCHITECTURE_AND_SPEC_SYNC.md)
