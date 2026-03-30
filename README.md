# Indie Ninja Adventures

**Vain Asher Gaming** — A fast-paced 1–4 player Metroidvania platformer with tight controls, authoritative multiplayer, input recording/replay, and a custom launcher.

> Version: **v0.8.0** | Status: Beta | Platform: Windows | Engine: Python 3.11 + Pygame 2.6

---

## Repository Architecture

This project spans four repositories:

```
VainAsher/indie-ninja-launcher   (PUBLIC)  — Launcher .exe, player guides, GitHub Pages
VainAsher/indie-ninja-adventures (PRIVATE) — Game source, CI/CD, build pipeline  ← you are here
VainAsher/indie-ninja-feedback   (PUBLIC)  — Bug reports, feature requests, feedback
VainAsher/indie-ninja-pipeline   (PRIVATE) — Dev triage, sprint planning, release management
```

**Players**: Download from the [launcher repo releases](https://github.com/VainAsher/indie-ninja-launcher/releases). Report issues at the [feedback repo](https://github.com/VainAsher/indie-ninja-feedback/issues/new/choose).

---

## What's in v0.8.0

| System | Status |
|--------|--------|
| Core engine (event bus, ECS, fixed 60Hz timestep) | Done |
| Physics + collision (AABB, 11+ edge case fixes) | Done |
| Player mechanics (move/jump/dash/crouch/wall/combat/shuriken/teleport/ninjutsu) | Done |
| Campaign mode (30 missions, 6 regions, ability gates, NPCs, 3 endings) | Done |
| Procedural world generation (7 biomes, seed-based, BFS-validated) | Done |
| Enemy AI (5+ types: patrol, chase, ranged, flying, static) | Done |
| Hazards, loot, trading (3-tier shops), inventory | Done |
| Story, dialogue (branching), cutscenes | Done |
| Save system (JSON + HMAC integrity) | Done |
| Animation state machine + autotiling | Done |
| Audio SFX (12 events hooked) | Done |
| HUD, minimap, menus, victory/death screens | Done |
| 1–4 player multiplayer (Phase 3 authoritative server, 60Hz) | Done |
| Input recording + deterministic replay | Done |
| Custom launcher (auto-update, multiplayer lobby, bug reporting) | Done |
| Boss framework (6 types wired) | Framework only — AI not implemented |
| Music / BGM | Not started |
| Gamepad support | Not started |

**Known gap**: Boss AI — framework and 6 boss mission slots exist, but no AI patterns or phase transitions. See [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Quick Start (Dev)

**Prerequisites**: Python 3.11+, Git, Windows (for builds)

```bash
git clone https://github.com/VainAsher/indie-ninja-adventures.git
cd indie-ninja-adventures
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

```bash
# Run the game
python demo_game.py

# Multiplayer (host)
python demo_game.py --host 7777

# Multiplayer (join)
python demo_game.py --connect 127.0.0.1:7777

# Replay a recorded session
python demo_game.py --replay user_data/replays/my_session.json

# Run all tests (headless)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python run_tests.py

# Build .exe
python build/build.py --production
```

Full setup guide: [docs/dev/SETUP.md](docs/dev/SETUP.md)

---

## Project Structure

```
indie-ninja-adventures/
├── core/           Event bus, ECS, clock, state, logger, mod system
├── systems/        Collision, physics, world gen, camera, save, autotiling
├── mechanics/      Jump, movement, dash, crouch, combat, shuriken, teleport
├── entities/       Player, enemies, bosses, NPCs, remote players, hazards, pickups
├── game/           Campaign, missions, story, dialogue, hub, trading, inventory
├── network/        Authoritative server, client, input pipeline, snapshots, protocol
├── rendering/      Animation, sprites, HUD, minimap, particles, enemy renderer
├── ui/             Menus, shop, inventory UI, dialogue UI, tutorial
├── audio/          AudioManager, SFX events
├── config/         Build config, physics constants, settings
├── launcher/       Standalone tkinter launcher (auto-update, multiplayer, reporting)
├── build/          PyInstaller specs + build scripts
├── tests/          46 test files (unit, integration, edge cases)
├── docs/           Documentation (see below)
├── assets/         Sprites, tilesets, splash
├── demo_game.py    Main entry point (~4500 lines)
├── version.json    Single version source of truth
└── pyproject.toml  Package config, tool settings
```

---

## Documentation

### Workflow
- [docs/workflow/BRANCHING.md](docs/workflow/BRANCHING.md) — Git flow model (main/develop/feature/hotfix)
- [docs/workflow/SPRINT_WORKFLOW.md](docs/workflow/SPRINT_WORKFLOW.md) — Weekly sprint process
- [docs/workflow/RELEASE_CHECKLIST.md](docs/workflow/RELEASE_CHECKLIST.md) — Monthly release cycle

### Developer Guides
- [docs/dev/SETUP.md](docs/dev/SETUP.md) — Dev environment setup
- [docs/dev/ARCHITECTURE.md](docs/dev/ARCHITECTURE.md) — System design, data flow, multiplayer/replay internals
- [docs/dev/SYSTEMS.md](docs/dev/SYSTEMS.md) — Per-module API reference
- [CONTRIBUTING.md](CONTRIBUTING.md) — Branching, commits, PR process, code standards

### Living Documents
- [docs/ROADMAP.md](docs/ROADMAP.md) — Milestones, backlog, planned features
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — Version history
- [docs/DEVLOG.md](docs/DEVLOG.md) — Development session notes
- [docs/operations/BUG_BACKLOG.md](docs/operations/BUG_BACKLOG.md) — Known issues

### Reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — ECS patterns, event system
- [docs/WORLD_GENERATION.md](docs/WORLD_GENERATION.md) — Procedural generation guide

---

## Branching Model

```
main        ← stable, tagged releases only
develop     ← integration (CI runs here)
feature/*   ← new work → PR to develop
hotfix/*    ← urgent fixes → PR to main + back-merge to develop
```

Commit format: `feat|fix|docs|test|chore: description`

---

## CI/CD

| Trigger | Action |
|---------|--------|
| Push to `master`, `develop`, `feature/**` | Tests, lint (ruff), format (black), type check (mypy) |
| Push tag `v*.*.*` | Build `ninja_dash.exe` + `ninja_dash_launcher.exe`, create GitHub Release |
| Monday 9am (scheduled) | Sync open issues from feedback repo → weekly intake summary |

**Required secret**: `CROSS_REPO_PAT` — classic PAT with `repo` scope for cross-repo dispatch.

---

## Versioning

Single source of truth: [`version.json`](version.json)

```json
{
  "version": "0.8.0",
  "build": "production",
  "build_date": "2026-03-29",
  "min_launcher_version": "1.1.0"
}
```

Release: `git tag v0.8.0 && git push origin v0.8.0` — GitHub Actions handles the rest.

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11 |
| Framework | Pygame 2.6.1 |
| Networking | asyncio TCP (authoritative server) |
| Build | PyInstaller (onefile Windows .exe) |
| Testing | pytest 7.4.4 (46 files) |
| Quality | Black, Ruff, MyPy, pre-commit |
| CI/CD | GitHub Actions (windows-latest) |

---

## License

MIT — see LICENSE file.

**Vain Asher Gaming** | [Feedback](https://github.com/VainAsher/indie-ninja-feedback) | [Launcher](https://github.com/VainAsher/indie-ninja-launcher)
