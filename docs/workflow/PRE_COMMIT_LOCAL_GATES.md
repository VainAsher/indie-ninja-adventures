---
doc_type: workflow
status: living
owner: release-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Pre-Commit Local Gates

Reference documents:
- [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [WORKFLOW_AUDIT_2026-04-17.md](WORKFLOW_AUDIT_2026-04-17.md)

Fast local gate workflow for preventing obvious breakage before commit or push.

## Rules

1. `pre-commit` must stay fast enough for day-to-day use.
2. `pre-push` may be slower, but must remain deterministic.
3. Any commit touching `.py` files must pass Black locally.
4. Any commit touching version or docs metadata must pass version-sync checks.
5. Do not rely on CI as the first formatting or basic test gate.
6. **`:client:test` is the required evidence surface when `GameScreen` construction changes** — new fields, new inline field initializers, new `create()` calls. Server tests do not cover this surface. If client tests cannot run locally (see Known Local Limitations), push the feature commit first and wait for CI green before tagging.
7. **libGDX renderer classes must guard `Gdx.app != null` in their constructors.** `ShapeRenderer`, `BitmapFont`, `SpriteBatch`, and any class wrapping OpenGL resources will throw `NullPointerException` in headless unit tests if constructed unconditionally. Pattern: `if (Gdx.app != null) { ... create renderer ... }`. Render methods must also null-check before using these objects.

## Known Local Test Limitations

`:client:test` may fail locally on Windows due to OneDrive or AV file locks on build output directories. This is expected and does not indicate a code defect. Treat CI as the authoritative gate for client tests. Consequence: **do not tag a release that touches `GameScreen` or any libGDX rendering class until the CI `java-build` job is green on the feature commit.**

## Recommended Hook Split

### Pre-Commit

Run only fast checks:

- Python formatting check on staged `.py` files
- fast Java tests or compile checks for changed modules
- version-sync check when release metadata changed
- docs link/frontmatter check when workflow or release docs changed

### Pre-Push

Run heavier checks:

- `python tools/check_version_sync.py`
- `python tools/check_docs_freshness.py --emit-report`
- `cd java && ./gradlew test --no-daemon`
- `python run_tests.py` only when intentionally touching the legacy Pygame migration lane

## Minimal Commands

```bash
python -m black --check tools
python tools/check_version_sync.py
cd java && ./gradlew test --no-daemon
```

## Done Criteria

- [ ] Fast local checks pass before commit
- [ ] Full local checks pass before tag or push
- [ ] Formatting failures are fixed locally, not in follow-up CI-only churn commits
- [ ] Hook behavior is documented and reproducible across machines

## Failure Path

If a pre-commit or pre-push hook fails:

1. Fix locally.
2. Re-run the failed gate.
3. Do not bypass the hook unless the failure is a verified false positive and the bypass reason is recorded in the commit body or loop note.

## Related Workflows

- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
