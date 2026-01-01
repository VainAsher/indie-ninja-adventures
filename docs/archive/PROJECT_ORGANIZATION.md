# Project Organization
**Vain Asher Gaming's: Indie Ninja Adventures**

Summary of the current repository layout and conventions (updated 2025-12-12).

---

## Directory Layout (top-level)
```
core/           # Event bus, logger, clock, state, entity system, mod system
systems/        # Collision, physics, camera, world generation
mechanics/      # Player mechanics (movement, jump, dash, crouch; wall_slide is legacy/disabled)
entities/       # Player orchestrator, components
rendering/      # Sprites, particles, HUD helpers
config/         # Logging config, settings
network/        # Client/server scaffolding
tests/          # Unit, integration, edge/regression suites
docs/           # Living documentation (legacy refs in docs/legacy/)
legacy/         # Archived original code
demo_game.py    # Demo entry point
run_tests.py    # Test runner
```

## Testing Structure
- `tests/unit/` — Core systems and mechanic units
- `tests/integration/` — Player + systems wiring
- `tests/edge_cases/` — Collision and regression scenarios
- Run all: `python run_tests.py`

## Conventions
- ASCII docs (avoid stray Unicode), Markdown for prose.
- Feature flags: wall jump/dash/crouch remain enabled; wall slide is currently disabled (wall friction + wall-jump coyote buffer active).
- Logging path defaults to `%APPDATA%/NinjaDash/logs`; override with `NINJADASH_LOG_DIR`.
- Branch/phase naming follows roadmap milestones (v0.7.0 currently).

## Recently Updated
- Wall interaction rework: wall slide disabled; wall friction + wall-jump buffer in player orchestrator.
- Input handling hardened for dict-style key inputs (tests updated).
- Documentation refreshed; legacy collision/playability notes moved to `docs/legacy/`.

---

**Last Updated**: 2025-12-12  
**Keeper**: Ensure this reflects structural or convention changes when adding/moving modules.
