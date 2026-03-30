# Contributing

Indie Ninja Adventures is currently solo-developed. This guide documents processes and standards
for future collaborators and for maintaining consistency as the project grows.

---

## Branching Model

See [docs/workflow/BRANCHING.md](docs/workflow/BRANCHING.md) for the full Git flow model.

Quick reference:

```
main        ← stable releases only
develop     ← integration — PR here from feature branches
feature/*   ← new work
hotfix/*    ← urgent production fixes
```

**Never commit directly to `main`.**

---

## Commit Messages

Format: `type: short description`

```
feat: add Forest boss phase 1 charge attack pattern
fix: resolve coin desync when host collects before client joins
docs: update ARCHITECTURE.md with authoritative server data flow
test: add edge case for wall jump during dash cancellation
chore: bump version to 0.8.1
refactor: extract world snapshot serialisation into snapshots.py
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`

---

## Pull Requests

- PR against `develop`, not `main`
- Fill in the PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
- All CI checks must pass before merge
- Squash optional — clear linear history is preferred but not required

---

## Code Standards

This project uses automated formatting and linting enforced by pre-commit hooks.

**Install hooks once:**
```bash
pip install pre-commit
pre-commit install
```

**Standards:**

| Tool | Config | Rule |
|------|--------|------|
| Black | `pyproject.toml` | Line length 100, Python 3.11 |
| Ruff | `pyproject.toml` | E, W, F, I, N, UP, B, C4 rules |
| MyPy | `pyproject.toml` | Gradual typing — `disallow_untyped_defs = false` |

Pre-commit runs automatically on `git commit`. To run manually:
```bash
pre-commit run --all-files
```

---

## Tests

All tests must pass before merging.

```bash
# Run full suite
python run_tests.py

# Run categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --edge

# Headless (CI mode)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python run_tests.py
```

**Rules:**
- New features require new tests
- Bug fixes require a regression test
- Tests must not open windows (use headless mode)
- Tests must not depend on file system state or random seeds (use fixtures)

If physics or the input pipeline changes, run a replay validation:
```bash
python demo_game.py --replay user_data/replays/<session>.json
```

---

## Dev Environment Setup

See [docs/dev/SETUP.md](docs/dev/SETUP.md) for full setup instructions.

Quick start:
```bash
git clone https://github.com/VainAsher/indie-ninja-adventures.git
cd indie-ninja-adventures
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
python demo_game.py
```

---

## Documentation

When making user-visible changes, update:

- `docs/CHANGELOG.md` — add entry under correct version
- `docs/dev/SYSTEMS.md` — if a public API changes
- `docs/dev/ARCHITECTURE.md` — if a system design changes
- `docs/ROADMAP.md` — mark completed milestones

For release PRs, also update:
- `version.json` — bump version + build_date
- `pyproject.toml` — match version

---

## Review Checklist

Before merging any PR:

- [ ] Tests pass (`python run_tests.py`)
- [ ] No regressions in multiplayer (smoke test if netcode touched)
- [ ] Replay determinism preserved (if physics/input changed)
- [ ] Docs updated if behaviour changed
- [ ] Version bumped if this is a release PR
