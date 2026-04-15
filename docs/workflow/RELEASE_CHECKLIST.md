---
doc_type: workflow
status: living
owner: release-team
last_updated: 2026-04-15
version_anchor: v0.11.47
---

# Release Checklist

Reference protocol: [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)

## Pre-Tag Gates

- [ ] Version parity passes: `python tools/check_version_sync.py --tag v0.<minor>.<patch>`
- [ ] Docs freshness baseline generated: `python tools/check_docs_freshness.py --emit-report`
- [ ] Java tests + build pass:
  - [ ] `cd java`
  - [ ] `gradle :server:test :server:shadowJar :client:shadowJar --no-daemon`
- [ ] Python tests pass if Python code/tooling changed: `python run_tests.py`

## Documentation Gate

- [ ] `docs/CHANGELOG.md` updated for user-facing changes
- [ ] Active plan updated (usually `docs/plans/implementing/PLAN_SHADOW_ASCENT.md`)
- [ ] Archive action recorded when retiring docs (`none/create/update`)

## Version + Tag Discipline

- [ ] Tag format `v0.<minor>.<patch>`
- [ ] Tag points to final iteration commit
- [ ] `version.json` matches the tag (without `v`)
- [ ] `README.md` version banner reflects release value

## Post-Push Verification

- [ ] `CI` workflow passed
- [ ] `Release` workflow passed
- [ ] Release includes:
  - [ ] EXE + launcher + checksum
  - [ ] server/client fat JARs
  - [ ] docs archive ZIP

## Failure Path

1. Fix on `master`.
2. Re-run gates.
3. Cut next patch tag.
4. Push and verify artifacts again.
