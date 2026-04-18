---
doc_type: workflow
status: living
owner: release-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Pre-Commit Local Gates

Reference documents:
- [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [WORKFLOW_AUDIT_2026-04-17.md](WORKFLOW_AUDIT_2026-04-17.md)

Fast local gate workflow for preventing obvious breakage before commit or push.

## Rules

1. `pre-commit` must stay fast enough for day-to-day use.
2. `pre-push` may be slower, but must remain deterministic.
3. Any commit touching `.py` files must pass Black locally.
4. Any commit touching version or docs metadata must pass version-sync checks.
5. Do not rely on CI as the first formatting or basic test gate.

## Recommended Hook Split

### Pre-Commit

Run only fast checks:

- Python formatting check on staged `.py` files
- fast Java tests or compile checks for changed modules
- version-sync check when release metadata changed
- docs link/frontmatter check when workflow or release docs changed

### Pre-Push

Run heavier checks:

- `python tools/check_version_sync.py`
- `python tools/check_docs_freshness.py --emit-report`
- `cd java && ./gradlew test --no-daemon`
- `python run_tests.py` when Python tooling changed

## Minimal Commands

```bash
python -m black --check tools
python tools/check_version_sync.py
cd java && ./gradlew test --no-daemon
```

## Done Criteria

- [ ] Fast local checks pass before commit
- [ ] Full local checks pass before tag or push
- [ ] Formatting failures are fixed locally, not in follow-up CI-only churn commits
- [ ] Hook behavior is documented and reproducible across machines

## Failure Path

If a pre-commit or pre-push hook fails:

1. Fix locally.
2. Re-run the failed gate.
3. Do not bypass the hook unless the failure is a verified false positive and the bypass reason is recorded in the commit body or loop note.

## Related Workflows

- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
