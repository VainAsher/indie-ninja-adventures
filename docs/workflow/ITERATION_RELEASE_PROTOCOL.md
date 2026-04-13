# Iteration Release Protocol

Single source of truth for commit, push, tag, and release behavior.

## Goal

Every completed development iteration must produce a buildable, testable release.

## Non-Negotiable Rules

1. Every iteration ends in a release tag and a GitHub release build.
2. Do not release with failing local tests or failing local build.
3. Never use `v1.0.0` (or any `v1.x.x`) until the project owner explicitly declares alpha readiness.
4. Use only `v0.<minor>.<patch>` tags during development (for example `v0.11.22` or `v0.25.3`).
5. Tag the final commit of the iteration, not an intermediate commit.
6. Prefer annotated tags for every iteration release.

## Canonical Iteration Loop

1. Sync branch:
   - `git checkout master`
   - `git pull origin master`
2. Implement one logical iteration (feature/fix/docs/test).
3. Run local quality gates:
   - Python path (if touched): `python run_tests.py`
   - Java path (required for shippable iteration):
     - `cd java`
     - `gradle :server:test :server:shadowJar :client:shadowJar --no-daemon`
4. Update version metadata for the next tag in `v0.<minor>.<patch>` format.
5. Commit the iteration.
6. Create annotated tag on the final commit:
   - `git tag -a v0.<minor>.<patch> -m "v0.<minor>.<patch> - <summary>"`
7. Push commit and tag:
   - `git push origin master`
   - `git push origin v0.<minor>.<patch>`
8. Verify CI/CD:
   - CI workflow passes.
   - Release workflow passes.
   - Release assets are attached and downloadable.
9. Publish a short iteration report: what changed, why, what to test.

## Release Source of Truth

- Primary path: tag push triggers `.github/workflows/release.yml`.
- Manual `gh release create/upload` is recovery-only (for a failed or missing release) and should be documented in the iteration report.

## Asset Verification

Minimum expected release outputs:

- `ninja_dash.exe`
- `ninja_dash_launcher.exe`
- `ninja_dash.exe.sha256`
- client fat JAR (`*-all.jar`)
- server fat JAR (`*-all.jar`)

## Failure Handling

If release build fails:

1. Fix on `master` (or `hotfix/*` if needed).
2. Re-run local gates.
3. Cut a new patch tag (`v0.<minor>.<patch+1>`).
4. Push and re-run release flow.

Do not advance to the next iteration until a testable release exists.

