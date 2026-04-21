---
doc_type: operations
status: implementing
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Pygame Split Checklist

Tracking checklist for extracting the legacy Pygame prototype lane into a separate repository.

## Phase 1 - Boundary Contract

- [x] Finalize move map (`docs/operations/PYGAME_EXTRACTION_INVENTORY.md`).
- [x] Classify temporary compatibility shims and removal stage.
- [x] Define launcher contract: no `demo_game.py` fallback in this repo.

## Phase 2 - New Repo Setup and Move

- [ ] Create target repository for prototype runtime (`indie-ninja-prototype`, or final chosen name).
- [ ] Move runtime packages (`core/`, `systems/`, `mechanics/`, `entities/`, `game/`, `network/`, `rendering/`, `ui/`, `audio/`, `config/`, `dev_tools/`, `utils/`).
- [ ] Move prototype tests (`tests/`, `run_tests.py`, `playtest_verification.py`).
- [ ] Move prototype build lane (`demo_game.py`, `build/build.py`, `build/ninja_dash_{dev,testing,production}.spec`).
- [ ] Split prototype packaging metadata (`pyproject.toml`, `requirements.txt`) into new-repo ownership.

## Phase 3 - Decouple This Repo

- [x] Remove launcher runtime fallback to `demo_game.py`.
- [x] Remove Python game lane from `ci.yml` default delivery path.
- [x] Remove `ninja_dash.exe` release lane from `release.yml`.
- [x] Update legacy workflow docs/checklists that still assume EXE-first release.

## Phase 4 - Cleanup and Archive

- [ ] Delete migrated prototype paths from this repo after transfer verification.
- [ ] Archive split-era planning notes in docs archive.
- [ ] Run repo hygiene pass and close extraction plan.

## Cross-Repo Follow-Up

- [ ] Open coordination item in launcher repo for release-asset expectations (JAR-first/default lane).
- [ ] Open coordination item in feedback/pipeline repo for intake wording and triage labels.
- [ ] Publish migration note with ownership and support boundaries.
