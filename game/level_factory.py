"""
Level Factory Module

This module contains level creation functions for Indie Ninja Adventures,
extracted from demo_game.py to reduce its size and improve modularity.

Functions:
- create_simple_level(): Create static test level with platforms
- create_procedural_level(): Generate procedural world with seed
- build_objective_location_targets(): Map location IDs to world positions
- spawn_objective_collectibles(): Spawn items needed for mission objectives
"""

import time
import random
from typing import Optional, Tuple, Any
import pygame

from config.physics_constants import (
    TILE_SIZE,
    ROOM_WIDTH_TILES,
    ROOM_HEIGHT_TILES,
    TILES_PER_ZONE,
)

# Display settings (virtual game resolution)
GAME_WIDTH = 1280
GAME_HEIGHT = 720

from systems.world_generation import WorldGenerator, generate_world_tilemaps, WorldShape
from systems.room_generation import TILE_SOLID, TILE_PLATFORM, TILE_EMPTY
from systems.megamap import build_megamap
from systems.connectivity import validate_world_connectivity
from game.mission_registry import ObjectiveType


def create_simple_level():
    """Create a simple test level with ground and platforms"""
    tiles = []

    # Ground
    for x in range(0, GAME_WIDTH, TILE_SIZE):
        tiles.append(pygame.Rect(x, GAME_HEIGHT - TILE_SIZE, TILE_SIZE, TILE_SIZE))

    # Left wall
    for y in range(0, GAME_HEIGHT, TILE_SIZE):
        tiles.append(pygame.Rect(0, y, TILE_SIZE, TILE_SIZE))

    # Right wall
    for y in range(0, GAME_HEIGHT, TILE_SIZE):
        tiles.append(pygame.Rect(GAME_WIDTH - TILE_SIZE, y, TILE_SIZE, TILE_SIZE))

    # Platforms
    # Low platform
    for x in range(200, 400, TILE_SIZE):
        tiles.append(pygame.Rect(x, 500, TILE_SIZE, TILE_SIZE))

    # Mid platform
    for x in range(600, 800, TILE_SIZE):
        tiles.append(pygame.Rect(x, 400, TILE_SIZE, TILE_SIZE))

    # High platform
    for x in range(300, 500, TILE_SIZE):
        tiles.append(pygame.Rect(x, 300, TILE_SIZE, TILE_SIZE))

    # Wall for wall jump practice
    for y in range(200, 500, TILE_SIZE):
        tiles.append(pygame.Rect(900, y, TILE_SIZE, TILE_SIZE))

    return tiles


def create_procedural_level(seed=None, shape_str="blob", num_rooms=10):
    """
    Create a procedurally generated level with megamap support.

    Args:
        seed: Random seed for generation (None = random)
        shape_str: World shape ("snake", "branchy", "blob", "spiral", "tree", "grid")
        num_rooms: Number of rooms to generate

    Returns:
        Tuple of (tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap)
    """
    start_time = time.time()

    if seed is None:
        seed = random.randint(1, 999999)

    # Convert shape string to WorldShape enum
    shape_map = {
        "snake": WorldShape.SNAKE,
        "branchy": WorldShape.BRANCHY,
        "blob": WorldShape.BLOB,
        "spiral": WorldShape.SPIRAL,
        "tree": WorldShape.TREE,
        "grid": WorldShape.GRID,
    }
    shape = shape_map.get(shape_str, WorldShape.BLOB)

    print(f"\n[PROCEDURAL] Generating world with seed={seed}, shape={shape_str}, rooms={num_rooms}...")

    # Generate world
    world_gen = WorldGenerator(seed=seed)
    world = world_gen.generate(num_biomes=1, rooms_per_biome=num_rooms, shape=shape)

    # Generate all room tilemaps
    print(f"[PROCEDURAL] Generating {len(world.all_rooms)} room tilemaps...")
    room_tilemaps = generate_world_tilemaps(world)

    # Validate connectivity
    print("[PROCEDURAL] Validating connectivity...")
    conn_result = validate_world_connectivity(world, room_tilemaps, verbose=False)
    print(f"[PROCEDURAL] Connectivity: {conn_result.tier_used} ({conn_result.fixes_applied} fixes)")

    # Build megamap
    print("[PROCEDURAL] Building megamap...")
    megamap = build_megamap(world, room_tilemaps)

    # Convert megamap to pygame rects
    tile_scale = TILE_SIZE  # 32 pixels per tile
    tiles = []
    platforms = []

    print(f"[PROCEDURAL] Converting {megamap.width_tiles}x{megamap.height_tiles} tiles...")
    for ty in range(megamap.height_tiles):
        for tx in range(megamap.width_tiles):
            tile_type = megamap.tilemap[ty][tx]
            x = tx * tile_scale
            y = ty * tile_scale

            if tile_type == TILE_SOLID:
                tiles.append(pygame.Rect(x, y, tile_scale, tile_scale))
            elif tile_type == TILE_PLATFORM:
                platforms.append(pygame.Rect(x, y, tile_scale, tile_scale))

    def ensure_support(point_x: float, point_y: float, tiles_list: list, search_height: int = 96):
        """
        Ensure there is ground under a critical point (spawn/exit). If no solid is found
        within search_height below the point, place a solid block directly underneath.
        """
        px = int(point_x)
        py = int(point_y)
        found = False
        for ty in range(py, min(py + search_height, megamap.height_tiles * tile_scale), tile_scale):
            test_rect = pygame.Rect(px - tile_scale // 2, ty, tile_scale, tile_scale)
            if any(test_rect.colliderect(t) for t in tiles_list):
                found = True
                break
        if not found:
            tiles_list.append(pygame.Rect(px - tile_scale // 2, py + tile_scale, tile_scale, tile_scale))

    # Find spawn point in start room
    start_room = world.start_room
    if start_room and start_room.anchors and "spawn" in start_room.anchors:
        # Get spawn anchor (in zone coordinates)
        zone_x, zone_y = start_room.anchors["spawn"][0]

        # Convert to world coordinates
        room_coords = (start_room.grid_x, start_room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        # Zone to pixel using configured zone size
        spawn_x = room_px + zone_x * TILES_PER_ZONE * tile_scale + (TILES_PER_ZONE * tile_scale) / 2
        spawn_y = room_py + zone_y * TILES_PER_ZONE * tile_scale + (TILES_PER_ZONE * tile_scale) / 2
    else:
        # Fallback: search for floor in start room tilemap
        room = world.start_room
        spawn_x = GAME_WIDTH / 2
        spawn_y = GAME_HEIGHT / 2

        for ty in range(len(room.tilemap) - 1, 0, -1):
            for tx in range(len(room.tilemap[0]) // 2 - 10, len(room.tilemap[0]) // 2 + 10):
                if (room.tilemap[ty][tx] == TILE_SOLID and
                    ty > 0 and room.tilemap[ty - 1][tx] == TILE_EMPTY):
                    spawn_x = tx * tile_scale + tile_scale / 2
                    spawn_y = (ty - 1) * tile_scale - 10
                    break
            if spawn_y != GAME_HEIGHT / 2:
                break

    # Find exit point in exit room
    exit_x = None
    exit_y = None
    exit_room = next((r for r in world.all_rooms if r.room_type.value == "exit"), None)

    if exit_room and exit_room.anchors and "exit" in exit_room.anchors:
        # Get exit anchor (in zone coordinates)
        zone_x, zone_y = exit_room.anchors["exit"][0]

        # Convert to world coordinates
        room_coords = (exit_room.grid_x, exit_room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        # Zone to pixel using configured zone size
        exit_x = room_px + zone_x * TILES_PER_ZONE * tile_scale + (TILES_PER_ZONE * tile_scale) / 2
        exit_y = room_py + zone_y * TILES_PER_ZONE * tile_scale + (TILES_PER_ZONE * tile_scale) / 2
    else:
        # Fallback: place exit in center of exit room
        if exit_room:
            room_coords = (exit_room.grid_x, exit_room.grid_y)
            room_px, room_py = megamap.room_positions[room_coords]
            exit_x = room_px + ROOM_WIDTH_TILES * tile_scale / 2
            exit_y = room_py + ROOM_HEIGHT_TILES * tile_scale / 2

    # Safety: ensure spawn/exit have support beneath
    ensure_support(spawn_x, spawn_y, tiles)
    if exit_x and exit_y:
        ensure_support(exit_x, exit_y, tiles)

    gen_time = time.time() - start_time
    print(f"[PROCEDURAL] Generated in {gen_time*1000:.1f}ms")
    print(f"[PROCEDURAL] World: {len(world.all_rooms)} rooms, bounds: {world.bounds}")
    print(f"[PROCEDURAL] Megamap: {megamap.width_tiles}x{megamap.height_tiles} tiles")
    print(f"[PROCEDURAL] Tiles: {len(tiles)} solid, {len(platforms)} platforms")
    print(f"[PROCEDURAL] Spawn point: ({spawn_x:.0f}, {spawn_y:.0f})")
    if exit_x and exit_y:
        print(f"[PROCEDURAL] Exit point: ({exit_x:.0f}, {exit_y:.0f})")

    # Print room distribution
    room_types = {}
    for room in world.all_rooms:
        rt = room.room_type.value
        room_types[rt] = room_types.get(rt, 0) + 1
    print(f"[PROCEDURAL] Room types: {', '.join(f'{k}={v}' for k, v in sorted(room_types.items()))}")

    return tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap


def build_objective_location_targets(world, megamap, spawn_x, spawn_y, exit_x, exit_y):
    """
    Build a location_id -> position mapping for reach objectives.

    Args:
        world: World instance from world generation
        megamap: Megamap instance with room positions
        spawn_x: Spawn point X coordinate
        spawn_y: Spawn point Y coordinate
        exit_x: Exit point X coordinate
        exit_y: Exit point Y coordinate

    Returns:
        Dict mapping location IDs to (x, y) tuples
    """
    targets = {}
    if spawn_x is not None and spawn_y is not None:
        targets["spawn"] = (spawn_x, spawn_y)
    if exit_x is not None and exit_y is not None:
        targets["exit"] = (exit_x, exit_y)

    if not world or not megamap:
        return targets

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        if room_coords not in megamap.room_positions:
            continue
        room_px, room_py = megamap.room_positions[room_coords]

        anchors = getattr(room, "anchors", {}) or {}
        for kind, anchor_positions in anchors.items():
            if anchor_positions is None:
                continue
            positions = anchor_positions if isinstance(anchor_positions, list) else [anchor_positions]
            for anchor_pos in positions:
                if not anchor_pos:
                    continue
                zx, zy = anchor_pos
                world_x = room_px + zx * TILES_PER_ZONE * TILE_SIZE + (TILES_PER_ZONE * TILE_SIZE) / 2
                world_y = room_py + zy * TILES_PER_ZONE * TILE_SIZE + (TILES_PER_ZONE * TILE_SIZE) / 2
                targets.setdefault(kind, (world_x, world_y))

        resolved_anchors = getattr(room, "resolved_anchors", {}) or {}
        for kind, anchor_pos in resolved_anchors.items():
            tx, ty = anchor_pos
            world_x = room_px + tx * TILE_SIZE + TILE_SIZE / 2
            world_y = room_py + ty * TILE_SIZE + TILE_SIZE / 2
            targets.setdefault(kind, (world_x, world_y))

    return targets


def _collect_objective_spawn_positions(world, megamap):
    """
    Collect valid pickup positions for objective items.

    Args:
        world: World instance from world generation
        megamap: Megamap instance with room positions

    Returns:
        List of (x, y) positions suitable for spawning pickups
    """
    positions = []
    if not world or not megamap:
        return positions

    for room in sorted(world.all_rooms, key=lambda r: (r.grid_y, r.grid_x)):
        if not room.tilemap:
            continue
        room_coords = (room.grid_x, room.grid_y)
        if room_coords not in megamap.room_positions:
            continue
        room_px, room_py = megamap.room_positions[room_coords]

        for ty in range(1, len(room.tilemap) - 1, 4):
            for tx in range(1, len(room.tilemap[0]) - 1, 4):
                tile = room.tilemap[ty][tx]
                tile_above = room.tilemap[ty - 1][tx]
                if tile in (TILE_SOLID, TILE_PLATFORM) and tile_above == TILE_EMPTY:
                    x = room_px + tx * TILE_SIZE
                    y = room_py + (ty - 1) * TILE_SIZE
                    positions.append((x, y))

    positions = sorted(set(positions))
    return positions


def spawn_objective_collectibles(world, megamap, pickup_manager, mission_def, seed):
    """
    Spawn collectibles for collect-item objectives so missions are completable.

    Args:
        world: World instance from world generation
        megamap: Megamap instance with room positions
        pickup_manager: PickupManager instance
        mission_def: Mission definition with objectives
        seed: Random seed for deterministic spawning

    Returns:
        Number of collectibles spawned
    """
    if not world or not megamap or not mission_def:
        return 0

    objective_items = []
    total_needed = 0
    for obj_def in mission_def.objectives:
        if obj_def.objective_type != ObjectiveType.COLLECT_ITEMS:
            continue
        item_id = getattr(obj_def, "item", None)
        if not item_id or item_id == "coin":
            continue
        base_target = obj_def.count if getattr(obj_def, "count", None) is not None else obj_def.target
        target_value = base_target if base_target is not None else 1
        if target_value <= 0:
            continue
        objective_items.append((item_id, target_value))
        total_needed += target_value

    if not objective_items:
        return 0

    positions = _collect_objective_spawn_positions(world, megamap)
    if len(positions) < total_needed:
        print(f"[MISSION] Warning: Only {len(positions)} spawn positions, need {total_needed}")

    # Deterministic distribution
    rng = random.Random(seed + 12345)
    rng.shuffle(positions)

    spawned_count = 0
    pos_idx = 0
    for item_id, target in objective_items:
        for _ in range(target):
            if pos_idx >= len(positions):
                break
            x, y = positions[pos_idx]
            pickup_manager.spawn_pickup(item_id, x, y)
            spawned_count += 1
            pos_idx += 1

    print(f"[MISSION] Spawned {spawned_count} objective collectibles across {len(positions)} positions")
    return spawned_count
