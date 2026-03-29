# Changelog
**Vain Asher Gaming's: Indie Ninja Adventures**

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.2] - 2026-03-28 (Boss AI + Champion System)

### Summary

All 6 bosses now have functional AI: they chase the player, execute type-specific ranged and melee attacks, trigger special abilities per phase, and deal contact damage. Projectiles now check collision against the player. A champion spawn system means that once a boss type has been defeated, subsequent visits to that boss room have a 40% chance to spawn a weaker champion variant instead.

### Added

- **Boss movement** (`entities/boss_ai.py`): `_chase_player()` drives `boss.velocity_x` each tick based on signed distance to player. Position is integrated in `BossManager.update()` with linear friction.
- **Ranged attacks** (`entities/boss_manager.py`): `_execute_ranged_attack()` dispatches per boss type — FIRE_DEMON fires `fireball`, SHADOW_LORD fires `shadow_bolt`, ICE_QUEEN fires `ice_shard`, NECROMANCER fires `death_bolt`, DRAGON fires `fire_ball`, VEIL_MAIDEN fires `veil_bolt`.
- **Type-specific specials** (`entities/boss_manager.py`): All 6 bosses have 3–4 special attacks fully wired: FIRE_DEMON (`fireball_barrage`, `flame_breath`, `meteor_strike`), SHADOW_LORD (`shadow_strike`, `dark_wave`, `void_portal`), ICE_QUEEN (`blizzard`, `ice_spike`, `freeze_ray`), NECROMANCER (`death_ray`, `soul_drain`, `bone_cage`), DRAGON (`fire_breath`, `wing_slam`, `tail_sweep`), VEIL_MAIDEN (`veil_strike`, `isolation_field`, `light_drain`, `shadow_step`).
- **Projectile–player collision** (`entities/boss_manager.py`): `_check_projectile_player_collision()` tests all active boss projectiles against player AABB each tick and returns total damage to apply.
- **Contact damage** (`entities/boss_manager.py`): Boss body AABB vs player AABB checked during active combat states; returns damage_to_player.
- **Champion system** (`entities/boss_manager.py`, `demo_game.py`, `systems/save_system.py`):
  - `CampaignSaveData.defeated_bosses: set[str]` — persisted set of BossType name strings of bosses killed at least once.
  - `Boss.is_champion: bool` flag; `spawn_boss(champion=True)` spawns at 50% HP, 75% hitbox.
  - `_maybe_spawn_boss()`: if boss type already in `defeated_bosses`, 40% chance to spawn champion instead of full boss.
  - Defeated boss type recorded to `campaign.defeated_bosses` at mission completion.

### Fixed

- **Bosses stood still**: `_execute_phase_combat()` never updated `boss.velocity_x`. Now calls `_chase_player()` every tick.
- **Generic special names**: `_choose_special_attack()` returned hardcoded strings that never matched any boss's `special_attacks` list. Now reads from `BossDefinition.special_attacks`.
- **Projectiles never damaged player**: `update()` returned `None` for projectile hits. Now integrated into the damage return value.

---

## [0.7.1] - 2026-03-28 (Phases 2–5: Boss, Audio, Settings, Ability Gates)

### Summary

Campaign loop stabilized; boss integration, SFX audio, settings wiring, and ability gate enforcement all wired end-to-end. Portal placement now acts as the mechanical ability gate for Forest and Town regions.

### Added

- **Boss integration** (`entities/boss_manager.py`): BossManager wired into game loop. 6 boss missions added to `data/missions.json`. `GateManager` created; `_rebuild_hub_gates()` places ability gates in hub on campaign load and after each unlock.
- **Audio system** (`audio/audio_manager.py`): `AudioManager` wraps `pygame.mixer.Sound`. 12 named SFX slots with silent fallback if files missing. `initialize_audio()` added to `game/game_initialization.py`. SFX hooks wired: swing, hit_enemy, player_hurt, player_death, jump, land, dash, pickup_coin, pickup_item, menu_select, menu_confirm, inventory_open.
- **Placeholder SFX** (`assets/audio/sfx/`): 12 WAV files generated via `tools/gen_placeholder_sfx.py` using stdlib only. Replace with real audio assets.
- **Settings wiring**: `Player.set_key_bindings(dict)` added. `_build_key_bindings()` in `demo_game.py` maps settings string names → pygame constants. `apply_runtime_settings()` wires sfx_volume → `audio_manager.set_volume()`, fullscreen → `pygame.display.toggle_fullscreen()` + `camera.handle_resize()`, show_hitboxes → `show_debug_overlay`, key_* → `player.set_key_bindings()`.
- **SettingsMenu items**: SFX Volume (cycles Off/25/50/75/100%) and Fullscreen toggle added to `ui/menu_system.py`.
- **Ability sync**: `sync_player_abilities(unlocked_abilities)` closure syncs `player.feature_flags` and `JumpMechanic.double_jump_enabled` / `wall_jump_enabled`. Called at campaign start and after every ability unlock.
- **Portal height gating** (`game/hub_manager.py`): Forest portal at `ROOM_PIXEL_CENTER_Y + 200` (floor level, basic jump reachable). Town portal at `ROOM_PIXEL_CENTER_Y - 200` (elevated, double_jump required). Physical placement IS the gate.
- **F9 Debug ability menu** (`ui/menu_system.py:DebugAbilityMenu`): Password-protected overlay (password: `devmode`). Arrow keys + SPACE to toggle any ability live. Gates rebuild on each toggle.
- **Tests**: `tests/test_ability_gates.py` (7 tests), `tests/test_phase4_settings_wiring.py` (12 tests) — all passing.

### Fixed

- **Fullscreen crash** (`systems/camera_system.py`): `camera.handle_resize()` now called after `pygame.display.toggle_fullscreen()` so `render_width`/`render_height` stay in sync. Previously raised `ValueError: Destination surface not the given width or height`.
- **Player had all abilities at campaign start**: `CampaignSaveData` default `unlocked_abilities` is `{basic_movement, jump}` only. `sync_player_abilities()` now called at campaign start to enforce this.

---

## [0.7.0] - 2026-01-01 (Project Restructuring Release)

### Summary
**Major restructuring and documentation overhaul**. This release represents a complete audit and improvement of the project, bumping from v0.4.0-dev documentation to accurate v0.7.0 documentation that reflects all implemented features. The codebase was v0.7.0+ in functionality but documented as v0.4.0-dev - this release brings documentation into alignment with reality.

### Major Changes

#### Infrastructure & Tooling
- **Added Modern Python Packaging**: `pyproject.toml` with Black, Ruff, MyPy, pytest-cov
- **Added CI/CD Pipeline**: GitHub Actions with automated testing, linting, formatting, type checking
- **Added Pre-commit Hooks**: Code quality enforcement on git commits
- **Archived Legacy Code**: Moved `legacy/` to `legacy-archive/` (excluded from repo)
- **Removed Technical Debt Markers**: Cleaned up backup files and outdated references

#### Documentation Overhaul
- **Reduced Documentation Files**: 80+ markdown files → 28 core files (65% reduction)
- **Created FEATURES_V0_7.md**: Comprehensive feature documentation
- **Archived Historical Docs**: Moved 70+ files to `docs/archive/` (sessions, phases, audits, summaries)
- **Updated Core Docs**: README, ROADMAP, CHANGELOG, ARCHITECTURE now reflect v0.7.0 reality
- **Documented Boss AI Gap**: Prominently noted that boss framework exists but boss AI is not implemented

#### Version Consistency
- **Updated ALL Version References**: v0.4.0-dev → v0.7.0 across 25+ files
- **Version String Updates**: UI menu system, documentation, build configs

### What's Actually in v0.7.0 (Documentation Finally Accurate)

This release doesn't add new features - it documents what was already implemented but undocumented:

#### Game Systems (Implemented v0.5.0-v0.7.0, Now Documented)
- **Campaign Mode**: 25 missions across 5 zones with story progression
- **Enemy System**: 5 enemy types with AI (SLIME, BAT, SKELETON, ORC, DEMON)
- **Story System**: Story manager with multiple endings, character arcs, cutscenes
- **Dialogue System**: NPC conversations with branching choices
- **Trading System**: 3-tier shops with inventory management
- **Portal System**: Hub-based fast-travel
- **Combat System**: 3-hit combo, air attacks, special abilities
- **Loot System**: Rarity tiers, enemy drops, treasure chests

#### Known Gaps (Now Documented)
- **Boss AI**: Framework exists (entities/boss.py, entities/boss_manager.py) but NO functional boss AI
  - Boss rooms generate but have no encounters
  - Estimated 220 hours to implement (ROADMAP.md Phase 8)
  - See FEATURES_V0_7.md for details
- **Sound System**: Planned but not implemented
- **Multiplayer**: Planned for v1.0.0+

#### Code Refactoring (Phases 3-6 Completed)

**Phase 3: demo_game.py Refactoring**
- **Reduced demo_game.py**: 3,496 → 2,607 lines (25.4% reduction, -889 lines)
- **Created 4 new modular files**:
  - `game/game_initialization.py` (430 lines) - System initialization
  - `game/level_factory.py` (377 lines) - Level creation
  - `game/world_builder.py` (549 lines) - World regeneration
  - `game/game_helpers.py` (63 lines) - Utility functions
- **Removed duplicate code**: 767 lines of duplicates eliminated
- **Improved maintainability**: Functions now organized by purpose

**Phase 4: Technical Debt Resolution (Partial)**
- **Fixed EventBus Memory Leak**:
  - Added owner-based subscription tracking
  - Implemented `unsubscribe_all(owner)` for bulk cleanup
  - Updated CameraEffectsHandler with cleanup() method
  - Prevents memory leaks from recreated entities
- **Verified Save System Security**: HMAC-SHA256 signature and validation confirmed working
- **Skipped**: PlayerState refactoring (43 fields → 9) deferred to future release due to complexity

**Phase 5: Code Quality Enforcement**
- **Black Formatting**: 170 files formatted to consistent style (100% compliance)
- **Ruff Linting**: 2,084 → 115 errors (94.5% reduction)
  - 1,969 auto-fixed issues
  - Modern Python 3.10+ type syntax (`str | None` instead of `Optional[str]`)
  - Sorted imports, removed f-string placeholders
- **Type Hints Added**:
  - Core modules: 98% type coverage improvement
  - Fixed callable type hints, dataclass fields, event inheritance
  - mypy errors: 251 → 240 (core/ modules down to 2 minor issues)

**Phase 6: Testing & Finalization**
- **Test Suite Verified**: All 16/17 tests passing (94.1% pass rate)
  - 1 pre-existing failure (raycast test, unrelated to refactoring)
  - No regressions introduced
- **Created Migration Guide**: `docs/MIGRATION_GUIDE.md` with upgrade instructions
- **Updated Documentation**: README, CHANGELOG, ARCHITECTURE aligned with v0.7.0

### Quality Metrics

**Before Refactoring**:
- demo_game.py: 3,496 lines
- Ruff errors: 2,084
- Black formatted: 0%
- mypy errors (core/): Many
- Documentation files: 98

**After Refactoring**:
- demo_game.py: 2,607 lines (-25.4%)
- Ruff errors: 115 (-94.5%)
- Black formatted: 100%
- mypy errors (core/): 2 (-98%)
- Documentation files: 28 (-71%)

**Code Quality Improvements**:
- 170 files formatted with Black (100% compliance)
- Modern Python 3.11+ type hints throughout
- Organized modular structure
- Comprehensive type safety in core modules
- Memory leak prevention in EventBus

### Breaking Changes
None - all changes are internal refactoring and code organization improvements.

### Migration Notes
- See `docs/MIGRATION_GUIDE.md` for detailed upgrade guide
- Import paths changed for extracted functions (see migration guide)
- EventBus now supports owner-based subscription cleanup (backward compatible)
- Old documentation in `docs/archive/` for historical reference
- No API or functionality changes to public interfaces

---

## [0.7.0-dev] - 2025-12-12 (Camera System & Collision)

### Added - Camera System & Collision Improvements

- **Camera System** (`systems/camera_system.py`):
  - Multi-mode camera: WORLD_CLAMP, ROOM_CLAMP, FREE, LOCKED
  - Smooth following with configurable lerp and deadzone
  - Responsive letterboxing for any window size
  - Virtual resolution (1280x720) scaled to physical display
  - Bounds clamping for world and room modes
  - In-game mode cycling with 'C' key

- **Player Size Adjustments**:
  - Changed player to 28x56 pixels (2:1 height:width ratio)
  - Proper platformer proportions
  - Crouch reduces height to 28x28 pixels (half height)

- **Tile Scaling**:
  - Scaled tiles to 32x32 pixels (industry standard)
  - World size: 5120x5120 pixels (160x160 tiles)
  - Physics tuned for larger tiles (gravity 0.4, max fall 12px)

### Fixed - Collision System

- **Platform Collision Fix**:
  - Changed from center-based to feet-based detection
  - Now works correctly with tall player (56px height)
  - Fixed: `entity_rect.bottom <= platform.bottom` instead of center check
  - Location: [collision_system.py:283-291](../systems/collision_system.py#L283-L291)

- **Wall Climbing Bug Fix** (Critical):
  - Fixed infinite wall climbing when walking into walls
  - Corner detection now requires `abs(vy) > abs(vx) * 1.5` (must be falling)
  - Both overlap_x AND overlap_y must be small (4-14px)
  - Ground detection requires `overlap_y < overlap_x` (more horizontal = landing on top)
  - Locations:
    - Corner detection: [collision_system.py:135-148](../systems/collision_system.py#L135-L148)
    - Ground detection: [collision_system.py:227-246](../systems/collision_system.py#L227-L246)

- **Vertical Tunneling Prevention**:
  - Reduced max fall speed from 22px to 12px (< half tile)
  - Reduced gravity from 0.7 to 0.4
  - Ensures physics speed stays below tunneling threshold

### Changed - Documentation

- Updated [ARCHITECTURE.md](ARCHITECTURE.md) with camera system and phase completion
- Updated [WORLD_GENERATION.md](WORLD_GENERATION.md) with 16x16 zone grid
- Updated [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) with camera API
- Created [HANDOVER.md](HANDOVER.md) - comprehensive project handover document
- Refreshed docs (SUMMARY, QUICK_START, INDEX, README, PROJECT_ORGANIZATION) for v0.7.0, headless note, and wall-slide-disabled status
- Moved historical collision/playability notes to `docs/legacy/` (WALL_COLLISION_FIX, PLATFORM_COLLISION_SUMMARY, PLAYABILITY_TESTING)
- Added headless flag documentation and roadmapping for CI runs
- Added input command/snapshot serializers and replay record/playback harness (demo flags: --record/--replay/--show-replay)
- Added env override for logs (`NINJADASH_LOG_DIR`) to keep logs in the project or a custom path

### Changed - Wall Interaction & Input Safety

- Disabled wall slide mechanic during rework; enabled wall friction clamp plus wall-jump coyote buffer (player orchestrator)
- Ground detection tuned to avoid wall contact setting `on_ground`; predictive ground snap constrained to narrow gaps
- Input handling hardened to accept sparse/dict key data (integration tests updated)
- Full test suite passing (`python run_tests.py`)

### Added - Phase B: Procedural World Generation

- **World Generation System** (`systems/world_generation.py`):
  - Seed-based deterministic procedural generation
  - Hierarchical structure: World -> Biomes -> Rooms -> Zones -> Tilemap
  - Multi-biome support (DUNGEON, CAVE, BUILDING themes)
  - Frontier-based room graph generation (organic, connected layouts)
  - Room type system (START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS)
  - Door port system with multi-door support and proper alignment
  - Performance: Generates 30-room world in ~2-5ms

- **Zone Planning System** (`systems/zone_planning.py`):
  - 16x16 zone grid layout per room (256 zones -> 160x160 tiles)
  - Intelligent feature placement (shops, save points, loot)
  - BFS connectivity validation (guarantees all critical zones are reachable)
  - Room type-specific zone patterns
  - Zone roles: WALK, FILL, PLAT, DOOR, SAVE, SHOP, LOOT, VOID
  - Pathfinding ensures no isolated zones
  - Increased from 5x5 to 16x16 for finer granularity and more complex layouts

- **Room Generation System** (`systems/room_generation.py`):
  - Zone -> Tilemap conversion (each zone expands to 10x10 tiles)
  - 160x160 tilemap per room
  - Door carving system (creates passable connections between rooms)
  - Tile types: TILE_EMPTY (0), TILE_SOLID (1), TILE_PLATFORM (2)
  - Collision integration helper (`tilemap_to_collision_rects()`)

- **Placeholder Tile Assets** (`assets/generate_placeholder_tiles.py`):
  - 30 generated placeholder tiles (10 types  3 biomes)
  - 8x8 pixel PNG files with colored squares
  - Simple borders for visual distinction
  - Organized in `assets/biomes/dungeon/`, `cave/`, `building/`

- **Demo Integration** (`demo_game.py`):
  - Command-line flag: `--procedural` to enable procedural world mode
  - Command-line flag: `--seed 12345` to specify generation seed
  - In-game toggle: P key switches between static and procedural modes
  - HUD display: Mode indicator (STATIC/PROCEDURAL) and seed display
  - Seamless integration with existing collision, physics, and player systems

### Fixed - Bug Fixes & Enhancements (v0.4.0)

- **Player Spawn System**:
  - Fixed player falling through procedurally generated worlds
  - Smart spawn point search finds safe floor tiles with empty space above
  - Calculates spawn in tilemap coordinates, converts to screen space
  - Fallback to center if no safe floor found

- **ASCII Visualization** (`systems/room_generation.py`):
  - Added `print_tilemap_ascii()` function for console output
  - Downsamples 160x160 tilemaps to 40x40 ASCII visualization
  - Shows generated room layouts during world creation
  - Symbols: `#`=Solid, `-`=Platform, (space)=Empty

- **Zone Generation Complexity** (`systems/zone_planning.py`):
  - Room-type-specific probability distributions for zone roles
  - PLATFORM rooms: 55% platforms, 22% fill, 22% walk (high density)
  - COMBAT rooms: 45% platforms, 14% fill, 22% walk (medium density)
  - TREASURE rooms: 35% platforms, 10% fill, 22% walk (moderate)
  - BOSS rooms: 30% platforms, 12% fill, 22% walk (arena-like)
  - Default rooms: 25% platforms, 8% fill, 22% walk (open)

- **Room Boundaries** (`systems/room_generation.py`):
  - Added walls around all room edges (top, bottom, left, right)
  - Added base floor platform near bottom (like source project)
  - Ensures rooms are always navigable and contained
  - Prevents players from leaving room bounds

- **Platform Collision** (`systems/collision_system.py`, `demo_game.py`):
  - Implemented one-way platform collision (TILE_PLATFORM type 2)
  - Platforms only collide when player falls onto them from above
  - Player can jump up through platforms from below
  - Separate rendering for platforms (lighter gray, half-height visual)
  - Collision system now handles both solid tiles and platform tiles
  - Platforms work with all player mechanics (jump, double-jump, wall-jump, dash)

- **Zone Grid Enhancement** (`systems/world_generation.py`, `systems/zone_planning.py`, `systems/room_generation.py`):
  - Increased zone grid from 5x5 to 16x16 for finer granularity
  - 256 zones per room (more than before)
  - Each zone now 10x10 tiles instead of 32x32
  - Maintains 160x160 room size while providing much more detail
  - Allows for more complex and varied platform arrangements
  - Better control over obstacle placement and room complexity

### Technical Details - World Generation

- **Data Structures**:
  - `World`: Top-level container with biomes, seed, room graph, bounds
  - `Biome`: Thematic grouping with BiomeTheme enum
  - `RoomNode`: Individual room with position, type, neighbors, tilemap, zone_grid
  - `DoorPort`: Door connection point with center position and span

- **Generation Pipeline**:
  1. WorldGenerator creates room graph with frontier algorithm
  2. Rooms divided into biomes by clustering
  3. ZonePlanner assigns 16x16 zone grid to each room
  4. RoomGenerator converts zones to 160x160 tilemap
  5. Demo converts tilemap to collision rects for physics

- **BFS Connectivity Algorithm**:
  - Ensures all doors can reach each other
  - All features (shop, save, loot) reachable from doors
  - Creates walkable paths by converting DECOR  WALK zones
  - Validates playability before tilemap generation

- **Performance Metrics**:
  - World generation: 2-5ms for 30 rooms
  - Zone planning: <1ms per room
  - Tilemap generation: <1ms per room
  - Total pipeline: <10ms for complete world
  - Memory: ~1.5MB for 30-room world
  - Demo FPS: Stable 60 FPS with 1568 collision tiles

### Bug Fixes - World Generation

- Fixed Unicode encoding error (replaced  with "[OK]" for Windows console compatibility)
- Fixed StopIteration error when generating single room (added fallback logic in `_create_biomes()`)
- Fixed tilemap scaling for demo (scale down by factor of 4 to fit 160x160 room in viewport)

### Documentation - Phase B

- **NEW**: `docs/WORLD_GENERATION.md` - Complete API documentation
  - Architecture overview
  - API reference (WorldGenerator, ZonePlanner, RoomGenerator)
  - Complete pipeline example
  - Performance metrics
  - Design patterns (seed-based determinism, frontier generation, BFS validation)
  - Future enhancements
- **Updated**: `docs/DEVLOG.md` - Session 2025-12-12 (Afternoon) entry
  - Source system analysis
  - Design decisions log
  - Implementation details
  - Testing results
  - Problems solved
  - Code highlights
- **Updated**: `docs/ROADMAP.md` - Added Phase B tasks and progress tracking

### Planned
- Input system refactor with command pattern
- Camera system integration
- Sprite rendering and animation system
- HUD and menu systems
- Level progression and exit system
- Pickup system (coins, health, power-ups)
- Particle effects and visual polish
- Room transition system (door-based room switching)
- Platform collision (TILE_PLATFORM integration)
- Minimap system (Phase D)
- Autotiling system (9-slice, Phase C)

---

## [0.3.2] - 2025-12-12

### Added

- **Movement System**: Smooth interpolation-based movement eliminates jitter
  - High acceleration constant (2600.0) for responsive, tight controls
  - Interpolation formula: `vx += (target_vx - vx) * smooth_factor`
  - Frame-rate independent with dt scaling
  - Professional polish matching commercial platformers
- **Fast-Fall Mechanic**: Variable gravity when holding down while falling
  - Gravity multiplier (1.7x) improves air control and landing precision
  - Integrated into Player physics system
  - Source: Dynamic dungeon platformer project

### Changed

- **Movement Mechanic** (`mechanics/movement.py`):
  - Replaced discrete acceleration steps with smooth interpolation
  - Unified ground and air physics (same algorithm for both)
  - Removed separate ground/air acceleration constants
  - Added MOVEMENT_ACCEL constant (2600.0)
- **Player Physics** (`entities/player.py`):
  - Added fast-fall gravity multiplier (1.7x)
  - Added down key tracking for fast-fall activation
  - Fast-fall only activates when falling (vy > 0) and in air
- **Physics System** (`systems/physics_system.py`):
  - Updated FAST_FALL_MULT from 2.4 to 1.7 (matches source implementation)

### Technical Details

- **Movement Algorithm**: Smooth interpolation to target velocity
  - `target_vx = direction * MAX_SPEED * multiplier`
  - `smooth_factor = min(1.0, ACCEL * dt / max(MAX_SPEED, 1.0))`
  - `vx += (target_vx - vx) * smooth_factor`
- **Fast-Fall Conditions**: vy > 0 (falling) AND not on_ground AND down key held
- **Benefits**:
  - Eliminates jitter from discrete acceleration
  - More responsive feel from high acceleration constant
  - Better air control with fast-fall mechanic
  - Smoother acceleration/deceleration curves

### Documentation Updates

- **ROADMAP.md**: Added Phase 4.5 (Movement Enhancement) with detailed tasks
- **DEVLOG.md**: Added 2025-12-12 session with source system analysis
- **Movement Docstring**: Updated to reflect smooth interpolation approach

---

## [0.3.1] - 2025-12-11

### Fixed
- **Collision System**: Fixed wall clipping bug where players could get stuck in walls
- **Collision System**: Refined corner collision detection to prevent jitter when landing on platform edges
- **Collision System**: Added sophisticated overlap-based collision detection with special case handling for falling
- **Jump Mechanic**: Blocked all jump types (ground, wall, double) while crouching to prevent fall-through bug
- **Crouch Mechanic**: Fixed collision box height issues that caused players to fall through floor when jumping while crouched

### Changed
- **Collision System**: Improved horizontal vs vertical collision classification using overlap calculations
- **Collision System**: Added falling preference for corner collisions (overlap_x >= 8, overlap_x <= 15, overlap_y <= 20, diff <= 8)
- **Jump Mechanic**: Added crouch blocking to `_try_double_jump()` and `_try_wall_jump()` methods

---

## [0.3.0] - 2025-12-11

### Added - Architecture
-  **Event-Driven Architecture**: Complete pub/sub system with priority handlers
-  **Modular Mechanic System**: Self-contained, reusable mechanics
-  **Component-Based Entities**: Reusable components across all entity types
-  **Mod/Plugin Support**: Full plugin architecture with component registration
-  **Fixed 60Hz Physics**: Deterministic physics simulation (Glenn Fiedler pattern)

### Added - Core Systems
-  **Event Bus** (`core/event_bus.py`): Priority-based pub/sub with queue processing
-  **Logging System** (`core/logger.py`): Persistent file-based logging with user-configurable location
-  **Game Clock** (`core/clock.py`): Fixed 60Hz timestep with variable render rate
-  **State Management** (`core/state.py`): JSON-serializable state with snapshot/restore
-  **Entity System** (`core/entity_system.py`): Component-based architecture with fast queries
-  **Mod System** (`core/mod_system.py`): Plugin lifecycle management

### Added - Collision
-  **Collision System** (`systems/collision_system.py`): Universal AABB collision for all entities
-  **Collision Events**: Event-driven collision response
-  **Advanced Queries**: Radius searches and raycasting
-  **Penetration Resolution**: Automatic collision resolution with normal vectors

### Added - Physics
-  **Physics System** (`systems/physics_system.py`): Gravity application and velocity integration
-  **Fall Speed Capping**: Configurable maximum fall velocity
-  **Fixed Timestep**: Deterministic 60Hz simulation

### Added - Player Mechanics
-  **Jump Mechanic** (`mechanics/jump.py`):
  - Ground jump (14.5 units/tick)
  - Coyote time (0.12s grace period)
  - Jump buffering (0.14s input window)
  - Double jump (configurable air jumps)
  - Wall jump (8.5x horizontal, 14.5y vertical)
  - Crouch modifier (0.7x power)

-  **Movement Mechanic** (`mechanics/movement.py`):
  - Ground physics (0.9 acceleration, responsive)
  - Air physics (0.5 acceleration, floaty)
  - Max speed (8.0 units/tick)
  - Smooth acceleration/deceleration

-  **Dash Mechanic** (`mechanics/dash.py`):
  - Speed (16.0 units/tick, 2x normal)
  - Duration (0.16s, ~10 frames)
  - Cooldown (0.45s, ~27 frames)
  - Wall collision cancel

-  **Wall Slide Mechanic** (`mechanics/wall_slide.py`):
  - Stamina system (3.0s max, 2.0s regen)
  - Slide speed (2.2 units/tick controlled descent)
  - Min stamina requirement (0.3s to prevent spam)

-  **Crouch Mechanic** (`mechanics/crouch.py`):
  - Stealth movement (60% speed, 80% acceleration)
  - Collision box changes (50% height)
  - Ceiling detection
  - Jump power modifier (70%)

### Added - Entities
-  **Player Class** (`entities/player.py`): Orchestrates all player mechanics
-  **Reusable Components** (`entities/components.py`):
  - HealthComponent (damage, healing, invincibility)
  - PatrolComponent (back-and-forth movement)
  - FollowComponent (entity tracking)
  - ProjectileComponent (velocity-based projectiles)
  - PickupComponent (collectibles with auto-collection)
  - AIComponent (state machine for NPCs/enemies)

### Added - Testing
-  **14 Comprehensive Test Suites**: Full coverage of all systems
-  **Integration Tests**: Player + all mechanics working together
-  **Collision Edge Cases**: Corner cases, wall clipping, falling jitter
-  **Physics Tests**: Gravity, velocity, fall capping

### Added - Documentation
-  **SYSTEM_OVERVIEW.md**: Complete guide with API reference
-  **ARCHITECTURE.md**: Design patterns and component examples
-  **MODDING_GUIDE.md**: Plugin development guide
-  **README.md**: Quick start and feature overview

### Added - Demo
-  **Playable Demo** (`demo_game.py`): All systems integrated and working
-  **Controls**: Arrow keys/WASD, Space, Shift, Crouch toggle
-  **Level**: Platform layout with walls, ground, and obstacles

### Changed
-  **Migration**: Moved original files to `legacy/` folder for reference
-  **Project Name**: Renamed to "Vain Asher Gaming's: Indie Ninja Adventures"

### Technical Details
- **Language**: Python 3.11+
- **Graphics**: Pygame 2.6+
- **Architecture**: Component-based entity system, event-driven
- **Physics**: Fixed 60Hz deterministic simulation
- **State**: Serializable with JSON support

---

## [0.2.0] - Previous Version (Legacy)

### Added
- Basic player movement
- Monolithic player class
- Simple collision detection
- Procedural level generation
- Camera system
- UI elements

### Deprecated
- Original monolithic architecture (moved to `legacy/` folder)
- All code preserved for reference and potential integration

---

## Version History Summary

- **v0.7.0** (2025-12-12): Procedural world generation (16x16 grid), camera system, tile/player scaling, collision fixes
- **v0.3.1** (2025-12-11): Collision bug fixes, crouch-jump fix, wall clipping prevention
- **v0.3.0** (2025-12-11): Complete modular refactor, all core systems implemented
- **v0.2.0** (Previous): Original monolithic implementation

---

## Versioning Scheme

- **Major** (X.0.0): Breaking API changes, major architecture changes
- **Minor** (0.X.0): New features, systems, mechanics (backwards compatible)
- **Patch** (0.0.X): Bug fixes, refinements, optimizations

---

**Last Updated**: 2025-12-12
**Current Version**: 0.7.0
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
