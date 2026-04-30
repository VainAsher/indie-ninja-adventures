---
doc_type: workflow
status: living
owner: release-team
last_updated: 2026-04-30
version_anchor: v0.13.17
---

# Release Checklist

Reference protocol: [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)

## Pre-Tag Gates

- [ ] Version parity passes: `python tools/check_version_sync.py --tag v0.<minor>.<patch>`
- [ ] Docs freshness baseline generated: `python tools/check_docs_freshness.py --emit-report`
- [ ] Java tests + build pass:
  - [ ] `cd java`
  - [ ] `gradle :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`
- [ ] If the slice changes worldgen snapshots, lab tooling, room rules, zone
  templates, or level-authoring data, run the worldgen gates:
  - [ ] `python tools/test_worldgen_lab.py`
  - [ ] `cd java`
  - [ ] `gradle :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon`
  - [ ] Generate or render the relevant baseline, currently seed `420`:
    `python tools/worldgen_lab.py act1 --out build/worldgen-lab/act1-seed-420`

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
  - [ ] server/client fat JARs
  - [ ] docs archive ZIP

## Failure Path

1. Fix on `master`.
2. Re-run gates.
3. Cut next patch tag.
4. Push and verify artifacts again.
