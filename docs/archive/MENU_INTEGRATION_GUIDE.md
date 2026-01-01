# Menu Integration Guide - Hooking Modes into UI

**Version:** v0.6.0
**Date:** 2025-12-15
**Status:** Implementation Ready

---

## Overview

This guide explains how to integrate game mode selection into the startup menus, replacing command-line arguments with a user-friendly UI flow.

### Current State (Command-Line)
```bash
python demo_game.py --mode campaign --mission forest_1
python demo_game.py --mode arcade --procedural
python demo_game.py --mode playtest --mission town_3
```

### Target State (Menu-Driven)
```
Main Menu
  ├─ Start Game
  │   ├─ Campaign Mode → Spawn in Central Hub → Talk to NPC → Mission
  │   ├─ Arcade Mode → Procedural run
  │   └─ Playtest Mode → Mission Selector → Mission
  ├─ Settings
  └─ Quit
```

---

## Menu Flow Diagram

```
┌─────────────────┐
│   Main Menu     │
│                 │
│ > Start Game    │ ◄──┐
│   Settings      │    │
│   Quit          │    │
└────────┬────────┘    │
         │             │
         ▼             │
┌─────────────────────────────┐
│  Game Mode Selection        │
│                             │
│ > Campaign Mode             │
│   Arcade Mode               │
│   Playtest Mode             │
│   Back                      │──┘
└─────┬───────┬────────┬──────┘
      │       │        │
      │       │        └──────┐
      │       │               │
      ▼       ▼               ▼
┌───────┐ ┌─────────┐  ┌──────────────┐
│ Hub   │ │Procedural│  │Mission Selector│
│ World │ │  Run    │  │                │
│       │ │         │  │ forest_1       │
│ NPCs  │ │ (start) │  │ forest_2       │
│Portals│ │         │  │ town_1         │
└───────┘ └─────────┘  │ ...            │
                       │ > Back         │
                       └────────────────┘
```

---

## Implementation Status

### ✅ Already Implemented

1. **Menu System** (`ui/menu_system.py`)
   - BaseMenu class with keyboard navigation
   - MainMenu with "Start Game" option
   - PauseMenu for in-game
   - SettingsMenu for options

2. **Mission Selector UI** (`ui/mission_menu.py`)
   - MissionMenuUI for displaying missions
   - Status icons (✓ completed, ! available, 🔒 locked)
   - Mission details panel
   - Already integrated with mission registry

3. **Hub System** (`game/hub_manager.py`)
   - HubManager with 4 hub definitions
   - Central Hub (15 rooms)
   - Forest Hub (8 rooms)
   - Town Hub (10 rooms)
   - Caves Hub (8 rooms)
   - NPC anchors (mission givers, shops)
   - Portal anchors (fast travel)

4. **Play Mode System** (`game/play_mode.py`)
   - PlayModeManager
   - Mode enum (ARCADE, CAMPAIGN, PLAYTEST, SANDBOX)
   - Mode-specific configuration

### 🆕 New Components Created

1. **Mode Selection Menu** (`ui/mode_selection_menu.py`)
   - GameModeSelectionMenu
   - Campaign/Arcade/Playtest options
   - Mode descriptions
   - MissionSelectorMenu for playtest

### ⚠️ Not Yet Implemented (Phase 2 Full Integration)

1. **NPC System** - Placeholders exist in `game/hub_manager.py`
   - NPC spawning
   - Interaction detection (press E)
   - Dialogue system
   - Mission giver NPCs

2. **Portal System** - Placeholders exist in `game/hub_manager.py`
   - Portal spawning
   - Activation detection (press E)
   - Fast travel between hubs
   - Portal visual effects

---

## Integration Steps

### Step 1: Update Main Menu

**File:** `demo_game.py`

**Change:** Instead of directly starting the game, push the Mode Selection Menu.

```python
# In menu handling code (around line 945):
if action == MenuAction.START_GAME:
    # Push mode selection menu instead of starting directly
    mode_menu = GameModeSelectionMenu(GAME_WIDTH, GAME_HEIGHT)
    menu_manager.push_menu(mode_menu)
```

### Step 2: Handle Mode Selection

**Add new menu action types:**

```python
# In ui/menu_system.py, add to MenuAction enum:
class MenuAction(Enum):
    # ... existing actions ...
    START_CAMPAIGN = "start_campaign"
    START_ARCADE = "start_arcade"
    START_PLAYTEST = "start_playtest"
```

**Handle mode selection in game loop:**

```python
# In demo_game.py main loop:
current_menu = menu_manager.get_current_menu()

# Check if mode selection menu
if isinstance(current_menu, GameModeSelectionMenu):
    selected_mode = current_menu.get_selected_mode()

    if selected_mode == "campaign":
        # Start campaign mode - spawn in hub
        start_campaign_mode()
    elif selected_mode == "arcade":
        # Start arcade mode - procedural run
        start_arcade_mode()
    elif selected_mode == "playtest":
        # Show mission selector
        mission_menu = MissionSelectorMenu(GAME_WIDTH, GAME_HEIGHT, mission_registry)
        menu_manager.push_menu(mission_menu)
```

### Step 3: Campaign Mode Hub Spawning

```python
def start_campaign_mode():
    """Start campaign mode by spawning player in central hub"""

    # Initialize hub manager with campaign seed
    from game.hub_manager import HubManager
    hub_manager = HubManager(world_seed=save_manager.data.campaign.world_seed)

    # Generate central hub
    world, hub_def = hub_manager.generate_hub_world("central_hub")
    megamap = generator.create_megamap(world)

    # Get spawn position
    spawn_pos = hub_manager.get_spawn_position("central_hub", megamap.room_positions)
    spawn_x, spawn_y = spawn_pos

    # Spawn player
    player = Player(entity_id=0, spawn_x=spawn_x, spawn_y=spawn_y)

    # TODO (Phase 2): Spawn NPCs from hub_def.npc_anchors
    # TODO (Phase 2): Spawn portals from hub_def.portal_anchors

    # Set game state to PLAYING
    game_state_manager.change_state(GameState.PLAYING)
    current_play_mode = PlayMode.CAMPAIGN

    print(f"[CAMPAIGN] Spawned in {hub_def.display_name}")
    print(f"[CAMPAIGN] {hub_def.description}")
```

### Step 4: Playtest Mode Mission Selection

```python
# Handle mission selector
if isinstance(current_menu, MissionSelectorMenu):
    selected_mission = current_menu.get_selected_mission()

    if selected_mission:
        # Load mission definition
        mission_def = mission_registry.get_mission(selected_mission)

        # Start mission in playtest mode
        start_playtest_mission(mission_def)
```

### Step 5: Arcade Mode (Existing Flow)

```python
def start_arcade_mode():
    """Start arcade mode - existing procedural generation"""
    # Use existing procedural generation code
    # Set current_play_mode = PlayMode.ARCADE
    # Generate world with WorldGenerator
    # Start game loop
    pass  # Already implemented
```

---

## Menu Navigation Flow

### From Main Menu to Game:

```python
Main Menu (START_GAME pressed)
    ↓
GameModeSelectionMenu.select_current() → mode selected
    ↓
    ├─ "campaign" → start_campaign_mode() → Hub World
    ├─ "arcade" → start_arcade_mode() → Procedural World
    └─ "playtest" → MissionSelectorMenu → start_playtest_mission()
```

### In-Game Menu Flow:

```python
Playing Game (ESC pressed)
    ↓
PauseMenu
    ↓
    ├─ RESUME_GAME → Return to gameplay
    ├─ OPEN_SETTINGS → SettingsMenu
    └─ QUIT_TO_MENU → Back to MainMenu
```

---

## Hub World with NPCs (Future Phase 2)

When NPC system is implemented:

```python
# In start_campaign_mode():

# Get NPC positions from hub
npc_positions = hub_manager.get_npc_positions("central_hub", megamap.room_positions)

# Spawn NPCs
for npc_anchor, world_x, world_y in npc_positions:
    npc = spawn_npc(
        npc_id=npc_anchor.npc_id,
        npc_type=npc_anchor.npc_type,
        x=world_x,
        y=world_y
    )

    # Set up interaction
    if npc_anchor.npc_type == "mission_giver":
        npc.dialogue = "Press E to see available missions"
        npc.on_interact = lambda: show_mission_menu()
```

**Mission Giver Interaction:**
1. Player walks near NPC
2. "Press E to talk" indicator appears
3. Player presses E
4. Mission menu opens (ui/mission_menu.py)
5. Player selects mission
6. Mission loads

---

## Portal System (Future Phase 2)

When portal system is implemented:

```python
# In start_campaign_mode():

# Get portal positions from hub
portal_positions = hub_manager.get_portal_positions("central_hub", megamap.room_positions)

# Spawn portals
for portal_anchor, world_x, world_y in portal_positions:
    portal = spawn_portal(
        portal_id=portal_anchor.portal_id,
        destination=portal_anchor.destination_hub_id,
        x=world_x,
        y=world_y
    )

    # Set up activation
    portal.on_activate = lambda dest=portal_anchor.destination_hub_id: travel_to_hub(dest)
```

**Portal Interaction:**
1. Player walks near portal
2. "Press E to travel to [destination]" appears
3. Player presses E
4. Fade transition
5. Load destination hub
6. Spawn player at destination spawn point

---

## Testing the Integration

### Test 1: Mode Selection Menu
```python
# Run game
python demo_game.py

# Navigate:
# Main Menu > Start Game
# Should see: Campaign Mode, Arcade Mode, Playtest Mode
# Arrow keys to navigate, Enter to select
```

### Test 2: Campaign Mode (Current State)
```python
# Select Campaign Mode
# Expected: Spawn in Central Hub (procedurally generated)
# Can walk around hub world
# No NPCs yet (Phase 2 placeholder)
# No portals yet (Phase 2 placeholder)
```

### Test 3: Playtest Mode
```python
# Select Playtest Mode
# Should see: Mission Selector with all 25 missions
# Navigate by region
# Select a mission (e.g., forest_1)
# Mission loads and starts
```

### Test 4: Arcade Mode
```python
# Select Arcade Mode
# Should work exactly as before
# Procedural generation
# No missions or objectives
```

---

## Code Locations Reference

### Menu System
- **Main Menu**: `ui/menu_system.py` lines 181-219
- **Menu Manager**: Uses menu stack pattern
- **Menu Actions**: `ui/menu_system.py` lines 18-26

### Mode Selection
- **Mode Selection Menu**: `ui/mode_selection_menu.py` (NEW)
- **Mission Selector**: `ui/mode_selection_menu.py` (NEW)

### Game Mode Integration
- **Play Mode Manager**: `game/play_mode.py`
- **Mode Enum**: PlayMode.ARCADE, CAMPAIGN, PLAYTEST

### Hub System
- **Hub Manager**: `game/hub_manager.py`
- **Hub Definitions**: Lines 234-445
- **NPC Anchors**: Defined per hub
- **Portal Anchors**: Defined per hub

### Mission System
- **Mission Registry**: `game/mission_registry.py`
- **Mission Definitions**: `data/missions.json`
- **Objective Tracker**: `game/objective_tracker.py`

---

## Implementation Priority

### Phase 1 (Can Do Now)
1. ✅ Create GameModeSelectionMenu
2. ✅ Create MissionSelectorMenu
3. [ ] Update MainMenu to push mode selection
4. [ ] Handle mode selection in game loop
5. [ ] Implement start_campaign_mode() to spawn in hub
6. [ ] Implement start_playtest_mission() with mission selector
7. [ ] Test all three modes from menus

### Phase 2 (Requires NPC/Portal Implementation)
1. [ ] Implement NPC spawning system
2. [ ] Implement NPC interaction detection (E key)
3. [ ] Implement dialogue system
4. [ ] Connect mission givers to mission menu
5. [ ] Implement portal spawning system
6. [ ] Implement portal activation (E key)
7. [ ] Implement hub travel system
8. [ ] Test full campaign flow: Hub → NPC → Mission → Hub

---

## Summary

**What You Get:**
- Professional menu-driven game mode selection
- Three distinct game modes accessible from UI
- Campaign mode spawns in hub world (NPCs/portals pending Phase 2)
- Playtest mode with full mission selector
- Arcade mode unchanged (backward compatible)

**Next Steps:**
1. Integrate mode selection menu into main menu
2. Add mode selection handling to game loop
3. Test campaign mode hub spawning
4. Test playtest mode mission selection
5. (Future) Implement NPC system for mission givers
6. (Future) Implement portal system for hub travel

**Result:**
No more command-line arguments! Players get a polished menu experience for selecting game modes, and developers can easily test missions via the playtest menu.

---

*Ready for integration into demo_game.py*
