---
doc_type: operations
status: living
owner: release-team
last_updated: 2026-04-15
version_anchor: v0.11.45
replaces: docs/archive/retired/2026-04-15_v0.11.45/CI_CD_PLAN.md
---

# CI/CD Plan

This plan mirrors the active GitHub workflows under `.github/workflows`.

## Active Pipelines

- `ci.yml`
  - Python quality/test lane (for launcher/tooling and regression harnesses)
  - Java build/test lane (`:server:test`, `:client:test`, fat JAR builds)
  - Informational strict-lint lane
- `release.yml`
  - Trigger: version tags `v0.*.*`
  - Validates version parity with `tools/check_version_sync.py --tag`
  - Builds game/launcher executables and Java fat JARs
  - Publishes GitHub release assets
- `generate_api_docs.yml`
  - Manual API docs artifact generation
- `sync_feedback.yml`
  - Scheduled feedback intake summary sync

## Docs Freshness Soft Gate

CI now includes a non-blocking docs freshness check:

- Command: `python tools/check_docs_freshness.py --emit-report`
- Report output: `docs/reports/docs_freshness_report.md`
- CI behavior: warnings only unless explicitly run with `--strict`

## Release Archive Contract

Each release run should produce a docs archive ZIP and attach it to the release.

- Filename contract: `docs-archive-YYYY-MM-DD-vX.Y.Z.zip`
- Repo storage path: `docs/archive/zips/`
- Same ZIP is uploaded as a release asset.
- Rotation policy: keep latest 6 ZIP files in repo, older snapshots remain in release assets.

## Required Local Gates Before Tag

1. `python tools/check_version_sync.py --tag v0.<minor>.<patch>`
2. `python tools/check_docs_freshness.py --emit-report`
3. `cd java && gradle :server:test :server:shadowJar :client:shadowJar --no-daemon`
4. `python run_tests.py` (if Python runtime/tooling changed)

## Ownership

- Release metadata parity: release team
- Docs freshness policy: docs owners + release team
- Workflow breakage triage: core-team
