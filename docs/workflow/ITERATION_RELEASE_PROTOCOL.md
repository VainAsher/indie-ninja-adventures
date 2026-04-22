---
doc_type: workflow
status: living
owner: release-team
last_updated: 2026-04-22
version_anchor: v0.12.01
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
   - `cd java && gradle :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`
   - If `:client:test` fails locally due to OneDrive/AV file locks: push the feature commit first (no tag), wait for CI `java-build` green, then continue to step 4.
4. Update docs (`CHANGELOG`, active plan, relevant contracts).
5. Commit.
6. Push feature commit (no tag yet): `git push origin master`
7. Wait for CI `java-build` to pass on the feature commit before tagging. Check: `gh run list --limit 3`. Do not proceed if the build is queued or in progress.
8. Bump version, commit, tag, push tag: `git tag v0.<minor>.<patch> && git push origin master && git push origin v0.<minor>.<patch>`
9. Monitor CI and Release before closing the session:

   ```bash
   gh run list --limit 3 --json status,conclusion,name,headSha
   ```

   Wait for both `CI` and `Release` to show `"conclusion":"success"`.
   If either shows `"conclusion":"failure"`: open the failure URL, diagnose, fix on `master`, cut the next patch tag, and re-run the release loop.
10. Confirm release assets include Java artifacts and docs archive ZIP.

## Release Assets Minimum

- server fat JAR (`*-all.jar`)
- client fat JAR (`*-all.jar`)
- docs archive ZIP (`docs-archive-YYYY-MM-DD-vX.Y.Z.zip`)

## Recovery

If release fails, fix on `master`, rerun gates, cut next patch tag, and rerun release.
