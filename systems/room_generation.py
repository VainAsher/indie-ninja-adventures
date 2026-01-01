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
    print("Legend: #=Solid  -=Platform  (space)=Empty")
    print(f"{'='*60}\n")
