---
doc_type: operations
status: living
owner: release-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Delivery Checklist (Java-first)

Use this checklist before push/tag actions in this repository.

## Local Push Gates

- [ ] `python tools/check_version_sync.py`
- [ ] `python tools/check_docs_freshness.py --emit-report`
- [ ] `cd java && ./gradlew :server:test :client:test --no-daemon`
- [ ] If release-facing: `cd java && ./gradlew :server:shadowJar :client:shadowJar --no-daemon`

## Workflow Consistency

- [ ] `.github/workflows/ci.yml` remains Java-default for required game validation.
- [ ] `.github/workflows/release.yml` remains JAR + docs-archive delivery (no `ninja_dash.exe` build lane).
- [ ] Docs and plans are updated when release process assumptions changed.

## Release Artifact Expectations

- [ ] server fat JAR (`*-all.jar`)
- [ ] client fat JAR (`*-all.jar`)
- [ ] docs archive ZIP (`docs-archive-YYYY-MM-DD-vX.Y.Z.zip`)

## Legacy Note

Legacy Pygame runtime checks now belong to `VainAsher/indie-ninja-prototype` and are not part of this repository's release gates.
