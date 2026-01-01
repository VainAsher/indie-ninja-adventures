# Documentation Overview
**Vain Asher Gaming's: Indie Ninja Adventures**

This folder contains living documentation for the project. Use it as your hub for status, plans, and technical references.

---

## Key Documents
- **CHANGELOG.md** — Version history (current: v0.7.0)
- **DEVLOG.md** — Daily/Session notes, decisions, metrics
- **ROADMAP.md** — Milestones, backlog, and goals
- **SYSTEM_OVERVIEW.md** — API reference and usage patterns
- **ARCHITECTURE.md** — Design principles and patterns
- **QUICK_START.md** — Run the game and tests in minutes
- **PROJECT_ORGANIZATION.md** — Current repo layout and conventions
- **MODDING_GUIDE.md** — How to build plugins/mods

Legacy/archived references are now under `docs/legacy/` (e.g., collision fix summaries, playability testing notes).

---

## Current Status
- **Version**: 0.7.0
- **Phase**: Rendering & Visual Polish next; core systems, collision, camera, and procedural world gen complete
- **Player Mechanics**: Movement, jump (ground/double/wall/coyote/buffer), dash, crouch; **wall slide disabled** (using wall friction + wall-jump coyote buffer)
- **Tests**: Full suite passing via `python run_tests.py`
- **Logging**: Defaults to `%APPDATA%/NinjaDash/logs`; override with `NINJADASH_LOG_DIR`

---

## How to Navigate
- New here? Start with `QUICK_START.md`, then `../README.md`.
- Need API details? Open `SYSTEM_OVERVIEW.md` and `ARCHITECTURE.md`.
- Planning work? Check `ROADMAP.md` and `CHANGELOG.md`.
- Tracking decisions? See `DEVLOG.md`.
- Legacy fixes or historical context? Look in `legacy/`.

---

## Maintenance Expectations
- **CHANGELOG.md**: Update each user-facing change; roll [Unreleased] into tagged sections.
- **DEVLOG.md**: Add session notes during active development.
- **ROADMAP.md**: Refresh when priorities shift or milestones close.
- **SYSTEM_OVERVIEW.md / ARCHITECTURE.md**: Update when APIs or patterns change.
- **INDEX.md / SUMMARY.md**: Keep links and counts current after adding/moving docs.

---

**Last Updated**: 2025-12-12  
**Maintainer Focus**: Keep docs in sync with code (wall slide disabled, wall friction + wall coyote buffer, input handling hardened, full test suite green).
