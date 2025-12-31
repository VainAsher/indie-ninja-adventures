# CI/CD Plan (GitHub Actions Ready)

Goal: lightweight pipeline that keeps the repo green and prepares for future packaging/distribution.

## Pipelines
- **lint-and-test (per push/PR)**  
  - `python -m pip install -r requirements.txt`  
  - Set `SDL_VIDEODRIVER=dummy` to run pygame headless.  
  - `python -m pytest` (or `python run_tests.py --unit --integration --edge` once the suite is fully green).  
  - Artifacts: `pytest` JUnit XML + logs (optional).
- **smoke-demo (nightly/optional)**  
  - Same install + headless env.  
  - `python demo_game.py --procedural --seed 12345 --headless` (add a `--headless` flag to skip display once implemented).  
  - Capture logs and fail on exceptions.
- **release (tag push, later)**  
  - Build wheel (if packaging) or zip of assets for testers.  
  - Attach artifacts to GitHub release.

## Environment
- Python 3.11.x
- `SDL_VIDEODRIVER=dummy` for headless.
- Cache `~/.cache/pip` between runs.

## Suggested GitHub Actions Skeleton
```yaml
name: ci
on:
  push:
  pull_request:
jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: python -m pip install -r requirements.txt
      - name: Run tests
        env:
          SDL_VIDEODRIVER: dummy
        run: python -m pytest
```

## Pre-flight Checklist (local)
- `python -m pip install -r requirements.txt`
- `SDL_VIDEODRIVER=dummy python -m pytest` (until run_tests.py is refit for headless CI)
- Ensure `user_data/` is writable; for CI point it to a temp dir via `NINJADASH_USER_DATA`.

## Follow-ups
- Add `--headless` to `demo_game.py` to avoid display creation.
- Add coverage reporting (coverage.py + Codecov) once the suite is consistently green.
- Add lint (ruff/black) once code is normalized.
