# World Generation System

Version: v0.7.0


## Overview

The world generation system builds procedural platformer worlds from a single integer seed. Every call with the same seed and the same parameters produces an identical world. The system is used for both campaign mission levels and hub world generation.


## Hierarchy

```
World
  seed: int
  biomes: list[Biome]          (one per thematic region)
  all_rooms: list[RoomNode]    (flat list across all biomes)
  start_room: RoomNode
  exit_room: RoomNode
  bounds: (minx, miny, maxx, maxy)

  Biome
    theme: BiomeTheme
    rooms: list[RoomNode]
    start_room: RoomNode

    RoomNode
      grid_x, grid_y: int         (position in abstract room grid)
      room_type: RoomType
      biome_theme: BiomeTheme
      seed: int                   (per-room seed derived from world seed)
      neighbors: set[tuple]       (adjacent room grid positions)
      neighbor_dirs: dict         (direction -> neighbor position)
      door_ports: dict            (direction -> list[DoorPort])
      zone_grid: list[list[str]]  (16 x 16 zone roles)
      tilemap: list[list[int]]    (128 x 128 tile IDs)
      anchors: dict               (named pixel positions for spawners)

      Zone Grid (16 x 16 zones)
        Each zone cell holds one ZoneRole string

        Tilemap (128 x 128 tiles)
          Each zone expands to 8 x 8 tiles (TILES_PER_ZONE = 8)
          Each tile is 32 x 32 pixels (TILE_SIZE = 32)
          Room dimensions: 128 tiles = 4096 pixels per axis
```

The critical dimension constants are all in `config/physics_constants.py`:

- `TILE_SIZE = 32` px
- `TILES_PER_ZONE = 8`
- `ROOM_WIDTH_TILES = 128` (16 zones x 8 tiles)
- `ROOM_HEIGHT_TILES = 128`

A single room is therefore 4096 x 4096 pixels. A 30-room world spans up to roughly 4-6 rooms wide and tall in grid space (world grid size is dynamically sized based on `sqrt(room_count) * 3.0`).


## Seed-Based Determinism

`WorldGenerator.__init__(seed)` constructs `random.Random(seed)`. All random choices during graph layout, biome assignment, door port placement, and per-room generation draw from this single RNG object, guaranteeing that the same seed always produces the same world.

Each `RoomNode` also receives its own `seed = self.rng.randrange(10**9)`, which is used by `ZonePlanner` and `RoomGenerator` independently. Changing the number of rooms or the order operations are performed would shift all subsequent seeds.

For hub worlds, `HubManager.generate_hub_world()` first derives a hub-specific seed via `SeedDerivation.derive_region_seed(world_seed, hub_id)` before constructing a `WorldGenerator`. This means the hub layout is always consistent with the campaign seed but independent for each hub ID.

The six-level seed hierarchy (from `systems/seed_hierarchy.py`):

1. worldSeed — user-provided or randomly chosen
2. regionSeed — `hash(worldSeed, regionId)`
3. missionSeed — `hash(regionSeed, missionId)`
4. roomSeed — `hash(missionSeed, roomNodeId)`
5. subroomSeed — `hash(roomSeed, subroomIndex)`
6. featureSeed — `hash(subroomSeed, featureType)`

Hashing uses SHA-256 truncated to 31 bits (`seed & 0x7FFFFFFF`).


## WorldShape Enum

Defined in `systems/world_generation.py` at line 39. Each value corresponds to a pair of shape parameters stored in `SHAPE_PRESETS`:

| Enum value | rev | straight | Character |
| --- | --- | --- | --- |
| `SNAKE` | 0.80 | 0.70 | Long winding corridor with few branches. Picks from the most recently added rooms. |
| `BRANCHY` | 0.25 | 0.30 | Maze-like. Frequently picks random frontier rooms and changes direction. |
| `BLOB` | 0.40 | 0.40 | Clustered, organic shape. Balanced between snake and branchy. |
| `SPIRAL` | 0.90 | 0.15 | Very recent frontier, rotates clockwise through directions. Tight spiral. |
| `TREE` | 0.10 | 0.60 | Picks random frontier rooms but tends to continue straight — long branches from a shared base. |
| `GRID` | 0.50 | 0.85 | Balanced frontier selection, high straight probability. Produces structured near-rectangular layouts. |

`rev` is the probability that the generator picks a room from the most recently added frontier entries rather than a random one. `straight` is the probability of continuing in the same direction as the previous step.

The `SPIRAL` shape also applies a clockwise direction rotation (up → right → down → left → up) rather than the standard straight-bias logic.

`SNAKE` hard-prunes the frontier to the last 6 entries. `SPIRAL` prunes to 3. `GRID` prunes with a 40% chance when the frontier exceeds 6. `BRANCHY` and `BLOB` prune with 30% when the frontier exceeds 8.

`data/missions.json` also references `"vertical"`, `"linear"`, `"arena"`, `"gauntlet"`, and `"labyrinth"` as shape values. These are stored as strings on `MissionDefinition.shape` but are not yet mapped to `WorldShape` enum values — they fall back to the default `WorldShape.BLOB` at generation time.


## BiomeTheme Values

Defined in `systems/world_generation.py` at line 102. Used to select tilesets, generation patterns, and visual style.

| Value | Description |
| --- | --- |
| `DUNGEON` | Default stone dungeon. Used for the central hub and fallback generation. |
| `CAVE` | Irregular rocky caverns. Used for Crystal Caverns region and Hollow Depths. |
| `BUILDING` | Structured interior architecture. Used for Castle region. |
| `FOREST` | Forest clearing with trees and organic shapes. Used for forest hub. |
| `TOWN` | Town buildings and streets. Used for town hub. |
| `SEWER` | Narrow channels and pipes. Used for sewer hub and region. |
| `HOLLOW` | Empty void with sparse platforms. Used for Hollow Depths region. |

In multi-biome worlds the generator assigns themes cyclically from `[DUNGEON, CAVE, BUILDING]` (line 541). Single-biome worlds (hub generation) use the theme specified in `HubDefinition.biome_theme`.


## Room Types

Defined in `systems/world_generation.py` at line 90.

| Type | Assignment | Purpose |
| --- | --- | --- |
| `START` | First room placed at grid centre | Player spawn point |
| `EXIT` | Room farthest from start by Manhattan distance | Goal destination |
| `SHOP` | ~10% of non-start/exit rooms | Merchant location |
| `TREASURE` | ~8% of remaining rooms | High-value loot |
| `BOSS` | ~6% of remaining rooms | Boss encounter |
| `PLATFORM` | ~25% of remaining rooms | Platforming challenge layout |
| `COMBAT` | All remaining rooms | Enemy encounter (default type) |

Distribution formula from `_generate_room_graph()` (line 447):

- SHOP: `max(1, room_count // 10)`
- TREASURE: `max(1, room_count // 12)`
- BOSS: `max(1, room_count // 16)`
- PLATFORM: `max(2, room_count // 4)`

Boss rooms receive at most one door port regardless of random rolls (line 617).


## Zone Roles

Defined in `systems/world_generation.py` at line 77 as `ZoneRole` enum, and mirrored as plain strings in `systems/zone_planning.py`. The zone planner works with strings internally.

| Role | String constant | Tile expansion |
| --- | --- | --- |
| `WALK` | `"walk"` | Solid floor tile at the bottom row of the zone |
| `FILL` | `"fill"` | All tiles solid (impassable terrain block) |
| `PLAT` | `"platform"` | One `TILE_PLATFORM` row at the vertical centre of the zone |
| `DOOR` | `"door"` | Same as WALK; door carving ensures the edge is open |
| `SAVE` | `"save"` | Same as WALK; save point spawner placed here |
| `SHOP` | `"shop"` | Same as WALK; shop NPC spawner placed here |
| `LOOT` | `"loot"` | Same as WALK; loot chest spawner placed here |
| `VOID` | `"void"` | All tiles empty (pit) |

Three internal-only roles used during planning (never output to zone_grid permanently):

| Role | Purpose |
| --- | --- |
| `Z_CHUTE` | Vertical shaft for downward traversal; keeps zone empty for falling |
| `Z_CLIMB` | Stepped platforms for upward traversal; creates staircase of `TILE_PLATFORM` |
| `Z_CONNECTOR` | Horizontal platform at zone centre for hub rooms with three or more doors |

Connected edge zones (WALK, DOOR, SAVE, SHOP, LOOT) skip placing the floor tile when the zone sits on an edge that connects to an adjacent room, to avoid blocking the traversal opening.


## BFS Connectivity Validation

Implemented in `systems/connectivity.py` as `ConnectivityValidator`. The system tries three tiers in order.

**Tier 1 — Natural pathfinding** (`_tier1_natural_pathfinding`, line 254). Performs a BFS across actual tilemap cells starting from the centre of the first room. A tile is walkable if its ID is one of `TILE_EMPTY`, `TILE_LAVA`, `TILE_WATER`, `TILE_PLATFORM`, `TILE_PLATFORM_FALLING`, or `TILE_PLATFORM_MOVING` (not `TILE_SOLID`). The BFS crosses room boundaries by detecting when tile coordinates go out of range and translating to the neighbouring room. Returns the set of room grid coordinates reachable from the spawn room. If all rooms are reachable, tier 1 succeeds and no modifications are made.

**Tier 2 — Spine and stairs fallback** (`_tier2_spine_stairs`, line 317). Finds disconnected room clusters using graph BFS on `RoomNode.neighbors`. Identifies the largest cluster as the main component. For each isolated cluster, finds the closest pair of rooms (by Manhattan distance) and forces a bidirectional `neighbors` connection plus a `neighbor_dirs` entry. Re-runs tier 1 to confirm.

**Tier 3 — Nuclear option** (`_tier3_nuclear`, line 460). Iterates all rooms. For every spatially adjacent pair (grid distance 1 in any cardinal direction) that is not already connected, forces a bidirectional `neighbors` connection and `neighbor_dirs` entry. Guarantees connectivity because every spatially adjacent room will share a traversable edge, but it may override intentional layout choices.

The public convenience function is:

```python
from systems.connectivity import validate_world_connectivity
result = validate_world_connectivity(world, room_tilemaps, verbose=True)
# result.tier_used: "natural", "spine", or "nuclear"
# result.fixes_applied: count of changes made
```


## Autotiling

Implemented in `systems/autotiling.py`. The function `autotile_key(tilemap, x, y, tile_id)` examines the four cardinal neighbours of a tile. Out-of-bounds positions are treated as a different tile type (value -1), which creates edge shapes at room boundaries.

The algorithm:

1. Get `(up, down, left, right)` tile IDs from `get_neighbors()`.
2. If the tile above differs from `tile_id` → row is `"top"`. Else if tile below differs → row is `"bottom"`. Else → row is `"mid"`.
3. If the tile to the left differs → col is `"left"`. Else if tile to the right differs → col is `"right"`. Else → col is `"mid"`.
4. Return `f"{row}_{col}"`.

The nine possible keys correspond to the 3x3 tile sheet layout:

```
top_left    top_mid    top_right
mid_left    mid_mid    mid_right
bottom_left bottom_mid bottom_right
```

These names are expected to match asset file names or atlas frame names loaded by `rendering/tile_loader.py`.


## Spawner Systems

After tilemap generation, the world builder resolves anchors for enemy, pickup, and hazard spawners.

**Enemy anchors.** `RoomNode.anchors` contains named positions (pixel coordinates) placed by zone expansion at `WALK`, `COMBAT`, and similar zones. The `systems/anchor_resolution.py` module provides `AnchorCandidate` objects that are collected during zone planning and resolved globally (accounting for save-point spacing, etc.) by `WorldGenerator._resolve_world_anchors()`.

**Pickup spawners.** `systems/pickup_spawner.py` reads resolved anchor positions for `LOOT` and `SHOP` zones and places coin, health potion, and item chest entities at those positions.

**Hazard spawners.** `systems/hazard_spawner.py` reads `VOID` zone positions and the mission's `hazards` list to place spike, poison, and lava hazards.

Spawner behaviour per mission is also controlled by the mission's `enemy_types` and `hazards` fields in `data/missions.json`, which constrain which entity types are eligible at spawn time.


## Performance

World generation runs entirely in Python on the main thread before the level starts. Based on the codebase structure (tilemap streaming comments in `systems/tilemap_streaming.py`) a 30-room world at 128x128 tiles generates approximately 2-5 ms of CPU time on typical desktop hardware. Memory usage without streaming is approximately 92 MB for a 30x30 grid at this tile density; the streaming system in `systems/tilemap_streaming.py` reduces active memory to roughly 18 MB by evicting rooms outside a cache window.

The world is generated once per mission entry. Hub worlds are regenerated each time the player enters a hub (they are not cached between transitions).


## How to Create a Custom World Shape

**Step 1 — Add an enum value.** Add the new shape to `WorldShape` in `systems/world_generation.py` (line 39):

```python
class WorldShape(Enum):
    ...
    MY_SHAPE = "my_shape"
```

**Step 2 — Add shape parameters.** Add an entry to `SHAPE_PRESETS` (line 67):

```python
SHAPE_PRESETS = {
    ...
    WorldShape.MY_SHAPE: ShapeParams(rev=0.60, straight=0.50),
}
```

`rev` controls how often the generator picks from recent frontier entries (0.0 = always random, 1.0 = always most recent). `straight` controls how often it continues in the same direction (0.0 = always turns, 1.0 = always goes straight).

**Step 3 — Add optional frontier pruning.** In `_generate_room_graph()` (line 346), find the frontier pruning block and add a case for the new shape:

```python
elif shape == WorldShape.MY_SHAPE:
    if len(frontier) > 5 and self.rng.random() < 0.5:
        frontier.pop(self.rng.randrange(len(frontier)))
```

**Step 4 — Add optional directional override.** If the shape needs special direction-picking logic (like `SPIRAL`'s clockwise rotation), add a branch before line 372.

**Step 5 — Use it.** Pass the new shape to `WorldGenerator.generate()`:

```python
generator = WorldGenerator(seed)
world = generator.generate(num_biomes=1, rooms_per_biome=12, shape=WorldShape.MY_SHAPE)
```

Or reference it by string value in `data/missions.json` once a string-to-enum mapping is added to `MissionRegistry` or `world_builder.py`.


## Key Classes

| Class | File | Line | Responsibility |
| --- | --- | --- | --- |
| `WorldGenerator` | `systems/world_generation.py` | 226 | Top-level orchestrator. Generates room graph, biomes, door ports, anchors. |
| `ZonePlanner` | `systems/zone_planning.py` | 182 | Converts a `RoomNode` to a 16x16 zone grid. Applies logic rules. |
| `RoomGenerator` | `systems/room_generation.py` | 48 | Expands a zone grid to a 128x128 tilemap. Applies tile variation and liquid patches. |
| `ConnectivityValidator` | `systems/connectivity.py` | 67 | Three-tier BFS connectivity validation and repair. |
| `WorldShape` | `systems/world_generation.py` | 39 | Enum of generation shape presets. |
| `BiomeTheme` | `systems/world_generation.py` | 102 | Enum of visual/generation themes. |
| `RoomType` | `systems/world_generation.py` | 90 | Enum of room purposes. |
| `ZoneRole` | `systems/world_generation.py` | 77 | Enum of zone planning roles. |
| `RoomNode` | `systems/world_generation.py` | 150 | Data container for one room (grid position, zone grid, tilemap, anchors). |
| `World` | `systems/world_generation.py` | 199 | Data container for a complete generated world. |
| `Biome` | `systems/world_generation.py` | 183 | Data container grouping rooms by theme. |
| `SeedDerivation` | `systems/seed_hierarchy.py` | 26 | SHA-256-based deterministic seed derivation for the 6-level hierarchy. |
| `HubManager` | `game/hub_manager.py` | 98 | Registers hub definitions and calls WorldGenerator for hub worlds. |
| `PortalAnchor` | `game/hub_manager.py` | 52 | Pixel-level placement specification for a portal in a hub room. |
| `NPCAnchor` | `game/hub_manager.py` | 32 | Pixel-level placement specification for an NPC in a hub room. |
