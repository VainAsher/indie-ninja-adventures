# Indie Ninja Adventures — Project Overview

**Vain Asher Gaming** | Version 0.7.1 | 2026-03-28

---

## Vision

A fast-paced, skill-based 2D ninja platformer built for mastery. Players explore procedurally generated worlds, earn abilities by completing missions, and work toward a story-driven campaign with multiple endings.

The long-horizon goal is online multiplayer distributed via a custom launcher: players download and verify client, server, and mod bundles from GitHub with version parity enforced.

---

## Game Modes

| Mode | Description |
| --- | --- |
| **Campaign** | Story-driven. 6 regions, 30 missions, NPCs, dialogue, ability unlock chain. Progress saves. |
| **Arcade** | Endless procedural dungeon with escalating difficulty and a depth-based score. |
| **Sandbox** | Free exploration. All mechanics unlocked. No objectives. |
| **Playtest** | Direct mission selector. Jump to any of the 30 missions for testing. |

---

## Quick Start

```bash
# Standard launch (shows main menu)
python demo_game.py

# Jump directly to a mode
python demo_game.py --mode campaign
python demo_game.py --mode arcade
python demo_game.py --mode playtest

# Specific world seed
python demo_game.py --procedural --seed 12345

# Headless (CI / no display)
python demo_game.py --headless --mode arcade

# Load a specific mission directly
python demo_game.py --mode playtest --mission forest_1
```

---

## Controls

| Action | Default keys |
| --- | --- |
| Move left / right | Arrow keys or A / D |
| Jump | Space, W, or Up arrow |
| Dash | Left Shift |
| Crouch / fast-fall | S or Down arrow |
| Attack | J |
| Shuriken | K (aim with Up / Down for diagonals) |
| Teleport | F |
| Ninjutsu | L or Q (hold for stance, release to cast) |
| Interact / confirm | E or Enter |
| Inventory | I |
| Map | M |
| Pause | Esc |
| Cycle camera mode | C |
| Debug hitboxes | F3 |
| Debug ability menu | F9 (password: `devmode`) |

Key bindings are configurable in the Settings menu. WASD and arrow keys always work as fallbacks.

---

## Technology Stack

| Component | Choice | Reason |
| --- | --- | --- |
| Language | Python 3.11+ | Rapid iteration; good enough performance for 60 Hz 2D |
| Framework | Pygame 2.6.1 | Low-level enough to control the full render loop |
| Physics | Fixed 60 Hz timestep | Deterministic — enables replay recording and future networking |
| Generation | Seed-based procedural | Reproducible worlds; same seed = same level every time |
| Build | PyInstaller (onefile EXE) | Single executable for Windows distribution |
| Testing | pytest | 49 test files, ~94% pass rate |

---

## Project Structure

```
indie-ninja-adventures/
├── demo_game.py           Main executable and game loop (~4,500 lines)
├── core/                  Engine: EventBus, Clock, Logger, EntityManager, ModSystem
├── systems/               Physics, collision, camera, world gen, save
├── mechanics/             Player abilities (each is a self-contained BaseMechanic)
├── entities/              Player, enemies, NPCs, bosses, hazards, pickups
├── game/                  Campaign, missions, story, dialogue, inventory, trading
├── rendering/             Animation, sprites, tiles, particles, HUD
├── ui/                    Menus, dialogue UI, inventory UI, shop UI
├── audio/                 AudioManager (SFX playback, silent fallback)
├── config/                GameSettings, physics constants, build config
├── network/               Input pipeline (command pattern, record/replay)
├── utils/                 Resource path resolution, frame profiler
├── assets/                Tile PNGs, sprite sheets, audio SFX
├── data/                  missions.json, dialogues.json, items.json, hub_states.json
├── tests/                 Unit, integration, edge cases, world gen, playability
├── build/                 PyInstaller specs and build scripts
├── docs/                  This documentation folder
└── user_data/             Runtime: saves, settings, logs, replays (gitignored)
```

---

## Architecture Summary

The game is **event-driven** and **component-based**. Systems communicate via an `EventBus` (pub/sub) rather than calling each other directly. This keeps coupling low and makes systems independently testable.

```
Game Loop (demo_game.py)
  ├── GameClock          Fixed 60 Hz physics ticks; variable render with interpolation
  ├── EventBus           Central pub/sub — no system imports another directly
  ├── InputPipeline      Command pattern; supports live play, recording, and replay
  │
  ├── Physics / Collision
  │   ├── PhysicsSystem  Gravity, velocity integration, tile effects
  │   └── CollisionSystem  AABB + swept; platforms; corners; spatial hash
  │
  ├── World Generation
  │   ├── WorldGenerator  Seed-based; 7 biome themes; BFS-validated
  │   ├── ZonePlanner     16×16 zone grid per room
  │   ├── RoomGenerator   160×160 tilemap from zone roles
  │   └── ConnectivitySystem  BFS + fallback spine
  │
  ├── Entities
  │   ├── Player          Orchestrates 11 mechanics; feature_flags gate abilities
  │   ├── EnemyManager    5 enemy types; patrol/chase/ranged AI
  │   ├── BossManager     6 boss types; wired into mission flow
  │   ├── NPCManager      Story-driven; dialogue triggers
  │   ├── HazardManager   Spikes, lava, poison, void
  │   └── PickupManager   Coins, health, items
  │
  ├── Campaign
  │   ├── CampaignManager  Region/ability unlock progression
  │   ├── MissionManager   Active mission state
  │   ├── ObjectiveTracker  Progress checks; exit unlock
  │   ├── HubManager       Hub world generation; portal placement
  │   ├── StoryManager     Acts, events, endings
  │   └── SaveSystem       JSON persistence with HMAC-SHA256 signature
  │
  ├── Rendering
  │   ├── AnimationSystem  Sprite sheet state machine
  │   ├── CameraSystem     World/room/free modes; letterboxing
  │   ├── TileLoader       PNG tiles; autotiling; 7 biomes
  │   ├── ParticleSystem   Dust, dash, impact
  │   └── HUD              Hearts, objectives, minimap
  │
  └── Audio
      └── AudioManager     12 SFX slots; pygame.mixer; silent fallback
```

For detailed coverage of each system, see `docs/systems/`.

---

## Current Status (v0.7.1)

| System | Status |
| --- | --- |
| Player mechanics (movement, jump, dash, crouch, wall slide, combat, shuriken, teleport, ninjutsu) | Complete |
| Enemies (5 types + AI) | Complete |
| Campaign (6 regions, 30 missions, story, dialogue, NPCs) | Complete |
| World generation (7 biomes, procedural, BFS-validated) | Complete |
| Rendering (animation, camera, tiles, particles, HUD) | Complete |
| Audio SFX (12 events wired end-to-end) | Complete |
| Settings (key bindings, fullscreen, sfx_volume, hitboxes) | Complete |
| Ability gates (sync + hub portal height gating) | Complete |
| Boss encounters (spawning + mission flow) | Partial — AI behaviour not implemented |
| Music / BGM | Not started |
| Gamepad support | Not started |

---

## Dependencies

```
pygame==2.6.1    Game framework (rendering, input, audio)
Pillow==10.1.0   Image loading for tile scaling
PyInstaller      Production build (onefile EXE) — dev dependency only
Python 3.11+     Required
```

---

## Running Tests

```bash
python -m pytest tests/ -q          # all tests (~280)
python -m pytest tests/unit/ -q     # unit tests only
python -m pytest tests/ -x -q       # stop on first failure
```

Expected: ~94% pass rate. One known pre-existing failure in the raycast test.

---

## Documentation Map

| Document | Purpose |
| --- | --- |
| [OVERVIEW.md](OVERVIEW.md) | This file — project context, quick start, architecture summary |
| [TASK_LIST.md](TASK_LIST.md) | Living task list — what to work on now, next, and backlog |
| [ROADMAP.md](ROADMAP.md) | Milestone definitions and completion status |
| [HANDOVER.md](HANDOVER.md) | Full handover for someone new to the project |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Deep-dive design principles and data flow |
| [systems/AUDIO.md](systems/AUDIO.md) | Audio system — AudioManager, SFX events, wiring |
| [systems/CAMPAIGN.md](systems/CAMPAIGN.md) | Campaign progression, missions, ability gates, portals |
| [systems/MECHANICS.md](systems/MECHANICS.md) | All player mechanics — tuning values, interactions |
| [systems/RENDERING.md](systems/RENDERING.md) | Rendering pipeline, camera, animation, particles |
| [systems/SETTINGS.md](systems/SETTINGS.md) | Settings system — all keys, wiring, how to add settings |
| [systems/WORLD_GEN.md](systems/WORLD_GEN.md) | Procedural world generation — hierarchy, biomes, zones |
| [WORLD_GENERATION.md](WORLD_GENERATION.md) | Extended world generation reference |
| [QUICK_START.md](QUICK_START.md) | Concise play guide |
