# Stage 5: Release Cycle

Monthly (or milestone-based) release process.

See the full checklist in the game repo:
[docs/workflow/RELEASE_CHECKLIST.md](https://github.com/VainAsher/indie-ninja-adventures/blob/main/docs/workflow/RELEASE_CHECKLIST.md)

---

## Release Rhythm

- **Target cadence**: monthly, tied to milestone completion
- **Hotfix releases**: any time a P0 is fixed and verified
- **Alpha/Beta builds**: tag as `v0.8.0-alpha.1` — launcher will not auto-update to pre-release tags

---

## Pre-Release Checklist (Summary)

- [ ] All sprint tasks complete and verified
- [ ] All tests green (`python run_tests.py`)
- [ ] Replay validation passed
- [ ] Multiplayer smoke test passed
- [ ] `version.json` and `pyproject.toml` bumped and consistent
- [ ] `docs/CHANGELOG.md` updated with full entry
- [ ] `docs/ROADMAP.md` milestone marked complete

## Release Steps (Summary)

```bash
# In game repo
git checkout main
git merge develop --no-ff -m "chore: release vX.X.X"
git tag vX.X.X
git push origin main && git push origin vX.X.X
# GitHub Actions builds and releases automatically
```

## Post-Release (This Repo)

- [ ] Copy changelog entry here for tracking
- [ ] Update DASHBOARD.md build stability to ✅
- [ ] Write devlog entry in game repo `docs/DEVLOG.md`
- [ ] Post monthly update (see template in game repo RELEASE_CHECKLIST.md)
- [ ] Pin release announcement in feedback repo
- [ ] Plan next sprint (start new cycle)

---

## Monthly Update Checklist

After every release, publish a monthly update:

1. Devlog entry in game repo
2. Update feedback repo pinned "Latest Version" issue
3. Update player-facing changelog at launcher repo `docs/changelog.md`
4. (Optional) Post devlog publicly if you have a community presence
