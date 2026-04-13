# Release Checklist

Per-iteration release checklist. Use this for every development loop, not only milestones.

Primary reference: [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)

## Pre-Tag Gates (Required)

### Local Validation

- [ ] Python tests pass (if touched): `python run_tests.py`
- [ ] Java build + tests pass:
  - [ ] `cd java`
  - [ ] `gradle :server:test :server:shadowJar :client:shadowJar --no-daemon`
- [ ] Solo smoke check starts and loads
- [ ] Multiplayer smoke check (host + join) for network-affecting changes

### Version Discipline

- [ ] Tag format is `v0.<minor>.<patch>`
- [ ] Tag is final commit of the iteration
- [ ] `version.json` matches target tag version (without the `v`)
- [ ] `java/build.gradle.kts` version matches target tag version
- [ ] `README.md` version/status is updated when player-facing behavior changed

### Documentation

- [ ] `docs/CHANGELOG.md` updated for user-facing changes
- [ ] Relevant plan/status docs updated (`docs/PLAN_*.md`, `docs/PLAYER_EXPECTATIONS.md` as applicable)

## Release Commands (Canonical)

```bash
# 1) sync
git checkout master
git pull origin master

# 2) commit final iteration state
git add <files>
git commit -m "fix|feat|docs|test|chore: <summary>"

# 3) annotated tag (required style)
git tag -a v0.<minor>.<patch> -m "v0.<minor>.<patch> - <summary>"

# 4) push commit + tag
git push origin master
git push origin v0.<minor>.<patch>
```

## Post-Push Verification (Required)

- [ ] `CI` workflow succeeded
- [ ] `Release` workflow succeeded
- [ ] GitHub release exists for the pushed tag
- [ ] Release includes:
  - [ ] `ninja_dash.exe`
  - [ ] `ninja_dash_launcher.exe`
  - [ ] `ninja_dash.exe.sha256`
  - [ ] client fat JAR (`*-all.jar`)
  - [ ] server fat JAR (`*-all.jar`)

## Recovery Path

If release workflow fails:

1. Fix the issue on `master`.
2. Re-run local gates.
3. Cut next patch tag in `v0.<minor>.<patch>` space.
4. Push again and re-verify artifacts.

Do not proceed to a new iteration until a testable release is available.

