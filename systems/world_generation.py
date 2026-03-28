"""
World Generation System - Procedural Metroidvania Worlds

Hierarchical generation system:
  World → Biomes → Rooms → Zone Grid (16x16) → Tilemap

Features:
- Seed-based deterministic generation
- Multiple biome themes (dungeon, cave, building)
- Intelligent room layout via zone planning
- Connectivity validation (BFS)
- Room types (start, exit, shop, combat, platform, treasure, boss)
- Door connection system with multiple ports

Source: Dynamic dungeon platformer project
Enhanced: Added biome layer for metroidvania structure
         Increased zone grid to 16×16 for finer granularity
"""

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from config.physics_constants import TILES_PER_ZONE

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from systems.anchor_resolution import AnchorCandidate


# ==========================================================
# Enums and Constants
# ==========================================================


class WorldShape(Enum):
    """World shape generation styles"""

    SNAKE = "snake"  # Long winding paths with few branches
    BRANCHY = "branchy"  # Maze-like interconnected rooms
    BLOB = "blob"  # Clustered layout
    SPIRAL = "spiral"  # Rotating spiral pattern
    TREE = "tree"  # Branching tree structure
    GRID = "grid"  # Structured grid-like layout


@dataclass
class ShapeParams:
    """
    Parameters for world shape generation

    Attributes:
        rev: Probability to pick most recent frontier (0.0-1.0)
             High = snake-like, Low = branchy
        straight: Probability to continue in same direction (0.0-1.0)
                 High = long corridors, Low = winding paths
    """

    rev: float  # Pick recent frontier probability
    straight: float  # Continue same direction probability


# World shape presets (from source analysis + new designs)
SHAPE_PRESETS = {
    WorldShape.SNAKE: ShapeParams(rev=0.80, straight=0.70),
    WorldShape.BRANCHY: ShapeParams(rev=0.25, straight=0.30),
    WorldShape.BLOB: ShapeParams(rev=0.40, straight=0.40),
    WorldShape.SPIRAL: ShapeParams(rev=0.90, straight=0.15),  # Very recent, frequent turns
    WorldShape.TREE: ShapeParams(rev=0.10, straight=0.60),  # Random selection, long branches
    WorldShape.GRID: ShapeParams(rev=0.50, straight=0.85),  # Balanced, very straight
}


class ZoneRole(Enum):
    """Zone roles for 16x16 planning grid"""

    WALK = "walk"  # Walkable floor
    FILL = "fill"  # Solid terrain
    PLAT = "platform"  # Platform (can jump through)
    DOOR = "door"  # Door connection
    SAVE = "save"  # Save point
    SHOP = "shop"  # Shop location
    LOOT = "loot"  # Treasure
    VOID = "void"  # Empty space (pits)


class RoomType(Enum):
    """Room types for world generation"""

    START = "start"
    EXIT = "exit"
    SHOP = "shop"
    COMBAT = "combat"
    PLATFORM = "platform"
    TREASURE = "treasure"
    BOSS = "boss"


class BiomeTheme(Enum):
    """Biome themes with unique generation patterns"""

    DUNGEON = "dungeon"
    CAVE = "cave"
    BUILDING = "building"
    FOREST = "forest"
    TOWN = "town"
    SEWER = "sewer"
    HOLLOW = "hollow"


# Zone grid constants - increased from 5×5 to 16×16 for finer granularity
ZONES_W = 16
ZONES_H = 16


# Directions
DIRS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


# ==========================================================
# Data Structures
# ==========================================================


@dataclass
class DoorPort:
    """
    A door port on a room edge.

    Attributes:
        side: "up", "down", "left", or "right"
        center_tile: Tile index at center of door
        span_tiles: How many tiles wide the door is
    """

    side: str
    center_tile: int
    span_tiles: int = max(3, TILES_PER_ZONE - 1)


@dataclass
class RoomNode:
    """
    A single room in the procedural world.

    Attributes:
        grid_x, grid_y: Position in world grid
        room_type: Type of room (start, exit, shop, etc.)
        biome_theme: Which biome this room belongs to
        seed: Random seed for this specific room
        neighbors: Set of (x, y) coordinates of adjacent rooms
        neighbor_dirs: Map of direction -> neighbor coordinate
        door_ports: Map of direction -> list of door ports
        zone_grid: 5x5 grid of zone roles
        tilemap: Generated tile map (None until generated)
        anchors: Special positions (spawn, shop, loot, etc.)
    """

    grid_x: int
    grid_y: int
    room_type: RoomType
    biome_theme: BiomeTheme
    seed: int
    neighbors: set[tuple[int, int]] = field(default_factory=set)
    neighbor_dirs: dict[str, tuple[int, int]] = field(default_factory=dict)
    door_ports: dict[str, list[DoorPort]] = field(default_factory=dict)
    zone_grid: list[list[ZoneRole]] | None = None
    tilemap: list[list[int]] | None = None
    anchors: dict[str, tuple[int, int]] = field(default_factory=dict)
    # Two-phase anchor resolution
    anchor_candidates: list["AnchorCandidate"] = field(default_factory=list)
    resolved_anchors: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class Biome:
    """
    A thematic region of the world.

    Attributes:
        theme: Visual/generation theme (dungeon, cave, building)
        rooms: List of rooms in this biome
        start_room: The entry room for this biome
    """

    theme: BiomeTheme
    rooms: list[RoomNode]
    start_room: RoomNode


@dataclass
class World:
    """
    Complete procedural world.

    Attributes:
        seed: Random seed for entire world
        biomes: List of biome regions
        all_rooms: Flat list of all rooms (for quick access)
        start_room: Global starting room (in first biome)
        exit_room: Global exit room (in last biome)
        bounds: World bounds (minx, miny, maxx, maxy) in grid coordinates
    """

    seed: int
    biomes: list[Biome]
    all_rooms: list[RoomNode]
    start_room: RoomNode
    exit_room: RoomNode
    bounds: tuple[int, int, int, int]  # minx, miny, maxx, maxy


# ==========================================================
# World Generator
# ==========================================================


class WorldGenerator:
    """
    Generates procedural metroidvania worlds with multiple biomes.

    Usage:
        generator = WorldGenerator(seed=12345)
        world = generator.generate(num_biomes=3, rooms_per_biome=10, shape=WorldShape.SNAKE)
    """

    def __init__(self, seed: int):
        """
        Initialize world generator.

        Args:
            seed: Random seed for deterministic generation
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def generate(
        self,
        num_biomes: int = 3,
        rooms_per_biome: int = 12,
        shape: WorldShape = WorldShape.BLOB,
        biome_theme: "BiomeTheme | None" = None,
    ) -> World:
        """
        Generate complete world with biomes.

        Args:
            num_biomes: Number of biome regions (1-5 recommended)
            rooms_per_biome: Average rooms per biome (8-15 recommended)
            shape: World shape style (SNAKE, BRANCHY, or BLOB)
            biome_theme: Force all rooms to this theme (used by single-biome hub generation)

        Returns:
            Complete World object with all biomes and rooms
        """
        # Generate room graph with specified shape
        total_rooms = num_biomes * rooms_per_biome

        rooms_dict, start_pos, exit_pos, bounds = self._generate_room_graph(total_rooms, shape)

        # Divide rooms into biomes
        all_rooms_list = list(rooms_dict.values())
        biomes = self._create_biomes(all_rooms_list, num_biomes, forced_theme=biome_theme)

        # Set start and exit rooms
        start_room = rooms_dict[start_pos]
        exit_room = rooms_dict[exit_pos]

        # Assign neighbor directions
        for room in all_rooms_list:
            room.neighbor_dirs = self._compute_neighbor_dirs(room)

        # Assign door ports
        self._assign_door_ports(rooms_dict)

        # Resolve anchors globally (save point spacing, etc.)
        self._resolve_world_anchors(rooms_dict)

        return World(
            seed=self.seed,
            biomes=biomes,
            all_rooms=all_rooms_list,
            start_room=start_room,
            exit_room=exit_room,
            bounds=bounds,
        )

    def _generate_room_graph(
        self, room_count: int, shape: WorldShape
    ) -> tuple[
        dict[tuple[int, int], RoomNode], tuple[int, int], tuple[int, int], tuple[int, int, int, int]
    ]:
        """
        Generate room graph with specific world shape.

        Args:
            room_count: Number of rooms to generate
            shape: World shape style (SNAKE, BRANCHY, or BLOB)

        Returns:
            (rooms_dict, start_pos, exit_pos, bounds)
        """
        # Get shape parameters
        params = SHAPE_PRESETS[shape]

        # Dynamic grid size based on room count
        base = max(8, int((room_count**0.5) * 3.0))
        grid_w = self.rng.randint(base, base + 6)
        grid_h = self.rng.randint(max(6, base - 2), base + 4)

        # Start room at center
        sx, sy = grid_w // 2, grid_h // 2

        # Create start room
        rooms: dict[tuple[int, int], RoomNode] = {}
        rooms[(sx, sy)] = RoomNode(
            grid_x=sx,
            grid_y=sy,
            room_type=RoomType.START,
            biome_theme=BiomeTheme.DUNGEON,  # Temporary, assigned later
            seed=self.rng.randrange(10**9),
        )

        # Frontier-based room generation with shape parameters
        frontier = [(sx, sy)]
        last_direction = None  # For directional continuity

        logger.debug(
            "[WORLD SHAPE] Generating %s world (rev=%.2f, straight=%.2f, grid=%sx%s, target=%s)",
            shape.value.upper(),
            params.rev,
            params.straight,
            grid_w,
            grid_h,
            room_count,
        )

        while len(rooms) < room_count and frontier:
            # Pick frontier room based on shape parameters
            if self.rng.random() < params.rev:
                # Pick from recent rooms (snake-like)
                candidates = frontier[-min(6, len(frontier)) :]
                current = self.rng.choice(candidates)
            else:
                # Pick random (more branching)
                current = self.rng.choice(frontier)

            # Get available directions
            directions = self._available_directions(current, rooms, grid_w, grid_h)

            if not directions:
                frontier.remove(current)
                continue

            # Choose direction with bias toward continuing straight
            if shape == WorldShape.SPIRAL and last_direction:
                # SPIRAL: Rotate clockwise through directions
                rotation = {"up": "right", "right": "down", "down": "left", "left": "up"}
                preferred = rotation.get(last_direction)
                if preferred and preferred in directions:
                    chosen_dir = preferred
                else:
                    chosen_dir = self.rng.choice(directions)
            elif last_direction and last_direction in directions:
                if self.rng.random() < params.straight:
                    chosen_dir = last_direction
                else:
                    chosen_dir = self.rng.choice(directions)
            else:
                chosen_dir = self.rng.choice(directions)

            # Place new room
            new_pos = self._apply_direction(current, chosen_dir)
            nx, ny = new_pos

            rooms[new_pos] = RoomNode(
                grid_x=nx,
                grid_y=ny,
                room_type=RoomType.COMBAT,  # Default type, specialized later
                biome_theme=BiomeTheme.DUNGEON,  # Temporary
                seed=self.rng.randrange(10**9),
            )

            # Connect rooms bidirectionally
            rooms[current].neighbors.add(new_pos)
            rooms[new_pos].neighbors.add(current)

            # Update frontier
            frontier.append(new_pos)

            # Prune frontier based on shape
            if shape == WorldShape.SNAKE:
                # Keep only last 6 rooms (creates long winding paths)
                if len(frontier) > 6:
                    frontier = frontier[-6:]
            elif shape == WorldShape.SPIRAL:
                # Keep only last 3 rooms (tight spiral)
                if len(frontier) > 3:
                    frontier = frontier[-3:]
            elif shape == WorldShape.TREE:
                # Keep many branches but prune occasionally
                if len(frontier) > 12 and self.rng.random() < 0.2:
                    frontier.pop(self.rng.randrange(len(frontier)))
            elif shape == WorldShape.GRID:
                # Moderate pruning for grid structure
                if len(frontier) > 6 and self.rng.random() < 0.4:
                    frontier.pop(self.rng.randrange(len(frontier)))
            elif shape in (WorldShape.BRANCHY, WorldShape.BLOB):
                # Random pruning to prevent runaway growth
                if len(frontier) > 8 and self.rng.random() < 0.3:
                    frontier.pop(self.rng.randrange(len(frontier)))

            last_direction = chosen_dir

        # Compute bounds
        coords = list(rooms.keys())
        minx = min(x for x, _ in coords)
        maxx = max(x for x, _ in coords)
        miny = min(y for _, y in coords)
        maxy = max(y for _, y in coords)
        bounds = (minx, miny, maxx, maxy)

        # Assign exit room (farthest from start)
        ex, ey = max(coords, key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))
        rooms[(ex, ey)].room_type = RoomType.EXIT

        # Assign special room types
        candidates = [p for p in coords if p not in [(sx, sy), (ex, ey)]]
        self.rng.shuffle(candidates)

        def take(n: int) -> list[tuple[int, int]]:
            """Take n candidates from the list."""
            nonlocal candidates
            n = max(0, min(n, len(candidates)))
            out = candidates[:n]
            candidates = candidates[n:]
            return out

        # Assign room types (from source distribution)
        for p in take(max(1, room_count // 10)):
            rooms[p].room_type = RoomType.SHOP
        for p in take(max(1, room_count // 12)):
            rooms[p].room_type = RoomType.TREASURE
        for p in take(max(1, room_count // 16)):
            rooms[p].room_type = RoomType.BOSS
        for p in take(max(2, room_count // 4)):
            rooms[p].room_type = RoomType.PLATFORM

        return rooms, (sx, sy), (ex, ey), bounds

    def _available_directions(
        self, pos: tuple[int, int], rooms: dict[tuple[int, int], RoomNode], grid_w: int, grid_h: int
    ) -> list[str]:
        """
        Get valid placement directions from current position.

        Args:
            pos: Current position (x, y)
            rooms: Dictionary of existing rooms
            grid_w: Grid width
            grid_h: Grid height

        Returns:
            List of valid direction names
        """
        x, y = pos
        directions = []

        # Check each cardinal direction with safety margins
        if y > 1 and (x, y - 1) not in rooms:
            directions.append("up")
        if y < grid_h - 2 and (x, y + 1) not in rooms:
            directions.append("down")
        if x > 1 and (x - 1, y) not in rooms:
            directions.append("left")
        if x < grid_w - 2 and (x + 1, y) not in rooms:
            directions.append("right")

        return directions

    def _apply_direction(self, pos: tuple[int, int], direction: str) -> tuple[int, int]:
        """
        Apply direction to get new position.

        Args:
            pos: Current position (x, y)
            direction: Direction name ("up", "down", "left", "right")

        Returns:
            New position after applying direction
        """
        x, y = pos
        if direction == "up":
            return (x, y - 1)
        elif direction == "down":
            return (x, y + 1)
        elif direction == "left":
            return (x - 1, y)
        elif direction == "right":
            return (x + 1, y)
        return pos

    def _create_biomes(
        self,
        all_rooms: list[RoomNode],
        num_biomes: int,
        forced_theme: "BiomeTheme | None" = None,
    ) -> list[Biome]:
        """
        Divide rooms into biomes and assign themes.

        Rooms are grouped spatially into biomes with different themes.
        """
        if num_biomes == 1:
            # Single biome — use forced_theme if provided, else default to DUNGEON
            theme = forced_theme if forced_theme is not None else BiomeTheme.DUNGEON
            for room in all_rooms:
                room.biome_theme = theme
            # Find start room or use first room as fallback
            start = next(
                (r for r in all_rooms if r.room_type == RoomType.START),
                all_rooms[0] if all_rooms else None,
            )
            if not start:
                raise ValueError("No rooms generated")
            return [Biome(theme=theme, rooms=all_rooms, start_room=start)]

        # Multi-biome: divide by y-coordinate (horizontal layers)
        # Sort rooms by y position
        sorted_rooms = sorted(all_rooms, key=lambda r: (r.grid_y, r.grid_x))

        # Assign themes cyclically
        themes = [BiomeTheme.DUNGEON, BiomeTheme.CAVE, BiomeTheme.BUILDING]
        biomes: list[Biome] = []

        rooms_per_biome = len(all_rooms) // num_biomes
        for i in range(num_biomes):
            # Slice rooms for this biome
            start_idx = i * rooms_per_biome
            end_idx = start_idx + rooms_per_biome if i < num_biomes - 1 else len(all_rooms)
            biome_rooms = sorted_rooms[start_idx:end_idx]

            # Assign theme
            theme = themes[i % len(themes)]
            for room in biome_rooms:
                room.biome_theme = theme

            # Find start room for this biome (or use first room)
            start_room = next(
                (r for r in biome_rooms if r.room_type == RoomType.START),
                biome_rooms[0] if biome_rooms else None,
            )

            if start_room:
                biomes.append(Biome(theme=theme, rooms=biome_rooms, start_room=start_room))

        return biomes

    def _compute_neighbor_dirs(self, room: RoomNode) -> dict[str, tuple[int, int]]:
        """
        Compute neighbor directions for a room.

        Returns map of direction name -> neighbor coordinate.
        """
        neighbor_dirs = {}
        for nx, ny in room.neighbors:
            dx, dy = nx - room.grid_x, ny - room.grid_y
            for dir_name, (ddx, ddy) in DIRS.items():
                if (dx, dy) == (ddx, ddy):
                    neighbor_dirs[dir_name] = (nx, ny)
        return neighbor_dirs

    def _assign_door_ports(self, rooms: dict[tuple[int, int], RoomNode]) -> None:
        """
        Assign door ports on room edges (from source algorithm).

        Each pair of connected rooms gets 1-3 door ports depending on room type.
        """
        rng = random.Random(self.seed ^ 0xA5A5A5)
        seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()

        # Room dimensions in zones (5x5 grid)
        # Each zone will expand to tiles later

        for room_pos, room in rooms.items():
            for neighbor_pos in room.neighbors:
                if neighbor_pos not in rooms:
                    continue

                # Skip if we've already processed this edge
                edge = tuple(sorted([room_pos, neighbor_pos]))
                if edge in seen:
                    continue
                seen.add(edge)

                # Compute direction
                ax, ay = room_pos
                bx, by = neighbor_pos
                dx, dy = bx - ax, by - ay

                # Number of doors (1-3)
                k = 1
                if rng.random() < 0.22:
                    k += 1
                if rng.random() < 0.06:
                    k += 1

                # Boss rooms only get 1 door
                if (
                    room.room_type == RoomType.BOSS
                    or rooms[neighbor_pos].room_type == RoomType.BOSS
                ):
                    k = min(k, 1)

                # Assign door ports based on direction
                span = max(3, TILES_PER_ZONE - 1)

                if (dx, dy) == (1, 0):  # Right
                    zones = rng.sample(range(ZONES_H), k=min(k, ZONES_H))
                    for zy in sorted(zones):
                        center_tile = zy * TILES_PER_ZONE + TILES_PER_ZONE // 2
                        # Right edge of current room, left edge of neighbor
                        room.door_ports.setdefault("right", []).append(
                            DoorPort(side="right", center_tile=center_tile, span_tiles=span)
                        )
                        rooms[neighbor_pos].door_ports.setdefault("left", []).append(
                            DoorPort(side="left", center_tile=center_tile, span_tiles=span)
                        )

                elif (dx, dy) == (0, 1):  # Down
                    zones = rng.sample(range(ZONES_W), k=min(k, ZONES_W))
                    for zx in sorted(zones):
                        center_tile = zx * TILES_PER_ZONE + TILES_PER_ZONE // 2
                        room.door_ports.setdefault("down", []).append(
                            DoorPort(side="down", center_tile=center_tile, span_tiles=span)
                        )
                        rooms[neighbor_pos].door_ports.setdefault("up", []).append(
                            DoorPort(side="up", center_tile=center_tile, span_tiles=span)
                        )

                elif (dx, dy) == (-1, 0):  # Left
                    zones = rng.sample(range(ZONES_H), k=min(k, ZONES_H))
                    for zy in sorted(zones):
                        center_tile = zy * TILES_PER_ZONE + TILES_PER_ZONE // 2
                        room.door_ports.setdefault("left", []).append(
                            DoorPort(side="left", center_tile=center_tile, span_tiles=span)
                        )
                        rooms[neighbor_pos].door_ports.setdefault("right", []).append(
                            DoorPort(side="right", center_tile=center_tile, span_tiles=span)
                        )

                elif (dx, dy) == (0, -1):  # Up
                    zones = rng.sample(range(ZONES_W), k=min(k, ZONES_W))
                    for zx in sorted(zones):
                        center_tile = zx * TILES_PER_ZONE + TILES_PER_ZONE // 2
                        room.door_ports.setdefault("up", []).append(
                            DoorPort(side="up", center_tile=center_tile, span_tiles=span)
                        )
                        rooms[neighbor_pos].door_ports.setdefault("down", []).append(
                            DoorPort(side="down", center_tile=center_tile, span_tiles=span)
                        )

    def _resolve_world_anchors(self, rooms: dict[tuple[int, int], RoomNode]) -> None:
        """
        Resolve anchor candidates globally with spacing constraints

        Delegates to anchor_resolution.resolve_world_anchors()

        Args:
            rooms: Dictionary of room nodes (modified in-place)
        """
        from systems.anchor_resolution import resolve_world_anchors

        resolve_world_anchors(rooms, self.seed)


# ==========================================================
# Utility Functions
# ==========================================================


def generate_world_tilemaps(world: World) -> dict[tuple[int, int], list[list[int]]]:
    """
    Generate tilemaps for all rooms in the world

    Args:
        world: Generated world with room graph

    Returns:
        Dictionary of (grid_x, grid_y) → tilemap
    """
    from systems.room_generation import RoomGenerator
    from systems.zone_planning import ZonePlanner

    logger.debug("[TILEMAPS] Generating tilemaps for %s rooms...", len(world.all_rooms))

    zone_planner = ZonePlanner(seed=world.seed)
    room_gen = RoomGenerator()

    room_tilemaps = {}

    for room in world.all_rooms:
        # Plan zones if not already done
        if room.zone_grid is None:
            room.zone_grid = zone_planner.plan_room(room)

        # Generate tilemap
        room.tilemap = room_gen.generate_tilemap(room)

        # Store in dictionary
        room_coords = (room.grid_x, room.grid_y)
        room_tilemaps[room_coords] = room.tilemap

    logger.debug("[TILEMAPS] Generated %s room tilemaps", len(room_tilemaps))

    return room_tilemaps


def build_world_megamap(world: World):
    """
    Generate tilemaps and build unified megamap

    Args:
        world: Generated world with room graph

    Returns:
        Megamap with unified tilemap
    """
    from systems.megamap import build_megamap

    # Generate all room tilemaps
    room_tilemaps = generate_world_tilemaps(world)

    # Build unified megamap
    megamap = build_megamap(world, room_tilemaps)

    return megamap


def print_world_debug(world: World) -> None:
    """
    Print ASCII representation of world for debugging.

    Shows room positions and types in a grid.
    """
    minx, miny, maxx, maxy = world.bounds
    w = maxx - minx + 1
    h = maxy - miny + 1

    def room_letter(room_type: RoomType) -> str:
        """Get single-character representation of room type."""
        return {
            RoomType.START: "S",
            RoomType.EXIT: "E",
            RoomType.SHOP: "$",
            RoomType.TREASURE: "T",
            RoomType.BOSS: "B",
            RoomType.PLATFORM: "P",
            RoomType.COMBAT: "C",
        }.get(room_type, "?")

    def biome_letter(theme: BiomeTheme) -> str:
        """Get single-character representation of biome."""
        return {
            BiomeTheme.DUNGEON: "D",
            BiomeTheme.CAVE: "V",
            BiomeTheme.BUILDING: "U",
        }.get(theme, "?")

    # Build grid
    grid = [["  " for _ in range(w)] for _ in range(h)]
    room_map = {(r.grid_x, r.grid_y): r for r in world.all_rooms}

    for room in world.all_rooms:
        x, y = room.grid_x - minx, room.grid_y - miny
        grid[y][x] = f"{room_letter(room.room_type)}{biome_letter(room.biome_theme)}"

    # Print
    print("\n=== World Map ===")
    print(f"Seed: {world.seed}")
    print(f"Size: {w}x{h} grid")
    print(f"Rooms: {len(world.all_rooms)}")
    print(f"Biomes: {len(world.biomes)}")
    print()
    for row in grid:
        print(" ".join(row))
    print()
    print("Legend: S=Start, E=Exit, $=Shop, T=Treasure, B=Boss, P=Platform, C=Combat")
    print("        D=Dungeon, V=Cave, U=Building")
    print("=" * 60)
