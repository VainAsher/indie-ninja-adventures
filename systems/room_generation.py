"""
Room Generation System - Convert Zones to Tilemaps

Converts 16x16 zone grids to tilemaps with actual tile coordinates.
Each zone expands to 8x8 tiles (128x128 room size).

Features:
- Zone expansion to tiles
- Door carving
- Platform generation
- Integration with existing collision system

Enhanced: Increased zone grid to 16x16 for finer granularity
"""

import random

from config.physics_constants import ROOM_HEIGHT_TILES, ROOM_WIDTH_TILES, TILES_PER_ZONE
from systems.world_generation import RoomNode
from systems.zone_planning import (
    Z_CHUTE,
    Z_CLIMB,
    Z_CONNECTOR,
    Z_DECOR,
    Z_DOOR,
    Z_FILL,
    Z_LOOT,
    Z_PLAT,
    Z_SAVE,
    Z_SHOP,
    Z_VOID,
    Z_WALK,
)

# Tile constants (match existing collision system)
TILE_EMPTY = 0  # Empty space (no collision)
TILE_SOLID = 1  # Solid terrain (full collision)
TILE_PLATFORM = 2  # Platform (one-way collision from top)
TILE_LAVA = 3  # Hazard liquid
TILE_WATER = 4  # Water liquid
TILE_PLATFORM_FALLING = 5  # Temp/falling platform
TILE_PLATFORM_MOVING = 6  # Moving platform


# Room/zone dimensions come from centralized physics constants


class RoomGenerator:
    """
    Generates tilemaps from zone grids.

    Converts abstract 16x16 zone layout to 160x160 tile grid with collision.
    """

    def __init__(self):
        """Initialize room generator."""
        pass

    def generate_tilemap(self, room: RoomNode) -> list[list[int]]:
        """
        Generate tilemap from room's zone grid.

        Args:
            room: Room with zone_grid assigned

        Returns:
            128x128 tilemap (2D list of tile IDs) with current scaling
        """
        if not room.zone_grid:
            raise ValueError("Room must have zone_grid assigned before generating tilemap")

        # Create empty tilemap
        tilemap = [[TILE_EMPTY for _ in range(ROOM_WIDTH_TILES)] for _ in range(ROOM_HEIGHT_TILES)]

        # Add room boundaries (only on edges without connections)
        self._add_room_boundaries(tilemap, room)

        # Expand each zone to tiles
        for zy in range(16):  # 16 zones high
            for zx in range(16):  # 16 zones wide
                zone_role = room.zone_grid[zy][zx]
                self._expand_zone(tilemap, zx, zy, zone_role, room)

        # Carve doors (make door zones passable) - may not be needed now
        # but keep for additional clearance
        self._carve_doors(tilemap, room)

        # Add intra-zone variation (blobs/patches) for richer shapes
        self._apply_tile_variation(tilemap, room)

        # Add liquid patches (lava/water) in void zones
        self._apply_liquid_variation(tilemap, room)

        # Add platform variants (falling/moving) for visual variety
        self._apply_platform_variants(tilemap, room)

        return tilemap

    def _expand_zone(
        self,
        tilemap: list[list[int]],
        zx: int,
        zy: int,
        zone_role: str,
        room: RoomNode | None = None,
    ):
        """
        Expand a single zone to 10x10 tiles.

        Args:
            tilemap: Tilemap to modify
            zx, zy: Zone coordinates (0-15 for 16x16 grid)
            zone_role: Role of this zone
            room: Room node (for checking edge connections)
        """
        # Calculate tile range for this zone
        tile_x_start = zx * TILES_PER_ZONE
        tile_y_start = zy * TILES_PER_ZONE
        tile_x_end = tile_x_start + TILES_PER_ZONE
        tile_y_end = tile_y_start + TILES_PER_ZONE

        # Check if this zone is on an edge that connects to another room
        is_top_edge = (zy == 0) and room and "up" in room.neighbor_dirs
        is_bottom_edge = (zy == 15) and room and "down" in room.neighbor_dirs
        is_left_edge = (zx == 0) and room and "left" in room.neighbor_dirs
        is_right_edge = (zx == 15) and room and "right" in room.neighbor_dirs
        is_connected_edge = is_top_edge or is_bottom_edge or is_left_edge or is_right_edge

        if zone_role == Z_FILL:
            # Solid terrain - fill entire zone
            for ty in range(tile_y_start, tile_y_end):
                for tx in range(tile_x_start, tile_x_end):
                    tilemap[ty][tx] = TILE_SOLID

        elif zone_role == Z_PLAT:
            # Platform - horizontal platform in middle of zone
            platform_y = tile_y_start + TILES_PER_ZONE // 2
            for tx in range(tile_x_start, tile_x_end):
                tilemap[platform_y][tx] = TILE_PLATFORM

        elif zone_role in (Z_WALK, Z_DOOR, Z_SAVE, Z_SHOP, Z_LOOT, Z_DECOR):
            # Walkable zones - floor at bottom
            # EXCEPTION: Don't add floor on bottom edge if room connects downward
            # EXCEPTION: Don't add floor on top edge if room connects upward
            if is_bottom_edge or is_top_edge:
                # Leave empty for traversal
                pass
            else:
                floor_y = tile_y_end - 1
                for tx in range(tile_x_start, tile_x_end):
                    tilemap[floor_y][tx] = TILE_SOLID

        elif zone_role == Z_CHUTE:
            # Vertical chute for downward movement - empty space with no floor
            # This allows player to fall through to room below
            pass  # Keep as TILE_EMPTY

        elif zone_role == Z_CLIMB:
            # Stepped platforms for upward movement
            # Create staircase-like platforms
            for i in range(TILES_PER_ZONE):
                platform_y = tile_y_end - 1 - (i // 2)  # Step every 2 tiles
                if platform_y >= tile_y_start:
                    tilemap[platform_y][tile_x_start + i] = TILE_PLATFORM

        elif zone_role == Z_CONNECTOR:
            # Horizontal connector platform for hub rooms
            platform_y = tile_y_start + TILES_PER_ZONE // 2
            for tx in range(tile_x_start, tile_x_end):
                tilemap[platform_y][tx] = TILE_PLATFORM

        elif zone_role == Z_VOID:
            # Empty space - already TILE_EMPTY
            pass

    def _add_room_boundaries(self, tilemap: list[list[int]], room: RoomNode | None = None):
        """
        Add room boundaries - only on edges that DON'T connect to other rooms.

        For multi-room worlds, we skip walls on connected edges to allow traversal.

        Args:
            tilemap: Tilemap to modify
            room: Room node (optional, for checking connections)
        """
        # Determine which edges have connections
        has_up = room and "up" in room.neighbor_dirs if room else False
        has_down = room and "down" in room.neighbor_dirs if room else False
        has_left = room and "left" in room.neighbor_dirs if room else False
        has_right = room and "right" in room.neighbor_dirs if room else False

        # Top wall (only if no upward connection)
        if not has_up:
            for x in range(ROOM_WIDTH_TILES):
                tilemap[0][x] = TILE_SOLID

        # Bottom wall (only if no downward connection)
        if not has_down:
            for x in range(ROOM_WIDTH_TILES):
                tilemap[ROOM_HEIGHT_TILES - 1][x] = TILE_SOLID

        # Left wall (only if no left connection)
        if not has_left:
            for y in range(ROOM_HEIGHT_TILES):
                tilemap[y][0] = TILE_SOLID

        # Right wall (only if no right connection)
        if not has_right:
            for y in range(ROOM_HEIGHT_TILES):
                tilemap[y][ROOM_WIDTH_TILES - 1] = TILE_SOLID

        # Platform near bottom (like source: room_h-2)
        # This gives a base floor for platforming
        # BUT: Don't add if there's a downward connection (blocks traversal)
        if not has_down:
            platform_y = ROOM_HEIGHT_TILES - 2
            for x in range(1, ROOM_WIDTH_TILES - 1):
                # Don't override existing solid tiles
                if tilemap[platform_y][x] == TILE_EMPTY:
                    tilemap[platform_y][x] = TILE_PLATFORM

    def _carve_doors(self, tilemap: list[list[int]], room: RoomNode):
        """
        Carve door openings at room edges.

        Args:
            tilemap: Tilemap to modify
            room: Room with door_ports
        """
        for direction, ports in room.door_ports.items():
            for port in ports:
                self._carve_door_opening(tilemap, direction, port.center_tile, port.span_tiles)

    def _carve_door_opening(
        self, tilemap: list[list[int]], direction: str, center_tile: int, span_tiles: int
    ):
        """
        Carve a single door opening.

        Args:
            tilemap: Tilemap to modify
            direction: "up", "down", "left", or "right"
            center_tile: Center position of door
            span_tiles: Width of door opening
        """
        half_span = span_tiles // 2

        if direction == "left":
            # Carve vertical opening on left edge
            for ty in range(
                max(0, center_tile - half_span), min(ROOM_HEIGHT_TILES, center_tile + half_span)
            ):
                tilemap[ty][0] = TILE_EMPTY

        elif direction == "right":
            # Carve vertical opening on right edge
            for ty in range(
                max(0, center_tile - half_span), min(ROOM_HEIGHT_TILES, center_tile + half_span)
            ):
                tilemap[ty][ROOM_WIDTH_TILES - 1] = TILE_EMPTY

        elif direction == "up":
            # Carve horizontal opening on top edge
            for tx in range(
                max(0, center_tile - half_span), min(ROOM_WIDTH_TILES, center_tile + half_span)
            ):
                tilemap[0][tx] = TILE_EMPTY

        elif direction == "down":
            # Carve horizontal opening on bottom edge
            for tx in range(
                max(0, center_tile - half_span), min(ROOM_WIDTH_TILES, center_tile + half_span)
            ):
                tilemap[ROOM_HEIGHT_TILES - 1][tx] = TILE_EMPTY

    def _apply_tile_variation(self, tilemap: list[list[int]], room: RoomNode | None):
        """
        Add smaller-scale formations inside the room for more variety.

        Creates random solid/empty blobs sized 2x2 to 32x32 tiles with
        varying densities. Modifies only FILL/VOID zones to preserve
        core navigable paths.
        """
        if room is None or not room.zone_grid:
            return

        zone_grid = room.zone_grid
        zones_h = len(zone_grid)
        zones_w = len(zone_grid[0]) if zones_h else 0
        if zones_h == 0 or zones_w == 0:
            return

        rng = random.Random(room.seed + 1337)

        # Blob count varies by room type
        if room.room_type and getattr(room.room_type, "value", "") in ("combat", "platform"):
            blob_count = rng.randint(10, 18)
        elif room.room_type and getattr(room.room_type, "value", "") in ("treasure", "shop"):
            blob_count = rng.randint(6, 12)
        else:
            blob_count = rng.randint(8, 14)

        for _ in range(blob_count):
            blob_w = rng.randint(2, 32)
            blob_h = rng.randint(2, 32)
            # Keep away from edges and doors to preserve traversal
            cx = rng.randint(2, ROOM_WIDTH_TILES - 3)
            cy = rng.randint(2, ROOM_HEIGHT_TILES - 3)

            density = rng.uniform(0.35, 0.9)
            kind = rng.choices(["carve", "solid"], weights=[0.5, 0.5], k=1)[0]

            self._stamp_blob(
                tilemap,
                zone_grid,
                zones_w,
                zones_h,
                cx,
                cy,
                blob_w,
                blob_h,
                density,
                kind,
                rng,
            )

    def _stamp_blob(
        self,
        tilemap: list[list[int]],
        zone_grid: list[list[str]],
        zones_w: int,
        zones_h: int,
        cx: int,
        cy: int,
        blob_w: int,
        blob_h: int,
        density: float,
        kind: str,
        rng: random.Random,
    ):
        half_w = max(1, blob_w // 2)
        half_h = max(1, blob_h // 2)

        min_x = max(1, cx - half_w)
        max_x = min(ROOM_WIDTH_TILES - 2, cx + half_w)
        min_y = max(1, cy - half_h)
        max_y = min(ROOM_HEIGHT_TILES - 2, cy + half_h)

        for ty in range(min_y, max_y + 1):
            for tx in range(min_x, max_x + 1):
                # Elliptical blob with noisy edge falloff
                nx = (tx - cx) / max(1, half_w)
                ny = (ty - cy) / max(1, half_h)
                dist = nx * nx + ny * ny
                if dist > 1.0 + rng.uniform(-0.15, 0.15):
                    continue

                falloff = max(0.0, 1.0 - dist)
                if rng.random() > density * (0.4 + 0.6 * falloff):
                    continue

                zx = min(zones_w - 1, max(0, tx // TILES_PER_ZONE))
                zy = min(zones_h - 1, max(0, ty // TILES_PER_ZONE))
                zone_role = zone_grid[zy][zx]

                if kind == "carve":
                    # Only carve inside solid zones
                    if zone_role != Z_FILL:
                        continue
                    if tilemap[ty][tx] == TILE_SOLID:
                        tilemap[ty][tx] = TILE_EMPTY
                else:
                    # Only add solids inside void zones
                    if zone_role != Z_VOID:
                        continue
                    if tilemap[ty][tx] == TILE_EMPTY:
                        tilemap[ty][tx] = TILE_SOLID

    def _apply_liquid_variation(self, tilemap: list[list[int]], room: RoomNode | None):
        """
        Add lava/water patches inside VOID zones for visual variety.
        """
        if room is None or not room.zone_grid:
            return

        zone_grid = room.zone_grid
        zones_h = len(zone_grid)
        zones_w = len(zone_grid[0]) if zones_h else 0
        if zones_h == 0 or zones_w == 0:
            return

        rng = random.Random(room.seed + 4242)

        if room.room_type and getattr(room.room_type, "value", "") in ("combat", "platform"):
            patch_count = rng.randint(8, 14)
        elif room.room_type and getattr(room.room_type, "value", "") in ("treasure", "shop"):
            patch_count = rng.randint(4, 8)
        else:
            patch_count = rng.randint(6, 10)

        for _ in range(patch_count):
            blob_w = rng.randint(2, 32)
            blob_h = rng.randint(2, 32)
            cx = rng.randint(2, ROOM_WIDTH_TILES - 3)
            cy = rng.randint(2, ROOM_HEIGHT_TILES - 3)

            zx = min(zones_w - 1, max(0, cx // TILES_PER_ZONE))
            zy = min(zones_h - 1, max(0, cy // TILES_PER_ZONE))
            if zone_grid[zy][zx] != Z_VOID:
                continue

            contained = self._is_contained_void(zone_grid, zx, zy)
            if contained and rng.random() < 0.7:
                tile_type = TILE_WATER
            else:
                tile_type = TILE_LAVA

            density = rng.uniform(0.35, 0.85)
            self._stamp_liquid_blob(
                tilemap,
                zone_grid,
                zones_w,
                zones_h,
                cx,
                cy,
                blob_w,
                blob_h,
                density,
                tile_type,
                rng,
            )

    def _apply_platform_variants(self, tilemap: list[list[int]], room: RoomNode | None):
        """
        Mark a subset of platforms as falling or moving for visual variety.
        """
        if room is None:
            return

        rng = random.Random(room.seed + 8675)
        room_type = getattr(room.room_type, "value", "")
        if room_type in ("platform", "combat"):
            fall_chance = 0.12
            move_chance = 0.10
        else:
            fall_chance = 0.06
            move_chance = 0.05

        for ty, row in enumerate(tilemap):
            for tx, tile in enumerate(row):
                if tile != TILE_PLATFORM:
                    continue
                r = rng.random()
                if r < fall_chance:
                    tilemap[ty][tx] = TILE_PLATFORM_FALLING
                elif r < fall_chance + move_chance:
                    tilemap[ty][tx] = TILE_PLATFORM_MOVING

    def _is_contained_void(self, zone_grid: list[list[str]], zx: int, zy: int) -> bool:
        """
        Check if a void zone is surrounded by solid zones (for lakes).
        """
        zones_h = len(zone_grid)
        zones_w = len(zone_grid[0]) if zones_h else 0
        if zx <= 0 or zy <= 0 or zx >= zones_w - 1 or zy >= zones_h - 1:
            return False

        neighbors = [
            (zx - 1, zy),
            (zx + 1, zy),
            (zx, zy - 1),
            (zx, zy + 1),
        ]
        for nx, ny in neighbors:
            if zone_grid[ny][nx] != Z_FILL:
                return False
        return True

    def _stamp_liquid_blob(
        self,
        tilemap: list[list[int]],
        zone_grid: list[list[str]],
        zones_w: int,
        zones_h: int,
        cx: int,
        cy: int,
        blob_w: int,
        blob_h: int,
        density: float,
        tile_type: int,
        rng: random.Random,
    ):
        half_w = max(1, blob_w // 2)
        half_h = max(1, blob_h // 2)

        min_x = max(1, cx - half_w)
        max_x = min(ROOM_WIDTH_TILES - 2, cx + half_w)
        min_y = max(1, cy - half_h)
        max_y = min(ROOM_HEIGHT_TILES - 2, cy + half_h)

        for ty in range(min_y, max_y + 1):
            for tx in range(min_x, max_x + 1):
                nx = (tx - cx) / max(1, half_w)
                ny = (ty - cy) / max(1, half_h)
                dist = nx * nx + ny * ny
                if dist > 1.0 + rng.uniform(-0.12, 0.12):
                    continue

                falloff = max(0.0, 1.0 - dist)
                if rng.random() > density * (0.5 + 0.5 * falloff):
                    continue

                zx = min(zones_w - 1, max(0, tx // TILES_PER_ZONE))
                zy = min(zones_h - 1, max(0, ty // TILES_PER_ZONE))
                if zone_grid[zy][zx] != Z_VOID:
                    continue
                if tilemap[ty][tx] == TILE_EMPTY:
                    tilemap[ty][tx] = tile_type


def tilemap_to_collision_rects(
    tilemap: list[list[int]], tile_size: int = 8
) -> list[tuple[int, int, int, int]]:
    """
    Convert tilemap to collision rectangles (for existing collision system).

    Args:
        tilemap: 2D tile grid
        tile_size: Size of each tile in pixels

    Returns:
        List of (x, y, width, height) rectangles for solid tiles
    """
    rects = []

    for ty, row in enumerate(tilemap):
        for tx, tile in enumerate(row):
            if tile == TILE_SOLID:
                # Solid tile - create collision rect
                x = tx * tile_size
                y = ty * tile_size
                rects.append((x, y, tile_size, tile_size))

    return rects


def print_tilemap_sample(tilemap: list[list[int]], sample_size: int = 20) -> None:
    """
    Print a sample of the tilemap (for debugging).

    Args:
        tilemap: Tilemap to print
        sample_size: Size of sample to print (default 20x20)
    """
    symbols = {
        TILE_EMPTY: " ",
        TILE_SOLID: "#",
        TILE_PLATFORM: "-",
        TILE_LAVA: "L",
        TILE_WATER: "W",
        TILE_PLATFORM_FALLING: "f",
        TILE_PLATFORM_MOVING: "m",
    }

    print(f"\nTilemap Sample ({sample_size}x{sample_size} of {len(tilemap[0])}x{len(tilemap)}):")
    for row in tilemap[:sample_size]:
        print("".join(symbols.get(tile, "?") for tile in row[:sample_size]))
    print()


def print_tilemap_ascii(tilemap: list[list[int]], scale: int = 4) -> None:
    """
    Print ASCII visualization of entire tilemap at reduced scale.

    Args:
        tilemap: Full tilemap to visualize
        scale: Downsample factor (default 4 = show every 4th tile)
    """
    symbols = {
        TILE_EMPTY: " ",
        TILE_SOLID: "#",
        TILE_PLATFORM: "-",
        TILE_LAVA: "L",
        TILE_WATER: "W",
        TILE_PLATFORM_FALLING: "f",
        TILE_PLATFORM_MOVING: "m",
    }

    height = len(tilemap)
    width = len(tilemap[0]) if height > 0 else 0

    print(f"\n{'='*60}")
    print(f"TILEMAP ASCII VISUALIZATION ({width}x{height} tiles, scale 1:{scale})")
    print(f"{'='*60}")

    # Downsample and print
    for y in range(0, height, scale):
        row_str = ""
        for x in range(0, width, scale):
            # Sample tile at this position
            tile = tilemap[y][x]
            row_str += symbols.get(tile, "?")
        print(row_str)

    print(f"{'='*60}")
    print("Legend: #=Solid  -=Platform  f=Falling  m=Moving  L=Lava  W=Water  (space)=Empty")
    print(f"{'='*60}\n")
