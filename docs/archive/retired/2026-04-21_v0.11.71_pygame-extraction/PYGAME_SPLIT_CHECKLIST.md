---
doc_type: operations
status: archived
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

- [x] Create target repository for prototype runtime (`VainAsher/indie-ninja-prototype`).
- [x] Seed runtime packages snapshot in target repo (`core/`, `systems/`, `mechanics/`, `entities/`, `game/`, `network/`, `rendering/`, `ui/`, `audio/`, `config/`, `dev_tools/`, `utils/`).
- [x] Seed prototype tests snapshot in target repo (`tests/`, `run_tests.py`, `playtest_verification.py`).
- [x] Seed prototype build lane snapshot in target repo (`demo_game.py`, `build/build.py`, `build/ninja_dash_{dev,testing,production}.spec`).
- [x] Seed packaging metadata in target repo (`pyproject.toml`, `requirements.txt`).
- [x] Complete ownership cutover by removing migrated prototype paths from this repo in Phase 4.

## Phase 3 - Decouple This Repo

- [x] Remove launcher runtime fallback to `demo_game.py`.
- [x] Remove Python game lane from `ci.yml` default delivery path.
- [x] Remove `ninja_dash.exe` release lane from `release.yml`.
- [x] Update legacy workflow docs/checklists that still assume EXE-first release.

## Phase 4 - Cleanup and Archive

- [x] Delete migrated prototype paths from this repo after transfer verification.
- [x] Archive split-era planning notes in docs archive.
- [x] Run repo hygiene pass and close extraction plan.

## Cross-Repo Follow-Up

- [x] Open coordination item in launcher repo for release-asset expectations (JAR-first/default lane): `VainAsher/indie-ninja-launcher#1`.
- [x] Open coordination item in feedback/pipeline repo for intake wording and triage labels:
  - `VainAsher/indie-ninja-feedback#2`
  - `VainAsher/indie-ninja-pipeline#1`
- [x] Publish migration note with ownership and support boundaries (`docs/operations/PYGAME_MIGRATION_HANDOVER.md`).

## Execution Links (2026-04-21)

- Launcher repo scaffold created: `https://github.com/VainAsher/indie-ninja-launcher`
- Launcher coordination issue: `https://github.com/VainAsher/indie-ninja-launcher/issues/1`
- Prototype repo created: `https://github.com/VainAsher/indie-ninja-prototype`
- Prototype phase-2 follow-up issue: `https://github.com/VainAsher/indie-ninja-prototype/issues/1`
- Feedback repo scaffold created: `https://github.com/VainAsher/indie-ninja-feedback`
- Feedback coordination issue: `https://github.com/VainAsher/indie-ninja-feedback/issues/2`
- Pipeline repo scaffold created: `https://github.com/VainAsher/indie-ninja-pipeline`
- Pipeline coordination issue: `https://github.com/VainAsher/indie-ninja-pipeline/issues/1`
