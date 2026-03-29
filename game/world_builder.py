"""
World Builder Module

This module contains the world regeneration logic for Indie Ninja Adventures,
extracted from demo_game.py to reduce its size and improve modularity.

The main function is regenerate_world_state(), which is called when:
1. Game starts with command-line args (--procedural, --mission, etc.)
2. Mode selected from menu (Campaign/Arcade/Playtest)
3. Switching between game modes

This properly clears all existing state and creates a new world.
"""

import random
import time

import pygame

from config.physics_constants import (
    ROOM_HEIGHT_TILES,
    ROOM_WIDTH_TILES,
    TILE_SIZE,
)
from entities.enemy import EnemyType, get_enemy_definition
from entities.enemy_manager import EnemySpawnAnchor
from game.level_factory import (
    create_procedural_level,
    spawn_objective_collectibles,
)
from game.portal_system import PortalType
from rendering import MinimapConfig, MinimapRenderer
from systems.hazard_spawner import HazardSpawner
from systems.pickup_spawner import PickupSpawner
from systems.room_generation import TILE_EMPTY, TILE_SOLID


def _clear_existing_state(
    enemy_manager,
    pickup_manager,
    hazard_manager,
    portal_manager,
    level_manager,
    npc_manager,
):
    """
    Clear all existing game state before regenerating world.

    This ensures a clean slate for world regeneration.
    """
    print("[WORLD REGEN] Clearing existing state...")

    # Clear enemies
    enemy_manager.clear()

    # Clear pickups (reset internal lists and stats)
    pickup_manager.pickups.clear()
    pickup_manager.coins_collected = 0
    pickup_manager.health_collected = 0
    pickup_manager.collectibles_collected = 0
    pickup_manager.total_collectibles = 0

    # Clear hazards (reset internal lists and stats)
    hazard_manager.hazards.clear()
    hazard_manager.total_spikes = 0
    hazard_manager.total_voids = 0
    hazard_manager.total_poison = 0
    hazard_manager.damage_dealt = 0
    hazard_manager.deaths_caused = 0

    # Clear portals
    if portal_manager:
        portal_manager.clear_portals()

    # Reset level manager (create new state)
    from game.level_manager import LevelState

    level_manager.state = LevelState()
    level_manager.level_start_time = 0.0

    # Clear NPCs (for hub world regeneration)
    npc_manager.clear_npcs()


def _snap_to_ground(entities, tiles):
    """Snap entities to nearest solid tile below their current position."""
    if not tiles:
        return
    for ent in entities:
        if hasattr(ent, "physics") and ent.physics:
            ex, ey, ew, eh = ent.physics.x, ent.physics.y, ent.physics.width, ent.physics.height
        elif hasattr(ent, "x"):
            ew = getattr(ent, "width", 32)
            eh = getattr(ent, "height", 48)
            ex, ey = ent.x, ent.y
        else:
            continue

        target_y = None
        ent_left = ex
        ent_right = ex + ew
        ent_bottom = ey + eh
        for tile in tiles:
            if tile.right <= ent_left or tile.left >= ent_right:
                continue
            if tile.top >= ent_bottom:
                gap = tile.top - ent_bottom
                if target_y is None or gap < (target_y - ent_bottom):
                    target_y = tile.top - eh
        if target_y is not None:
            if hasattr(ent, "physics") and ent.physics:
                ent.physics.y = float(target_y)
                ent.physics.vy = 0.0
                ent.physics.on_ground = True
                if hasattr(ent, "sync_from_physics"):
                    ent.sync_from_physics()
            else:
                ent.y = float(target_y)


def _find_portal_floor(
    x: float, y: float, tiles_list: list, portal_width: int, portal_height: int, max_drop: int
) -> float:
    """Find floor position for portal placement."""
    center_x = x + portal_width / 2
    nearest_top = None
    for tile in tiles_list:
        if tile.left <= center_x <= tile.right and y <= tile.top <= y + max_drop:
            if nearest_top is None or tile.top < nearest_top:
                nearest_top = tile.top
    if nearest_top is None:
        return None
    return nearest_top - portal_height


def _find_clear_portal_position(
    base_x: float, base_y: float, tiles_list: list, portal_width: int, portal_height: int
) -> tuple[float, float]:
    """Find a clear position for portal placement without colliding with tiles."""
    step = TILE_SIZE
    max_radius = 8
    max_drop = ROOM_HEIGHT_TILES * TILE_SIZE

    for radius in range(max_radius + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                candidate_x = base_x + dx * step
                candidate_y = base_y + dy * step
                floor_y = _find_portal_floor(
                    candidate_x, candidate_y, tiles_list, portal_width, portal_height, max_drop
                )
                if floor_y is None:
                    continue
                portal_rect = pygame.Rect(
                    int(candidate_x), int(floor_y), portal_width, portal_height
                )
                if any(portal_rect.colliderect(tile) for tile in tiles_list):
                    continue
                return candidate_x, floor_y
    return base_x, base_y


def _spawn_portal_safe(
    portal_manager,
    tiles,
    portal_id: str,
    destination_id: str,
    world_x: float,
    world_y: float,
    bidirectional: bool = True,
):
    """Spawn a portal at a safe position (not colliding with tiles)."""
    portal_width = 64
    portal_height = 64
    base_x = world_x - portal_width / 2
    base_y = world_y - portal_height / 2
    safe_x, safe_y = _find_clear_portal_position(base_x, base_y, tiles, portal_width, portal_height)
    portal_manager.spawn_portal(
        portal_id=portal_id,
        portal_type=PortalType.HUB,
        destination_id=destination_id,
        x=safe_x,
        y=safe_y,
        bidirectional=bidirectional,
    )


def _spawn_pickups_and_hazards(
    world,
    megamap,
    spawn_x,
    spawn_y,
    exit_x,
    exit_y,
    seed,
    pickup_manager,
    hazard_manager,
    hub_id,
    mission_def,
):
    """Spawn pickups and hazards for all rooms in the world."""
    print("[WORLD REGEN] Spawning pickups and hazards...")
    pickup_spawner = PickupSpawner(seed)
    hazard_spawner = HazardSpawner(seed)

    # Detect boss/champion level: any defeat_boss objective means tripled health drops
    boss_level = False
    if mission_def:
        for obj in mission_def.objectives:
            obj_type = getattr(obj, "objective_type", None)
            if obj_type is not None and str(obj_type).endswith("DEFEAT_BOSS"):
                boss_level = True
                break
            if getattr(obj, "type", None) == "defeat_boss":
                boss_level = True
                break

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        room_spawn_pos = (spawn_x, spawn_y) if room.room_type.value == "start" else None
        room_exit_pos = (exit_x, exit_y) if room.room_type.value == "exit" else None

        pickup_spawner.spawn_pickups_for_room(room, pickup_manager, room_px, room_py, boss_level=boss_level)
        if not hub_id:  # Keep hubs safe and avoid exit-based hazard offsets
            hazard_spawner.spawn_hazards_for_room(
                room,
                hazard_manager,
                room_px,
                room_py,
                spawn_pos=room_spawn_pos,
                exit_pos=room_exit_pos,
            )

    objective_pickups = 0
    if mission_def and not hub_id:
        objective_pickups = spawn_objective_collectibles(
            world, megamap, pickup_manager, mission_def, seed
        )

    print(
        f"[WORLD REGEN] Spawned: {len([p for p in pickup_manager.pickups if p.pickup_type == 'coin'])} coins, "
        + f"{pickup_manager.total_collectibles} collectibles, "
        + f"{hazard_manager.total_spikes} spikes, {hazard_manager.total_poison} poison zones"
    )
    if objective_pickups:
        print(f"[WORLD REGEN] Objective pickups: {objective_pickups}")


def _spawn_enemies(world, megamap, seed, enemy_manager, tiles, hub_id):
    """Spawn enemies for all rooms in the world."""
    print("[WORLD REGEN] Spawning enemies...")
    enemy_spawn_rng = random.Random(seed)

    if hub_id:
        print("[WORLD REGEN] Hub world detected - skipping enemy spawns for safety")
        return

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        # Skip start and exit rooms
        if room.room_type.value in ["start", "exit"]:
            continue

        # Determine number of enemies based on room type
        if room.room_type.value == "challenge":
            num_enemies = enemy_spawn_rng.randint(3, 5)
        elif room.room_type.value == "treasure":
            num_enemies = enemy_spawn_rng.randint(2, 3)
        else:
            num_enemies = enemy_spawn_rng.randint(1, 2)

        def find_ground_spawn(definition):
            """Find a spawn point above ground (empty above solid) in this room."""
            positions = []
            if room.tilemap:
                for ty in range(1, len(room.tilemap) - 1, 2):
                    for tx in range(1, len(room.tilemap[0]) - 1, 2):
                        tile = room.tilemap[ty][tx]
                        above = room.tilemap[ty - 1][tx]
                        if tile == TILE_SOLID and above == TILE_EMPTY:
                            world_x = (
                                room_px + tx * TILE_SIZE + TILE_SIZE / 2 - definition.width / 2
                            )
                            # Place enemy standing on this solid tile (feet on top of the solid)
                            world_y = room_py + ty * TILE_SIZE - definition.height
                            positions.append((world_x, world_y))
            return positions

        # Spawn enemies
        for i in range(num_enemies):
            enemy_types = [EnemyType.GOBLIN, EnemyType.SLIME, EnemyType.BAT]
            enemy_type = enemy_spawn_rng.choice(enemy_types)
            definition = get_enemy_definition(enemy_type)
            # Spawn on valid ground when possible
            spawn_positions = find_ground_spawn(definition)
            if spawn_positions:
                world_x, world_y = enemy_spawn_rng.choice(spawn_positions)
            else:
                max_local_x = max(2, ROOM_WIDTH_TILES - 3)
                max_local_y = max(2, ROOM_HEIGHT_TILES - 3)
                local_x = enemy_spawn_rng.randint(2, max_local_x) * TILE_SIZE
                local_y = enemy_spawn_rng.randint(2, max_local_y) * TILE_SIZE
                world_x = room_px + local_x
                world_y = room_py + local_y

            anchor = EnemySpawnAnchor(
                anchor_id=f"room_{room.grid_x}_{room.grid_y}_enemy_{i}",
                enemy_type=enemy_type,
                x=world_x,
                y=world_y,
                patrol_type="horizontal" if enemy_type != EnemyType.BAT else "circle",
                patrol_distance=100.0 if enemy_type == EnemyType.GOBLIN else 64.0,
                spawn_seed=enemy_spawn_rng.randint(0, 999999),
            )
            enemy_manager.register_spawn_anchor(anchor)

    enemy_manager.spawn_all_enemies()
    print(f"[WORLD REGEN] Spawned: {len(enemy_manager.enemies)} enemies")
    _snap_to_ground(enemy_manager.enemies.values(), tiles)


def _spawn_npcs(
    hub_manager,
    hub_id,
    megamap,
    npc_manager,
    spawn_x,
    spawn_y,
    base_room_coords,
    tiles,
    rooms,
    shape,
):
    """Spawn NPCs for hub worlds."""
    print("[WORLD REGEN] Spawning NPCs...")

    if hub_manager and hub_id and megamap:
        npc_positions = hub_manager.get_npc_positions(
            hub_id, megamap.room_positions, base_room_coords
        )
        for anchor, world_x, world_y in npc_positions:
            npc_manager.spawn_npc(anchor.npc_id, world_x, world_y)
        if npc_positions:
            print(f"[WORLD REGEN] Spawned NPCs from hub anchors: {len(npc_positions)}")
        else:
            # Fallback: drop core NPCs near spawn if anchors missing
            fallback_offset = 150
            if hub_id == "central_hub":
                npc_manager.spawn_npc("tutorial_elder", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc(
                    "forest_ranger", spawn_x - fallback_offset, spawn_y
                )  # mission giver fallback
            elif "forest" in hub_id:
                npc_manager.spawn_npc("forest_ranger", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc("forest_merchant", spawn_x - fallback_offset, spawn_y)
            elif "town" in hub_id:
                npc_manager.spawn_npc("town_captain", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc("town_blacksmith", spawn_x - fallback_offset, spawn_y)
            elif "cave" in hub_id or "caves" in hub_id:
                npc_manager.spawn_npc("cave_explorer", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc("crystal_trader", spawn_x - fallback_offset, spawn_y)
            elif "castle" in hub_id:
                npc_manager.spawn_npc("castle_commander", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc("castle_armorer", spawn_x - fallback_offset, spawn_y)
            elif "sewer" in hub_id:
                npc_manager.spawn_npc("sewer_scout", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc("sewer_vendor", spawn_x - fallback_offset, spawn_y)
            print(f"[WORLD REGEN] Spawned fallback NPCs for hub '{hub_id}'")
    else:
        # Only spawn default NPCs in central hub fallback
        if rooms == 10 and shape == "blob":
            npc_manager.spawn_npc("tutorial_elder", spawn_x + 150, spawn_y)
            print(f"[WORLD REGEN] Spawned NPCs: {len(npc_manager.npcs)} NPCs in hub")

    # Snap NPCs to ground after spawn
    _snap_to_ground(npc_manager.npcs, tiles)


def _spawn_portals(
    portal_manager, hub_manager, hub_id, megamap, base_room_coords, tiles, spawn_x, spawn_y
):
    """Spawn portals for hub worlds."""
    if not (portal_manager and hub_manager and hub_id and megamap):
        return

    portal_positions = hub_manager.get_portal_positions(
        hub_id, megamap.room_positions, base_room_coords
    )
    for anchor, world_x, world_y in portal_positions:
        _spawn_portal_safe(
            portal_manager,
            tiles,
            portal_id=anchor.portal_id,
            destination_id=anchor.destination_hub_id,
            world_x=world_x,
            world_y=world_y,
            bidirectional=anchor.bidirectional,
        )
    if portal_positions:
        print(f"[WORLD REGEN] Spawned {len(portal_positions)} portals for hub '{hub_id}'")
    else:
        # Fallback portals near spawn
        fallback_y = spawn_y
        if hub_id == "central_hub":
            _spawn_portal_safe(
                portal_manager,
                tiles,
                "portal_to_forest",
                "forest_hub",
                spawn_x,
                fallback_y - 240,
                bidirectional=True,
            )
            _spawn_portal_safe(
                portal_manager,
                tiles,
                "portal_to_town",
                "town_hub",
                spawn_x + 300,
                fallback_y,
                bidirectional=True,
            )
            _spawn_portal_safe(
                portal_manager,
                tiles,
                "portal_to_caves",
                "caves_hub",
                spawn_x,
                fallback_y + 240,
                bidirectional=True,
            )
            _spawn_portal_safe(
                portal_manager,
                tiles,
                "portal_to_castle",
                "castle_hub",
                spawn_x + 300,
                fallback_y - 200,
                bidirectional=True,
            )
            _spawn_portal_safe(
                portal_manager,
                tiles,
                "portal_to_sewer",
                "sewer_hub",
                spawn_x - 300,
                fallback_y + 200,
                bidirectional=True,
            )
            _spawn_portal_safe(
                portal_manager,
                tiles,
                "portal_to_arcade",
                "arcade_loop",
                spawn_x - 300,
                fallback_y,
                bidirectional=True,
            )
        else:
            _spawn_portal_safe(
                portal_manager,
                tiles,
                f"portal_to_central_from_{hub_id}",
                "central_hub",
                spawn_x + 300,
                fallback_y,
                bidirectional=True,
            )
        print(f"[WORLD REGEN] Spawned fallback portals for hub '{hub_id}'")


def regenerate_world_state(
    # World parameters
    seed,
    shape,
    rooms,
    # System references
    collision_system,
    camera,
    player,
    enemy_manager,
    pickup_manager,
    hazard_manager,
    level_manager,
    npc_manager,
    bus,
    # Constants
    GAME_WIDTH,
    GAME_HEIGHT,
    # Hub/portal
    hub_id=None,
    hub_manager=None,
    portal_manager=None,
    mission_def=None,
):
    """
    Regenerate entire world state - properly clears all existing state and creates new world.

    This function is called:
    1. On game startup if command-line args provided (--procedural, --mission, etc.)
    2. When mode selected from menu (Campaign/Arcade/Playtest)
    3. When switching between modes

    Returns: tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap
    """
    print(f"\n[WORLD REGEN] Regenerating world: seed={seed}, shape={shape}, rooms={rooms}")

    # ============================================================
    # Step 1: Clear all existing game state
    # ============================================================
    _clear_existing_state(
        enemy_manager, pickup_manager, hazard_manager, portal_manager, level_manager, npc_manager
    )

    # ============================================================
    # Step 2: Generate new world
    # ============================================================
    print("[WORLD REGEN] Generating new world...")

    # Hub-aware overrides for deterministic travel (avoid hub/world desync)
    if hub_manager and hub_id:
        from systems.seed_hierarchy import SeedDerivation

        hub_def = hub_manager.get_hub_definition(hub_id)
        seed = SeedDerivation.derive_region_seed(hub_manager.world_seed, hub_id)
        if hub_def:
            shape = hub_def.world_shape.value if hasattr(hub_def.world_shape, "value") else shape
            rooms = hub_def.room_count

    tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap = (
        create_procedural_level(seed, shape, rooms)
    )

    # Override spawn with hub-specific spawn if available
    base_room_coords = None
    if world and getattr(world, "start_room", None):
        base_room_coords = (world.start_room.grid_x, world.start_room.grid_y)

    if hub_manager and hub_id and megamap:
        spawn_pos = hub_manager.get_spawn_position(hub_id, megamap.room_positions, base_room_coords)
        if spawn_pos:
            spawn_x, spawn_y = spawn_pos
        # Hubs don't use procedural exits
        exit_x = None
        exit_y = None

    # ============================================================
    # Step 3: Update collision system with new tiles
    # ============================================================
    print("[WORLD REGEN] Updating collision system...")
    collision_system.set_tiles(tiles, platforms)

    # ============================================================
    # Step 4: Update camera bounds
    # ============================================================
    print("[WORLD REGEN] Updating camera bounds...")
    if world and megamap:
        world_w = megamap.width_tiles * 32
        world_h = megamap.height_tiles * 32
        camera.set_world_bounds(world_w, world_h)
        camera.set_room_bounds(0, 0, world_w, world_h)
    else:
        camera.set_world_bounds(GAME_WIDTH, GAME_HEIGHT)
        camera.set_room_bounds(0, 0, GAME_WIDTH, GAME_HEIGHT)

    # ============================================================
    # Step 5: Create minimap
    # ============================================================
    minimap = MinimapRenderer(
        MinimapConfig(
            position=(20, 500),
            show_connections=True,
            show_player=True,
            highlight_current=True,
            scale=16 if rooms <= 10 else 12,
        )
    )

    # ============================================================
    # Step 6: Spawn pickups and hazards
    # ============================================================
    _spawn_pickups_and_hazards(
        world,
        megamap,
        spawn_x,
        spawn_y,
        exit_x,
        exit_y,
        seed,
        pickup_manager,
        hazard_manager,
        hub_id,
        mission_def,
    )

    # ============================================================
    # Step 7: Spawn enemies
    # ============================================================
    _spawn_enemies(world, megamap, seed, enemy_manager, tiles, hub_id)

    # ============================================================
    # Step 7.5: Spawn NPCs (for hub worlds)
    # ============================================================
    _spawn_npcs(
        hub_manager,
        hub_id,
        megamap,
        npc_manager,
        spawn_x,
        spawn_y,
        base_room_coords,
        tiles,
        rooms,
        shape,
    )

    # ============================================================
    # Step 7.6: Spawn portals (for hubs)
    # ============================================================
    _spawn_portals(
        portal_manager, hub_manager, hub_id, megamap, base_room_coords, tiles, spawn_x, spawn_y
    )

    # ============================================================
    # Step 8: Teleport player to spawn
    # ============================================================
    print(f"[WORLD REGEN] Teleporting player to spawn: ({spawn_x:.0f}, {spawn_y:.0f})")
    player.state.physics.x = float(spawn_x)
    player.state.physics.y = float(spawn_y)
    player.state.physics.vx = 0
    player.state.physics.vy = 0

    # Snap camera to player
    camera.x = player.state.physics.x - camera.config.game_width // 2
    camera.y = player.state.physics.y - camera.config.game_height // 2
    camera.target_x = camera.x
    camera.target_y = camera.y

    # ============================================================
    # Step 9: Update level manager
    # ============================================================
    if exit_x is not None and exit_y is not None:
        level_manager.set_exit_position(exit_x, exit_y)
    level_manager.set_spawn_position(spawn_x, spawn_y)
    level_manager.set_total_collectibles(pickup_manager.total_collectibles)

    level_manager.start_level(time.time())

    print("[WORLD REGEN] World regeneration complete!\n")

    return tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3: server-side headless world bootstrap
# ──────────────────────────────────────────────────────────────────────────────


def create_server_world(
    seed: int,
    shape: str,
    rooms: int,
    collision_system,
    enemy_manager,
    pickup_manager,
    hazard_manager,
):
    """
    Minimal world generation for the authoritative server (Phase 3).

    Differs from regenerate_world_state() in that it:
    - Does not require camera, player, level_manager, or npc_manager.
    - Does not create a minimap renderer (display-only).
    - Returns the subset of data the GameSimulator needs.

    Args:
        seed: World seed — must match the seed sent to clients in GAME_START.
        shape: World shape string ("snake", "blob", etc.)
        rooms: Number of rooms.
        collision_system, enemy_manager, pickup_manager, hazard_manager:
            Pre-created manager instances.

    Returns:
        Tuple of (tiles, platforms, seed, spawn_x, spawn_y, megamap)
    """
    # 1. Generate world geometry
    tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap = (
        create_procedural_level(seed, shape, rooms)
    )

    # 2. Wipe any prior state in managers
    enemy_manager.clear()
    pickup_manager.pickups.clear()
    pickup_manager.coins_collected = 0
    pickup_manager.health_collected = 0
    pickup_manager.collectibles_collected = 0
    pickup_manager.total_collectibles = 0
    hazard_manager.hazards.clear()
    hazard_manager.total_spikes = 0
    hazard_manager.total_voids = 0
    hazard_manager.total_poison = 0
    hazard_manager.damage_dealt = 0
    hazard_manager.deaths_caused = 0

    # 3. Update collision system
    collision_system.set_tiles(tiles, platforms)

    # 4. Spawn enemies, pickups, hazards (same logic as regenerate_world_state)
    _spawn_pickups_and_hazards(
        world, megamap, spawn_x, spawn_y, exit_x, exit_y,
        seed, pickup_manager, hazard_manager,
        hub_id=None, mission_def=None,
    )
    _spawn_enemies(world, megamap, seed, enemy_manager, tiles, hub_id=None)

    print(
        f"[SERVER WORLD] Generated: seed={seed}  enemies={len(enemy_manager.enemies)}"
        f"  pickups={len(pickup_manager.get_alive_pickups())}"
    )
    return tiles, platforms, seed, spawn_x, spawn_y, megamap
