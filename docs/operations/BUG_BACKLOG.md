# Bug Backlog (stabilize before v0.6.1)

## Test Failures (blocking)
- `tests/unit/test_core_infrastructure.py::test_state` expects `PlayerState.health` and snapshot `health`; update to use `health_state` (fixed in code – rerun suite).
- `tests/unit/test_jump_mechanic.py` instantiates `PlayerState` with `health` kw; update to `HealthState` (fixed in code – rerun suite).
- `tests/unit/test_physics_system.py::test_fall_speed_cap` references `PhysicsSystem.MAX_FALL_SPEED`; expose attributes in system (fixed in code – rerun suite).

## Noise / Flakiness
- `rendering/tile_loader.py` and `systems/world_generation.py` printed debug info on import; converted to logger.debug (avoid stdout noise in CI).
- Tests write logs to `user_data/logs` in repo; consider redirecting to temp dir in CI via `NINJADASH_USER_DATA`.

## Known Gaps (next in line)
- No automated coverage for new systems: inventory/trading/missions/hub/portals/boss/enemy AI, rendering/autotiling, pickup/hazard spawners.
- No headless flag for `demo_game.py`; currently needs display unless `SDL_VIDEODRIVER=dummy` is set.
- Docs and README still describe v0.4 scope; keep aligning with the scope freeze (Campaign/Arcade/Sandbox vertical slice).
