# Release Checklist

Monthly (or milestone-based) release process for Indie Ninja Adventures.

---

## Pre-Release

### Code + Tests

- [ ] All sprint tasks for this milestone are complete and verified
- [ ] `python run_tests.py` passes — all tests green
- [ ] Replay validation: run a saved session from `user_data/replays/`, verify it plays back correctly
- [ ] Multiplayer smoke test: host + join 2-player local session, verify basic sync
- [ ] No P0 or P1 issues open in feedback repo for this version

### Version Consistency

- [ ] `version.json` — `"version"` set to new version, `"build_date"` updated to today
- [ ] `pyproject.toml` — `version` matches `version.json`
- [ ] Launcher `LAUNCHER_VERSION` (if launcher has changes) — bump and test

### Documentation

- [ ] `docs/CHANGELOG.md` — new version entry added (see template below)
- [ ] `docs/ROADMAP.md` — completed milestone marked done, next milestone updated
- [ ] `docs/operations/BUG_BACKLOG.md` — resolved issues removed or marked fixed
- [ ] Known issues section in changelog reflects current state

---

## Release

```bash
# 1. Merge develop → main
git checkout main
git pull origin main
git merge develop --no-ff -m "chore: release vX.X.X"

# 2. Tag the release
git tag vX.X.X

# 3. Push — triggers GitHub Actions build + release
git push origin main
git push origin vX.X.X

# 4. Monitor GitHub Actions
#    → build-and-release job should complete in ~5 minutes
#    → verify ninja_dash.exe + ninja_dash_launcher.exe attached to release
#    → verify ninja_dash.exe.sha256 attached
#    → verify launcher repo received dispatch notification (if CROSS_REPO_PAT set)
```

- [ ] GitHub Release created with correct tag
- [ ] Both `.exe` files attached to release
- [ ] SHA256 checksum attached
- [ ] Release notes auto-generated (review and edit if needed)

---

## Post-Release

### Communication

- [ ] Pin a comment to the [feedback repo](https://github.com/VainAsher/indie-ninja-feedback) with the release notes
- [ ] Update the "Latest Version" pinned issue if one exists in feedback repo

### Documentation

- [ ] Write devlog entry in `docs/DEVLOG.md` (see template below)
- [ ] Write monthly update post (see template below)
- [ ] Update UAT notes in `docs/UAT_SUITE.md` if UAT was performed

### Pipeline

- [ ] Push changelog to pipeline repo (copy relevant entry to pipeline repo's release tracking)
- [ ] Create next sprint planning issue in pipeline repo
- [ ] Cut fresh `develop` from `main`:

```bash
git checkout develop
git merge main
git push origin develop
```

---

## Changelog Entry Template

```markdown
## [X.X.X] - YYYY-MM-DD (Short Description)

### Summary

One paragraph describing what this release delivers and why it matters.

### Added

- **Feature name** (`file/path.py`): Description of what was added.

### Changed

- **What changed** (`file/path.py`): What it does now vs before.

### Fixed

- **Bug description** (`file/path.py`): Root cause and fix.

### Known Issues

- Issue description — workaround if any.
```

---

## Devlog Entry Template

```markdown
## [Month YYYY] — vX.X.X

### Session Summary

What was worked on, key decisions made, surprises encountered.

### What Shipped

- Feature / fix description
- Feature / fix description

### What Didn't Make It

- Deferred to next sprint and why.

### Lessons Learned

- Anything worth remembering for next time.

### Next Up

- Planned work for next sprint.
```

---

## Monthly Update Template

```markdown
## [Month YYYY] — vX.X.X

### What shipped

- Bullet point summary of changes (player-friendly language)

### What was fixed

- Bug fixes in plain language

### What's next

- Next milestone goals

### Known issues

- Active known issues with workarounds

### Playtest notes

- Any observations from testing sessions
```

---

## Build Verification

After the release workflow completes, verify locally:

```bash
# Download and verify checksum
# (PowerShell)
$hash = (Get-FileHash ninja_dash.exe -Algorithm SHA256).Hash.ToLower()
$expected = (Get-Content ninja_dash.exe.sha256).Split(' ')[0]
if ($hash -eq $expected) { "OK" } else { "MISMATCH" }

# Test launcher
.\ninja_dash_launcher.exe
# Should show: "v0.X.X (up to date)" or offer update
```
