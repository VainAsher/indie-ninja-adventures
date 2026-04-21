---
doc_type: operations
status: living
owner: release-team
last_updated: 2026-04-21
version_anchor: v0.11.71
replaces: docs/archive/retired/2026-04-15_v0.11.45/CI_CD_PLAN.md
---

# CI/CD Plan

This plan mirrors the active GitHub workflows under `.github/workflows`.

## Active Pipelines

- `ci.yml`
  - Docs freshness soft gate (`python tools/check_docs_freshness.py --emit-report`)
  - Java default build/test lane (`:server:test`, `:client:test`, `:server:shadowJar`, `:client:shadowJar`)
  - Python setup exists for repo tooling only, not Python game-runtime CI
- `release.yml`
  - Trigger: version tags `v0.*.*`
  - Validates version parity with `tools/check_version_sync.py --tag`
  - Builds/tests Java server+client artifacts
  - Publishes server/client fat JARs plus docs archive ZIP
  - Does not build or publish `ninja_dash.exe` from this repo
- `generate_api_docs.yml`
  - Manual API docs artifact generation
- `sync_feedback.yml`
  - Scheduled feedback intake summary sync

## Docs Freshness Soft Gate

CI includes a non-blocking docs freshness check:

- Command: `python tools/check_docs_freshness.py --emit-report`
- Report output: `docs/reports/docs_freshness_report.md`
- CI behavior: warnings only unless explicitly run with `--strict`

## Release Archive Contract

Each release run produces a docs archive ZIP and attaches it to the release.

- Filename contract: `docs-archive-YYYY-MM-DD-vX.Y.Z.zip`
- Repo storage path: `docs/archive/zips/`
- Same ZIP is uploaded as a release asset
- Rotation policy: keep latest 6 ZIP files in repo; older snapshots remain in release assets

## Required Local Gates Before Tag

1. `python tools/check_version_sync.py --tag v0.<minor>.<patch>`
2. `python tools/check_docs_freshness.py --emit-report`
3. `cd java && gradle :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`

## Ownership

- Release metadata parity: release team
- Docs freshness policy: docs owners + release team
- Workflow breakage triage: core-team
