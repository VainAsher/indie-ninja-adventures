# Quick Start Guide
**Vain Asher Gaming's: Indie Ninja Adventures**

> Get up and running in under 5 minutes!

---

## Play the Demo

```bash
python demo_game.py
```

**Controls**:
- **Move**: Arrow keys or WASD
- **Jump**: Space / W / Up Arrow
- **Dash**: Shift
- **Crouch**: S / Down Arrow (toggle)
- **Toggle procedural**: P
- **Cycle camera**: C
- **Quit**: ESC

Procedural mode:
```bash
python demo_game.py --procedural --seed 12345
```

Headless/CI mode:
```bash
SDL_VIDEODRIVER=dummy python demo_game.py --headless --procedural --seed 12345
```

Record & replay:
```bash
# Record a run
python demo_game.py --procedural --seed 12345 --record run1.json

# Replay headless
python demo_game.py --replay run1.json

# Replay with a window
python demo_game.py --replay run1.json --show-replay
```

Logs:
- Default: `%APPDATA%/NinjaDash/logs` (platform-specific)
- Override to project directory: set env `NINJADASH_LOG_DIR=.` before running

---

## Run Tests

```bash
# Run all tests
python run_tests.py

# Run specific categories
python run_tests.py --unit          # Unit tests only
python run_tests.py --integration   # Integration tests only
python run_tests.py --edge          # Edge case tests only

# Verbose output
python run_tests.py --verbose
```

---

## Documentation

### First Time Here?
1. Read [README.md](README.md) - Project overview
2. Play the demo (see above)
3. Browse [docs/INDEX.md](docs/INDEX.md) - Documentation hub

### Want to Understand the Code?
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Complete API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - Design patterns
- [docs/DEVLOG.md](docs/DEVLOG.md) - Development decisions

### Want to Create a Mod?
- [MODDING_GUIDE.md](MODDING_GUIDE.md) - Plugin development guide

### Want to Report a Bug?
- Use [docs/templates/BUG_REPORT.md](docs/templates/BUG_REPORT.md)

### Want to See What's Coming?
- [docs/ROADMAP.md](docs/ROADMAP.md) - Future plans
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - Version history

---

## Project Structure

```
VainAsherGamings_IndieNinjaAdventures_v0_3/
  core/              # Engine (event bus, logger, clock, state)
  systems/           # Game systems (physics, collision, camera, world gen)
  mechanics/         # Player mechanics (jump, dash, crouch, etc.)
  entities/          # Game entities (player, components)
  rendering/         # Rendering helpers (sprites, particles, HUD)
  tests/             # Organized test suite
    unit/            # Component tests
    integration/     # System tests
    edge_cases/      # Regression tests
    playability/     # Playability validation helpers
  docs/              # Living documentation
  demo_game.py       # Demo entry point
  run_tests.py       # Test runner
```

---

## Common Tasks

### Create a Simple Player

```python
from entities.player import Player
from core import EventBus, GameLogger

bus = EventBus()
logger = GameLogger()

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
```

### Run a Specific Test

```bash
# Individual test file
python tests/unit/test_jump_mechanic.py
python tests/edge_cases/test_wall_clip.py
```

---

## Current Status

**Version**: 0.7.0  
**Status**: Core, collision, camera, world generation complete; wall slide disabled (wall friction + wall-jump buffer); rendering/UI polish in progress

--- 

**Created**: 2025-12-11  
**Updated**: 2025-12-12  
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
