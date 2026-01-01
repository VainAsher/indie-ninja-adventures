# Vain Asher Gaming's: Indie Ninja Adventures
**A Modular, Event-Driven Platformer Engine**

> *Fast-paced, skill-based 2D platformer with tight controls, deep mechanics, and full mod support.*

---

## Current Status: **v0.7.0 (Campaign Mode + Story System)**

A feature-complete platformer with campaign mode, story system, enemy AI, dialogue, trading, and 25 missions across 5 zones. All foundational systems are implemented and tested. The game includes procedural world generation, multiple game modes (Campaign, Arcade, Sandbox), and comprehensive gameplay systems.

**📋 For a complete feature breakdown, see [FEATURES_V0_7.md](docs/FEATURES_V0_7.md)**

### ⚠️ Known Gap: Boss AI

**IMPORTANT**: While the boss system framework exists, **boss AI is not implemented**. Boss rooms generate but have no functional boss encounters. This is documented in ROADMAP.md Phase 8 (220 hour estimate). See [FEATURES_V0_7.md](docs/FEATURES_V0_7.md#boss-system-framework-only---not-implemented) for details.

### What's Working

- **Core Systems**: Event bus, logging, fixed timestep, state management, entity system, mod support
- **Physics & Collision**: Gravity, velocity integration, AABB collision with advanced edge case handling (11+ fixes)
- **Player Mechanics**: Movement (smooth interpolation), jump (ground/double/wall/coyote/buffer), dash, crouch (stealth), fast-fall, combat (3-hit combo, air attacks), special abilities (shuriken, teleport, ninjutsu)
- **Enemy System**: 5 enemy types (SLIME, BAT, SKELETON, ORC, DEMON) with AI behaviors (patrol, chase, ranged, flying, static), spawning, health, loot drops
- **World Generation**: Seed-based procedural generation with hierarchical structure (World → Biomes → Rooms → 16x16 Zones → 160x160 Tilemap), BFS connectivity validation
- **Campaign Mode**: 25 missions across 5 zones (Forest, Town, Caves, Castle, Sewers) with story progression, dialogue, and hub system
- **Story & Dialogue**: Story manager with multiple endings, NPC dialogue system with branching conversations, cutscene framework
- **Trading & Inventory**: 3-tier shop system, item management, loot system with rarity tiers, coin-based economy
- **Portal System**: Hub-based fast-travel, mission portals, shop access
- **Game Modes**: Campaign (story-driven), Arcade (endless procedural), Sandbox (free exploration)
- **Camera System**: Multi-mode camera (world clamp, room clamp, free, locked) with smoothing and letterboxing
- **UI Systems**: Menus (main/pause/settings/mode selection), HUD (health/stamina/objectives), minimap, dialogue UI, shop UI, victory/death screens
- **Testing**: 46 test files with unit/integration/edge case coverage, world-gen validation, playability testing
- **Documentation**: Architecture guide, modding guide, world generation guide, complete feature list (v0.7.0)
- **Build System**: PyInstaller configs for dev/testing/production builds with CI/CD pipeline

### Latest Features (v0.7.0) - New Since v0.4.0-dev

**Major Additions** (from v0.4.0-dev to v0.7.0):
- **Campaign Mode**: Complete story-driven mode with 25 missions across 5 zones, hub system, mission progression
- **Enemy System**: Full enemy AI with 5 enemy types, patrol/chase/ranged behaviors, spawning, health, loot drops
- **Story System**: Story manager with character arcs, multiple endings (Redemption/Hollow/Balance), cutscene framework
- **Dialogue System**: NPC conversations with branching choices, dialogue UI, quest givers, shop keepers
- **Trading System**: 3-tier shops (Basic/Advanced/Master), inventory management, item purchasing, coin economy
- **Portal System**: Hub fast-travel, mission portals, shop access portals
- **Combat System**: 3-hit combo, air attacks, dash attack, special abilities (shuriken, teleport, ninjutsu)
- **Companion System**: Orbital companion orbs with unique abilities
- **Advanced UI**: Shop UI, inventory browser, mission selector, dialogue boxes, victory/death screens, objective tracking
- **Loot System**: Rarity tiers (Common→Legendary), enemy drops, treasure chests, pickup notifications

**Infrastructure** (v0.7.0):
- **CI/CD Pipeline**: GitHub Actions with automated testing, linting, formatting, type checking
- **Code Quality**: Black formatter, Ruff linter, MyPy type checking, pre-commit hooks
- **Modern Packaging**: pyproject.toml, proper Python package structure
- **46 Test Files**: Comprehensive test coverage including edge cases and playability validation
- **Build System**: PyInstaller configs for dev/testing/production with automated builds

**From v0.4.0-dev** (Still Working):
- Procedural world generation (seed-based, hierarchical, BFS connectivity)
- Multi-mode camera system
- Advanced physics & collision (11+ edge case fixes)
- Player mechanics (movement, jump, dash, crouch)

###  Previous Features (v0.3.2)

- **Smooth Movement**: Interpolation-based movement eliminates jitter, feels responsive and polished
- **Fast-Fall Mechanic**: Hold down while falling for improved air control (1.7x gravity)
- **Enhanced Physics**: High acceleration constant (2600.0) for tight, responsive controls
- **Professional Feel**: Movement quality matches commercial platformers (Celeste, Hollow Knight)

###  Previous Fixes (v0.3.1)

- Fixed wall clipping bug (players getting stuck in walls)
- Fixed crouch-jump exploit (falling through floor)
- Fixed player going off-screen (wall collision detection)
- Fixed falling jitter (corner collision handling)
- Refined collision detection with overlap-based classification

###  Demo Ready

- **Demo Game**: Playable demo with all systems integrated ([demo_game.py](demo_game.py))
- **Physics System**: Gravity, velocity integration, fall speed capping
- **Game Loop**: All systems working together

---

##  Quick Start

### Running the Demo

```bash
# Play the demo game (static test level)
python demo_game.py

# Play with procedural world generation
python demo_game.py --procedural

# Run headless (CI/servers)
python demo_game.py --headless --procedural --seed 12345

# Use specific seed for reproducible world
python demo_game.py --procedural --seed 12345

# Controls:
# - Arrow keys / WASD: Move
# - Space / W / Up: Jump
# - Shift: Dash
# - S / Down: Crouch (toggle)
# - P: Toggle static/procedural mode
# - ESC: Quit
```

### Running Tests

```bash
# Run all tests (recommended)
python run_tests.py

# Run specific test categories
python run_tests.py --unit             # Unit tests only
python run_tests.py --integration      # Integration tests only
python run_tests.py --edge             # Edge case tests only

# Run with verbose output
python run_tests.py --verbose

# Run individual test files
python tests/unit/test_core_infrastructure.py
python tests/integration/test_player_integration.py
python tests/edge_cases/test_wall_clip.py

# Expected:  ALL TESTS PASSED!
```

Headless tip (CI/servers): set `SDL_VIDEODRIVER=dummy` before running tests to avoid opening a window.

See [tests/README.md](tests/README.md) for detailed test documentation.

### Creating a Player

```python
from entities.player import Player
from core import EventBus, GameLogger

# Initialize
bus = EventBus()
logger = GameLogger()

# Create player
player = Player(
    player_id=0,
    spawn_x=100,
    spawn_y=100,
    event_bus=bus,
    logger_factory=logger,
    feature_flags={
        "double_jump": True,
        "wall_jump": True,
        "dash": True,
        "crouch": True
    }
)

# Game loop
while running:
    keys = pygame.key.get_pressed()
    player.process_input(keys)

    clock.tick()  # Emits TickEvent
    bus.process()
```

---

##  Project Structure

```
vain_asher_indie_ninja_adventures_v0_3/
 core/                      # Engine infrastructure
    event_bus.py          # Pub/sub event system
    logger.py             # Persistent logging
    clock.py              # Fixed 60Hz timestep
    state.py              # Serializable state
    entity_system.py      # Component-based entities
    mod_system.py         # Plugin architecture

 systems/                   # Game systems
    physics_system.py     # Gravity & velocity
    collision_system.py   # Universal collision
    world_generation.py   # Procedural world generation
    zone_planning.py      # Room layout planning
    room_generation.py    # Tilemap generation
    camera_system.py      # Multi-mode camera

 mechanics/                 # Player mechanics
    jump.py               # All jump types
    movement.py           # Ground/air movement
    dash.py               # Dash with cooldown
    wall_slide.py         # Legacy wall slide (disabled during wall rework)
    crouch.py             # Stealth movement

 entities/                  # Game entities
    player.py             # Player orchestrator
    components.py         # Reusable components

 config/                    # Configuration
    settings.py           # Persistent settings system

 network/                   # Network & replay
    commands.py           # Input command pattern
    snapshots.py          # State snapshots
    input_pipeline.py     # Record/replay system

 rendering/                 # Rendering systems
    sprite_manager.py     # Sprite loading
    particles.py          # Particle effects
    hud.py                # HUD rendering

 user_data/                 # User data (project-local)
    logs/                 # Session logs
    replays/              # Recorded replays
    saves/                # Save files (future)
    settings/             # Persistent settings

 tests/                     # Test suites (organized)
    unit/                 # Unit tests (5 files)
    integration/          # Integration tests (2 files)
    edge_cases/           # Edge case tests (8 files)
    world_gen/            # World generation tests
    README.md             # Test documentation

 docs/                      # All documentation
    QUICK_START.md        # 5-minute quick start
    SYSTEM_OVERVIEW.md    # Complete API reference
    ARCHITECTURE.md       # Design patterns
    MODDING_GUIDE.md      # Plugin development
    WORLD_GENERATION.md   # Procedural generation guide
    CHANGELOG.md          # Version history (LIVE)
    DEVLOG.md             # Development log (LIVE)
    ROADMAP.md            # Future plans (LIVE)
    INDEX.md              # Documentation index
    PROJECT_ORGANIZATION.md  # Organization guide
    templates/            # Issue & report templates
       BUG_REPORT.md
       PLAYTEST_REPORT.md
       ISSUE_TEMPLATE.md
    README.md             # Docs guide

 legacy/                    # Archived original files
    main.py, player.py    # Original monolithic code
    camera.py, level_gen.py  # Can be integrated

 run_tests.py               # Test runner script
 demo_game.py               # Playable demo
 README.md                  # This file (project overview)
```

---

##  Features

### Player Mechanics

**Movement**
- Ground physics: High acceleration (0.9), responsive
- Air physics: Lower acceleration (0.5), floaty
- Speed cap: 8.0 units/tick
- Smooth acceleration/deceleration

**Jump System**
- Ground jump: 14.5 units/tick power
- Coyote time: 0.12s grace period
- Jump buffering: 0.14s input window
- Double jump: Air jump (configurable)
- Wall jump: Horizontal boost (8.5x, 14.5y)
- Crouch modifier: 0.7x power

**Dash**
- Speed: 16.0 units/tick (double normal)
- Duration: 0.16s (~10 frames)
- Cooldown: 0.45s (~27 frames)
- Cancels on wall collision

**Wall Interaction (current)**
- Wall slide is disabled while we rework interaction
- Light wall friction clamps descent near walls (vy damped, clamped to 5.0)
- Wall jump remains enabled with a short wall-coyote buffer

**Crouch**
- Stealth movement: 60% speed, 80% accel
- Height: 50% (collision box changes)
- Jump: 70% power when crouched
- Ceiling detection (can't stand if blocked)

### Architecture

**Event-Driven**
- Pub/sub event bus with priority handlers
- Systems communicate via events (no coupling)
- Easy to add new systems

**Modular Mechanics**
- Each mechanic is self-contained
- Reusable across players/NPCs/enemies
- Can be enabled/disabled via feature flags

**Network-Ready**
- Fixed 60Hz deterministic physics
- Serializable state (JSON)
- Replay-friendly

**Extensible**
- Component-based entities
- Mod system with plugin architecture
- Easy to add new mechanics

---

##  Test Results

```
[PASS] Core Infrastructure Tests
  - Event bus (subscribe, emit, priority)
  - Logger (persistent storage, levels)
  - Clock (fixed timestep, interpolation)
  - State (serialization, history)

[PASS] Collision System Tests
  - Tile collision detection
  - Penetration resolution
  - Collision events
  - Radius queries, raycasting

[PASS] Jump Mechanic Tests
  - Ground jump, coyote time
  - Jump buffering
  - Double jump, wall jump
  - Crouch modifier
  - Collision response

[PASS] Player Integration Tests
  - Basic movement
  - Crouch + movement interaction
  - Dash mechanics
  - Wall contact/grounding regression (no sticking, proper snap)
  - Full gameplay scenario

ALL TESTS PASSED 
```

---

##  Documentation

All documentation is organized in the [docs/](docs/) directory:

### Quick Links
- **[docs/QUICK_START.md](docs/QUICK_START.md)** -  **START HERE** - 5-minute quick start guide
- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index and navigation

### Technical Documentation
- **[docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md)** - Complete API reference
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Design patterns and best practices
- **[docs/MODDING_GUIDE.md](docs/MODDING_GUIDE.md)** - Plugin development guide

### Development Documentation (Living Documents)
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Version history (updated each release)
- **[docs/DEVLOG.md](docs/DEVLOG.md)** - Daily development log (updated during dev)
- **[docs/ROADMAP.md](docs/ROADMAP.md)** - Future plans and milestones (updated monthly)
- **[docs/PROJECT_ORGANIZATION.md](docs/PROJECT_ORGANIZATION.md)** - Project structure guide

### Templates
- **[docs/templates/](docs/templates/)** - Bug reports, playtest feedback, feature requests

---

##  Roadmap

### Phase 1: Core Infrastructure  COMPLETE
- [x] Event bus system
- [x] Persistent logging
- [x] Fixed timestep clock
- [x] State management
- [x] Entity system
- [x] Mod system

### Phase 2: Collision System  COMPLETE
- [x] AABB collision detection
- [x] Penetration resolution
- [x] Collision events
- [x] Advanced queries (radius, raycast)

### Phase 3: Player Mechanics  COMPLETE
- [x] Jump mechanic (all types)
- [x] Movement mechanic
- [x] Dash mechanic
- [ ] Wall slide mechanic (disabled pending rework; wall friction fallback active)
- [x] Crouch mechanic (stealth)
- [x] Player orchestrator class

### Phase 4: Physics & Game Loop  COMPLETE
- [x] Physics system (gravity, integration)
- [x] Demo game (wire all systems)
 - [x] Input system (command pattern + record/replay pipeline)
- [?] Integrate level generation (baseline hooked up; additional complexity planned later)
- [x] Integrate camera system

### Phase 5: Rendering & UI
- [ ] Sprite rendering
- [ ] Camera interpolation
- [ ] HUD system
- [ ] Menu system
- [ ] Settings UI (log location, controls)

### Phase 6: Gameplay
- [ ] Pickup system (coins, health, lives)
- [ ] Hazards (spikes, pits)
- [ ] Exit/goal system
- [ ] Level progression
- [ ] Score tracking

### Phase 7: Polish
- [ ] Particle effects
- [ ] Sound system
- [ ] Animation system
- [ ] Screen shake, juice

### Phase 8: Network (Future)
- [ ] Client/server architecture
- [ ] State synchronization
- [ ] Client prediction
- [ ] Server reconciliation

---

##  Ideas & Future Features

### Gameplay
- **Grappling hook**: Swing mechanic with physics
- **Time slow**: Bullet-time for precise movement
- **Ghost replay**: Record runs, race against ghosts
- **Level editor**: In-game level creation
- **Daily challenges**: Procedural levels with leaderboards

### Mechanics
- **Slide**: Fast ground slide after dash
- **Ledge grab**: Hang from ledges
- **Ground pound**: Slam down from air
- **Air dash**: Horizontal burst in mid-air
- **Momentum conservation**: Speed carries between mechanics

### Systems
- **Save system**: Save/load game state
- **Replay system**: Record and playback runs
- **Achievement system**: Track player accomplishments
- **Statistics**: Track jumps, deaths, time, etc.
- **Accessibility**: Colorblind modes, control remapping

### Multiplayer
- **Co-op**: 2-4 player cooperative
- **Versus**: Race mode, tag mode
- **Level sharing**: Upload/download custom levels
- **Spectator mode**: Watch other players

---

##  Changelog

### v0.3.0 - Complete Modular Refactor (2025-12-11)

**Architecture**
-  Complete event-driven architecture
-  Modular mechanic system
-  Component-based entities
-  Mod/plugin support
-  Fixed 60Hz deterministic physics

**Core Systems**
-  Event bus with priority handlers
-  Persistent logging with user-configurable location
-  Game clock with fixed timestep
-  Serializable state management
-  Entity system with components

**Collision**
-  Universal collision system for all entities
-  Collision events
-  Radius queries and raycasting

**Player Mechanics**
-  Jump mechanic (ground, double, wall, coyote, buffer)
-  Movement mechanic (ground/air physics)
-  Dash mechanic (cooldown, wall cancel)
-  Wall slide mechanic (stamina system) — implemented in v0.3.0, **disabled during current wall rework (v0.7.0)**
-  Crouch mechanic (stealth movement)

**Testing**
-  Comprehensive test coverage
-  Integration tests for all systems
-  Full gameplay scenario tests

**Documentation**
-  SYSTEM_OVERVIEW.md - Complete guide
-  ARCHITECTURE.md - Design patterns
-  MODDING_GUIDE.md - Plugin development

**Migration**
-  Moved legacy files to legacy/ folder
-  Original code preserved for reference

### v0.2.0 - Original Implementation
- Basic player movement
- Monolithic player class
- Simple collision
- Level generation
- Camera system

---

##  Development Log

### 2025-12-11: Modular Architecture Complete

**Morning Session**
- Implemented core infrastructure (event bus, logger, clock, state)
- Created entity system and mod support
- Comprehensive testing for core systems

**Afternoon Session**
- Implemented collision system with events
- Created jump mechanic (all types unified)
- Jump tests passing (ground, coyote, double, wall, crouch)

**Evening Session**
- Implemented movement, dash, wall slide, crouch mechanics
- Enhanced wall slide with stamina system (now disabled while wall interaction is reworked)
- Enhanced crouch with stealth characteristics
- Created Player orchestrator class
- Full integration tests passing
- Comprehensive documentation
- Legacy migration complete

**Late Session**
- Implemented physics system (gravity, velocity integration, fall speed capping)
- Created comprehensive physics tests
- Built playable demo game integrating all systems
- Fixed player input handling for pygame compatibility
- All systems working together in game loop

**Status**: All core systems complete, tested, and integrated. Playable demo available. Ready for advanced features (level generation, camera, rendering enhancements).

**Next Session Goals**:
1. Integrate level generation from legacy
2. Integrate camera system from legacy
3. Enhanced rendering (sprites, animations)
4. Input system refactor (command pattern)
5. Additional gameplay features

---

##  Contributing

This is a personal project demonstrating modular game architecture. Feel free to fork and experiment!

### Code Style
- Type hints for all functions
- Docstrings for all classes/methods
- Comprehensive logging
- Test coverage for new features

### Adding a New Mechanic

1. Create `mechanics/my_mechanic.py` inheriting from `BaseMechanic`
2. Implement `on_tick()`, `can_activate()`, `reset()`
3. Add to `mechanics/__init__.py`
4. Create test file in `tests/unit/`
5. Update documentation

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed patterns.

---

##  License

MIT License - See LICENSE file for details

---

##  Credits

Built with:
- Python 3.11+
- Pygame 2.6+
- Love for modular architecture

Inspired by:
- Celeste (movement mechanics)
- Hollow Knight (responsive controls)
- Super Meat Boy (tight platforming)

---

##  Support

- **Issues**: Report bugs via GitHub issues
- **Documentation**: See docs/ folder
- **Logs**: Check `user_data/logs/` for debugging

---

**Last Updated**: 2025-12-12
**Version**: 0.7.0
**Status**: Procedural World Generation - Playability Testing Framework
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
