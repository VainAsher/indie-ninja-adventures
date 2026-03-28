# Campaign System

Version: v0.7.0


## Overview

The campaign is a mission-based progression mode with six regions, thirty total missions, and an ability-unlock chain that gates access to later regions and harder content. The player operates from hub worlds, enters missions through portals, and earns new movement abilities by completing missions. Each ability unlocks access to regions and portals that were previously inaccessible.

Regions in order of typical progression:

1. Central Hub (always unlocked, connects all regions)
2. Forest (unlocked at start)
3. Town (requires forest_1, forest_2, forest_3 completed)
4. Caves (requires double_jump and dash abilities)
5. Castle (requires town_1 through town_5 completed and wall_jump ability)
6. Sewer (requires 50% overall campaign completion)
7. Hollow Depths (Act 2 recovery zone, unlocked via story progression)

Mission count per region: demo_coin_run (tutorial), forest x5, town x6, caves x5, castle x6, sewer x3. The `hollow_depths` region is defined in the data but has no missions in `data/missions.json` at this time.

The ability-unlock chain flows directly from mission rewards:

- forest_1 awards `double_jump`
- forest_3 awards `dash`
- town_3 awards `wall_jump`

All later regions (caves, castle, sewer) require abilities earned through forest and town missions, so the player naturally progresses through those regions first.


## CampaignSaveData Fields

Defined in `systems/save_system.py` at line 102.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `world_seed` | int | 0 | Seed used to generate all hub and mission worlds |
| `current_hub_id` | str | "central_hub" | Hub the player is currently in |
| `current_hub_position` | tuple[float, float] | (0.0, 0.0) | Player's last-known position inside that hub |
| `unlocked_regions` | set[str] | {"central_hub", "forest"} | Set of region IDs the player can visit |
| `completed_missions` | set[str] | (empty set) | Set of mission IDs the player has finished at least once |
| `unlocked_abilities` | set[str] | {"basic_movement", "jump"} | Abilities available to the player |
| `mission_attempts` | dict[str, int] | {} | Attempt count per mission ID |
| `mission_best_times` | dict[str, float] | {} | Best completion time in seconds per mission ID |
| `player_inventory` | dict[str, int] | {} | Item ID to quantity mapping |
| `equipped_weapon` | str or None | None | ID of the currently equipped weapon |
| `equipped_armor` | str or None | None | ID of the currently equipped armor |
| `currency` | int | 0 | Player's current gold |
| `total_deaths` | int | 0 | Campaign-lifetime death count |
| `total_play_time` | float | 0.0 | Campaign-lifetime playtime in seconds |
| `story_state` | dict or None | None | Serialised StoryManager state (v0.7.0) |

When serialised to JSON, Python sets are written as lists and tuples are written as arrays. The deserialiser in `SaveManager._dict_to_savedata()` converts them back.


## Region Progression

Region unlock logic lives in `game/campaign_manager.py`, in the `CampaignManager.region_requirements` dictionary (line 92).

**Central Hub** — always unlocked, no requirements.

**Forest** — always unlocked at campaign start alongside the central hub.

**Town** — requires `forest_1`, `forest_2`, and `forest_3` all in `completed_missions`.

**Caves** — requires the `double_jump` and `dash` abilities both in `unlocked_abilities`.

**Castle** — requires `town_1`, `town_2`, `town_3`, `town_4`, and `town_5` all completed, and the `wall_jump` ability.

**Sewer** — requires 50% overall campaign completion (`completion_percent >= 0.5`). Overall completion is the average of per-region completion percentages across forest, town, caves, castle, and sewer.

**Hollow Depths** — not in `region_requirements`; unlocked via story scripting rather than the standard check.

Region checks run automatically after every `complete_mission()` and `unlock_ability()` call in `CampaignManager._check_region_unlocks()`.


## Ability Gating

### _ABILITY_TO_FLAG

Defined in `demo_game.py` near line 1262. Maps ability IDs to the player `feature_flags` key that enables that mechanic:

```python
_ABILITY_TO_FLAG = {
    "double_jump": "double_jump",
    "wall_jump":   "wall_jump",
    "dash":        "dash",
    "shuriken":    "shuriken",
    "teleport":    "teleport",
    "ninjutsu":    "ninjutsu",
}
```

`basic_movement`, `jump`, and `crouch` are always enabled and have no entry here.

### sync_player_abilities()

Defined in `demo_game.py` near line 1273. Iterates `_ABILITY_TO_FLAG` and sets each flag on `player.feature_flags` based on whether that ability is in `unlocked_abilities`. It also manually syncs `player.jump.double_jump_enabled` and `player.jump.wall_jump_enabled` because `JumpMechanic` caches those as instance variables at initialisation time.

Called in three places:

- Campaign mode start, after loading save data
- After every mission completion that awards new abilities
- When the F9 debug ability menu is toggled (dev builds)

### _rebuild_hub_gates()

Defined in `demo_game.py` near line 1046. Places `GateType.LOCKED_DOOR` entities in front of portals whose destination region requires an ability the player does not yet have. Called whenever the player returns to a hub.

The ability requirements per destination are defined in `_REGION_GATE_ABILITY` (line 1039):

```python
_REGION_GATE_ABILITY = {
    "caves_hub":  "double_jump",
    "castle_hub": "dash",
    "sewer_hub":  "wall_jump",
    "hollow_hub": "shuriken",
}
```

Forest and town portals are always open. If the player attempts to interact with a locked portal, the interaction is blocked and a log message is printed; no gate entity collision is needed for the block to work because the interaction code also re-checks `_REGION_GATE_ABILITY` directly (line 2540).


## Portal Placement as Mechanical Gate

All portals are defined as `PortalAnchor` instances registered on `HubDefinition` objects inside `HubManager._register_default_hubs()` (`game/hub_manager.py`, line 276).

The `local_y` field controls vertical position within a room. Rooms are `128 tiles * 32 px = 4096 px` tall. The centre y value `ROOM_PIXEL_CENTER_Y` equals `ROOM_HEIGHT_TILES * TILE_SIZE // 2 = 2048`.

**Forest portal** — `grid_x=0, grid_y=-1` (north room), `local_y = ROOM_PIXEL_CENTER_Y + 200`. Placing the portal below centre seats it near floor level. A player with only `basic_movement` and `jump` can reach it with a single jump or no jump at all once collision snap places them on solid ground.

**Town portal** — `grid_x=1, grid_y=0` (east room), `local_y = ROOM_PIXEL_CENTER_Y - 200`. Placing it 200 px above centre puts it on an elevated platform. A player needs `double_jump` to reach it, which is consistent with `_REGION_GATE_ABILITY` not listing town (the double_jump is earned from forest_1 before town unlocks).

**Caves, Castle, Sewer, Hollow portals** — these destinations are in `_REGION_GATE_ABILITY` so an invisible soft lock (ability check in interaction code) blocks entry. Their portals share rooms with other portals (`grid_x=0, grid_y=1` for caves and sewer; `grid_x=1, grid_y=0` for castle alongside town), so they are physically reachable but logically locked.


## Mission Flow

```
Hub world
  -> Player interacts with NPC mission giver or portal
  -> MissionManager.start_mission(mission_id)
     - Sets current_mission_id
     - Calls MissionProgress.start_attempt()
     - Emits MissionStartEvent
     - Emits ExitLockedEvent (exit portal locked)
  -> ObjectiveTracker.start_mission_objectives(mission_id)
     - Creates ObjectiveState for each objective
     - Subscribes to game events
  -> Player plays mission level
     - Game events (EnemyDeathEvent, ItemCollectedEvent, etc.) flow through EventBus
     - ObjectiveTracker updates ObjectiveState.current_value
     - On completion: calls MissionManager.complete_objective()
     - When all objectives complete: MissionManager.unlock_exit()
       - Emits AllObjectivesCompleteEvent
       - Emits ExitUnlockedEvent
  -> Player reaches exit portal
  -> MissionManager.complete_mission(mission_id, player_inventory)
     - Records completion time and best time
     - Distributes rewards via _distribute_rewards()
     - Emits MissionCompleteEvent
  -> demo_game.py handles MissionCompleteEvent:
     - Adds abilities to save data
     - Calls sync_player_abilities()
     - Calls story_manager.on_mission_complete()
     - Triggers victory screen
  -> Victory screen displayed (rendering/victory_screen.py)
  -> Player dismissed, returns to hub
  -> _rebuild_hub_gates() updates portal locks
```

The exit portal remains locked (`MissionManager.exit_locked = True`) until all objectives are complete. On mission failure (death), `fail_mission()` unlocks the exit so the player can return to the hub without being trapped.


## Objective Types

Defined in `game/mission_registry.py` as `ObjectiveType` enum. Tracked in `game/objective_tracker.py`.

| Type | Enum value | Progress mechanic |
| --- | --- | --- |
| Kill enemies | `kill_all_enemies` | Increments on `EnemyDeathEvent`; any enemy type unless objective specifies a filter |
| Collect items | `collect_items` | Increments on `ItemCollectedEvent`; checks `obj.item_id` against `event.item_id` if set |
| Activate switches | `activate_switches` | Increments on `SwitchActivatedEvent`; can restrict to specific switch IDs via `tracked_entity_ids` |
| Reach location | `reach_location` | Checked on `PlayerPositionUpdateEvent`; completes when distance to `target_position` is within `target_radius` (default 100 px) |
| Time challenge | `time_challenge` | `elapsed_time` increments each tick via `TickEvent`; exceeding `time_limit_seconds` signals failure to the mission manager |
| Defeat boss | `defeat_boss` | Increments on `BossDeathEvent`; checks `obj.boss_id` against `event.boss_id` or `event.boss_type` |

`ObjectiveState.target_value` is read from the `count` field in the JSON if present, otherwise from `target`. The display helper `get_objective_display_text()` formats progress as `"description (current/target)"` for countable types.

HUD rendering is handled in `rendering/objective_hud.py`.


## How to Add a New Mission

All missions are data-driven. Adding a mission requires one JSON object in `data/missions.json` inside the `"missions"` array. No Python code changes are needed unless a new objective type is required.

**Step 1 — Choose a mission ID.** Use the pattern `<region>_<n>`, for example `forest_6`. The ID must be unique across all missions.

**Step 2 — Write the JSON object.** All required fields:

```json
{
  "mission_id": "forest_6",
  "mission_name": "Display Name",
  "region": "forest",
  "difficulty": 2,
  "room_count": 10,
  "shape": "snake",
  "description": "Short description shown in the mission select UI.",
  "objectives": [
    {
      "type": "kill_all_enemies",
      "description": "Defeat all goblins",
      "target": 8
    }
  ],
  "required_abilities": ["basic_movement", "jump", "double_jump"],
  "unlock_abilities": [],
  "rewards": {
    "currency": 75,
    "items": [
      { "id": "health_potion_small", "quantity": 1 }
    ]
  },
  "enemy_types": ["goblin"],
  "hazards": ["spike"],
  "time_limit": null,
  "unlock_requirements": ["forest_1"],
  "act": 0,
  "story_trigger": null,
  "hub_impact": null
}
```

**Step 3 — Objective type reference.**

For `collect_items`: replace `"target"` with `"count"` and add `"item": "<item_id>"`.
For `activate_switches`: use `"count"` (no item field needed).
For `reach_location`: use `"location": "<location_id>"` with no target count.
For `time_challenge`: use `"time_limit": <seconds_as_float>`.
For `defeat_boss`: use `"boss": "<boss_type_id>"`.

**Step 4 — Set unlock requirements.** List mission IDs that must be completed before this one becomes available. The `MissionRegistry.is_mission_unlocked()` method checks both `unlock_requirements` and `required_abilities`.

**Step 5 — Set ability rewards.** If completing this mission should unlock an ability, add it to `"unlock_abilities"`. The string must match an `_ABILITY_TO_FLAG` key (`double_jump`, `wall_jump`, `dash`, `shuriken`, `teleport`, `ninjutsu`).

**Step 6 — Validate.** The schema is at `data/schemas/missions_schema.json`. Run `game/data_validation.py` or the data integrity test suite (`tests/test_data_integrity.py`) to confirm the JSON is valid before shipping.

**Step 7 — Update CampaignManager (if needed).** If the region's mission list in `CampaignManager._get_region_missions()` (`game/campaign_manager.py`, line 294) is used for completion-percentage calculations, add the new ID there. Currently that method returns hardcoded lists.


## Hub Worlds

### HubManager

`game/hub_manager.py`. Responsible for registering hub definitions and generating hub worlds on demand. Initialised once with `initialize_hub_manager(world_seed)` and accessed globally via `get_hub_manager()`.

`generate_hub_world(hub_id)` derives a per-hub seed using `SeedDerivation.derive_region_seed(world_seed, hub_id)`, then delegates to `WorldGenerator` with `num_biomes=1`. The resulting rooms are all flagged `is_hub = True` and `hub_id = hub_id`.

### HubDefinition

A dataclass (`game/hub_manager.py`, line 73) holding:

- `hub_id`, `hub_type` (CENTRAL or REGION), `display_name`, `description`
- `biome_theme` — controls tileset and generation rules
- `room_count` — how many rooms to generate
- `world_shape` — currently `WorldShape.GRID` for all registered hubs
- `npc_anchors` — list of `NPCAnchor` instances
- `portal_anchors` — list of `PortalAnchor` instances
- `spawn_grid` and `spawn_local` — where the player spawns

### PortalAnchor

Dataclass at line 52. Fields:

- `portal_id` — unique identifier
- `destination_hub_id` — hub or mission target
- `grid_x`, `grid_y` — which generated room to place the portal in (relative to origin, or absolute depending on generator output)
- `local_x`, `local_y` — pixel offset within that room
- `bidirectional` — whether the player can return through this portal

`get_world_position(room_px, room_py)` adds `local_x`/`local_y` to the room's world-space origin to produce the final pixel position.

### NPCAnchor

Dataclass at line 32. Same grid/local coordinate system as `PortalAnchor`. The `npc_type` field (`"mission_giver"`, `"shop"`, `"lore"`, `"tutorial"`) is used by NPC spawning code to decide what behaviour to attach. `local_y = ROOM_PIXEL_CENTER_Y` places the NPC at vertical centre of the room.

### Registered hubs

| Hub ID | Display name | Biome | Rooms | Notable NPCs |
| --- | --- | --- | --- | --- |
| `central_hub` | Adventurer's Nexus | DUNGEON | 15 | tutorial_elder |
| `forest_hub` | Whispering Grove | FOREST | 4 | forest_ranger (mission_giver), forest_merchant (shop) |
| `town_hub` | Ashenvale Square | TOWN | 4 | town_captain (mission_giver), town_blacksmith (shop), town_historian (lore) |
| `caves_hub` | Crystal Cavern Haven | CAVE | 4 | cave_explorer (mission_giver), crystal_trader (shop) |
| `castle_hub` | Obsidian Castle | BUILDING | 4 | castle_commander (mission_giver), castle_armorer (shop) |
| `sewer_hub` | Shadow Sewers | SEWER | 4 | sewer_scout (mission_giver), sewer_vendor (shop) |


## Save / Load

### File locations

```
user_data/
  saves/
    savegame.json        <- active save file
    backups/
      savegame_YYYYMMDD_HHMMSS.json  <- up to 3 rolling backups
```

The save directory defaults to `user_data/saves` relative to the working directory. A custom path can be passed to `SaveManager.__init__(save_dir=...)`.

### File format

The JSON file is a wrapper object:

```json
{
  "version": "0.7.0",
  "signature": "<hex HMAC-SHA256>",
  "data": { ... }
}
```

Old saves without a `"signature"` key are detected and loaded with a compatibility warning. They are validated but not blocked.

### HMAC-SHA256 integrity check

`SaveManager._calculate_signature()` (line 200) computes `HMAC-SHA256(SAVE_SECRET_KEY, canonical_json)` where canonical JSON is produced with `json.dumps(data_dict, sort_keys=True)`. The key is the module-level constant `SAVE_SECRET_KEY = b"ninja_dash_v0_3_save_integrity_key_2025"`.

On load, `_verify_signature()` uses `hmac.compare_digest()` (constant-time comparison) to check the stored signature against a fresh calculation. A mismatch prints a warning but does not prevent loading — instead the data is passed through `_validate_save_data()` which clamps currency, playtime, and inventory values to safe ranges.

### Version migration

`_migrate_save()` (line 523) handles upgrades from older save formats:

- Pre-v0.6.0: adds an empty `campaign` block
- Pre-v0.7.0: adds `story_state = null` to the campaign block

### Auto-save

`SaveManager.auto_save(current_time)` saves if `needs_save` is true and at least `auto_save_interval` (60 seconds) has elapsed since the last save. Any method that mutates save data must call `mark_dirty()` to set `needs_save = True`.

### Backup rotation

Before every explicit save, the existing file is copied to `backups/savegame_<timestamp>.json`. The backup directory is pruned to keep only the three most recent files.


## Known Issues

**Boss AI not implemented.** The `entities/boss_ai.py` module defines a ten-state state machine (`BossAIState`: INTRO, IDLE, PHASE_1, PHASE_2, PHASE_3, SPECIAL_ATTACK, VULNERABLE, SUMMONING, TELEPORTING, DEAD) but the actual per-phase combat logic is either stubbed or minimal. Several missions define boss objectives (`forest_3`, `forest_5`, `town_5`, `town_6`, `caves_4`, `caves_5`, `castle_4`, `castle_6`, `sewer_2`, `sewer_3`) that will not behave as intended until boss AI is fully implemented.

**Hollow Depths has no missions.** The region is defined in `data/missions.json` and in `campaign_manager.py` but contains zero mission entries. Attempting to reach its hub will succeed if the story system unlocks it, but there is nothing to do there.

**_get_region_missions() is hardcoded.** `CampaignManager._get_region_missions()` returns hardcoded lists rather than reading from the mission registry. Missions added only to `data/missions.json` will not count toward region completion percentages until this method is updated.
