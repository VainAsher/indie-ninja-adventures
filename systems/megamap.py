"""
Megamap Stitching System - Unified World Tilemap

Stitches all room tilemaps into a single unified tilemap for:
- Simplified collision detection (single tilemap lookup)
- Seamless room transitions (no loading/unloading)
- Easier minimap rendering
- Better performance for large worlds

Based on: Dynamic dungeon platformer megamap system
"""

from dataclasses import dataclass

from config.physics_constants import (
    ROOM_HEIGHT_TILES as ROOM_H_TILES,
)

# Room dimensions in tiles (from room_generation.py)
from config.physics_constants import (
    ROOM_WIDTH_TILES as ROOM_W_TILES,
)
from systems.room_generation import TILE_EMPTY
from systems.world_generation import World


@dataclass
class Megamap:
    """
    Unified world tilemap with room stitching

    Attributes:
        tilemap: 2D array of tiles covering entire world
        width_tiles: Total width in tiles
        height_tiles: Total height in tiles
        room_positions: Map of room coords → pixel position in megamap
        bounds: World bounds (minx, miny, maxx, maxy) in room coordinates
    """

    tilemap: list[list[int]]
    width_tiles: int
    height_tiles: int
    room_positions: dict[tuple[int, int], tuple[int, int]]  # room_coords → (px, py)
    bounds: tuple[int, int, int, int]


def build_megamap(world: World, room_tilemaps: dict[tuple[int, int], list[list[int]]]) -> Megamap:
    """
    Stitch all room tilemaps into single unified tilemap

    Args:
        world: Generated world with room graph
        room_tilemaps: Dictionary of (grid_x, grid_y) → tilemap

    Returns:
        Megamap with unified tilemap and room position lookup
    """
    minx, miny, maxx, maxy = world.bounds

    # Calculate megamap dimensions
    span_w = maxx - minx + 1  # Number of rooms horizontally
    span_h = maxy - miny + 1  # Number of rooms vertically

    mega_w = span_w * ROOM_W_TILES
    mega_h = span_h * ROOM_H_TILES

    print("\n[MEGAMAP] Building unified tilemap")
    print(f"[MEGAMAP] World bounds: ({minx}, {miny}) to ({maxx}, {maxy})")
    print(f"[MEGAMAP] Room span: {span_w}×{span_h} rooms")
    print(f"[MEGAMAP] Megamap size: {mega_w}×{mega_h} tiles ({mega_w * mega_h:,} total)")

    # Allocate megamap (filled with empty tiles)
    megamap = [[TILE_EMPTY for _ in range(mega_w)] for _ in range(mega_h)]

    # Track room pixel positions for camera/minimap
    room_positions: dict[tuple[int, int], tuple[int, int]] = {}

    # Stitch each room's tilemap into megamap
    rooms_stitched = 0
    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)

        # Get room's tilemap
        if room_coords not in room_tilemaps:
            print(f"[MEGAMAP] Warning: No tilemap for room {room_coords}")
            continue

        room_tilemap = room_tilemaps[room_coords]

        # Calculate position in megamap
        # Room (grid_x, grid_y) maps to pixel position in megamap
        offset_x = (room.grid_x - minx) * ROOM_W_TILES
        offset_y = (room.grid_y - miny) * ROOM_H_TILES

        # Store room position (in pixels, for camera)
        room_positions[room_coords] = (offset_x * 32, offset_y * 32)  # tiles → pixels

        # Copy room tilemap into megamap
        for local_y in range(min(ROOM_H_TILES, len(room_tilemap))):
            for local_x in range(min(ROOM_W_TILES, len(room_tilemap[0]))):
                mega_y = offset_y + local_y
                mega_x = offset_x + local_x

                if 0 <= mega_y < mega_h and 0 <= mega_x < mega_w:
                    megamap[mega_y][mega_x] = room_tilemap[local_y][local_x]

        rooms_stitched += 1

    print(f"[MEGAMAP] Stitched {rooms_stitched}/{len(world.all_rooms)} rooms")
    print(f"[MEGAMAP] Memory: ~{(mega_w * mega_h * 4) // 1024}KB for tilemap array")

    return Megamap(
        tilemap=megamap,
        width_tiles=mega_w,
        height_tiles=mega_h,
        room_positions=room_positions,
        bounds=world.bounds,
    )


def get_room_at_position(megamap: Megamap, pixel_x: float, pixel_y: float) -> tuple[int, int]:
    """
    Get room coordinates containing a pixel position

    Args:
        megamap: Unified megamap
        pixel_x, pixel_y: World position in pixels

    Returns:
        Room coordinates (grid_x, grid_y)
    """
    minx, miny, _, _ = megamap.bounds

    # Convert pixels to tiles
    tile_x = int(pixel_x // 32)
    tile_y = int(pixel_y // 32)

    # Convert tiles to room coordinates
    room_x = minx + (tile_x // ROOM_W_TILES)
    room_y = miny + (tile_y // ROOM_H_TILES)

    return room_x, room_y


def get_tile_at_position(megamap: Megamap, pixel_x: float, pixel_y: float) -> int:
    """
    Get tile ID at pixel position (for collision)

    Args:
        megamap: Unified megamap
        pixel_x, pixel_y: World position in pixels

    Returns:
        Tile ID (TILE_EMPTY, TILE_SOLID, TILE_PLATFORM, etc.)
    """
    tile_x = int(pixel_x // 32)
    tile_y = int(pixel_y // 32)

    # Bounds check
    if 0 <= tile_y < megamap.height_tiles and 0 <= tile_x < megamap.width_tiles:
        return megamap.tilemap[tile_y][tile_x]

    return TILE_EMPTY


def print_megamap_stats(megamap: Megamap) -> None:
    """
    Print statistics about the megamap

    Args:
        megamap: Unified megamap
    """
    total_tiles = megamap.width_tiles * megamap.height_tiles

    # Count tile types
    tile_counts = {}
    for row in megamap.tilemap:
        for tile in row:
            tile_counts[tile] = tile_counts.get(tile, 0) + 1

    print("\n[MEGAMAP STATS]")
    print(f"Dimensions: {megamap.width_tiles}×{megamap.height_tiles} tiles")
    print(f"Total tiles: {total_tiles:,}")
    print("Tile distribution:")
    for tile_id, count in sorted(tile_counts.items()):
        percentage = (count / total_tiles) * 100
        tile_name = {0: "EMPTY", 1: "SOLID", 2: "PLATFORM"}.get(tile_id, f"UNKNOWN({tile_id})")
        print(f"  {tile_name}: {count:,} ({percentage:.1f}%)")
    print(f"Rooms: {len(megamap.room_positions)}")
