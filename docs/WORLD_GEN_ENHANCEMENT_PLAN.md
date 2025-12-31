# World Generation Enhancement Plan
**Based on Dynamic Dungeon Platformer Analysis**

## Executive Summary

The dynamic dungeon platformer uses a sophisticated **zone-based procedural generation system** that we can integrate into our engine. This document outlines enhancements to adopt the most valuable techniques.

**Source Analysis**: [Deep Dive Report](../WORLD_GEN_ENHANCEMENT_PLAN.md)

---

## Current System vs. Enhanced System

### What We Have Now (v0.4.0-dev)

✅ **Completed**:
- Hierarchical world generation (World → Biomes → Rooms → Zones → Tilemap)
- Seed-based deterministic generation
- BFS connectivity validation
- Room type system (START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS)
- 16×16 zone grid per room
- Zone role system (WALK, FILL, PLAT, DOOR, SAVE, SHOP, LOOT)
- Door connection system
- Basic room generation from zones

### What We're Missing (High-Value Features)

❌ **Not Yet Implemented**:
1. **Context-Aware Zone Logic Rules**
2. **Two-Phase Anchor Resolution System**
3. **World Shape Algorithms** (snake, branchy, blob)
4. **3×3 Autotiling System**
5. **Three-Tier Connectivity Fallback**
6. **Megamap Stitching** (unified tilemap)
7. **Enhanced Minimap** (room type colors, player dot)
8. **Reachability-Based Pathfinding** (jump arc simulation)
9. **Zone Template System** (boss rooms)
10. **Deterministic Tile Variant Selection**

---

## Phase 1: Autotiling System (HIGHEST PRIORITY)

**Why First**: Most immediate visual impact, builds on our new 8×8 tileset

### Implementation Plan

#### 1.1 Define 3×3 Autotile Shapes

**File**: `systems/autotiling.py` (NEW)

```python
from typing import List, Tuple
from systems.room_generation import TILE_SOLID, TILE_PLATFORM

# 9-slice shape names
SHAPES_3X3 = [
    "top_left", "top_mid", "top_right",
    "mid_left", "mid_mid", "mid_right",
    "bottom_left", "bottom_mid", "bottom_right",
]

def get_neighbors(tilemap: List[List[int]], x: int, y: int) -> Tuple[int, int, int, int]:
    """Get tile IDs of 4-directional neighbors"""
    h, w = len(tilemap), len(tilemap[0])
    up = tilemap[y-1][x] if y > 0 else -1
    dn = tilemap[y+1][x] if y < h-1 else -1
    lf = tilemap[x][y-1] if x > 0 else -1
    rt = tilemap[x][y+1] if x < w-1 else -1
    return up, dn, lf, rt

def autotile_key(tilemap: List[List[int]], x: int, y: int, tile_id: int) -> str:
    """
    Determine which 3×3 autotile shape to use

    Args:
        tilemap: 2D tile array
        x, y: Tile position
        tile_id: Current tile type (TILE_SOLID or TILE_PLATFORM)

    Returns:
        Shape key like "top_left", "mid_mid", etc.
    """
    up, dn, lf, rt = get_neighbors(tilemap, x, y)

    # Determine row (vertical edge detection)
    if up != tile_id:
        row = "top"
    elif dn != tile_id:
        row = "bottom"
    else:
        row = "mid"

    # Determine column (horizontal edge detection)
    if lf != tile_id:
        col = "left"
    elif rt != tile_id:
        col = "right"
    else:
        col = "mid"

    return f"{row}_{col}"
```

#### 1.2 Organize Tileset by Autotile Shapes

**Current Structure**:
```
assets/biomes/dungeon/tile_r0_c0.png  (56 tiles)
assets/biomes/cave/tile_r4_c0.png     (71 tiles)
assets/biomes/building/tile_r8_c0.png (70 tiles)
```

**Target Structure**:
```
assets/biomes/<biome>/
    wall/
        top_left_01.png
        top_mid_01.png
        top_right_01.png
        mid_left_01.png
        mid_mid_01.png      # Interior tile
        mid_right_01.png
        bottom_left_01.png
        bottom_mid_01.png
        bottom_right_01.png
    platform/
        top_left_01.png
        top_mid_01.png
        ... (same 9 shapes)
    door/
        door_01.png
```

**Migration Script**: Manually categorize extracted tiles by visual appearance, or use all tiles for all shapes initially.

#### 1.3 Update TileLoader for Autotiling

**File**: `rendering/tile_loader.py`

Add new method:
```python
def get_autotiled_tile(self, biome: str, tile_type: str,
                       tilemap: List[List[int]], x: int, y: int,
                       tile_id: int, seed: int = 0) -> pygame.Surface:
    """
    Get tile with 3×3 autotiling

    Args:
        biome: Biome name
        tile_type: 'wall' or 'platform'
        tilemap: Full tilemap for neighbor detection
        x, y: Tile position
        tile_id: TILE_SOLID or TILE_PLATFORM
        seed: World seed for deterministic variants

    Returns:
        Scaled and autotiled pygame.Surface
    """
    from systems.autotiling import autotile_key

    # Determine autotile shape
    shape = autotile_key(tilemap, x, y, tile_id)

    # Get tile path with shape
    # Example: assets/biomes/dungeon/wall/top_left_01.png
    tile_path = self._get_autotile_path(biome, tile_type, shape, x, y, seed)

    if tile_path is None or not tile_path.exists():
        return self._get_fallback_tile(biome, tile_type)

    # Load and scale as usual
    cache_key = (biome, tile_type, shape, seed, x, y)
    if cache_key in self.cache:
        return self.cache[cache_key]

    tile_surface = self._load_and_scale_tile(tile_path)
    self.cache[cache_key] = tile_surface
    return tile_surface
```

#### 1.4 Deterministic Variant Selection

```python
def _get_autotile_path(self, biome: str, tile_type: str, shape: str,
                       x: int, y: int, seed: int) -> Path:
    """
    Get tile path with deterministic variant selection

    Uses large primes to hash position + seed for stable variants
    """
    # Hash position for deterministic variant
    hsh = (x * 73856093) ^ (y * 19349663) ^ (seed * 83492791)

    # Find all variants for this shape
    # Example: wall/top_left_01.png, wall/top_left_02.png, ...
    pattern = f"{tile_type}/{shape}_*.png"
    variants = sorted(self._biome_path(biome).glob(pattern))

    if not variants:
        return None

    # Select variant based on hash
    index = hsh % len(variants)
    return variants[index]
```

#### 1.5 Update Demo Renderer

**File**: `demo_game.py`

```python
# BEFORE (current):
for tile in tiles:
    screen_rect = camera.apply(tile)
    tile_index = (tile.x // 32 + tile.y // 32) % 3
    tile_surface = tile_loader.get_tile(current_biome, 'solid', tile_index)
    game_surface.blit(tile_surface, screen_rect)

# AFTER (with autotiling):
for tile in tiles:
    screen_rect = camera.apply(tile)
    tx, ty = tile.x // 32, tile.y // 32

    # Get autotiled tile based on neighbors
    tile_surface = tile_loader.get_autotiled_tile(
        biome=current_biome,
        tile_type='wall',  # or 'platform' for platforms
        tilemap=current_room.tilemap,
        x=tx, y=ty,
        tile_id=TILE_SOLID,
        seed=current_seed
    )
    game_surface.blit(tile_surface, screen_rect)
```

### Acceptance Criteria

- ✅ Tiles automatically select edge/corner shapes based on neighbors
- ✅ Interior tiles use `mid_mid` shape
- ✅ Corners use appropriate diagonal shapes
- ✅ Variants selected deterministically (same seed = same tiles)
- ✅ Performance: <1ms per tile with caching

---

## Phase 2: Context-Aware Zone Logic Rules

**Why Second**: Makes procedural generation feel more intelligent and intentional

### Implementation Plan

#### 2.1 Define Logic Rule Interface

**File**: `systems/zone_planning.py`

```python
from typing import Callable, Set
from dataclasses import dataclass

@dataclass
class RoomContext:
    """Context info for logic rules"""
    room_type: str
    neighbor_dirs: Set[str]  # {"up", "down", "left", "right"}
    degree: int  # Number of doors
    zone_grid: List[List[str]]
    zone_spec: 'ZoneGridSpec'

# Logic rule function signature
ZoneRuleFn = Callable[[RoomContext], None]

def rule_force_down_chute(ctx: RoomContext):
    """If DOWN door exists, force bottom-center zone to CHUTE"""
    if "down" not in ctx.neighbor_dirs:
        return

    zx, zy = ctx.zone_spec.zx, ctx.zone_spec.zy
    bottom_row = zy - 1
    center_col = zx // 2

    # Force bottom-center to CHUTE for vertical drop
    ctx.zone_grid[bottom_row][center_col] = "CHUTE"

def rule_force_up_climb(ctx: RoomContext):
    """If UP door exists, force top-center zone to CLIMB"""
    if "up" not in ctx.neighbor_dirs:
        return

    zx, zy = ctx.zone_spec.zx, ctx.zone_spec.zy
    top_row = 0
    center_col = zx // 2

    # Force top-center to CLIMB for vertical ascent
    ctx.zone_grid[top_row][center_col] = "CLIMB"

def rule_high_degree_connector(ctx: RoomContext):
    """If 3+ doors, force center to CONNECTOR (hub room)"""
    if ctx.degree < 3:
        return

    zx, zy = ctx.zone_spec.zx, ctx.zone_spec.zy
    center_x = zx // 2
    center_y = zy // 2

    # Hub rooms need strong horizontal connectivity
    ctx.zone_grid[center_y][center_x] = "CONNECTOR"

def rule_dead_end_bonus_corner(ctx: RoomContext):
    """If degree==1 (dead end), add secret in random corner"""
    if ctx.degree != 1:
        return

    import random
    zx, zy = ctx.zone_spec.zx, ctx.zone_spec.zy

    # Pick random corner
    corners = [(0, 0), (0, zy-1), (zx-1, 0), (zx-1, zy-1)]
    cx, cy = random.choice(corners)

    # Avoid door buffer zones
    if ctx.zone_grid[cy][cx] in ["ENTRY_BUFFER", "EXIT_BUFFER"]:
        return

    # Place secret stash in corner
    ctx.zone_grid[cy][cx] = "SECRET_STASH"
```

#### 2.2 Add Rules to Room Specs

**File**: `systems/zone_planning.py`

```python
ROOM_TYPE_SPECS = {
    "start": RoomZoneSpec(
        grid=ZoneGridSpec(3, 3),
        allowed_roles=["SPAWN_SAFE", "CONNECTOR", "CLIMB", "CHUTE", "DECOR"],
        mandatory=[...],
        optional_weights={...},
        logic_rules=[
            rule_force_down_chute,
            rule_force_up_climb,
        ]
    ),

    "shop": RoomZoneSpec(
        grid=ZoneGridSpec(3, 6),  # Tall room
        allowed_roles=["SHOPKEEPER", "SAVE_POINT", "SECRET_STASH", "DISPLAY", "DECOR"],
        mandatory=[...],
        optional_weights={...},
        logic_rules=[
            rule_high_degree_connector,
        ]
    ),

    "treasure": RoomZoneSpec(
        grid=ZoneGridSpec(3, 3),
        allowed_roles=["TREASURE_CORE", "SECRET_STASH", "CLIMB", "DECOR"],
        mandatory=[...],
        optional_weights={...},
        logic_rules=[
            rule_dead_end_bonus_corner,
        ]
    ),

    # ... more room types
}
```

#### 2.3 Execute Rules After Zone Assignment

```python
def assign_zone_roles(room_type: str, neighbor_dirs: Set[str],
                     seed: int) -> List[List[str]]:
    """Assign zone roles with context-aware rules"""

    spec = ROOM_TYPE_SPECS[room_type]
    zone_grid = _initial_assignment(spec, seed)  # Existing logic

    # Build context
    ctx = RoomContext(
        room_type=room_type,
        neighbor_dirs=neighbor_dirs,
        degree=len(neighbor_dirs),
        zone_grid=zone_grid,
        zone_spec=spec.grid
    )

    # Execute logic rules
    for rule in spec.logic_rules:
        rule(ctx)

    # Clamp to allowed roles (safety check)
    for zy in range(spec.grid.zy):
        for zx in range(spec.grid.zx):
            if zone_grid[zy][zx] not in spec.allowed_roles:
                # Fall back to most common allowed role
                zone_grid[zy][zx] = spec.allowed_roles[0]

    return zone_grid
```

### Acceptance Criteria

- ✅ DOWN doors automatically get CHUTE zones below
- ✅ UP doors automatically get CLIMB zones above
- ✅ Hub rooms (3+ doors) get CONNECTOR center zones
- ✅ Dead-end rooms get bonus SECRET_STASH in corners
- ✅ Rules execute after initial assignment
- ✅ Results clamped to allowed_roles for safety

---

## Phase 3: Two-Phase Anchor Resolution System

**Why Third**: Enables global decision-making (e.g., save point spacing)

### Implementation Plan

#### 3.1 Define Anchor Candidate System

**File**: `systems/anchor_resolution.py` (NEW)

```python
from dataclasses import dataclass
from typing import Tuple, Set, Dict, List, Optional

@dataclass
class AnchorCandidate:
    """Potential anchor placement from zone generation"""
    kind: str  # "shopkeeper", "save_point", "loot", "spawn", "exit"
    pos: Tuple[int, int]  # Tile coordinates within room
    weight: float  # Higher = more likely to resolve
    tags: Set[str]  # {"chest", "npc", "healing", "secret"}

@dataclass
class ResolvedAnchor:
    """Finalized anchor placement"""
    kind: str
    pos: Tuple[int, int]
    room_coords: Tuple[int, int]  # Room position in world grid
```

#### 3.2 Emit Candidates from Zone Generators

**File**: `systems/room_generation.py`

Modify zone generators to emit candidates:

```python
def generate_zone_tilemap(zone_role: str, zone_rect: Rect,
                         tilemap: List[List[int]],
                         rng: random.Random,
                         candidates: List[AnchorCandidate]) -> None:
    """
    Generate tilemap for a zone and emit anchor candidates

    Args:
        zone_role: Zone type (SPAWN_SAFE, SHOPKEEPER, etc.)
        zone_rect: Zone bounds in tile coordinates
        tilemap: Room tilemap to modify
        rng: Random number generator
        candidates: OUTPUT list to append candidates to
    """

    if zone_role == "SPAWN_SAFE":
        # ... generate safe platform ...
        spawn_x, spawn_y = _calculate_spawn_position(zone_rect)
        candidates.append(AnchorCandidate(
            kind="spawn",
            pos=(spawn_x, spawn_y),
            weight=1.0,
            tags={"safe"}
        ))

    elif zone_role == "SHOPKEEPER":
        # ... generate shop platform ...
        shop_x, shop_y = _calculate_shop_position(zone_rect)
        candidates.append(AnchorCandidate(
            kind="shopkeeper",
            pos=(shop_x, shop_y),
            weight=1.0,
            tags={"npc", "shop"}
        ))

    elif zone_role == "SAVE_POINT":
        # ... generate healing platform ...
        save_x, save_y = _calculate_save_position(zone_rect)
        candidates.append(AnchorCandidate(
            kind="save_point",
            pos=(save_x, save_y),
            weight=1.0,
            tags={"healing"}
        ))

        # Optional loot near save point (70% chance)
        if rng.random() < 0.7:
            loot_x = save_x + rng.randint(-3, 3)
            loot_y = save_y - 2
            candidates.append(AnchorCandidate(
                kind="loot",
                pos=(loot_x, loot_y),
                weight=0.6,
                tags={"chest"}
            ))

    elif zone_role == "SECRET_STASH":
        # ... generate hidden platform ...
        secret_x, secret_y = _calculate_secret_position(zone_rect)
        candidates.append(AnchorCandidate(
            kind="loot",
            pos=(secret_x, secret_y),
            weight=0.8,
            tags={"chest", "secret"}
        ))

    # ... other zone types ...
```

#### 3.3 World-Level Resolver

**File**: `systems/anchor_resolution.py`

```python
SAVE_POINT_PROXIMITY = 2  # Room distance

def resolve_world_features(rooms: Dict[Tuple[int,int], RoomNode],
                          seed: int) -> None:
    """
    Resolve anchor candidates globally with spacing constraints

    Modifies rooms in-place to set resolved_anchors
    """

    # Priority: START/SHOP first, COMBAT last
    priority_order = sorted(rooms.keys(), key=lambda rc: (
        rooms[rc].room_type not in ("start", "shop"),
        rooms[rc].room_type == "combat",
        rc[1], rc[0]  # Tiebreaker: top-left to bottom-right
    ))

    chosen_save_rooms: Set[Tuple[int,int]] = set()

    for room_coords in priority_order:
        room = rooms[room_coords]

        # Always resolve these
        _resolve_always(room, "shopkeeper")
        _resolve_always(room, "secret_stash")
        _resolve_always(room, "exit_portal")
        _resolve_always(room, "spawn")

        # Save points with proximity check
        save_candidate = _best_candidate(room, "save_point")

        if save_candidate is None:
            continue

        # Check if any save within PROXIMITY rooms
        too_close = False
        for other_coords in chosen_save_rooms:
            distance = _bfs_room_distance(rooms, room_coords, other_coords)
            if distance <= SAVE_POINT_PROXIMITY:
                too_close = True
                break

        if not too_close:
            room.resolved_anchors["save_point"] = save_candidate.pos
            chosen_save_rooms.add(room_coords)
        else:
            # Too close to existing save → convert to loot
            loot_candidate = _best_candidate(room, "loot")
            if loot_candidate:
                room.resolved_anchors["loot"] = loot_candidate.pos
            else:
                # No loot candidate → use save position for loot
                room.resolved_anchors["loot"] = save_candidate.pos

def _best_candidate(room: RoomNode, kind: str) -> Optional[AnchorCandidate]:
    """Get highest-weight candidate of given kind"""
    candidates = [c for c in room.anchor_candidates if c.kind == kind]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.weight)

def _resolve_always(room: RoomNode, kind: str) -> None:
    """Always place if candidate exists"""
    candidate = _best_candidate(room, kind)
    if candidate:
        room.resolved_anchors[kind] = candidate.pos

def _bfs_room_distance(rooms: Dict, start: Tuple[int,int],
                       end: Tuple[int,int]) -> int:
    """Calculate room-to-room distance via BFS"""
    from collections import deque

    queue = deque([(start, 0)])
    visited = {start}

    while queue:
        current, dist = queue.popleft()

        if current == end:
            return dist

        for neighbor in rooms[current].neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))

    return float('inf')  # Unreachable
```

### Acceptance Criteria

- ✅ Zone generators emit weighted anchor candidates
- ✅ Shopkeepers, exits, spawns always placed
- ✅ Save points spaced at least 2 rooms apart
- ✅ Excess save candidates converted to loot
- ✅ Highest-weight candidates selected
- ✅ Resolved anchors stored in room.resolved_anchors

---

## Phase 4: World Shape Algorithms

**Why Fourth**: Adds variety to world layouts (snake paths, branchy mazes, blob clusters)

### Implementation Plan

#### 4.1 Add Shape Parameters to WorldGenerator

**File**: `systems/world_generation.py`

```python
from enum import Enum

class WorldShape(Enum):
    SNAKE = "snake"      # Long winding paths
    BRANCHY = "branchy"  # Multiple branches
    BLOB = "blob"        # Clustered layout

@dataclass
class ShapeParams:
    """Parameters for world shape generation"""
    rev: float      # Probability to pick most recent frontier (0.0-1.0)
    straight: float # Probability to continue in same direction (0.0-1.0)

SHAPE_PRESETS = {
    WorldShape.SNAKE: ShapeParams(rev=0.80, straight=0.70),
    WorldShape.BRANCHY: ShapeParams(rev=0.25, straight=0.30),
    WorldShape.BLOB: ShapeParams(rev=0.40, straight=0.40),
}
```

#### 4.2 Modify Room Graph Generation

**File**: `systems/world_generation.py`

```python
def generate_room_graph(self, num_rooms: int, shape: WorldShape) -> Dict:
    """Generate room graph with specific world shape"""

    params = SHAPE_PRESETS[shape]
    rng = random.Random(self.seed)

    # Dynamic grid size based on room count
    base = max(8, int((num_rooms ** 0.5) * 3.0))
    grid_w = rng.randint(base, base + 6)
    grid_h = rng.randint(max(6, base - 2), base + 4)

    # Start room at center
    start_pos = (grid_w // 2, grid_h // 2)
    rooms = {start_pos: RoomNode(position=start_pos, room_type="start")}

    # Frontier: candidate positions for next room
    frontier = [start_pos]
    last_direction = None  # For directional continuity

    while len(rooms) < num_rooms:
        if not frontier:
            break  # Dead end (shouldn't happen with proper params)

        # Pick frontier room (recent vs random based on rev param)
        if rng.random() < params.rev:
            # Pick from last 6 rooms (snake-like)
            candidates = frontier[-min(6, len(frontier)):]
            current = rng.choice(candidates)
        else:
            # Pick random (more branching)
            current = rng.choice(frontier)

        # Determine next direction
        directions = self._available_directions(current, rooms, grid_w, grid_h)

        if not directions:
            frontier.remove(current)
            continue

        # Bias toward continuing in same direction (straight param)
        if last_direction and last_direction in directions:
            if rng.random() < params.straight:
                chosen_dir = last_direction
            else:
                chosen_dir = rng.choice(directions)
        else:
            chosen_dir = rng.choice(directions)

        # Place new room
        new_pos = self._apply_direction(current, chosen_dir)
        rooms[new_pos] = RoomNode(position=new_pos)

        # Connect rooms
        rooms[current].neighbors.append(new_pos)
        rooms[new_pos].neighbors.append(current)

        # Update frontier
        frontier.append(new_pos)

        # Prune frontier based on shape
        if shape == WorldShape.SNAKE:
            # Keep last 6 rooms only
            if len(frontier) > 6:
                frontier = frontier[-6:]
        elif shape in (WorldShape.BRANCHY, WorldShape.BLOB):
            # Random pruning to prevent runaway growth
            if len(frontier) > 8 and rng.random() < 0.3:
                frontier.pop(rng.randint(0, len(frontier)-1))

        last_direction = chosen_dir

    return rooms

def _available_directions(self, pos: Tuple[int,int], rooms: Dict,
                         grid_w: int, grid_h: int) -> List[str]:
    """Get valid placement directions from current position"""
    x, y = pos
    directions = []

    # Check each cardinal direction
    if y > 1 and (x, y-1) not in rooms:
        directions.append("up")
    if y < grid_h - 2 and (x, y+1) not in rooms:
        directions.append("down")
    if x > 1 and (x-1, y) not in rooms:
        directions.append("left")
    if x < grid_w - 2 and (x+1, y) not in rooms:
        directions.append("right")

    return directions

def _apply_direction(self, pos: Tuple[int,int], direction: str) -> Tuple[int,int]:
    """Apply direction to get new position"""
    x, y = pos
    if direction == "up": return (x, y - 1)
    elif direction == "down": return (x, y + 1)
    elif direction == "left": return (x - 1, y)
    elif direction == "right": return (x + 1, y)
    return pos
```

#### 4.3 CLI Support for World Shapes

**File**: `demo_game.py`

```python
parser.add_argument('--shape', type=str, default='blob',
                   choices=['snake', 'branchy', 'blob'],
                   help='World shape style')

# Usage:
# python demo_game.py --procedural --shape snake --seed 12345
```

### Acceptance Criteria

- ✅ SNAKE generates long winding paths with few branches
- ✅ BRANCHY generates maze-like interconnected rooms
- ✅ BLOB generates clustered layouts
- ✅ Directional continuity creates natural-feeling paths
- ✅ Grid safety margins prevent edge placements
- ✅ CLI flag supports shape selection

---

## Phase 5: Megamap Stitching

**Why Fifth**: Simplifies collision and enables seamless world traversal

### Implementation Plan

#### 5.1 Build Unified Tilemap

**File**: `systems/world_generation.py`

```python
def build_megamap(rooms: Dict[Tuple[int,int], RoomNode]) -> List[List[int]]:
    """
    Stitch all room tilemaps into single unified tilemap

    Args:
        rooms: Dictionary of room nodes

    Returns:
        2D array containing full world tilemap
    """

    # Find world bounding box
    minx = min(x for x, y in rooms.keys())
    miny = min(y for x, y in rooms.keys())
    maxx = max(x for x, y in rooms.keys())
    maxy = max(y for x, y in rooms.keys())

    spanw = maxx - minx + 1
    spanh = maxy - miny + 1

    # Room dimensions in tiles
    ROOM_W_TILES = 52  # From ROOM_GENERATION.md
    ROOM_H_TILES = 30

    # Allocate megamap
    mega_w = spanw * ROOM_W_TILES
    mega_h = spanh * ROOM_H_TILES
    megamap = [[TILE_EMPTY for _ in range(mega_w)] for _ in range(mega_h)]

    # Copy each room tilemap to correct offset
    for (rx, ry), room in rooms.items():
        ox = (rx - minx) * ROOM_W_TILES
        oy = (ry - miny) * ROOM_H_TILES

        for y in range(ROOM_H_TILES):
            for x in range(ROOM_W_TILES):
                megamap[oy + y][ox + x] = room.tilemap[y][x]

    return megamap
```

#### 5.2 Update Collision System

**File**: `systems/collision_system.py`

```python
class CollisionSystem:
    def set_megamap(self, megamap: List[List[int]]):
        """
        Set collision from unified megamap

        Args:
            megamap: Full world tilemap
        """
        self.tiles = []
        self.platforms = []

        h, w = len(megamap), len(megamap[0])

        for y in range(h):
            for x in range(w):
                tile_id = megamap[y][x]

                if tile_id == TILE_SOLID:
                    rect = pygame.Rect(x * 32, y * 32, 32, 32)
                    self.tiles.append(rect)

                elif tile_id == TILE_PLATFORM:
                    rect = pygame.Rect(x * 32, y * 32, 32, 32)
                    self.platforms.append(rect)
```

#### 5.3 Update Camera for Megamap

**File**: `systems/camera_system.py`

```python
def set_megamap_bounds(self, megamap: List[List[int]]):
    """Set camera bounds from megamap dimensions"""
    h, w = len(megamap), len(megamap[0])
    self.world_bounds = pygame.Rect(0, 0, w * 32, h * 32)
```

### Acceptance Criteria

- ✅ All rooms stitched into single tilemap
- ✅ Door overlaps create seamless connections
- ✅ Collision system uses unified tilemap
- ✅ Camera bounds cover entire megamap
- ✅ No room transition logic needed
- ✅ Performance: <50ms to build megamap for 30 rooms

---

## Phase 6: Enhanced Minimap

**Why Sixth**: Improves player navigation and spatial awareness

### Implementation Plan

#### 6.1 Room Type Color Coding

**File**: `rendering/minimap.py` (NEW)

```python
from typing import Dict, Tuple
import pygame

ROOM_COLORS = {
    "start": (120, 220, 140),    # Green
    "exit": (240, 120, 120),     # Red
    "shop": (220, 200, 120),     # Yellow
    "treasure": (120, 200, 220), # Cyan
    "boss": (220, 120, 220),     # Magenta
    "platform": (160, 160, 220), # Blue
    "combat": (170, 170, 170)    # Gray
}

def draw_minimap(screen: pygame.Surface,
                rooms: Dict[Tuple[int,int], RoomNode],
                current_room_coords: Tuple[int,int],
                player_rect: pygame.Rect,
                cell_size: int = 10) -> None:
    """
    Draw minimap overlay in top-right corner

    Args:
        screen: Display surface
        rooms: Dictionary of room nodes
        current_room_coords: Player's current room position
        player_rect: Player bounding box (for sub-room position)
        cell_size: Size of each room cell in pixels
    """

    # Calculate minimap dimensions
    minx = min(x for x, y in rooms.keys())
    miny = min(y for x, y in rooms.keys())
    maxx = max(x for x, y in rooms.keys())
    maxy = max(y for x, y in rooms.keys())

    spanw = maxx - minx + 1
    spanh = maxy - miny + 1

    map_w = spanw * cell_size + 20  # +20 for padding
    map_h = spanh * cell_size + 20

    # Create semi-transparent surface
    minimap_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    minimap_surf.fill((15, 15, 18, 140))  # Dark background

    # Draw room connections (white lines)
    for (rx, ry), room in rooms.items():
        cx = 10 + (rx - minx) * cell_size + cell_size // 2
        cy = 10 + (ry - miny) * cell_size + cell_size // 2

        for neighbor_coords in room.neighbors:
            nx, ny = neighbor_coords
            ncx = 10 + (nx - minx) * cell_size + cell_size // 2
            ncy = 10 + (ny - miny) * cell_size + cell_size // 2

            # Only draw once (avoid duplicates)
            if neighbor_coords > (rx, ry):
                pygame.draw.line(minimap_surf, (255, 255, 255, 60),
                               (cx, cy), (ncx, ncy), 2)

    # Draw room cells with type colors
    for (rx, ry), room in rooms.items():
        cx = 10 + (rx - minx) * cell_size
        cy = 10 + (ry - miny) * cell_size

        color = ROOM_COLORS.get(room.room_type, (100, 100, 100))

        # Fill room cell
        rect = pygame.Rect(cx, cy, cell_size, cell_size)
        pygame.draw.rect(minimap_surf, (*color, 180), rect)
        pygame.draw.rect(minimap_surf, (255, 255, 255, 100), rect, 1)

    # Highlight current room
    crx, cry = current_room_coords
    cur_cx = 10 + (crx - minx) * cell_size
    cur_cy = 10 + (cry - miny) * cell_size
    highlight_rect = pygame.Rect(cur_cx - 2, cur_cy - 2,
                                 cell_size + 4, cell_size + 4)
    pygame.draw.rect(minimap_surf, (255, 255, 255, 240),
                    highlight_rect, 2, border_radius=4)

    # Draw player position dot (within current room)
    current_room = rooms[current_room_coords]
    room_px_w = len(current_room.tilemap[0]) * 32
    room_px_h = len(current_room.tilemap) * 32

    # Calculate player position relative to current room origin
    room_origin_x = crx * room_px_w
    room_origin_y = cry * room_px_h
    rel_x = max(0, min(room_px_w - 1, player_rect.centerx - room_origin_x))
    rel_y = max(0, min(room_px_h - 1, player_rect.centery - room_origin_y))

    # Map to minimap cell
    dot_x = cur_cx + int((rel_x / room_px_w) * cell_size)
    dot_y = cur_cy + int((rel_y / room_px_h) * cell_size)

    # Two-layer dot (dark core + bright center)
    pygame.draw.circle(minimap_surf, (15, 15, 18, 230),
                      (dot_x, dot_y), cell_size // 5)
    pygame.draw.circle(minimap_surf, (245, 245, 250, 230),
                      (dot_x, dot_y), cell_size // 7)

    # Blit to top-right corner
    screen_w, screen_h = screen.get_size()
    screen.blit(minimap_surf, (screen_w - map_w - 10, 10))
```

#### 6.2 Integrate with Demo

**File**: `demo_game.py`

```python
from rendering.minimap import draw_minimap

# In main game loop, after HUD rendering:
if use_procedural:
    # Determine current room coords
    player_world_x = player.state.physics.x
    player_world_y = player.state.physics.y
    current_room_coords = (
        int(player_world_x // (52 * 32)),
        int(player_world_y // (30 * 32))
    )

    # Draw minimap
    draw_minimap(
        screen=screen,
        rooms=world.all_rooms,  # Need to store this from world gen
        current_room_coords=current_room_coords,
        player_rect=player.get_rect(),
        cell_size=10
    )
```

### Acceptance Criteria

- ✅ Minimap shows all rooms with type-based colors
- ✅ Room connections drawn as white lines
- ✅ Current room highlighted with white border
- ✅ Player position shown as two-layer dot within room cell
- ✅ Semi-transparent overlay in top-right corner
- ✅ Updates every frame

---

## Phase 7: Three-Tier Connectivity Fallback

**Why Seventh**: Guarantees playability even with difficult layouts

### Implementation Plan

#### 7.1 Natural Reachability Check

**File**: `systems/connectivity.py` (NEW)

```python
from typing import List, Tuple, Set
import pygame

@dataclass
class JumpConfig:
    """Player jump/movement capabilities"""
    dx: int = 7        # Max horizontal jump distance (tiles)
    dy_up: int = 4     # Max jump height (tiles)
    drop: int = 14     # Max fall distance (tiles)
    samples: int = 10  # Arc collision samples

def is_reachable(tilemap: List[List[int]],
                start: Tuple[int,int],
                targets: List[Tuple[int,int]],
                cfg: JumpConfig) -> bool:
    """
    Check if all targets reachable from start via BFS with jump simulation

    Args:
        tilemap: Room tilemap
        start: Starting tile position
        targets: List of required reachable positions
        cfg: Jump configuration

    Returns:
        True if all targets reachable
    """

    # Find all standable tiles
    standables = _find_standable_tiles(tilemap)

    # BFS from start
    reachable = _bfs_reachable(tilemap, start, standables, cfg)

    # Check if all targets reached
    return all(t in reachable for t in targets)
```

#### 7.2 Spine System

**File**: `systems/connectivity.py`

```python
def ensure_spine(tilemap: List[List[int]],
                downholes: List[int]) -> int:
    """
    Create horizontal platform at h-3 spanning entire room

    Args:
        tilemap: Room tilemap to modify
        downholes: X positions where DOWN doors exist (skip these)

    Returns:
        Y position of spine
    """
    h, w = len(tilemap), len(tilemap[0])
    spine_y = h - 3

    for x in range(1, w - 1):
        # Skip DOWN door holes
        if x in downholes:
            continue

        # Place platform tile
        if tilemap[spine_y][x] == TILE_EMPTY:
            tilemap[spine_y][x] = TILE_PLATFORM

        # Clear above spine (2 tiles)
        for clear_y in range(max(1, spine_y - 2), spine_y):
            if tilemap[clear_y][x] != TILE_SOLID:
                tilemap[clear_y][x] = TILE_EMPTY

    return spine_y
```

#### 7.3 Zigzag Stairs

**File**: `systems/connectivity.py`

```python
def carve_stairs(tilemap: List[List[int]],
                target_x: int, target_y: int,
                spine_y: int, cfg: JumpConfig) -> None:
    """
    Carve zigzag platforms from spine to target

    Args:
        tilemap: Room tilemap to modify
        target_x, target_y: Destination position
        spine_y: Spine platform Y position
        cfg: Jump configuration (for step height)
    """
    w = len(tilemap[0])
    step = max(2, min(3, cfg.dy_up))  # Step height 2-3 tiles

    y = spine_y
    i = 0

    # Calculate zigzag anchor points (±3 from target)
    xa = max(2, min(w - 3, target_x - 3))
    xb = max(2, min(w - 3, target_x + 3))

    # Zigzag upward
    while y - step > target_y:
        y -= step
        x = xa if i % 2 == 0 else xb
        _place_platform(tilemap, x, y, width=5)
        i += 1

    # Final platform at target
    _place_platform(tilemap, target_x, target_y, width=5)

def _place_platform(tilemap: List[List[int]],
                   x: int, y: int, width: int) -> None:
    """Place horizontal platform centered at x, y"""
    w = len(tilemap[0])
    half = width // 2

    for px in range(max(1, x - half), min(w - 1, x + half + 1)):
        if tilemap[y][px] == TILE_EMPTY:
            tilemap[y][px] = TILE_PLATFORM

        # Clear above platform
        if y > 1 and tilemap[y - 1][px] != TILE_SOLID:
            tilemap[y - 1][px] = TILE_EMPTY
```

#### 7.4 Three-Tier System

**File**: `systems/connectivity.py`

```python
def ensure_connectivity(tilemap: List[List[int]],
                       doors: List[Tuple[int,int]],
                       required_anchors: Set[Tuple[int,int]],
                       cfg: JumpConfig) -> None:
    """
    Guarantee connectivity using three-tier fallback system

    Tier 1: Natural reachability (do nothing if already connected)
    Tier 2: Spine + stairs
    Tier 3: Nuclear fallback (clear and rebuild)

    Args:
        tilemap: Room tilemap to modify in-place
        doors: Door positions
        required_anchors: Resolved anchor positions (must be reachable)
        cfg: Jump configuration
    """

    # Combine all required positions
    all_targets = set(doors) | required_anchors

    if not all_targets:
        return  # No targets, nothing to connect

    # Pick arbitrary start (first door or anchor)
    start = list(all_targets)[0]
    targets = list(all_targets - {start})

    # TIER 1: Check natural reachability
    if is_reachable(tilemap, start, targets, cfg):
        return  # Already connected, do nothing

    print(f"[CONNECTIVITY] Tier 1 failed, applying Tier 2 (spine + stairs)")

    # TIER 2: Spine + stairs
    downholes = _get_downhole_x_positions(tilemap, doors)
    spine_y = ensure_spine(tilemap, downholes)

    for tx, ty in targets:
        carve_stairs(tilemap, tx, ty, spine_y, cfg)

    # Re-check reachability
    if is_reachable(tilemap, start, targets, cfg):
        return  # Tier 2 succeeded

    print(f"[CONNECTIVITY] Tier 2 failed, applying Tier 3 (nuclear rebuild)")

    # TIER 3: Nuclear fallback
    _nuclear_clear(tilemap)

    # Rebuild from scratch
    spine_y = ensure_spine(tilemap, downholes)
    for tx, ty in all_targets:
        carve_stairs(tilemap, tx, ty, spine_y, cfg)

    # Place doors at their positions
    for dx, dy in doors:
        tilemap[dy][dx] = TILE_DOOR

def _nuclear_clear(tilemap: List[List[int]]) -> None:
    """Clear entire room interior (preserve border walls)"""
    h, w = len(tilemap), len(tilemap[0])

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if tilemap[y][x] not in (TILE_SOLID, TILE_DOOR):
                tilemap[y][x] = TILE_EMPTY
```

### Acceptance Criteria

- ✅ Tier 1: Most rooms naturally connected (no modification)
- ✅ Tier 2: Spine + stairs fix 95% of connectivity issues
- ✅ Tier 3: Nuclear fallback guarantees 100% connectivity
- ✅ All doors and resolved anchors reachable
- ✅ Performance: <5ms per room for connectivity check

---

## Implementation Priority & Timeline

### Immediate (Week 1-2):
1. **Phase 1: Autotiling** - Biggest visual impact
2. **Phase 2: Logic Rules** - Enhances procedural quality

### Near-Term (Week 3-4):
3. **Phase 3: Anchor Resolution** - Enables save point spacing
4. **Phase 6: Enhanced Minimap** - Improves UX

### Medium-Term (Week 5-6):
5. **Phase 4: World Shapes** - Adds layout variety
6. **Phase 5: Megamap** - Simplifies architecture

### Long-Term (Week 7-8):
7. **Phase 7: Connectivity** - Playability guarantee

---

## Success Metrics

### Visual Quality
- ✅ Autotiled edges create cohesive terrain
- ✅ Minimap provides clear spatial information
- ✅ Tile variants prevent repetitive visuals

### Procedural Quality
- ✅ Logic rules create intentional-feeling layouts
- ✅ World shapes offer distinct exploration experiences
- ✅ Save points feel well-spaced

### Technical Quality
- ✅ All generated rooms playable (100% connectivity)
- ✅ Performance maintains 60 FPS
- ✅ Memory usage scales linearly with world size

### Code Quality
- ✅ Systems remain modular and extensible
- ✅ Comprehensive test coverage
- ✅ Documentation kept up-to-date

---

**Next Step**: Implement **Phase 1: Autotiling System** for immediate visual improvement.
