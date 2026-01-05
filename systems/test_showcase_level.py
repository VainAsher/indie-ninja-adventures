"""
Test Showcase Level - Display All Zone Patterns and Tile Types

Creates a special test level that showcases:
- All 12 new zone types
- All 8 new tile types
- Zone patterns in action
- Ability gates at various depths
- Fluid physics areas

Usage:
    from systems.test_showcase_level import generate_showcase_level
    tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap = generate_showcase_level()
"""

from systems.room_generation import (
    TILE_BREAKABLE,
    TILE_CRACKED,
    TILE_EMPTY,
    TILE_ICE,
    TILE_LAVA,
    TILE_MUD,
    TILE_PLATFORM,
    TILE_PUSHABLE,
    TILE_SOLID,
    TILE_STICKY,
    TILE_WATER,
    RoomGenerator,
)
from systems.world_generation import RoomNode, RoomType, World, Biome, BiomeTheme, DoorPort
from systems.zone_planning import (
    Z_ALCOVE,
    Z_CHAMBER,
    Z_DIAGONAL,
    Z_FLOATING,
    Z_FLUID_SURFACE,
    Z_L_PLATFORM,
    Z_LAVA_POOL,
    Z_SHAFT_DOWN,
    Z_SHAFT_UP,
    Z_T_PLATFORM,
    Z_TUNNEL,
    Z_WALK,
    Z_WATER_POOL,
)
from config.physics_constants import TILE_SIZE, ROOM_WIDTH_TILES, ROOM_HEIGHT_TILES
from systems.megamap import Megamap
import pygame


def _create_showcase_zone_grid(grid_x: int, grid_y: int, showcase_zones: list) -> list[list[str]]:
    """
    Create a zone grid that's actually traversable.

    Creates a continuous walkable floor across the bottom with feature zones above.
    """
    # Start with empty grid
    zone_grid = [["" for _ in range(16)] for _ in range(16)]

    # Create solid walkable floor across bottom 2 rows for reliable traversal
    for zy in range(14, 16):
        for zx in range(16):
            zone_grid[zy][zx] = Z_WALK

    # Add a secondary platform level for vertical interest (row 10-11)
    for zx in range(2, 14):
        zone_grid[10][zx] = Z_WALK

    # Clear middle areas for traversal (rows 0-9, 11-13)
    for zy in range(14):
        for zx in range(16):
            if zone_grid[zy][zx] == "":
                zone_grid[zy][zx] = ""  # Empty air

    # Now add showcase zones on top of the basic layout
    for zone_role, zx, zy in showcase_zones:
        if 0 <= zy < 16 and 0 <= zx < 16:
            # Don't override the main floor (bottom 2 rows)
            if zy < 14:
                zone_grid[zy][zx] = zone_role

    return zone_grid


def _assign_showcase_door_ports(rooms: list[RoomNode]) -> None:
    """
    Assign door ports to showcase rooms for traversability.

    Creates a single wide door in the middle of each connected edge.
    """
    # Create room lookup dictionary
    room_dict = {(room.grid_x, room.grid_y): room for room in rooms}

    for room in rooms:
        room.door_ports = {}

        # Check each neighbor and add door port
        for neighbor_coords in room.neighbors:
            neighbor = room_dict.get(neighbor_coords)
            if not neighbor:
                continue

            dx = neighbor_coords[0] - room.grid_x
            dy = neighbor_coords[1] - room.grid_y

            # 64 tiles wide door (half of 128 tiles) centered at tile 64
            center_tile = 64
            span = 64

            if (dx, dy) == (1, 0):  # Right neighbor
                room.door_ports.setdefault("right", []).append(
                    DoorPort(side="right", center_tile=center_tile, span_tiles=span)
                )
            elif (dx, dy) == (-1, 0):  # Left neighbor
                room.door_ports.setdefault("left", []).append(
                    DoorPort(side="left", center_tile=center_tile, span_tiles=span)
                )
            elif (dx, dy) == (0, 1):  # Down neighbor
                room.door_ports.setdefault("down", []).append(
                    DoorPort(side="down", center_tile=center_tile, span_tiles=span)
                )
            elif (dx, dy) == (0, -1):  # Up neighbor
                room.door_ports.setdefault("up", []).append(
                    DoorPort(side="up", center_tile=center_tile, span_tiles=span)
                )


def generate_showcase_level():
    """
    Generate a test showcase level displaying all new features

    Returns:
        Same format as create_procedural_level():
        (tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap)
    """
    print("\n" + "="*60)
    print("GENERATING TEST SHOWCASE LEVEL")
    print("="*60)

    # Create a 3x3 grid of test rooms
    showcase_rooms = []

    # Row 1: Zone Pattern Showcase
    room_configs = [
        # (grid_x, grid_y, room_type, description, zones_to_add)
        (0, 0, RoomType.START, "START + Diagonal Stairs", [(Z_DIAGONAL, 4, 4), (Z_WALK, 8, 14)]),
        (1, 0, RoomType.PLATFORM, "Chambers & Alcoves", [(Z_CHAMBER, 4, 4), (Z_ALCOVE, 12, 4)]),
        (2, 0, RoomType.PLATFORM, "L & T Platforms", [(Z_L_PLATFORM, 3, 4), (Z_T_PLATFORM, 11, 4)]),

        # Row 2: Fluid & Hazard Showcase
        (0, 1, RoomType.PLATFORM, "Water Pool", [(Z_WATER_POOL, 4, 6), (Z_FLUID_SURFACE, 4, 4), (Z_WALK, 8, 14)]),
        (1, 1, RoomType.COMBAT, "Lava Pool", [(Z_LAVA_POOL, 4, 6), (Z_WALK, 12, 14)]),
        (2, 1, RoomType.PLATFORM, "Shafts & Tunnels", [(Z_SHAFT_UP, 4, 2), (Z_SHAFT_DOWN, 8, 2), (Z_TUNNEL, 12, 8)]),

        # Row 3: Interactive Tiles Showcase
        (0, 2, RoomType.PLATFORM, "Interactive Blocks", []),  # Manual tile placement
        (1, 2, RoomType.TREASURE, "Hazard Tiles", []),  # Manual tile placement
        (2, 2, RoomType.EXIT, "EXIT + Floating", [(Z_FLOATING, 6, 4), (Z_FLOATING, 10, 8)]),
    ]

    for grid_x, grid_y, room_type, description, zones in room_configs:
        room = RoomNode(
            grid_x=grid_x,
            grid_y=grid_y,
            room_type=room_type,
            biome_theme=BiomeTheme.DUNGEON,
            seed=12345 + grid_x * 100 + grid_y,
            neighbors=[]
        )

        # Create zone grid with proper walkable floor
        room.zone_grid = _create_showcase_zone_grid(grid_x, grid_y, zones)

        # Store description for display
        room.description = description
        showcase_rooms.append(room)

    # Connect rooms in grid pattern
    for room in showcase_rooms:
        # Right neighbor
        if room.grid_x < 2:
            room.neighbors.append((room.grid_x + 1, room.grid_y))
        # Left neighbor
        if room.grid_x > 0:
            room.neighbors.append((room.grid_x - 1, room.grid_y))
        # Down neighbor
        if room.grid_y < 2:
            room.neighbors.append((room.grid_x, room.grid_y + 1))
        # Up neighbor
        if room.grid_y > 0:
            room.neighbors.append((room.grid_x, room.grid_y - 1))

    # Assign door ports for all connections
    _assign_showcase_door_ports(showcase_rooms)

    # Generate tilemaps
    room_gen = RoomGenerator()
    room_tilemaps = {}

    print("\n[SHOWCASE] Generating room tilemaps...")
    for room in showcase_rooms:
        room.tilemap = room_gen.generate_tilemap(room)

        # Manual tile placement for interactive blocks showcase (room 0,2)
        if room.grid_x == 0 and room.grid_y == 2:
            _add_interactive_tiles_showcase(room.tilemap)

        # Manual tile placement for hazard tiles showcase (room 1,2)
        if room.grid_x == 1 and room.grid_y == 2:
            _add_hazard_tiles_showcase(room.tilemap)

        room_tilemaps[(room.grid_x, room.grid_y)] = room.tilemap
        print(f"  [{room.grid_x},{room.grid_y}] {room.description}")

    # Create world object
    start_room = showcase_rooms[0]
    exit_room = showcase_rooms[-1]

    biome = Biome(
        theme=BiomeTheme.DUNGEON,
        rooms=showcase_rooms,
        start_room=start_room
    )

    world = World(
        seed=12345,
        biomes=[biome],
        all_rooms=showcase_rooms,
        start_room=start_room,
        exit_room=exit_room,
        bounds=(0, 0, 2, 2)
    )

    # Build megamap
    print("\n[SHOWCASE] Building megamap...")
    megamap = _build_showcase_megamap(showcase_rooms, room_tilemaps)

    # Convert to pygame rects
    tiles = []
    platforms = []

    # Define which tiles are solid for collision
    SOLID_TILES = {
        TILE_SOLID,      # Normal solid
        TILE_ICE,        # Ice - solid but slippery
        TILE_MUD,        # Mud - solid but sticky
        TILE_BREAKABLE,  # Breakable - solid until broken
        TILE_CRACKED,    # Cracked - solid but fragile
        TILE_PUSHABLE,   # Pushable - solid block
        TILE_STICKY,     # Sticky - solid surface
    }

    # Liquids (water, lava) are NOT solid - player passes through with special physics
    LIQUID_TILES = {TILE_WATER, TILE_LAVA}

    for ty in range(len(megamap.tilemap)):
        for tx in range(len(megamap.tilemap[0])):
            tile_id = megamap.tilemap[ty][tx]
            x = tx * TILE_SIZE
            y = ty * TILE_SIZE

            if tile_id in SOLID_TILES:
                tiles.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
            elif tile_id == TILE_PLATFORM:
                platforms.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
            # Note: LIQUID_TILES don't create collision rects - handled by physics system

    # Spawn in START room at grid (0, 0) - center horizontally, near bottom vertically
    start_room_x_offset = 0 * ROOM_WIDTH_TILES  # START room is at grid (0, 0)
    start_room_y_offset = 0 * ROOM_HEIGHT_TILES
    spawn_x = (start_room_x_offset + 64) * TILE_SIZE  # Middle of room
    spawn_y = (start_room_y_offset + 118) * TILE_SIZE  # Near bottom, on walkable floor

    # Exit in EXIT room at grid (2, 2) - center horizontally, near bottom vertically
    exit_room_x_offset = 2 * ROOM_WIDTH_TILES  # EXIT room is at grid (2, 2)
    exit_room_y_offset = 2 * ROOM_HEIGHT_TILES
    exit_x = (exit_room_x_offset + 64) * TILE_SIZE
    exit_y = (exit_room_y_offset + 118) * TILE_SIZE

    print(f"\n[SHOWCASE] Level created:")
    print(f"  Rooms: 3x3 grid (9 rooms)")
    print(f"  Megamap: {megamap.width_tiles}x{megamap.height_tiles} tiles")
    print(f"  Tiles: {len(tiles)} solid, {len(platforms)} platforms")
    print(f"  Spawn: ({spawn_x}, {spawn_y})")
    print(f"  Exit: ({exit_x}, {exit_y})")
    print("="*60 + "\n")

    return tiles, platforms, 12345, spawn_x, spawn_y, exit_x, exit_y, world, megamap


def _add_interactive_tiles_showcase(tilemap):
    """Add interactive block tiles in a display pattern"""
    height = len(tilemap)
    width = len(tilemap[0]) if height > 0 else 0

    # Clear center area (safe bounds)
    for ty in range(40, min(100, height)):
        for tx in range(20, min(140, width)):
            tilemap[ty][tx] = TILE_EMPTY

    # Bottom platform
    if height > 100:
        for tx in range(20, min(140, width)):
            tilemap[100][tx] = TILE_SOLID

    # Breakable blocks section (left)
    for i in range(4):
        if 95 - i >= 0 and 95 - i < height:
            tilemap[95 - i][30] = TILE_BREAKABLE
    if 102 < height:
        tilemap[102][30] = TILE_SOLID  # Label platform

    # Cracked blocks section
    for i in range(4):
        if 95 - i >= 0 and 95 - i < height:
            tilemap[95 - i][50] = TILE_CRACKED
    if 102 < height:
        tilemap[102][50] = TILE_SOLID

    # Pushable blocks section
    for i in range(3):
        if 97 < height and 70 + i * 8 < width:
            tilemap[97][70 + i * 8] = TILE_PUSHABLE
    if 102 < height:
        tilemap[102][74] = TILE_SOLID

    # Sticky blocks section (right) - for wall jumping
    for i in range(6):
        if 94 - i >= 0 and 94 - i < height and 110 < width and 115 < width:
            tilemap[94 - i][110] = TILE_STICKY
            tilemap[94 - i][115] = TILE_STICKY
    if 102 < height and 112 < width:
        tilemap[102][112] = TILE_SOLID


def _add_hazard_tiles_showcase(tilemap):
    """Add environmental hazard tiles in a display pattern"""
    height = len(tilemap)
    width = len(tilemap[0]) if height > 0 else 0

    # Clear center area (safe bounds)
    for ty in range(40, min(100, height)):
        for tx in range(20, min(140, width)):
            tilemap[ty][tx] = TILE_EMPTY

    # Bottom platform
    if height > 100:
        for tx in range(20, min(140, width)):
            tilemap[100][tx] = TILE_SOLID

    # Ice section (left) - slippery floor
    for ty in range(95, min(101, height)):
        for tx in range(25, min(45, width)):
            tilemap[ty][tx] = TILE_ICE

    # Mud section (center-left) - slow movement
    for ty in range(95, min(101, height)):
        for tx in range(55, min(75, width)):
            tilemap[ty][tx] = TILE_MUD

    # Water section (center-right) - reduced gravity
    for ty in range(90, min(101, height)):
        for tx in range(85, min(100, width)):
            tilemap[ty][tx] = TILE_WATER

    # Lava section (right) - damage
    for ty in range(90, min(101, height)):
        for tx in range(110, min(125, width)):
            tilemap[ty][tx] = TILE_LAVA

    # Platform above hazards for comparison
    if 85 < height:
        for tx in range(25, min(125, width)):
            tilemap[85][tx] = TILE_PLATFORM


def _build_showcase_megamap(rooms, room_tilemaps):
    """Build megamap for showcase level"""
    # Calculate world dimensions
    grid_width = 3
    grid_height = 3

    megamap_width = grid_width * ROOM_WIDTH_TILES
    megamap_height = grid_height * ROOM_HEIGHT_TILES

    # Initialize megamap
    tilemap = [[TILE_EMPTY for _ in range(megamap_width)] for _ in range(megamap_height)]

    # Stitch rooms
    room_positions = {}
    for room in rooms:
        room_x = room.grid_x * ROOM_WIDTH_TILES
        room_y = room.grid_y * ROOM_HEIGHT_TILES

        room_positions[(room.grid_x, room.grid_y)] = (room_x * TILE_SIZE, room_y * TILE_SIZE)

        # Copy room tilemap
        room_tilemap = room_tilemaps[(room.grid_x, room.grid_y)]
        for ty in range(ROOM_HEIGHT_TILES):
            for tx in range(ROOM_WIDTH_TILES):
                if ty < len(room_tilemap) and tx < len(room_tilemap[0]):
                    tilemap[room_y + ty][room_x + tx] = room_tilemap[ty][tx]

    return Megamap(
        tilemap=tilemap,
        width_tiles=megamap_width,
        height_tiles=megamap_height,
        room_positions=room_positions,
        bounds=(0, 0, 2, 2)  # 3x3 grid (0-2 in both dimensions)
    )
