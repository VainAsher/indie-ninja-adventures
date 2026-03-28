# Deep Dive Review (2026-03-25)

Scope
This review is based on static inspection of the repository and planning documents. I did not run the game during this pass. Evidence references point to code files.

**Current State Snapshot**
- Primary entry point: `demo_game.py`
- Core architecture: event bus, fixed timestep clock, modular mechanics, component entities in `core/` and `systems/`
- Data-driven content: `data/missions.json`, `data/items.json`, `data/dialogues.json`, `data/hub_states.json`
- Game modes: campaign, arcade, playtest flows in `demo_game.py` and `game/play_mode.py`
- UI: menu system, inventory, mission selection, shop, dialogue in `ui/`
- Procedural world: generators in `systems/world_generation.py`, `systems/zone_planning.py`, `systems/room_generation.py`, and orchestration in `game/world_builder.py`
- Build: PyInstaller specs and batch wrappers in `build/`

**What Is Implemented And Wired**
- Game loop and state management: `demo_game.py`, `game/game_state.py`, `core/clock.py`
- Physics and collision: `systems/physics_system.py`, `systems/collision_system.py`
- Camera system and effects: `systems/camera_system.py`, `game/game_initialization.py`
- Player mechanics: movement, jump, dash, crouch, wall slide, shuriken, teleport, ninjutsu in `mechanics/` and `entities/player.py`
- Combat and damage flow: `mechanics/combat_mechanic.py`, `mechanics/damage.py`, `entities/enemy_manager.py`
- Enemies and AI: `entities/enemy.py`, `entities/enemy_ai.py`, `entities/enemy_manager.py`
- Hazards, pickups, loot: `entities/hazards.py`, `entities/pickups.py`, `game/loot_system.py`
- Inventory and trading: `game/inventory_system.py`, `game/trading_system.py`, `ui/inventory_ui.py`, `ui/shop_ui.py`
- Dialogue and story: `game/dialogue_system.py`, `game/story_manager.py`, `ui/dialogue_ui.py`
- Missions and objectives: `game/mission_registry.py`, `game/mission_system.py`, `game/objective_tracker.py`
- Save and replay: `systems/save_manager.py`, input pipeline in `network/`, replay handling in `demo_game.py`

**Implemented But Not Fully Wired**
- Boss encounters: `entities/boss.py`, `entities/boss_ai.py`, `entities/boss_manager.py` exist but are not integrated into `demo_game.py` or `game/game_initialization.py`
- Ability gates: `entities/ability_gate.py` exists but is not referenced in the game loop or world generation
- Settings coverage: `config/settings.py` includes key bindings and display options, but input handling is still hardcoded in `entities/player.py` and display options are not applied in `game/game_initialization.py`

**Not Implemented In Code**
- Audio system: no runtime use of `pygame.mixer` or sound assets found
- Gamepad support: no input handling for controllers found

**Content And Data Status**
- Missions: `data/missions.json` contains 30 missions across 6 regions (forest, town, caves, castle, sewer, hollow_depths)
- Boss missions: no missions in `data/missions.json` include a `boss` field
- Items and dialogues: data files load via `get_resource_path` in `game/game_initialization.py`

**Doc Alignment Review**
- `docs/ROADMAP.md` and `docs/SYSTEM_OVERVIEW.md` are out of sync with the codebase
- `docs/FEATURES_V0_7.md` says boss AI is not implemented, but a full AI module exists; the real gap is integration and mission data
- Multiple docs claim wall slide is disabled, but `mechanics/wall_slide.py` is enabled by default and invoked in `entities/player.py`
- Docs list 25 missions and 5 zones, but `data/missions.json` has 30 missions and 6 regions

**Gameplay Flow Review**
- Current flow is menu-first with mode selection, then mission or hub start in `demo_game.py`
- In-game state transitions use `game/game_state.py` and menu system in `ui/menu_system.py`
- Inventory, shop, and mission menu can block player input when open (recent fixes to input routing)

**Build And Packaging Notes**
- Production PyInstaller spec is onefile in `build/ninja_dash_production.spec`
- Build scripts live in `build/` with multi-config wrapper `build/build_all.bat`
- User-data paths are handled in `demo_game.py` to support PyInstaller and local runs

**Key Gaps To Resolve For A Stable Vertical Slice**
- Boss fights are not playable despite extensive boss systems in code
- Ability gates are not present in levels or progression
- Settings do not control key bindings, fullscreen, vsync, or hitbox display
- Audio system is missing entirely
- Documentation is materially out of date versus the actual game state

**Suggested Immediate Verifications**
- Validate the updated menu flow, inventory navigation, and map sizing in a playtest
- Confirm camera shake tuning and damage shake feel
- Run the UAT suite to establish a verified baseline
