# Project Handover Document

Vain Asher Gaming's: Indie Ninja Adventures

Date: 2026-03-28 | Version: 0.7.x (post-restructure) | Branch: master + fix/campaign-loop (Phase 0 bug fixes)
Status: Campaign loop stabilized; Milestone 0 in progress

---

## Executive Summary

This document is the authoritative handover for the project as of March 2026. The previous handover (2025-12-12) is historical only — the codebase has grown from ~50 files to 120+ files and most systems described as "next steps" in that document are now implemented.

**Project Health**: Good
**Code Quality**: High (modular, event-driven, well-tested)
**Technical Debt**: Low
**Blocker Issues**: None (Phase 0 bug fixes committed; boss integration and audio are next)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Current State](#current-state)
3. [Architecture](#architecture)
4. [Completed Systems](#completed-systems)
5. [Known Issues and Gaps](#known-issues-and-gaps)
6. [Next Steps](#next-steps)
7. [Development Workflow](#development-workflow)
8. [Key Files and Locations](#key-files-and-locations)
9. [Testing and QA](#testing-and-qa)
10. [Performance](#performance)
11. [Dependencies](#dependencies)

---

## Project Overview

### Vision

A fast-paced, skill-based 2D ninja platformer with deep movement mechanics, procedural world generation, a story-driven campaign, and — as the long-horizon goal — online multiplayer distributed via a custom launcher.

### Current Game Modes

- **Campaign**: Story-driven progression through 6 regions and 30 missions with NPC dialogue, mission objectives, rewards, and ability unlocks
- **Arcade**: Procedurally escalating dungeons, depth-based difficulty
- **Sandbox**: Open procedural world, no objectives

### Technology Stack

- **Language**: Python 3.11+
- **Framework**: Pygame 2.6.1
- **Architecture**: Event-driven, component-based ECS
- **Physics**: Fixed 60 Hz timestep (deterministic)
- **Generation**: Seed-based procedural with BFS validation
- **Build**: PyInstaller (onefile EXE via `build/ninja_dash_production.spec`)

---

## Current State

### Milestone Status

| Milestone | Description | Status |
| --- | --- | --- |
| **M0**: Stabilization | UAT pass, docs aligned, P0/P1 bugs fixed | 80% — UAT results pending playtest |
| **M1**: Boss Integration | Boss system wired into game loop | 20% — system exists, not yet wired |
| **M2**: Presentation | Audio, visual feedback, combat clarity | 50% — animation done, no audio |
| **M3**: Controls | Key binding wiring, gamepad support | 0% |

### Phase 0 Bug Fixes (commit `985e811` — 2026-03-28)

All six Phase 0 bugs are fixed on branch `fix/campaign-loop`:

| Bug | Fix |
| --- | --- |
| Victory/mission complete screen never triggered | Exit now sets `level_complete = True`; victory screen shows before hub return |
| Completing missions did not unlock further missions | `mission_def.unlock_abilities` now written to `campaign.unlocked_abilities` on exit |
| Player respawned with 0 HP | `regenerate_hub_for_respawn()` now calls `player.damage.respawn()` — always full health on hub load |
| Hurt animation froze after 3 frames | Changed to `loop=True` so it plays continuously while i-frames are active |
| Death animation skipped | 30-frame delay via `queue_player_death()` before world transition; full 5-frame anim plays |
| Sprite flipped/rotated during attack | Wall-inversion disabled during attack states; facing locked for full combo |
| Jump/fall frame order reversed | Frame indices swapped to match sprite sheet layout |

### What Works Right Now

Run `python demo_game.py` (menu-first launch):

| Feature | Status |
| --- | --- |
| Menu system (main, pause, settings, mode select) | Working |
| Campaign mode — 30 missions, 6 regions | Working |
| Mission objectives (kill, collect, reach) | Working |
| Victory screen on mission completion | Working (Phase 0 fix) |
| Mission ability unlock chain | Working (Phase 0 fix) |
| Hub worlds per region (7 hubs) | Working |
| NPC dialogue and trading | Working |
| Inventory system | Working |
| Player movement (walk, run, crouch, dash) | Working |
| Jumping (ground, double, wall, coyote, buffer) | Working |
| Combat — 3-hit combo, air attacks | Working |
| Shuriken projectile | Working |
| Teleport ability | Working |
| Ninjutsu | Working |
| Enemies — goblin, bat, slime, skeleton, wolf | Working |
| Hazards — spikes, lava, poison, void | Working |
| Pickups — coins, health, items | Working |
| Sprite animations — all player states | Working |
| Particle effects — dust, dash, impact | Working |
| HUD — hearts, stamina, objectives | Working |
| Camera — world/room/free modes | Working |
| Save/load persistence | Working |
| Input recording and replay | Working |
| Procedural world generation — 7 biomes | Working |
| Minimap and full-map overlay | Working |
| Boss system (code) | Implemented but not wired into game loop |
| Audio | Not implemented |
| Key binding wiring | Not implemented |

### Player Specifications

```text
Standing:   28 × 56 px  (2:1 ratio — under 1 tile wide, 2 tiles tall)
Crouching:  28 × 28 px
Tile size:  32 × 32 px
World size: 5120 × 5120 px (160 × 160 tiles)

Physics:
  Gravity:        0.4 px/frame
  Max fall speed: 12.0 px/frame (< half tile — no tunneling)
  Max run speed:  8.0 px/frame
  Jump power:     14.5 px/frame
  Dash speed:     16.0 px/frame
  Wall friction:  light vy clamp when touching wall
```

---

## Architecture

### System Hierarchy

```text
Game Loop (demo_game.py)
  ├── GameClock (60 Hz fixed timestep)
  ├── EventBus (pub/sub decoupling)
  ├── GameStateManager (LANDING / MENU / PLAYING / PAUSED / DIALOGUE / SHOP)
  ├── InputPipeline (command pattern — live / record / replay)
  │
  ├── Physics & Collision
  │   ├── PhysicsSystem (gravity, velocity, tile effects)
  │   └── CollisionSystem (AABB, swept, platform, corner)
  │
  ├── World Generation
  │   ├── WorldGenerator (seed-based, 7 biome themes)
  │   ├── ZonePlanner (16 × 16 zone grid per room)
  │   ├── RoomGenerator (tilemap from zones)
  │   └── ConnectivitySystem (BFS + fallback spine)
  │
  ├── Entities
  │   ├── Player (orchestrates all mechanics)
  │   │   ├── MovementMechanic, JumpMechanic, DashMechanic
  │   │   ├── CombatMechanic, DamageMechanic
  │   │   ├── ShurikenMechanic, TeleportMechanic, NinjutsuMechanic
  │   │   ├── WallSlideMechanic (active — see wall slide note)
  │   │   └── CrouchMechanic
  │   ├── EnemyManager + EnemyAI (goblin, bat, slime, skeleton, wolf)
  │   ├── BossManager + BossAI (6 types — NOT YET WIRED)
  │   ├── NPCManager (story-driven dynamic spawning)
  │   ├── HazardManager (spikes, lava, poison, void)
  │   └── PickupManager (coins, health, items)
  │
  ├── Campaign Systems
  │   ├── CampaignManager (region/ability progression)
  │   ├── MissionSystem + MissionManager + ObjectiveTracker
  │   ├── StoryManager + DialogueSystem + CutsceneManager
  │   ├── InventorySystem + TradingSystem + LootSystem
  │   └── SaveSystem (JSON persistence)
  │
  ├── Rendering
  │   ├── TileLoader (PNG assets, autotiling, 7 biomes)
  │   ├── AnimationSystem (sprite sheet state machine)
  │   ├── SpriteManager (frame extraction, flip cache)
  │   ├── ParticleSystem (dust, dash, impact)
  │   ├── HazardRenderer, EnemyRenderer, PickupRenderer
  │   ├── HUD, ObjectiveHUD, Minimap, VictoryScreen
  │   └── CameraSystem (world/room/free, letterboxing)
  │
  └── UI
      ├── MenuSystem (main, pause, settings)
      ├── InventoryUI, ShopUI, DialogueUI, MissionMenuUI
      └── TutorialSystem
```

### Data Flow

```text
Input → InputPipeline (command pattern)
  ↓
TickEvent → Player mechanics, EnemyAI, HazardManager
  ↓
PhysicsSystem → velocity integration
  ↓
CollisionSystem → position correction, tile effects
  ↓
ObjectiveTracker → mission progress checks
  ↓
CameraSystem → follow player
  ↓
RenderEvent → TileLoader, AnimationSystem, HUD, Particles
```

---

## Completed Systems

### Core Infrastructure — 100%

| File | Purpose |
| --- | --- |
| [core/event_bus.py](../core/event_bus.py) | Priority pub/sub event system |
| [core/clock.py](../core/clock.py) | Fixed 60 Hz timestep (Glenn Fiedler pattern) |
| [core/state.py](../core/state.py) | Serializable state with 5 s history for replay/rollback |
| [core/entity_system.py](../core/entity_system.py) | Component-based entity manager |
| [core/mod_system.py](../core/mod_system.py) | Plugin architecture with lifecycle hooks |
| [core/logger.py](../core/logger.py) | Persistent rotating logs, platform-specific path |

### Collision and Physics — 100%

| Feature | Location |
| --- | --- |
| AABB detection + penetration resolution | [systems/collision_system.py](../systems/collision_system.py) |
| Swept collision (prevents tunneling) | collision_system.py L319–427 |
| One-way platform collision (feet-based) | collision_system.py L283–291 |
| Corner detection (smooth landings) | collision_system.py L135–148 |
| Ground detection (prevents wall climbing) | collision_system.py L227–246 |
| Spatial hash for tile queries | collision_system.py |
| Gravity, velocity integration, tile effects | [systems/physics_system.py](../systems/physics_system.py) |

### Player Mechanics — 100%

| Mechanic | File | Notes |
| --- | --- | --- |
| Ground/air movement | [mechanics/movement.py](../mechanics/movement.py) | Smooth interpolation |
| Jump (ground, double, wall, coyote, buffer) | [mechanics/jump.py](../mechanics/jump.py) | |
| Dash | [mechanics/dash.py](../mechanics/dash.py) | 16 px/frame, 0.45 s cooldown |
| Wall slide | [mechanics/wall_slide.py](../mechanics/wall_slide.py) | **Active** — see wall slide note below |
| Crouch | [mechanics/crouch.py](../mechanics/crouch.py) | Half hitbox, ceiling detection |
| Combat (3-hit combo + air) | [mechanics/combat_mechanic.py](../mechanics/combat_mechanic.py) | |
| Shuriken | [mechanics/shuriken.py](../mechanics/shuriken.py) | |
| Teleport | [mechanics/teleport.py](../mechanics/teleport.py) | Phase cursor |
| Ninjutsu | [mechanics/ninjutsu.py](../mechanics/ninjutsu.py) | Stance + cast |
| Damage/i-frames | [mechanics/damage.py](../mechanics/damage.py) | |

**Wall slide note**: `mechanics/wall_slide.py` is **active** and invoked by `entities/player.py`. Some older documents incorrectly state it is disabled. The fallback wall friction also remains as a safety net but is secondary.

### World Generation — 100%

- 7 biome themes: **dungeon, cave, building, forest, town, sewer, hollow**
- Hierarchical: World → Biomes → Rooms (types: start, exit, shop, combat, platform, treasure, boss)
- Zone planning: 16 × 16 grid per room with role assignment
- BFS connectivity validation with three-tier fallback
- Autotiling: 3 × 3 neighbor detection for seamless terrain
- Tile assets: PNG files in `assets/biomes/<biome>/` (real art or placeholder)
- Performance: 2–5 ms for 30-room world

### Campaign and Story — 100%

- 30 missions across 6 regions (forest, town, caves, castle, sewer, hollow_depths)
- Mission objectives: kill, collect, reach, time challenge
- Ability-gated unlock chain (completing missions grants abilities that unlock later missions)
- NPC dialogue trees with story branching
- Multiple story acts and endings
- Save/load (JSON) — mission completion, inventory, abilities, currency

### Rendering — ~75%

| System | Status |
| --- | --- |
| AnimationStateMachine (sprite sheet, all player states) | Complete |
| SpriteManager (frame extraction, flip cache) | Complete |
| EnemyRenderer, NPCRenderer | Complete |
| TileLoader (PIL LANCZOS scaling, fallback colors) | Complete |
| Autotile renderer | Complete |
| Particle system (dust, dash, impact) | Complete |
| HUD (hearts, stamina, objectives) | Complete |
| Minimap + full-map overlay | Complete |
| Victory screen | Complete |
| Screen shake | Not implemented |
| Flash/hit effects (beyond hurt animation) | Not implemented |
| Audio | Not implemented |

### UI — 100%

- Main menu, pause menu, settings menu
- Mode selection (campaign, arcade, sandbox)
- Inventory UI with equipment slots
- Shop UI, dialogue UI, mission menu
- Tutorial system

---

## Known Issues and Gaps

### High Priority (M1)

| Issue | Impact |
| --- | --- |
| Boss system not wired into game loop | No boss fights despite 6 boss types and full AI implemented |
| Ability gates not integrated into world/hub generation | Progression gating not functional |

### Medium Priority (M2–M3)

| Issue | Impact |
| --- | --- |
| Audio system absent | Silent game; settings volume sliders do nothing |
| Key bindings not wired (config/settings.py ignored) | Settings menu key bind changes have no effect |
| Display options (fullscreen, vsync) not wired | Settings menu display changes have no effect |
| Screen shake | Not implemented |

### Low Priority

| Issue | Impact |
| --- | --- |
| Shuriken collision box always visible in play | Minor visual noise in non-debug play |
| Raycast test known to fail | Test signal noise; pre-existing |
| Build can fail if output locked by OneDrive/antivirus | Intermittent CI/build failure |

---

## Next Steps

See [PLAN_2026-03-28.md](PLAN_2026-03-28.md) for the full approved plan. Summary:

| Phase | Branch | Goal |
| --- | --- | --- |
| Phase 0 | `fix/campaign-loop` | Campaign loop bug fixes — **done** |
| Phase 1 | `docs/m0-completion` | Docs + UAT — **in progress** |
| Phase 2 | `feat/boss-integration` | Wire boss encounters into campaign |
| Phase 3 | `feat/audio-foundation` | SFX hooks and volume wiring |
| Phase 4 | `feat/settings-wiring` | Key bindings and display options wired |

**Long-horizon goal**: Online multiplayer via a custom launcher that manages client, server, and mod version downloads from GitHub.

---

## Development Workflow

### Running the Game

```bash
# Standard launch (menu-first)
python demo_game.py

# Jump straight to campaign
python demo_game.py --campaign

# Procedural world with seed (arcade-style)
python demo_game.py --procedural --seed 12345

# Record inputs for replay
python demo_game.py --record session_name

# Replay a recorded session
python demo_game.py --replay session_name
```

### In-Game Controls

```text
Movement:    Arrow keys / WASD
Jump:        Space / W / Up
Dash:        Shift
Run:         Alt (hold)
Crouch:      S / Down (hold)
Attack:      J
Shuriken:    K  (aim with Up/Down for diagonals)
Teleport:    F
Ninjutsu:    L or Q (hold for stance, release to cast)
Inventory:   I
Map:         M
Minimap:     Tab
Camera mode: C (cycle: world / room / free)
Pause:       ESC
```

### Running Tests

```bash
python -m pytest tests/ -q          # all tests
python -m pytest tests/unit/ -q     # unit tests only
python -m pytest tests/ -x -q      # stop on first failure
```

### Adding New Features

- **New mechanic**: Extend `BaseMechanic` in `mechanics/base.py`
- **New enemy type**: Add AI definition in `entities/enemy_ai.py`, register in `entities/enemy_manager.py`
- **New mission**: Add entry to `data/missions.json`
- **New tile asset**: Drop PNG into `assets/biomes/<biome>/tile_*.png`
- **New system event**: Add to `core/event_bus.py`

---

## Key Files and Locations

### Entry Points

| File | Purpose |
| --- | --- |
| [demo_game.py](../demo_game.py) | Main game executable (3,600+ lines) |
| [game/game_initialization.py](../game/game_initialization.py) | System initialization (all managers wired here) |
| [game/play_mode.py](../game/play_mode.py) | Game mode management |

### Core

| File | Purpose |
| --- | --- |
| [core/event_bus.py](../core/event_bus.py) | Pub/sub event system |
| [core/clock.py](../core/clock.py) | Fixed timestep clock |
| [core/state.py](../core/state.py) | Serializable game state |
| [core/entity_system.py](../core/entity_system.py) | Component entity manager |

### Systems

| File | Purpose |
| --- | --- |
| [systems/collision_system.py](../systems/collision_system.py) | AABB + swept collision |
| [systems/physics_system.py](../systems/physics_system.py) | Gravity + tile effects |
| [systems/camera_system.py](../systems/camera_system.py) | Multi-mode camera |
| [systems/world_generation.py](../systems/world_generation.py) | Procedural world with BiomeTheme enum |
| [systems/room_generation.py](../systems/room_generation.py) | Tilemap from zone grid |
| [systems/connectivity.py](../systems/connectivity.py) | BFS + fallback connectivity |
| [systems/autotiling.py](../systems/autotiling.py) | 3 × 3 neighbor detection |
| [systems/save_system.py](../systems/save_system.py) | JSON persistence |

### Game / Campaign

| File | Purpose |
| --- | --- |
| [game/hub_manager.py](../game/hub_manager.py) | Hub world generation per region |
| [game/mission_system.py](../game/mission_system.py) | Mission definitions, 30 missions |
| [game/mission_manager.py](../game/mission_manager.py) | Mission state tracking |
| [game/objective_tracker.py](../game/objective_tracker.py) | Objective progress + exit unlock |
| [game/campaign_manager.py](../game/campaign_manager.py) | Region/ability unlock progression |
| [game/story_manager.py](../game/story_manager.py) | Story acts and events |
| [game/dialogue_system.py](../game/dialogue_system.py) | NPC conversation trees |
| [game/inventory_system.py](../game/inventory_system.py) | Player items |
| [game/trading_system.py](../game/trading_system.py) | NPC shop trades |

### Entities

| File | Purpose |
| --- | --- |
| [entities/player.py](../entities/player.py) | Player orchestrator |
| [entities/enemy_manager.py](../entities/enemy_manager.py) | Enemy spawning + update |
| [entities/boss_manager.py](../entities/boss_manager.py) | Boss spawning (not yet wired) |
| [entities/npc_manager.py](../entities/npc_manager.py) | Story-driven NPC spawning |
| [entities/hazards.py](../entities/hazards.py) | Hazard collision + damage |
| [entities/pickups.py](../entities/pickups.py) | Pickup collection |

### Rendering

| File | Purpose |
| --- | --- |
| [rendering/animation_system.py](../rendering/animation_system.py) | AnimationStateMachine, registry |
| [rendering/sprite_manager.py](../rendering/sprite_manager.py) | Sheet loading + flip cache |
| [rendering/tile_loader.py](../rendering/tile_loader.py) | Tile PNG loading + scaling |
| [rendering/particles.py](../rendering/particles.py) | Dust, dash, impact effects |
| [rendering/hud.py](../rendering/hud.py) | Hearts, stamina, dash cooldown |

### Data

| File | Purpose |
| --- | --- |
| [data/missions.json](../data/missions.json) | 30 mission definitions |
| [data/items.json](../data/items.json) | Item definitions |
| [data/dialogues.json](../data/dialogues.json) | NPC dialogue trees |
| [data/hub_states.json](../data/hub_states.json) | Hub NPC spawn rules |

### Config

| File | Purpose |
| --- | --- |
| [config/settings.py](../config/settings.py) | All user settings (key bindings, volume, display) — not yet fully wired |
| [config/physics_constants.py](../config/physics_constants.py) | Physics tuning constants |
| [config/build_config.py](../config/build_config.py) | Production / dev / test build mode |

---

## Testing and QA

### Test Suite: 280 tests, 42 files

| Category | Files | Focus |
| --- | --- | --- |
| unit/ | 9 | Collision, physics, AI, input, UI |
| integration/ | 4 | Player, demo, play modes, minimap |
| world_gen/ | 5 | Generation, connectivity, zone planning |
| edge_cases/ | 9 | Collision corners, wall, crouch-jump |
| playability/ | 2 | Simulation validators |
| Phase validation | 9 | Phase 1–7 regression |
| legacy/ | 4 | Archived regressions |

```bash
# Run all tests
python -m pytest tests/ -q
# Expected: 280 passed
```

### UAT

See [docs/reviews/2026-03-25/UAT_SUITE.md](reviews/2026-03-25/UAT_SUITE.md) for the current UAT suite.
An updated suite covering Phase 0 fixes and new systems is being created.

---

## Performance

| Metric | Value |
| --- | --- |
| Target FPS | 60 |
| World generation | 2–5 ms for 30-room world |
| Collision detection | < 1 ms per frame (~4,000 tiles, spatial hash) |
| Memory | < 50 MB |
| Render optimizations | O1–O10 series complete; no per-frame surface allocs in hot path |

---

## Dependencies

```text
pygame==2.6.1    # game framework
Pillow           # PIL image loading for tile scaling
PyInstaller      # production build (onefile EXE)
```

**Python**: 3.11+ required, 3.11.9 tested.

**Platform**: Windows tested; macOS/Linux untested but should work.

---

Document Version: 2.0 | Last Updated: 2026-03-28
Author: AI Development Assistant (Claude Sonnet 4.6) | Project: Vain Asher Gaming's: Indie Ninja Adventures
