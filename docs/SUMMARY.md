# Documentation Summary
**Vain Asher Gaming's: Indie Ninja Adventures**

Snapshot of what’s documented and where.

---

## Live Documents (kept current)
- **CHANGELOG.md** — v0.4.0-dev history, features/fixes
- **DEVLOG.md** — Session notes and decisions
- **ROADMAP.md** — Phases, milestones, backlog
- **SYSTEM_OVERVIEW.md** — API reference
- **ARCHITECTURE.md** — Design patterns
- **QUICK_START.md** — Run/play/test instructions
- **PROJECT_ORGANIZATION.md** — Repo layout and conventions
- **MODDING_GUIDE.md** — Mod/plugin guidance

## Archive (legacy references)
- `legacy/WALL_COLLISION_FIX.md`
- `legacy/PLATFORM_COLLISION_SUMMARY.md`
- `legacy/PLAYABILITY_TESTING.md`
- `legacy/PLAYABILITY_TESTING_SUMMARY.md`
- `legacy/SESSION_SUMMARY.md`

---

## Current Status
- **Version**: 0.4.0-dev
- **Player Mechanics**: Movement, jump (ground/double/wall/coyote/buffer), dash, crouch; wall slide **disabled** (wall friction + wall-jump coyote buffer)
- **Testing**: `python run_tests.py` passes all suites
- **Updated**: 2025-12-12

---

## Update Workflow
1. Add feature/bugfix → log in `CHANGELOG.md` ([Unreleased]) and `DEVLOG.md`.
2. API or behavior change → update `SYSTEM_OVERVIEW.md` / `ARCHITECTURE.md`.
3. Milestone progress → refresh `ROADMAP.md`.
4. New or moved docs → refresh `INDEX.md` and this summary.

---

**Maintainer Note**: Wall slide remains off; documentation and tests reflect the wall-friction fallback and wall-jump coyote buffer. All log paths still use `%APPDATA%/NinjaDash` unless overridden via `NINJADASH_LOG_DIR`.
