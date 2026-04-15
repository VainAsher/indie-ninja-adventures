---
doc_type: workflow
status: living
owner: release-team
last_updated: 2026-04-15
version_anchor: v0.11.48
---

# Iteration Release Protocol

Single source of truth for commit, tag, push, and release behavior.

## Rules

1. Every shippable iteration ends with a release tag and release workflow run.
2. Only `v0.<minor>.<patch>` tags are allowed until alpha authorization.
3. Tag only the final commit for that iteration.
4. Use annotated tags.
5. Do not tag if version-sync or docs-freshness checks fail in strict lane.

## Canonical Loop

1. Sync `master`.
2. Implement one logical unit.
3. Run local gates:
   - `python tools/check_version_sync.py`
   - `python tools/check_docs_freshness.py --emit-report`
   - `cd java && gradle :server:test :server:shadowJar :client:shadowJar --no-daemon`
   - `python run_tests.py` when Python code/tooling changed
4. Update docs (`CHANGELOG`, active plan, relevant contracts).
5. Commit.
6. Tag: `git tag -a v0.<minor>.<patch> -m "v0.<minor>.<patch> - <summary>"`
7. Push commit + tag.
8. Verify `CI` and `Release` workflows.
9. Confirm release assets include game artifacts and docs archive ZIP.

## Release Assets Minimum

- `ninja_dash.exe`
- `ninja_dash_launcher.exe`
- `ninja_dash.exe.sha256`
- server fat JAR (`*-all.jar`)
- client fat JAR (`*-all.jar`)
- docs archive ZIP (`docs-archive-YYYY-MM-DD-vX.Y.Z.zip`)

## Recovery

If release fails, fix on `master`, rerun gates, cut next patch tag, and rerun release.
