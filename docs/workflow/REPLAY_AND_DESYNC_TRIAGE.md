---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Replay and Desync Triage Workflow

Reference documents:
- [docs/workflow/DEBUG_EVIDENCE_CAPTURE.md](DEBUG_EVIDENCE_CAPTURE.md)
- [docs/dev/JAVA_ARCHITECTURE.md](../dev/JAVA_ARCHITECTURE.md)
- [docs/templates/BUG_REPORT.md](../templates/BUG_REPORT.md)

Workflow for using deterministic replay and desync signals as primary debugging tools instead of memory-driven debugging.

## Rules

1. Replays are a first-class debugging artifact.
2. Any desync claim must include version/build context and session identifiers.
3. Replay naming must be consistent enough to find later.
4. Regression-worthy replays should be promoted into long-lived regression assets.

## Capture Standard

Each replay bundle should include:

- version
- build date if relevant
- branch/commit
- session id
- player id if present
- seed/world id if present
- short bug label
- expected result
- observed result

## Naming Convention

Use a stable path such as:

`replays/bugs/<version>/<date>_<system>_<short-label>`

## Canonical Loop

1. Capture the replay at the time of failure.
2. Attach session id, seed, and branch/commit metadata.
3. Re-run the replay.
4. Compare observed replay behavior against the original report.
5. Classify outcome:
   - reproducible bug
   - replay mismatch
   - true desync
   - non-deterministic/insufficient evidence
6. Escalate networking/protocol issues when frame-hash or state divergence indicates cross-peer mismatch.
7. Promote stable repro cases into regression coverage.

## Desync Classification

- local gameplay bug: replay reproduces the same incorrect behavior without cross-session divergence
- replay issue: replay cannot faithfully reproduce the original captured behavior
- protocol/state desync: peers or server/client disagree on authoritative state
- insufficient evidence: identifiers or artifacts are missing

## Done Criteria

- [ ] Replay captured and named correctly
- [ ] Session id / seed attached
- [ ] Replay re-run completed
- [ ] Classification recorded
- [ ] Escalation made if networking/protocol risk exists
- [ ] Regression candidate identified when useful

## Failure Path

If replay files or identifiers are incomplete:

1. Preserve the artifact anyway.
2. Mark the bundle incomplete.
3. Do not over-claim root cause.
4. Improve capture on the next repro before attempting broad fixes.

## Related Workflows

- [DEBUG_EVIDENCE_CAPTURE.md](DEBUG_EVIDENCE_CAPTURE.md)
- [GOLDEN_PATH_REGRESSION.md](GOLDEN_PATH_REGRESSION.md)
