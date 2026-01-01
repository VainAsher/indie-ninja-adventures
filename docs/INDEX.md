# Documentation Index
**Vain Asher Gaming's: Indie Ninja Adventures**

Navigation hub for all project docs.

---

## Primary Guides
- `QUICK_START.md` — Run the game/tests fast
- `../README.md` — Project overview and controls
- `SYSTEM_OVERVIEW.md` — API reference and system details
- `ARCHITECTURE.md` — Design patterns and conventions
- `ROADMAP.md` — Milestones, backlog, success metrics
- `CHANGELOG.md` — Version history (current v0.7.0)
- `DEVLOG.md` — Session notes and decisions
- `PROJECT_ORGANIZATION.md` — Current repo layout and conventions
- `PROJECT_REORGANIZATION_2025_12_14.md` — Documentation/test reorganization summary
- `MODDING_GUIDE.md` — Plugin/mod development

## Testing & Operations
- `../tests/README.md` — Test suite structure
- `QUICK_START.md` — Command examples for `run_tests.py`
- Logging: default `%APPDATA%/NinjaDash/logs`, override with `NINJADASH_LOG_DIR`

## Release Notes & Milestones
- `releases/CHANGES_SUMMARY.md` — High-level changes summary
- `releases/SPRITE_INTEGRATION_COMPLETE.md` — Sprite system integration milestone
- `releases/TILE_INTEGRATION_COMPLETE.md` — Tile system integration milestone
- `releases/TILE_RENDERING_COMPLETE.md` — Tile rendering system milestone
- `releases/TILESET_REPLACEMENT_COMPLETE.md` — Tileset replacement milestone
- `releases/WALL_SLIDE_ANIMATION_FIX.md` — Wall slide animation fix

## Operations & Maintenance
- `operations/USER_DATA_MIGRATION.md` — User data directory migration guide

## Legacy / Archive
- `legacy/WALL_COLLISION_FIX.md` — Historical collision fix notes
- `legacy/PLATFORM_COLLISION_SUMMARY.md` — Legacy collision summary
- `legacy/PLAYABILITY_TESTING.md` — Archived playability checklist
- `legacy/PLAYABILITY_TESTING_SUMMARY.md` — Archived playability framework summary
- `legacy/SESSION_SUMMARY.md` — Archived session recap for procedural generation/playability work

---

## Quick Paths
- Want to play? `python demo_game.py --procedural --seed 12345`
- Need current state? See `CHANGELOG.md` and `ROADMAP.md`
- Need implementation detail? `SYSTEM_OVERVIEW.md`
- Need design rationale? `ARCHITECTURE.md` and `DEVLOG.md`

---

**Last Updated**: 2025-12-14
**Notes**: Wall slide is disabled; wall friction + wall-jump coyote buffer is active. Documentation and tests reorganized into subdirectories.
