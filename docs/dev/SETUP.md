# Developer Setup Guide

Everything needed to run, test, and build Indie Ninja Adventures from source.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Exactly 3.11 recommended (CI uses 3.11) |
| Git | Any | |
| Windows | 10/11 | Required for building `.exe` files |

Linux/macOS: can run and test, but cannot build the Windows `.exe`.

---

## Setup

```bash
# 1. Clone
git clone https://github.com/VainAsher/indie-ninja-adventures.git
cd indie-ninja-adventures

# 2. Create virtual environment
python -m venv .venv

# 3. Activate (Windows)
.venv\Scripts\activate

# 4. Install with dev dependencies
pip install -e ".[dev]"

# 5. Install pre-commit hooks
pre-commit install
```

---

## Running the Game

```bash
# Standard launch
python demo_game.py

# Procedural world generation
python demo_game.py --procedural

# Specific seed
python demo_game.py --procedural --seed 42

# Headless (no window, for CI)
python demo_game.py --headless --procedural

# Multiplayer: host
python demo_game.py --host 7777

# Multiplayer: join
python demo_game.py --connect 127.0.0.1:7777

# Record session
python demo_game.py --record

# Replay a session
python demo_game.py --replay user_data/replays/my_session.json
```

---

## Running Tests

```bash
# Full test suite (recommended)
python run_tests.py

# By category
python run_tests.py --unit          # Unit tests
python run_tests.py --integration   # Integration tests
python run_tests.py --edge          # Edge cases

# Headless (required for CI, avoids opening a window)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python run_tests.py

# Direct pytest
pytest tests/ -v
pytest tests/unit/ -v
pytest tests/edge_cases/ -v
```

Expected output: `ALL TESTS PASSED` (46 test files).

---

## Code Quality

```bash
# Format with Black
black .

# Lint with Ruff
ruff check .

# Type check with MyPy (informational — gradual typing)
mypy core/ systems/ entities/

# Run all pre-commit checks
pre-commit run --all-files
```

Pre-commit runs automatically on `git commit`. CI enforces Black and critical Ruff errors.

---

## Building Executables

Requires Windows. PyInstaller is used for single-file `.exe` builds.

```bash
# Build everything
python build/build.py --all

# Production game exe only
python build/build.py --production

# Launcher exe only
python build/build.py --launcher

# Testing build (multi-file, with debug overlay)
python build/build.py --testing
```

Output in `build/dist/`:
- `ninja_dash.exe` — production game
- `ninja_dash_launcher.exe` — launcher
- `ninja_dash_testing/` — testing build with `_internal/`

---

## Build Modes

The game reads `version.json` at startup to determine its build mode:

| Mode | `version.json` `"build"` | Console | Dev tools | Auto-record |
|------|--------------------------|---------|-----------|-------------|
| Production | `"production"` | Hidden | Off | Off |
| Testing | `"testing"` | Visible | On | On |
| Dev | `"dev"` | Visible | On | Off |

Change `"build"` in `version.json` to switch mode without rebuilding.

---

## Project Layout

```
demo_game.py          Main entry point (~4500 lines)
version.json          Single version source of truth
pyproject.toml        Package config, tool settings
run_tests.py          Test runner

core/                 Engine: event bus, ECS, clock, state, logger, mod system
systems/              Game systems: collision, physics, world gen, camera, save
mechanics/            Player mechanics: jump, dash, crouch, combat, shuriken
entities/             Entities: player, enemies, bosses, NPCs, remote players
game/                 Game logic: campaign, missions, story, dialogue, trading
network/              Networking: server, client, input pipeline, protocol
rendering/            Rendering: animation, sprites, HUD, minimap, particles
ui/                   UI: menus, shop UI, inventory UI, dialogue UI
audio/                Audio: AudioManager, SFX events
config/               Config: build_config, physics_constants, settings
launcher/             Launcher: tkinter app with auto-update
build/                PyInstaller specs + build scripts
tests/                Test suites (unit, integration, edge cases)
assets/               Sprites, tilesets, audio, splash
docs/                 Documentation
user_data/            Runtime data: logs, saves, replays (gitignored)
```

---

## VSCode Setup (Recommended)

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true
}
```

---

## Troubleshooting

**`pygame` import fails:**
```bash
pip install pygame==2.6.1
```

**`SDL_VIDEODRIVER: dummy` not working on Windows:**
Use `set SDL_VIDEODRIVER=dummy` in Command Prompt, or pass via Python:
```bash
python -c "import os; os.environ['SDL_VIDEODRIVER']='dummy'; import demo_game"
```

**Tests fail with "no display" errors:**
Run with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.

**PyInstaller build fails:**
Make sure you're in the `build/` directory when running `pyinstaller`:
```bash
cd build
pyinstaller --clean ninja_dash_production.spec
```
