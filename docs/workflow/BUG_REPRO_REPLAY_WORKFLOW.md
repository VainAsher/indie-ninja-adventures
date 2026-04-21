---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Bug Repro and Replay Workflow

Use this workflow when converting a bug report into reproducible evidence plus replay-backed triage.

## Canonical Loop

1. Capture bug evidence using `DEBUG_EVIDENCE_CAPTURE.md`.
2. Capture replay/session identifiers.
3. Classify bug vs replay mismatch vs protocol desync using `REPLAY_AND_DESYNC_TRIAGE.md`.
4. Promote stable repro cases into regression checks.

## Related Workflows

- [DEBUG_EVIDENCE_CAPTURE.md](DEBUG_EVIDENCE_CAPTURE.md)
- [REPLAY_AND_DESYNC_TRIAGE.md](REPLAY_AND_DESYNC_TRIAGE.md)
