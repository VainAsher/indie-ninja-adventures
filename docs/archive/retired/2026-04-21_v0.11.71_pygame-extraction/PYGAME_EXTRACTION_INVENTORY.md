---
doc_type: operations
status: archived
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Pygame Extraction Inventory

Phase 1 boundary contract for splitting the legacy Pygame runtime and `ninja_dash.exe` lane out of this repository.

## Migration Window and Shim Contract

- Legacy launcher fallback window: closed on 2026-04-21.
- Runtime fallback shim status: removed on 2026-04-21 (`demo_game.py` launch path no longer supported by launcher).
- Source-path compatibility shim status: removed on 2026-04-21 (migrated prototype paths deleted from this repo after transfer verification).

## Exact Move Map (Leaves This Repo)

| Path | Action | Notes |
| --- | --- | --- |
| `demo_game.py` | move | Legacy Pygame runtime entrypoint (`ninja_dash.exe` source lane). |
| `core/` | move | Legacy Python runtime package. |
| `systems/` | move | Legacy Python runtime package. |
| `mechanics/` | move | Legacy Python runtime package. |
| `entities/` | move | Legacy Python runtime package. |
| `game/` | move | Legacy Python runtime package. |
| `network/` | move | Legacy Python runtime package. |
| `rendering/` | move | Legacy Python runtime package. |
| `ui/` | move | Legacy Python runtime package. |
| `audio/` | move | Legacy Python runtime package. |
| `config/` | move | Legacy Python runtime config package used by `demo_game.py`. |
| `dev_tools/` | move | Prototype-era Python tooling. |
| `utils/` | move | Prototype-era Python helper modules. |
| `tests/` | move | Legacy Python game test suites. |
| `run_tests.py` | move | Legacy Python game test runner. |
| `playtest_verification.py` | move | Legacy Python playtest helper. |
| `build/build.py` | move | Pygame EXE build orchestrator. |
| `build/ninja_dash_production.spec` | move | Pygame game EXE spec. |
| `build/ninja_dash_dev.spec` | move | Pygame game EXE spec. |
| `build/ninja_dash_testing.spec` | move | Pygame game EXE spec. |
| `pyproject.toml` | split/move | Current package metadata is prototype-runtime centric. |
| `requirements.txt` | split/move | Current dependency list is prototype-runtime centric. |

## Post-Cutover Compatibility Notes

- Launcher historical-release installer logic remains able to install EXE assets from old tags when users manually select those tags.
- Prototype runtime ownership is now in `VainAsher/indie-ninja-prototype`.

## Java-First Surfaces (Stay In This Repo)

- `java/` modules (`:core`, `:shadowascent`, `:server`, `:client`)
- Java tests under `java/*/src/test/java/`
- Java JAR release assets (`ninja-client-all.jar`, `ninja-server-all.jar`)
- Launcher Java runtime lane (`launcher/launcher.py`) without `demo_game.py` fallback

## CI and Release Decouple Targets

- `.github/workflows/ci.yml`: remove Python game lint/test lanes as required gates.
- `.github/workflows/release.yml`: remove Python game test + `ninja_dash.exe` build/publish lane.
- Keep Python only where required for repo tooling (docs/archive scripts), not game-runtime validation.
