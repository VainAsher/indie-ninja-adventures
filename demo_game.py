"""
Vain Asher Gaming's: Indie Ninja Adventures - Simple Game Demo

Demonstrates all systems working together:
- Event-driven architecture
- Physics system (gravity)
- Collision system
- Player with all mechanics
- Fixed 60Hz physics
- Procedural world generation (with --procedural flag)python demo_game.py --procedural --seed 12345

Controls:
- Arrow keys / WASD: Move
- Space / W / Up: Jump
- Shift: Dash
- S / Down: Crouch (toggle)
- P: Toggle between static/procedural (in-game)
- ESC: Quit

Usage:
    python demo_game.py           # Static test level
    python demo_game.py --procedural  # Procedural world
"""

import os
import sys
import json
import argparse
import math
import time
import random
from typing import Tuple

import pygame

# Add parent dir to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.physics_constants import TILE_SIZE as CONFIG_TILE_SIZE, ROOM_WIDTH_TILES, ROOM_HEIGHT_TILES, TILES_PER_ZONE
from core import EventBus, GameLogger, GameClock, EntityManager, EntityType, PhysicsState
from core.event_bus import CollisionEvent, VelocityChangeEvent
from systems import CollisionSystem, PhysicsSystem, CameraSystem, CameraConfig, CameraMode, get_recommended_window_size, SaveManager
from systems.world_generation import WorldGenerator, generate_world_tilemaps
from systems.zone_planning import ZonePlanner
from systems.room_generation import (
    RoomGenerator, TILE_SOLID, TILE_PLATFORM, TILE_EMPTY,
    print_tilemap_ascii
)
from systems.megamap import build_megamap, get_room_at_position, get_tile_at_position
from systems.connectivity import validate_world_connectivity
from rendering import SpriteManager, ParticleSystem, HUDRenderer, MinimapRenderer, MinimapConfig, get_current_room_coords, VictoryScreen, render_pickups, render_hazards
from rendering.tile_loader import TileLoader
from rendering.npc_prompt import NPCPromptRenderer, NPCIndicatorRenderer
from network import InputCommand, InputPipeline
from entities.player import Player
from entities import PickupManager, PickupCollectedEvent, HazardManager, PlayerDamageEvent, PlayerDeathEvent
from game import LevelManager, LevelCompletionEvent, GameStateManager, GameState
from ui import MenuManager, MainMenu, PauseMenu, SettingsMenu, MenuAction, TutorialManager, ControlsHintOverlay
from ui.inventory_ui import InventoryUI
from ui.mode_selection_menu import GameModeSelectionMenu, MissionSelectorMenu
from ui.mission_menu import MissionMenuUI, MissionDisplay, MissionStatus
from ui.shop_ui import ShopUI
from systems.hazard_spawner import HazardSpawner
from systems.pickup_spawner import PickupSpawner

# Phase 4-7: New system imports
from entities.enemy import Enemy, EnemyType, get_enemy_definition
from entities.enemy_manager import EnemyManager, EnemySpawnAnchor
from game.play_mode import PlayModeManager, PlayMode
from game.campaign_manager import CampaignManager
from game.mission_registry import get_mission_registry, ObjectiveType
from rendering.objective_hud import ObjectiveHUDRenderer
from rendering.loot_notification import LootNotificationManager
from game.trading_system import TradingManager, ShopTier
from game.inventory_system import Inventory, initialize_item_manager, get_item_manager
from game.objective_tracker import (
    ObjectiveTracker,
    get_objective_display_text,
    ItemCollectedEvent,
    PlayerPositionUpdateEvent,
)
from mechanics.combat_mechanic import CombatMechanic
from game.portal_system import PortalManager, PortalType, PortalTravelEvent, draw_portal
from game.hub_manager import HubManager
from systems.seed_hierarchy import SeedDerivation
from entities.components.enemy_movement import EnemyMovementComponent

# Phase 2: Dialogue System
from game.dialogue_system import DialogueManager
from ui.dialogue_ui import DialogueUI
from entities.npc import NPCManager, DialogueStartEvent, ShopOpenEvent as NPCShopOpenEvent, MissionMenuOpenEvent

# Phase 3: Story System (v0.7.0 - The Hollowed Ninja)
from game.story_manager import StoryManager
from game.ending_manager import EndingManager, EndingChoice, EndingState
from entities.companions import CompanionOrbs
from rendering.hub_effects import HubEffectsRenderer


# Display settings (virtual game resolution)
GAME_WIDTH = 1280
GAME_HEIGHT = 720
FPS = 60

# Colors
COLOR_BG = (10, 10, 20)
COLOR_TILE = (200, 200, 200)
COLOR_PLAYER = (255, 80, 80)
COLOR_TEXT = (230, 230, 255)

# Tile size
TILE_SIZE = CONFIG_TILE_SIZE

# User data directory helpers
def get_user_data_dir():
    """Get the user_data directory path (project-local by default)"""
    env_dir = os.environ.get("NINJADASH_USER_DATA")
    if env_dir:
        return Path(env_dir)

    # Default: project-local user_data directory
    # When frozen (PyInstaller), use executable directory, not __file__
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle - use executable directory
        project_root = Path(sys.executable).parent
    else:
        # Running as script - use script directory
        project_root = Path(__file__).parent

    return project_root / 'user_data'

def ensure_user_data_dirs():
    """Ensure all user_data subdirectories exist"""
    user_data = get_user_data_dir()
    print(f"[USER DATA] Creating directories at: {user_data}")
    (user_data / 'logs').mkdir(parents=True, exist_ok=True)
    (user_data / 'replays').mkdir(parents=True, exist_ok=True)
    (user_data / 'saves').mkdir(parents=True, exist_ok=True)
    (user_data / 'settings').mkdir(parents=True, exist_ok=True)
    return user_data


class CameraEffectsHandler:
    """Handles camera effects triggered by game events"""

    def __init__(self, camera: CameraSystem, event_bus: EventBus, player_id: int):
        self.camera = camera
        self.event_bus = event_bus
        self.player_id = player_id

        # Track previous state to detect transitions
        self.was_on_ground = False
        self.was_on_wall = False

        # Subscribe to events
        event_bus.subscribe(CollisionEvent, self._on_collision)
        event_bus.subscribe(VelocityChangeEvent, self._on_velocity_change)

    def _on_collision(self, event: CollisionEvent):
        """Handle collision events for camera effects"""
        if event.entity_id != self.player_id:
            return

        # Screen shake on ground landing (only if falling)
        if event.collision_type == 'ground' and not self.was_on_ground:
            # Shake intensity based on impact (placeholder - could use fall speed)
            self.camera.add_screen_shake(intensity=3.0, duration=0.1)
            self.was_on_ground = True
        elif event.collision_type != 'ground':
            self.was_on_ground = False

    def _on_velocity_change(self, event: VelocityChangeEvent):
        """Handle velocity changes for camera effects"""
        if event.entity_id != self.player_id:
            return

        # Camera pan on wall jump (push camera away from wall)
        if event.reason == 'wall_jump':
            # Determine wall direction from velocity change
            if event.new_vx > 0:  # Jumping right
                self.camera.add_camera_pan(offset_x=30, offset_y=0)
            elif event.new_vx < 0:  # Jumping left
                self.camera.add_camera_pan(offset_x=-30, offset_y=0)


def get_player_render_state(player):
    """Derive a simple render state string for animation selection."""
    physics = player.state.physics
    state = player.state
    # Highest priority: death/hurt placeholders based on health
    if state.health_state.current_hp <= 0:
        return "death"
    if state.health_state.invincibility_frames > 0:
        return "hurt"
    if state.is_teleporting_phase or state.is_teleporting_invuln:
        return "teleport"
    if state.ninjutsu_casting:
        return "ninjutsu_summon"
    if state.ninjutsu_active:
        return "ninjutsu_hand"
    if state.is_throwing:
        if not physics.on_ground:
            return "throw_air"
        if state.crouching:
            return "throw_crouch"
        return "throw_ground"
    if state.is_air_attacking or (not physics.on_ground and getattr(state, "attack_stage", 0) > 0):
        return "slash_air"
    if state.attack_stage == 1:
        return "slash1"
    if state.attack_stage == 2:
        return "slash2"
    if state.attack_stage >= 3:
        return "slash3"
    if state.is_dashing:
        return "dash"
    if state.is_wall_hanging:
        return "wall_hang"
    if state.is_ceiling_hanging:
        return "ceiling_hang"
    if not physics.on_ground:
        if physics.on_wall:
            return "wall_slide"
        # Air spin if mid-air and jumps_left < max_jumps
        if state.jumps_left < state.max_jumps:
            return "air_spin"
        # Simple sign-based air anim
        if physics.vy < 0:
            return "jump"
        return "fall"
    if state.crouching:
        return "crouch"
    if getattr(state, "is_running", False) and abs(physics.vx) > 0.5:
        return "run"
    if abs(physics.vx) > 0.1:
        return "slow_walk"
    return "idle"


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
    """Create a procedurally generated level with megamap support"""
    import time
    start_time = time.time()

    if seed is None:
        seed = random.randint(1, 999999)

    # Convert shape string to WorldShape enum
    from systems.world_generation import WorldShape
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
    """Build a location_id -> position mapping for reach objectives."""
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
    """Collect valid pickup positions for objective items."""
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
    """Spawn collectibles for collect-item objectives so missions are completable."""
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
    if not positions:
        print("[WORLD REGEN] Warning: no valid positions for objective pickups")
        return 0

    objective_seed = SeedDerivation.derive_seed(seed, "objective_pickups")
    rng = random.Random(objective_seed)
    rng.shuffle(positions)

    placed = 0
    for item_id, count in objective_items:
        for _ in range(count):
            if placed >= len(positions):
                print("[WORLD REGEN] Warning: not enough positions for all objective pickups")
                return placed
            x, y = positions[placed]
            placed += 1
            pickup = pickup_manager.spawn_collectible(x, y)
            pickup.item_id = item_id

    if placed < total_needed:
        print(f"[WORLD REGEN] Warning: spawned {placed}/{total_needed} objective pickups")

    return placed


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

    def snap_to_ground(entities, tiles):
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

    def find_portal_floor(x: float, y: float, tiles_list: list,
                          portal_width: int, portal_height: int,
                          max_drop: int = ROOM_HEIGHT_TILES * TILE_SIZE) -> float:
        center_x = x + portal_width / 2
        nearest_top = None
        for tile in tiles_list:
            if tile.left <= center_x <= tile.right and y <= tile.top <= y + max_drop:
                if nearest_top is None or tile.top < nearest_top:
                    nearest_top = tile.top
        if nearest_top is None:
            return None
        return nearest_top - portal_height

    def find_clear_portal_position(base_x: float, base_y: float, tiles_list: list,
                                   portal_width: int, portal_height: int) -> Tuple[float, float]:
        step = TILE_SIZE
        max_radius = 8
        for radius in range(max_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    candidate_x = base_x + dx * step
                    candidate_y = base_y + dy * step
                    floor_y = find_portal_floor(
                        candidate_x, candidate_y, tiles_list, portal_width, portal_height
                    )
                    if floor_y is None:
                        continue
                    portal_rect = pygame.Rect(int(candidate_x), int(floor_y), portal_width, portal_height)
                    if any(portal_rect.colliderect(tile) for tile in tiles_list):
                        continue
                    return candidate_x, floor_y
        return base_x, base_y

    def spawn_portal_safe(portal_id: str, destination_id: str,
                          world_x: float, world_y: float,
                          bidirectional: bool = True):
        portal_width = 64
        portal_height = 64
        base_x = world_x - portal_width / 2
        base_y = world_y - portal_height / 2
        safe_x, safe_y = find_clear_portal_position(base_x, base_y, tiles, portal_width, portal_height)
        portal_manager.spawn_portal(
            portal_id=portal_id,
            portal_type=PortalType.HUB,
            destination_id=destination_id,
            x=safe_x,
            y=safe_y,
            bidirectional=bidirectional
        )

    # Reset level manager (create new state)
    from game.level_manager import LevelState
    level_manager.state = LevelState()
    level_manager.level_start_time = 0.0

    # Clear NPCs (for hub world regeneration)
    npc_manager.clear_npcs()

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

    tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap = create_procedural_level(
        seed, shape, rooms
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
    minimap = MinimapRenderer(MinimapConfig(
        position=(20, 500),
        show_connections=True,
        show_player=True,
        highlight_current=True,
        scale=16 if rooms <= 10 else 12
    ))

    # ============================================================
    # Step 6: Spawn pickups and hazards
    # ============================================================
    print("[WORLD REGEN] Spawning pickups and hazards...")
    pickup_spawner = PickupSpawner(seed)
    hazard_spawner = HazardSpawner(seed)

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        room_spawn_pos = (spawn_x, spawn_y) if room.room_type.value == "start" else None
        room_exit_pos = (exit_x, exit_y) if room.room_type.value == "exit" else None

        pickup_spawner.spawn_pickups_for_room(room, pickup_manager, room_px, room_py)
        if not hub_id:  # Keep hubs safe and avoid exit-based hazard offsets
            hazard_spawner.spawn_hazards_for_room(
                room, hazard_manager, room_px, room_py,
                spawn_pos=room_spawn_pos, exit_pos=room_exit_pos
            )

    objective_pickups = 0
    if mission_def and not hub_id:
        objective_pickups = spawn_objective_collectibles(
            world, megamap, pickup_manager, mission_def, seed
        )

    print(f"[WORLD REGEN] Spawned: {len([p for p in pickup_manager.pickups if p.pickup_type == 'coin'])} coins, " +
          f"{pickup_manager.total_collectibles} collectibles, " +
          f"{hazard_manager.total_spikes} spikes, {hazard_manager.total_poison} poison zones")
    if objective_pickups:
        print(f"[WORLD REGEN] Objective pickups: {objective_pickups}")

    # ============================================================
    # Step 7: Spawn enemies
    # ============================================================
    print("[WORLD REGEN] Spawning enemies...")
    from entities.enemy import EnemyType
    from entities.enemy_manager import EnemySpawnAnchor

    enemy_spawn_rng = random.Random(seed)

    if hub_id:
        print("[WORLD REGEN] Hub world detected - skipping enemy spawns for safety")
    else:
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
                                world_x = room_px + tx * TILE_SIZE + TILE_SIZE / 2 - definition.width / 2
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
                    spawn_seed=enemy_spawn_rng.randint(0, 999999)
                )
                enemy_manager.register_spawn_anchor(anchor)

    enemy_manager.spawn_all_enemies()
    print(f"[WORLD REGEN] Spawned: {len(enemy_manager.enemies)} enemies")
    snap_to_ground(enemy_manager.enemies.values(), tiles)

    # ============================================================
    # Step 7.5: Spawn NPCs (for hub worlds)
    # ============================================================
    print("[WORLD REGEN] Spawning NPCs...")

    if hub_manager and hub_id and megamap:
        npc_positions = hub_manager.get_npc_positions(hub_id, megamap.room_positions, base_room_coords)
        for anchor, world_x, world_y in npc_positions:
            npc_manager.spawn_npc(anchor.npc_id, world_x, world_y)
        if npc_positions:
            print(f"[WORLD REGEN] Spawned NPCs from hub anchors: {len(npc_positions)}")
        else:
            # Fallback: drop core NPCs near spawn if anchors missing
            fallback_offset = 150
            if hub_id == "central_hub":
                npc_manager.spawn_npc("tutorial_elder", spawn_x + fallback_offset, spawn_y)
                npc_manager.spawn_npc("forest_ranger", spawn_x - fallback_offset, spawn_y)  # mission giver fallback
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
    snap_to_ground(npc_manager.npcs, tiles)

    # ============================================================
    # Step 7.6: Spawn portals (for hubs)
    # ============================================================
    if portal_manager and hub_manager and hub_id and megamap:
        portal_positions = hub_manager.get_portal_positions(hub_id, megamap.room_positions, base_room_coords)
        for anchor, world_x, world_y in portal_positions:
            spawn_portal_safe(
                portal_id=anchor.portal_id,
                destination_id=anchor.destination_hub_id,
                world_x=world_x,
                world_y=world_y,
                bidirectional=anchor.bidirectional
            )
        if portal_positions:
            print(f"[WORLD REGEN] Spawned {len(portal_positions)} portals for hub '{hub_id}'")
        else:
            # Fallback portals near spawn
            fallback_y = spawn_y
            if hub_id == "central_hub":
                spawn_portal_safe("portal_to_forest", "forest_hub", spawn_x, fallback_y - 240, bidirectional=True)
                spawn_portal_safe("portal_to_town", "town_hub", spawn_x + 300, fallback_y, bidirectional=True)
                spawn_portal_safe("portal_to_caves", "caves_hub", spawn_x, fallback_y + 240, bidirectional=True)
                spawn_portal_safe("portal_to_castle", "castle_hub", spawn_x + 300, fallback_y - 200, bidirectional=True)
                spawn_portal_safe("portal_to_sewer", "sewer_hub", spawn_x - 300, fallback_y + 200, bidirectional=True)
                spawn_portal_safe("portal_to_arcade", "arcade_loop", spawn_x - 300, fallback_y, bidirectional=True)
            else:
                spawn_portal_safe(f"portal_to_central_from_{hub_id}", "central_hub", spawn_x + 300, fallback_y, bidirectional=True)
            print(f"[WORLD REGEN] Spawned fallback portals for hub '{hub_id}'")

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

    import time
    level_manager.start_level(time.time())

    print(f"[WORLD REGEN] World regeneration complete!\n")

    return tiles, platforms, seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap


def main():
    """Main game loop"""
    # Ensure user_data directories exist
    user_data_dir = ensure_user_data_dirs()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Vain Asher Gaming's: Indie Ninja Adventures Demo")

    # Build mode selection (for distribution builds)
    parser.add_argument("--build-mode", type=str, default=None,
                       choices=["production", "testing", "dev"],
                       help="Build configuration mode (set by launcher scripts)")

    # Game mode selection (NEW in v0.6.0)
    parser.add_argument("--mode", type=str, default="arcade",
                       choices=["arcade", "campaign", "playtest"],
                       help="Game mode: arcade (infinite procedural), campaign (mission-based), playtest (single mission)")
    parser.add_argument("--mission", type=str, help="Mission ID for campaign/playtest mode (e.g., forest_1)")

    # Procedural generation options (kept for compatibility but ignored)
    parser.add_argument("--procedural", action="store_true", help="(ignored) Procedural is always enabled")
    parser.add_argument("--seed", type=int, default=None, help="Seed for procedural generation")
    parser.add_argument("--shape", type=str, default="blob",
                       choices=["snake", "branchy", "blob", "spiral", "tree", "grid"],
                       help="World shape style (ignored; hubs choose their own)")
    parser.add_argument("--rooms", type=int, default=10, help="Number of rooms to generate (ignored; hubs choose their own)")

    # Technical options
    parser.add_argument("--headless", action="store_true", help="Run without opening a window (SDL dummy driver)")
    parser.add_argument("--record", type=str, help="Record input to replay JSON file (saves to user_data/replays/)")
    parser.add_argument("--replay", type=str, help="Replay input from JSON file (looks in user_data/replays/)")
    parser.add_argument("--show-replay", action="store_true", help="Replay with window instead of headless")
    parser.add_argument("--log-input", nargs="?", const="input_commands.log",
                       help="Log per-frame input commands to JSONL (default: user_data/logs/input_commands.log)")
    args = parser.parse_args()

    if args.record and args.replay:
        print("Cannot use --record and --replay at the same time.")
        sys.exit(1)

    use_procedural = True  # Always procedural (no static demo room)
    current_seed = args.seed
    world_shape = "blob"
    num_rooms = 8
    headless = args.headless
    show_replay = args.show_replay

    # Always drive startup via menu → hub generation; skip static demo path
    menu_driven_startup = False

    # ============================================================
    # Play Mode Manager Setup (v0.6.0)
    # ============================================================
    play_mode_manager = PlayModeManager()
    mission_definition = None
    current_play_mode = PlayMode.ARCADE  # Default
    objective_hud_renderer = None  # Only used in campaign/playtest modes
    objective_tracker = None  # Only used in campaign/playtest modes

    # Force campaign hub start as default
    current_play_mode = PlayMode.CAMPAIGN
    print("[INFO] Starting CAMPAIGN mode (default hub flow)")
    mission_definition = None

    # Handle record/replay paths - use user_data/replays directory
    record_path = None
    replay_path = None
    log_input_path = None
    log_commands = False

    # Auto-record for TESTING build
    from config.build_config import get_build_config
    # Pass build mode from command line if provided
    if args.build_mode:
        os.environ['BUILD_MODE'] = args.build_mode.upper()
    build_config = get_build_config()

    if build_config.auto_record and not args.replay and not args.record:
        auto_filename = build_config.get_auto_record_filename()
        if auto_filename:
            args.record = auto_filename
            print(f"[TESTING BUILD] Auto-recording session to: {auto_filename}")

    if args.record:
        # If just a filename, save to user_data/replays/
        record_file = args.record if args.record.endswith('.json') else f"{args.record}.json"
        if not os.path.isabs(record_file):
            record_path = str(user_data_dir / 'replays' / record_file)
        else:
            record_path = record_file
        log_commands = True  # auto-log when recording
        # Default log filename for recordings
        if not log_input_path:
            log_input_path = str(user_data_dir / 'logs' / 'input_commands.record.log')

    replay_world_seed = None
    replay_hub_id = None
    replay_world_context = None
    replay_mission_id = None

    if args.replay:
        # If just a filename, look in user_data/replays/
        replay_file = args.replay if args.replay.endswith('.json') else f"{args.replay}.json"
        if not os.path.isabs(replay_file):
            replay_path = str(user_data_dir / 'replays' / replay_file)
        else:
            replay_path = replay_file
        # If logging enabled later, prefer a replay-specific default name
        if not log_input_path and args.log_input is None:
            log_input_path = str(user_data_dir / 'logs' / 'input_commands.replay.log')
        log_commands = True  # capture replay commands for debugging by default

    if args.log_input:
        log_commands = True
        log_file = args.log_input
        if not os.path.isabs(log_file):
            log_input_path = str(user_data_dir / 'logs' / log_file)
        else:
            log_input_path = log_file

    frame_idx = 0

    if replay_path:
        with open(replay_path, "r", encoding="utf-8") as f:
            replay_data = json.load(f)
        use_procedural = replay_data.get("procedural", use_procedural)
        # Prefer explicit world_seed/current_seed metadata for deterministic replays
        replay_world_seed = replay_data.get("world_seed", replay_data.get("seed"))
        replay_hub_id = replay_data.get("hub_id")
        replay_world_context = replay_data.get("world_context")
        replay_mission_id = replay_data.get("mission_id")
        if replay_world_seed is not None:
            current_seed = replay_world_seed
        else:
            current_seed = replay_data.get("seed", current_seed)
        if not show_replay:
            headless = True  # default to headless during playback unless overridden

        print(f"[REPLAY] Loaded commands from {replay_path}")

    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    print("\n" + "="*60)
    print("Vain Asher Gaming's: Indie Ninja Adventures - Modular Architecture Demo")
    print("="*60)
    print(f"\nMode: {'PROCEDURAL' if use_procedural else 'STATIC'}")
    if use_procedural and current_seed:
        print(f"Seed: {current_seed}")
    if record_path:
        print(f"Recording input to: {record_path}")
        if log_commands and log_input_path:
            print(f"Logging input commands to: {log_input_path}")
        if replay_path:
            print(f"Replaying input from: {replay_path}")
        if log_commands and log_input_path:
            print(f"Logging replay commands to: {log_input_path}")
    print("\nControls:")
    print("  Move: Arrow keys / WASD")
    print("  Jump: Space / W / Up")
    print("  Dash: Shift")
    print("  Walk: default | Run: Alt")
    print("  Crouch: S / Down (hold)")
    print("  C: Cycle camera mode (world/room/free)")
    print("  Arrow keys in free cam: Move camera")
    print("  H: Toggle controls overlay")
    print("  Quit: ESC")
    print("\nAll mechanics active:")
    print("  - Ground/air movement")
    print("  - Jump (ground, double, wall, coyote)")
    print("  - Dash with cooldown")
    print("  - Wall slide with stamina")
    print("  - Crouch (stealth movement)")
    if use_procedural:
        print("  - Procedural world generation")
    print("="*60)

    # Initialize pygame
    pygame.init()

    if headless:
        window_width, window_height = GAME_WIDTH, GAME_HEIGHT
        screen = pygame.Surface((window_width, window_height))
        clock_pygame = pygame.time.Clock()
    else:
        # Get recommended window size
        window_width, window_height = get_recommended_window_size()
        screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Vain Asher Gaming's: Indie Ninja Adventures - Responsive Demo")
        clock_pygame = pygame.time.Clock()
    sprite_manager = SpriteManager()  # Loads from assets/sprites/player/
    tile_loader = TileLoader()  # Loads and scales tiles from assets/biomes/
    particles = ParticleSystem()
    hud = HUDRenderer()
    inventory_ui = InventoryUI()
    npc_prompt_renderer = NPCPromptRenderer()  # Renders "Press E to talk" prompts
    npc_indicator_renderer = NPCIndicatorRenderer()  # Renders NPC indicators (!, $, ?)

    # Initialize core systems
    bus = EventBus()
    logger = GameLogger()
    game_clock = GameClock(bus, logger=logger.get_logger("clock"))
    entity_manager = EntityManager(bus, logger.get_logger("entity_manager"))

    # Initialize save system early (needed for campaign data/inventory)
    save_manager = SaveManager()
    save_manager.load()  # Load existing save or create new

    # Initialize pickup manager
    pickup_manager = PickupManager(bus)

    # Initialize hazard manager
    hazard_manager = HazardManager(bus)

    # Initialize NPC manager (v0.6.0 - Phase 2)
    npc_manager = NPCManager(bus)

    # Initialize dialogue system (v0.6.0 - Phase 2)
    dialogue_manager = DialogueManager(bus)
    dialogue_manager.load_dialogues("data/dialogues.json")
    dialogue_ui = DialogueUI(GAME_WIDTH, GAME_HEIGHT)

    # Initialize developer tools (DEV build only)
    dev_console = None
    hot_reload = None

    if build_config.enable_dev_console:
        from dev_tools import DevConsole
        dev_console = DevConsole(enabled=True)
        dev_console.initialize_font()
        print("[DEV BUILD] Developer console enabled (press ` to toggle)")

    if build_config.enable_hot_reload:
        from dev_tools import HotReloadWatcher
        hot_reload = HotReloadWatcher()
        # Note: We'll watch settings.json if it exists, but this game doesn't currently use GameSettings
        # You can add watches for other config files here
        print("[DEV BUILD] Hot reload enabled")

    # Initialize mission menu UI (Phase 2 integration)
    mission_menu_ui = MissionMenuUI()
    active_mission_pool: list[str] = []

    # Initialize shop UI and trading (Phase 2 integration)
    shop_ui = ShopUI()
    trading_manager = TradingManager(bus, current_seed if current_seed else 0)
    active_shop_npc_id = None

    # Initialize inventory system for player (for shops)
    initialize_item_manager()
    item_manager = get_item_manager()
    try:
        with open("data/items.json", "r", encoding="utf-8") as f:
            items_data = json.load(f)
            item_manager.load_from_dict(items_data)
    except FileNotFoundError:
        print("[WARNING] items.json not found; shop items will be empty")

    campaign_data = save_manager.data.campaign if save_manager and save_manager.data else None
    if campaign_data and campaign_data.player_inventory:
        player_inventory = Inventory.from_dict(campaign_data.player_inventory, max_slots=20)
    else:
        player_inventory = Inventory(max_slots=20)
    player_inventory.set_item_database(item_manager)
    if campaign_data:
        player_inventory.currency = campaign_data.currency
        player_inventory.equipped_weapon = campaign_data.equipped_weapon
        player_inventory.equipped_armor = campaign_data.equipped_armor

    def apply_shuriken_capacity_bonus():
        """Set shuriken max based on equipped armor."""
        base = 10
        armor_bonus = 0
        armor_id = getattr(player_inventory, "equipped_armor", None)
        if armor_id and item_manager:
            itm = item_manager.get_item(armor_id)
            if itm:
                bonus_map = {
                    "armor_cloth": 0,
                    "armor_leather": 2,
                    "armor_chain_mail": 4,
                    "armor_bark_plate": 4,
                    "armor_crystal_plate": 6,
                    "armor_dark_plate": 8,
                    "armor_legendary_set": 12,
                }
                armor_bonus = bonus_map.get(armor_id, 0)
        player.state.shuriken_max = base + armor_bonus
        player.state.shuriken_ammo = min(player.state.shuriken_ammo, player.state.shuriken_max)

    # Hub/portal systems
    # Normalize campaign world seed (treat 0 as unset)
    if campaign_data and getattr(campaign_data, "world_seed", 0) == 0:
        campaign_data.world_seed = current_seed if current_seed is not None else random.randint(1, 999999)
        save_manager.mark_dirty()

    if replay_world_seed is not None:
        base_hub_seed = replay_world_seed
    else:
        base_hub_seed = (
            campaign_data.world_seed
            if campaign_data and getattr(campaign_data, "world_seed", 0) != 0
            else (current_seed if current_seed is not None else random.randint(1, 999999))
        )
    hub_manager = HubManager(base_hub_seed)
    portal_manager = PortalManager(bus)
    current_hub_id = replay_hub_id or (campaign_data.current_hub_id if campaign_data and campaign_data.current_hub_id else "central_hub")
    current_world_context = replay_world_context or "hub"  # hub | mission | arcade
    show_minimap = True
    show_full_map = False
    show_debug_overlay = build_config.debug_overlay_default
    arcade_depth = 0
    arcade_rooms = 8

    def persist_player_inventory():
        """Persist current inventory/currency into campaign save data."""
        if save_manager and save_manager.data and save_manager.data.campaign:
            inv_dict = {}
            for slot in player_inventory.slots:
                if slot:
                    inv_dict[slot.item_id] = inv_dict.get(slot.item_id, 0) + slot.quantity
            save_manager.save_inventory(
                inv_dict,
                player_inventory.equipped_weapon,
                player_inventory.equipped_armor,
                player_inventory.currency
            )

    def persist_story_state():
        """Persist current story state into campaign save data (v0.7.0)."""
        if save_manager and save_manager.data and save_manager.data.campaign:
            save_manager.data.campaign.story_state = story_manager.to_dict()
            save_manager.mark_dirty()

    # Objective tracking (create up-front for mission flows)
    objective_tracker = ObjectiveTracker(bus)
    objective_hud_renderer = ObjectiveHUDRenderer()

    # Track last key states for dialogue input (to detect key press, not hold)
    prev_key_state = {k: False for k in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                                         pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
                                         pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT,
                                         pygame.K_p, pygame.K_c, pygame.K_ESCAPE, pygame.K_e,
                                         pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_j, pygame.K_k, pygame.K_f,
                                         pygame.K_l, pygame.K_q, pygame.K_TAB, pygame.K_m,
                                         pygame.K_r, pygame.K_i, pygame.K_F3, pygame.K_h,
                                         pygame.K_LALT, pygame.K_RALT]}

    # Event handler for dialogue start
    def on_dialogue_start(event: DialogueStartEvent):
        """Handle dialogue start event from NPC interaction"""
        if dialogue_manager.start_dialogue(event.dialogue_id):
            dialogue_ui.reset_selection()
            game_state_manager.transition_to(GameState.DIALOGUE)
            print(f"[DIALOGUE] Started dialogue: {event.dialogue_id}")
        else:
            print(f"[WARNING] Failed to start dialogue: {event.dialogue_id}")

    # Subscribe to dialogue events
    bus.subscribe(DialogueStartEvent, on_dialogue_start)

    # Initialize game state manager
    game_state_manager = GameStateManager(initial_state=GameState.PLAYING)

    # Initialize story system (v0.7.0 - The Hollowed Ninja)
    # Load story state from save (if exists)
    if save_manager and save_manager.data and save_manager.data.campaign and save_manager.data.campaign.story_state:
        story_manager = StoryManager.from_dict(save_manager.data.campaign.story_state)
        print(f"[STORY] Loaded story state: Act {story_manager.current_act}")
    else:
        story_manager = StoryManager()
        print("[STORY] No saved story state, starting fresh")

    story_manager.event_bus = bus  # Connect to event bus
    companion_orbs = CompanionOrbs()
    hub_effects = HubEffectsRenderer()
    ending_manager = story_manager.ending_manager  # Get ending manager reference

    print("[STORY] Story systems initialized")

    # Mission menu open handler
    def on_mission_menu_open(event: MissionMenuOpenEvent):
        """Open mission menu from NPC interaction"""
        nonlocal active_mission_pool
        registry = get_mission_registry()
        campaign = save_manager.data.campaign if save_manager and save_manager.data else None
        # Always include baseline movement abilities so early missions show up
        default_abilities = {"basic_movement", "jump"}
        unlocked = set(campaign.unlocked_abilities) if campaign else set()
        unlocked |= default_abilities
        completed = set(campaign.completed_missions) if campaign else set()
        best_times = campaign.mission_best_times if campaign else {}

        missions_to_show = []
        for mission_id in event.mission_pool:
            mission_def = registry.get_mission(mission_id)
            if not mission_def:
                continue

            # Determine status
            has_abilities = all(req in unlocked for req in mission_def.required_abilities)
            has_prereqs = all(req in completed for req in mission_def.unlock_requirements)

            if mission_id in completed:
                status = MissionStatus.COMPLETED
            elif not has_abilities or not has_prereqs:
                status = MissionStatus.LOCKED
            else:
                status = MissionStatus.AVAILABLE

            objectives = [obj.description for obj in mission_def.objectives]
            requirements = mission_def.required_abilities + mission_def.unlock_requirements
            rewards = []
            if mission_def.rewards.currency:
                rewards.append(f"{mission_def.rewards.currency} Gold")
            for reward_item in mission_def.rewards.items:
                rewards.append(reward_item.get("item_id", "Item"))

            missions_to_show.append(MissionDisplay(
                mission_id=mission_def.mission_id,
                mission_name=mission_def.mission_name,
                region=mission_def.region,
                status=status,
                difficulty=mission_def.difficulty,
                objectives=objectives,
                requirements=requirements,
                rewards=rewards,
                best_time=best_times.get(mission_def.mission_id)
            ))

        if missions_to_show:
            active_mission_pool = list(event.mission_pool)
            mission_menu_ui.show(missions_to_show)
            game_state_manager.transition_to(GameState.MISSION_MENU)
            print(f"[MISSION MENU] Opened with {len(missions_to_show)} missions")
        else:
            print("[MISSION MENU] No missions available for this NPC")

    bus.subscribe(MissionMenuOpenEvent, on_mission_menu_open)

    # Shop open handler
    def on_shop_open(event: NPCShopOpenEvent):
        """Open shop UI for NPC"""
        nonlocal active_shop_npc_id
        npc_def = npc_manager.get_npc_definition(event.npc_id)
        npc_name = npc_def.display_name if npc_def else event.npc_id

        # Ensure shop tier is valid
        try:
            tier = ShopTier(event.shop_tier)
        except Exception:
            tier = ShopTier.TIER_1

        # Keep trading seed aligned with current world seed
        if current_seed is not None:
            trading_manager.world_seed = current_seed

        shop_inventory = trading_manager.get_shop(event.npc_id)
        if shop_inventory is None:
            shop_inventory = trading_manager.create_shop(event.npc_id, tier)

        shop_ui.open(npc_name)
        active_shop_npc_id = event.npc_id
        game_state_manager.transition_to(GameState.SHOP)
        print(f"[SHOP] Opened shop for {npc_name} (tier {tier.value})")

    bus.subscribe(NPCShopOpenEvent, on_shop_open)

    def process_shop_action(action: str, index: int):
        """Handle shop actions from input (event or replay)."""
        nonlocal active_shop_npc_id
        if action == "close":
            shop_ui.close()
            active_shop_npc_id = None
            game_state_manager.transition_to(GameState.PLAYING)
            return

        if action == "buy":
            if active_shop_npc_id is None:
                return
            shop_inventory = trading_manager.get_shop(active_shop_npc_id)
            if shop_inventory and 0 <= index < len(shop_inventory.items):
                item_id = shop_inventory.items[index].item_id
                if trading_manager.buy_item(active_shop_npc_id, item_id, 1, player_inventory):
                    print(f"[SHOP] Purchased {item_id}")
                    if campaign_data:
                        campaign_data.currency = player_inventory.currency
                    persist_player_inventory()
                else:
                    print(f"[SHOP] Could not purchase {item_id}")
            return

        if action == "sell":
            player_items_flat = [slot for slot in player_inventory.slots if slot is not None]
            if 0 <= index < len(player_items_flat):
                item_id = player_items_flat[index].item_id
                if trading_manager.sell_item(active_shop_npc_id, item_id, 1, player_inventory):
                    print(f"[SHOP] Sold {item_id}")
                    if campaign_data:
                        campaign_data.currency = player_inventory.currency
                    persist_player_inventory()
                else:
                    print(f"[SHOP] Could not sell {item_id}")
            return

    # Portal travel handler
    def on_portal_travel(event: PortalTravelEvent):
        """Handle portal travel between hubs"""
        nonlocal current_hub_id, current_seed, tiles, platforms, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap, current_world_context
        dest_hub = event.destination_id
        if dest_hub == "arcade_loop":
            # Enter endless arcade loop from hub
            nonlocal arcade_depth, arcade_rooms
            arcade_depth = 0
            arcade_rooms = 8
            current_world_context = "arcade"
            current_play_mode = PlayMode.ARCADE
            arcade_seed = get_arcade_seed(arcade_depth)
            tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                seed=arcade_seed,
                shape="snake",
                rooms=arcade_rooms,
                hub_id=None,
                hub_manager=hub_manager,
                portal_manager=portal_manager,
                collision_system=collision_system,
                camera=camera,
                player=player,
                enemy_manager=enemy_manager,
                pickup_manager=pickup_manager,
                hazard_manager=hazard_manager,
                level_manager=level_manager,
                npc_manager=npc_manager,
                bus=bus,
                GAME_WIDTH=GAME_WIDTH,
                GAME_HEIGHT=GAME_HEIGHT
            )
            game_state_manager.transition_to(GameState.PLAYING)
            update_replay_metadata()
            print("[ARCADE] Entered arcade loop from hub")
            return

        hub_def = hub_manager.get_hub_definition(dest_hub)
        shape_str = "blob"
        rooms_count = hub_def.room_count if hub_def else 8
        if hub_def:
            shape_str = hub_def.world_shape.value if hasattr(hub_def.world_shape, "value") else str(hub_def.world_shape)

        current_hub_id = dest_hub
        tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
            seed=current_seed if current_seed is not None else hub_manager.world_seed,
            shape=shape_str,
            rooms=rooms_count,
            hub_id=current_hub_id,
            hub_manager=hub_manager,
            portal_manager=portal_manager,
            collision_system=collision_system,
            camera=camera,
            player=player,
            enemy_manager=enemy_manager,
            pickup_manager=pickup_manager,
            hazard_manager=hazard_manager,
            level_manager=level_manager,
            npc_manager=npc_manager,
            bus=bus,
            GAME_WIDTH=GAME_WIDTH,
            GAME_HEIGHT=GAME_HEIGHT
        )
        current_world_context = "hub"

        if campaign_data:
            campaign_data.current_hub_id = current_hub_id
            campaign_data.current_hub_position = (spawn_x, spawn_y)
            save_manager.mark_dirty()

        game_state_manager.transition_to(GameState.PLAYING)
        update_replay_metadata()
        print(f"[PORTAL] Traveled to {dest_hub}")

    bus.subscribe(PortalTravelEvent, on_portal_travel)

    # Initialize menu system (but start directly in campaign hub)
    menu_manager = MenuManager(GAME_WIDTH, GAME_HEIGHT)

    # Initialize tutorial system
    first_run = not save_manager.data.player_progress.tutorials_seen
    tutorial_manager = TutorialManager(GAME_WIDTH, GAME_HEIGHT, save_manager)
    controls_hint = ControlsHintOverlay(
        GAME_WIDTH,
        GAME_HEIGHT,
        start_visible=first_run,
        auto_fade=first_run
    )

    # Trigger welcome tutorial if first time
    if first_run:
        tutorial_manager.trigger_tutorial("welcome")

    # Initialize game systems
    physics_system = PhysicsSystem(bus, entity_manager, logger.get_logger("physics"))
    collision_system = CollisionSystem(bus, entity_manager, logger.get_logger("collision"))
    enemy_manager = EnemyManager(bus, current_seed if current_seed else base_hub_seed)

    # Initialize objective tracker for campaign/playtest modes (v0.6.0)
    if mission_definition:  # Only if in campaign or playtest mode
        objective_tracker.start_mission_objectives(args.mission)

    # Initialize camera system
    camera_config = CameraConfig(
        game_width=GAME_WIDTH,
        game_height=GAME_HEIGHT,
        follow_speed=0.1,
        deadzone_width=200,
        deadzone_height=150
    )
    camera = CameraSystem(camera_config)
    camera.handle_resize(window_width, window_height)

    # Create level containers
    world = None
    megamap = None
    minimap = None
    exit_x = None
    exit_y = None
    spawn_x = GAME_WIDTH / 2
    spawn_y = GAME_HEIGHT - 100

    # Player + level manager setup (player will be teleported after world regen)
    level_manager = LevelManager(bus)
    player = Player(
        player_id=0,
        spawn_x=spawn_x,
        spawn_y=spawn_y,
        event_bus=bus,
        logger_factory=logger,
        collision_system=collision_system,
        feature_flags={
            "double_jump": True,
            "wall_jump": True,
            "dash": True,
            "crouch": True,
            "shuriken": True,
            "teleport": True,
            "ninjutsu": True
        }
    )
    # Wire mechanic contexts
    player.shuriken.set_context(enemy_manager=enemy_manager)
    player.teleport.set_collision_system(collision_system)
    player.ninjutsu.set_hazard_manager(hazard_manager)
    apply_shuriken_capacity_bonus()

    # Add player entity to entity manager so PhysicsSystem can process it
    player_entity = entity_manager.create_entity(
        entity_type=EntityType.PLAYER,
        physics=player.state.physics
    )

    # Combat handling (dash/jump attacks and contact damage)
    combat_mechanic = CombatMechanic(player_entity.entity_id, bus, logger.get_logger("combat"))
    attack_cooldown = 0.35  # seconds between sword swings
    attack_timer = 0.0
    attack_fx_timer = 0.0
    attack_fx_rect = None

    # Create camera effects handler
    camera_effects = CameraEffectsHandler(camera, bus, player_entity.entity_id)

    # Initial hub generation (central hub by default)
    initial_hub_def = hub_manager.get_hub_definition(current_hub_id)
    initial_rooms = initial_hub_def.room_count if initial_hub_def else num_rooms
    initial_shape = initial_hub_def.world_shape.value if initial_hub_def and hasattr(initial_hub_def.world_shape, "value") else world_shape
    initial_seed = current_seed if current_seed is not None else base_hub_seed
    current_seed = initial_seed

    tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
        seed=initial_seed,
        shape=initial_shape,
        rooms=initial_rooms,
        hub_id=current_hub_id,
        hub_manager=hub_manager,
        portal_manager=portal_manager,
        collision_system=collision_system,
        camera=camera,
        player=player,
        enemy_manager=enemy_manager,
        pickup_manager=pickup_manager,
        hazard_manager=hazard_manager,
        level_manager=level_manager,
        npc_manager=npc_manager,
        bus=bus,
        GAME_WIDTH=GAME_WIDTH,
        GAME_HEIGHT=GAME_HEIGHT
    )
    current_world_context = "hub"

    # Create victory screen
    victory_screen = VictoryScreen(GAME_WIDTH, GAME_HEIGHT)

    # Game state
    level_complete = False

    def regenerate_hub_for_respawn(reason: str = "", target_hub_id=None):
        """
        Return player to current hub (used for deaths/mission completion).
        """
        nonlocal tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap, current_world_context, level_complete, current_hub_id
        # Stop any active mission objectives when returning to a hub
        if objective_tracker:
            objective_tracker.stop_mission_objectives()
        target_hub = target_hub_id or current_hub_id
        hub_def = hub_manager.get_hub_definition(target_hub)
        hub_rooms = hub_def.room_count if hub_def else num_rooms
        hub_shape = hub_def.world_shape.value if hub_def and hasattr(hub_def.world_shape, "value") else world_shape
        tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
            seed=current_seed if current_seed is not None else hub_manager.world_seed,
            shape=hub_shape,
            rooms=hub_rooms,
            hub_id=target_hub,
            hub_manager=hub_manager,
            portal_manager=portal_manager,
            collision_system=collision_system,
            camera=camera,
            player=player,
            enemy_manager=enemy_manager,
            pickup_manager=pickup_manager,
            hazard_manager=hazard_manager,
            level_manager=level_manager,
            npc_manager=npc_manager,
            bus=bus,
            GAME_WIDTH=GAME_WIDTH,
            GAME_HEIGHT=GAME_HEIGHT
        )
        current_world_context = "hub"
        level_complete = False
        current_hub_id = target_hub
        if campaign_data:
            campaign_data.current_hub_id = target_hub
            campaign_data.current_hub_position = (spawn_x, spawn_y)
            save_manager.mark_dirty()
        if reason:
            print(f"[RESPAWN] Returned to {target_hub} ({reason})")
        update_replay_metadata()

    print(f"\n[OK] All systems initialized")
    print(f"[OK] Player spawned at ({spawn_x}, {spawn_y})")
    if exit_x is not None and exit_y is not None:
        print(f"[OK] Exit positioned at ({exit_x:.0f}, {exit_y:.0f})")
    print(f"[OK] Level created ({len(tiles)} tiles)")
    print(f"\nStarting game loop...\n")

    running = True
    last_on_ground = player.state.physics.on_ground
    last_is_dashing = player.state.is_dashing

    KEYS_TO_TRACK = [
        pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
        pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT,
        pygame.K_p, pygame.K_c, pygame.K_ESCAPE, pygame.K_e,
        pygame.K_j,  # sword attack
        pygame.K_k,  # shuriken
        pygame.K_f,  # teleport
        pygame.K_l, pygame.K_q,  # ninjutsu stance
        pygame.K_TAB,  # minimap toggle
        pygame.K_m,  # full map
        pygame.K_h,  # controls hint toggle
        pygame.K_r,  # consumable
        pygame.K_i,  # inventory
        pygame.K_RETURN,  # dialogue advance/selection
        pygame.K_F3,  # debug overlay
        pygame.K_LALT, pygame.K_RALT,  # slow walk
    ]

    input_pipeline = InputPipeline(
        record_path=record_path,
        replay_path=replay_path,
        metadata={
            "procedural": use_procedural,
            "seed": current_seed,
        },
        log_commands=log_commands,
        log_path=log_input_path,
    )

    def get_arcade_seed(depth: int) -> int:
        """Derive deterministic arcade seed for a given depth."""
        base_seed = SeedDerivation.derive_region_seed(hub_manager.world_seed, "arcade_loop")
        return SeedDerivation.derive_seed(base_seed, f"depth:{depth}")

    def update_replay_metadata(mission_id: str | None = None):
        """Capture current context into replay metadata for determinism."""
        ctx = {
            "mode": current_play_mode.value if 'current_play_mode' in locals() and current_play_mode else None,
            "hub_id": current_hub_id,
            "world_context": current_world_context,
            "current_seed": current_seed,
            "world_seed": hub_manager.world_seed if 'hub_manager' in locals() and hub_manager else current_seed,
            "mission_id": mission_id,
        }
        input_pipeline.metadata.update(ctx)

    update_replay_metadata()

    # Start level timer
    import time
    level_manager.start_level(time.time())

    # If started with procedural/replay args, skip menu and start game directly
    if use_procedural or replay_path:
        game_state_manager.start_game()
        menu_manager.clear_menus()

    # Set dev console context with game objects (DEV build)
    if dev_console:
        dev_console.set_context(
            player=player,
            camera=camera,
            entities=entity_manager,
            physics=physics_system,
            collision=collision_system,
            game_state=game_state_manager,
            level_manager=level_manager,
            enemy_manager=enemy_manager,
            pickup_manager=pickup_manager,
            hazard_manager=hazard_manager,
            bus=bus,
        )
        print("[DEV BUILD] Console context initialized")

    while running:
        # Check for hot reload changes (DEV build)
        if hot_reload:
            hot_reload.check(time.time())
        keydown_keys = set()
        # Process pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Mark termination for deterministic replay if recording
                input_pipeline.metadata["terminated_frame"] = frame_idx
                running = False
                continue

            if not headless and event.type == pygame.VIDEORESIZE:
                # Handle window resize
                window_width, window_height = event.w, event.h
                screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
                camera.handle_resize(window_width, window_height)
                continue

            if event.type == pygame.KEYDOWN and not replay_path:
                keydown_keys.add(event.key)

                # Developer console handling (DEV build only)
                if dev_console and event.key == pygame.K_BACKQUOTE:
                    dev_console.toggle()
                    continue

                # If dev console is visible, let it handle all input
                if dev_console and dev_console.visible:
                    if dev_console.handle_keydown(event):
                        continue

            # Modal state handling (shop/mission menu/dialogue)
            if event.type == pygame.KEYDOWN and not replay_path:
                # Shop/mission menu input is handled via command pipeline for determinism.
                if game_state_manager.is_dialogue():
                    if event.key == pygame.K_ESCAPE:
                        dialogue_manager.end_dialogue()
                        game_state_manager.transition_to(GameState.PLAYING)
                    # Dialogue input handled separately via pressed-key detection
                    continue

            if event.type == pygame.KEYDOWN and not replay_path:
                if event.key == pygame.K_SPACE and level_complete and not replay_path:
                    # Advance after victory based on context
                    level_complete = False
                    level_manager.reset_level()
                    if current_world_context == "mission":
                        regenerate_hub_for_respawn("mission complete")
                    elif current_world_context == "arcade":
                        # Advance arcade loop with bigger room count
                        arcade_depth += 1
                        arcade_rooms = min(8 + arcade_depth * 2, 24)
                        arcade_seed = get_arcade_seed(arcade_depth)
                        tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                            seed=arcade_seed,
                            shape="snake",
                            rooms=arcade_rooms,
                            hub_id=None,
                            hub_manager=hub_manager,
                            portal_manager=portal_manager,
                            collision_system=collision_system,
                            camera=camera,
                            player=player,
                            enemy_manager=enemy_manager,
                            pickup_manager=pickup_manager,
                            hazard_manager=hazard_manager,
                            level_manager=level_manager,
                            npc_manager=npc_manager,
                            bus=bus,
                            GAME_WIDTH=GAME_WIDTH,
                            GAME_HEIGHT=GAME_HEIGHT
                        )
                        current_seed = arcade_seed
                        current_world_context = "arcade"
                        update_replay_metadata()
                        print(f"[ARCADE] Generated new level (depth {arcade_depth}, rooms {arcade_rooms}, seed {current_seed})")
                    else:
                        # Hub victory (should not normally trigger) just respawns player
                        player.damage.respawn(player.state, spawn_x, spawn_y)
                        player.state.health_state.current_hp = player.state.health_state.max_hp
                    continue

                elif event.key == pygame.K_c and not replay_path:
                    # Cycle camera mode (disabled during replay)
                    modes = [CameraMode.WORLD_CLAMP, CameraMode.ROOM_CLAMP, CameraMode.FREE]
                    current_idx = modes.index(camera.mode)
                    next_idx = (current_idx + 1) % len(modes)
                    camera.set_mode(modes[next_idx])
                    print(f"\n[CAMERA] Mode: {camera.mode.value}")
                elif event.key == pygame.K_i and game_state_manager.is_playing():
                    # Inventory debug dump
                    print("[INVENTORY] Currency:", player_inventory.currency)
                    if player_inventory.slots:
                        print("[INVENTORY] Items:")
                        for idx, slot in enumerate(player_inventory.slots):
                            if slot:
                                print(f"  Slot {idx}: {slot.item_id} x{slot.quantity}")
                    else:
                        print("[INVENTORY] No items")

        # Process input via command pipeline (live/replay/record)
        raw_keys = pygame.key.get_pressed()
        keys, current_command = input_pipeline.next(raw_keys, frame_idx, keydown_keys)

        # Track single-press keys for dialogue/menu interactions
        pressed_once = set(keydown_keys)
        for key_code in prev_key_state:
            if keys[key_code] and not prev_key_state[key_code]:
                pressed_once.add(key_code)
            prev_key_state[key_code] = bool(keys[key_code])
        if pygame.K_KP_ENTER in pressed_once:
            pressed_once.add(pygame.K_RETURN)

        # Pause toggle (consume ESC so menu doesn't immediately close)
        if pygame.K_ESCAPE in pressed_once:
            if game_state_manager.is_playing() and not menu_manager.has_menu():
                game_state_manager.pause()
                menu_manager.push_menu(PauseMenu(GAME_WIDTH, GAME_HEIGHT))
                pressed_once.discard(pygame.K_ESCAPE)
            elif game_state_manager.is_paused():
                game_state_manager.resume()
                menu_manager.pop_menu()
                pressed_once.discard(pygame.K_ESCAPE)

        pressed_once = list(pressed_once)

        # Sword swipe (command-driven for deterministic replay)
        if game_state_manager.is_playing() and pygame.K_j in pressed_once:
            if attack_timer <= 0.0 and player.state.stamina >= 2.0:
                sword_w = 48
                sword_h = 32
                px = player.state.physics.x
                py = player.state.physics.y
                pw = player.state.physics.width
                ph = player.state.physics.height
                facing = player.state.facing if player.state.facing != 0 else (1 if player.state.physics.vx >= 0 else -1)
                attack_x = px + pw if facing >= 0 else px - sword_w
                attack_y = py + ph / 2 - sword_h / 2
                hits = enemy_manager.check_attack_collision((attack_x, attack_y, sword_w, sword_h))
                for enemy_id in hits:
                    knock_x = 300.0 if facing >= 0 else -300.0
                    enemy_manager.damage_enemy(enemy_id, damage=2, knockback_x=knock_x, knockback_y=-120.0, stun_duration=0.35)
                attack_timer = attack_cooldown
                attack_fx_rect = pygame.Rect(attack_x, attack_y, sword_w, sword_h)
                attack_fx_timer = 0.12
                player.state.stamina = max(0.0, player.state.stamina - 2.0)
                # Track attack stage for animations
                player.state.attack_stage = (player.state.attack_stage % 3) + 1
                player.state.attack_timer = attack_cooldown

        # Stop replay cleanly when commands are exhausted/terminated
        if replay_path and input_pipeline.is_replay_exhausted(frame_idx):
            running = False
            continue

        # UI toggles (use pressed-once for determinism)
        if pygame.K_TAB in pressed_once:
            show_minimap = not show_minimap
        if pygame.K_m in pressed_once:
            show_full_map = not show_full_map
        if pygame.K_h in pressed_once:
            controls_hint.toggle()
        if pygame.K_F3 in pressed_once:
            show_debug_overlay = not show_debug_overlay
        if pygame.K_i in pressed_once:
            inventory_ui.toggle()
        if pygame.K_r in pressed_once and game_state_manager.is_playing():
            # Quick-use consumable (first health potion)
            used = False
            for slot in player_inventory.slots:
                if slot:
                    item_def = item_manager.get_item(slot.item_id) if item_manager else None
                    if item_def and item_def.consumable and item_def.health_restore > 0:
                        healed = player.state.health_state.heal(item_def.health_restore)
                        if healed > 0:
                            slot.quantity -= 1
                            if slot.quantity <= 0:
                                # Remove slot
                                slot_idx = player_inventory.slots.index(slot)
                                player_inventory.slots[slot_idx] = None
                            used = True
                            break
            if used:
                persist_player_inventory()

        # Handle menu input if menu is active
        selected_mode = None
        if menu_manager.has_menu():
            # Drive menus via unified command pipeline (replay-compatible)
            menu_action = menu_manager.handle_input(keys, pressed_once)

            if menu_action == MenuAction.START_GAME:
                # Show mode selection menu instead of starting directly
                mode_menu = GameModeSelectionMenu(GAME_WIDTH, GAME_HEIGHT)
                menu_manager.push_menu(mode_menu)
                print("[MENU] Showing game mode selection...")
            elif menu_action == MenuAction.RESUME_GAME:
                # Resume from pause
                game_state_manager.resume()
                menu_manager.pop_menu()
            elif menu_action == MenuAction.OPEN_SETTINGS:
                # Open settings menu
                menu_manager.push_menu(SettingsMenu(GAME_WIDTH, GAME_HEIGHT))
            elif menu_action == MenuAction.BACK:
                # Go back (close settings)
                menu_manager.pop_menu()
            elif menu_action == MenuAction.QUIT_TO_MENU:
                # Return to main menu
                game_state_manager.quit_to_menu()
                menu_manager.clear_menus()
                menu_manager.push_menu(MainMenu(GAME_WIDTH, GAME_HEIGHT))
                print("[MENU] Returned to main menu")
            elif menu_action == MenuAction.QUIT_GAME:
                # Quit game
                running = False

            # Handle mode selection from GameModeSelectionMenu
            current_menu = menu_manager.get_current_menu()
            if isinstance(current_menu, GameModeSelectionMenu):
                selected_mode = current_menu.get_selected_mode()
                if selected_mode == "campaign":
                    # Start campaign mode - spawn in hub world
                    print("[MODE] Starting Campaign Mode...")
                    menu_manager.clear_menus()
                    current_play_mode = PlayMode.CAMPAIGN

                    # Generate campaign seed if needed
                    campaign_seed = save_manager.data.campaign.world_seed
                    if campaign_seed == 0:
                        base_seed = hub_manager.world_seed if getattr(hub_manager, "world_seed", 0) != 0 else (current_seed if current_seed is not None else 1)
                        campaign_seed = SeedDerivation.derive_region_seed(base_seed, "campaign_world")
                        save_manager.start_new_campaign(campaign_seed)
                        hub_manager = HubManager(campaign_seed)
                        current_hub_id = "central_hub"

                    print(f"[CAMPAIGN] Generating Central Hub (seed: {campaign_seed})...")

                    hub_def = hub_manager.get_hub_definition(current_hub_id)
                    hub_rooms = hub_def.room_count if hub_def else 10
                    hub_shape = hub_def.world_shape.value if hub_def and hasattr(hub_def.world_shape, "value") else "blob"

                    # Regenerate world using centralized function
                    tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                        seed=campaign_seed,
                        shape=hub_shape,
                        rooms=hub_rooms,
                        hub_id=current_hub_id,
                        hub_manager=hub_manager,
                        portal_manager=portal_manager,
                        collision_system=collision_system,
                        camera=camera,
                        player=player,
                        enemy_manager=enemy_manager,
                        pickup_manager=pickup_manager,
                        hazard_manager=hazard_manager,
                        level_manager=level_manager,
                        npc_manager=npc_manager,
                        bus=bus,
                        GAME_WIDTH=GAME_WIDTH,
                        GAME_HEIGHT=GAME_HEIGHT
                    )
                    current_world_context = "hub"
                    update_replay_metadata()

                    # Start game
                    game_state_manager.start_game()

                elif selected_mode == "arcade":
                    # Start arcade mode - existing procedural generation
                    print("[MODE] Starting Arcade Mode...")
                    menu_manager.clear_menus()
                    current_play_mode = PlayMode.ARCADE
                    arcade_depth = 0

                    # Generate new arcade world
                    arcade_seed = get_arcade_seed(arcade_depth)

                    print(f"[ARCADE] Generating procedural level (seed: {arcade_seed})...")

                    # Regenerate world using centralized function
                    tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                        seed=arcade_seed,
                        shape="snake",
                        rooms=8,
                        hub_id=None,
                        hub_manager=hub_manager,
                        portal_manager=portal_manager,
                        collision_system=collision_system,
                        camera=camera,
                        player=player,
                        enemy_manager=enemy_manager,
                        pickup_manager=pickup_manager,
                        hazard_manager=hazard_manager,
                        level_manager=level_manager,
                        npc_manager=npc_manager,
                        bus=bus,
                        GAME_WIDTH=GAME_WIDTH,
                        GAME_HEIGHT=GAME_HEIGHT
                    )
                    current_world_context = "arcade"
                    update_replay_metadata()

                    # Start game
                    game_state_manager.start_game()

                elif selected_mode == "playtest":
                    # Show mission selector
                    print("[MODE] Opening Mission Selector...")
                    mission_menu = MissionSelectorMenu(GAME_WIDTH, GAME_HEIGHT, get_mission_registry())
                    menu_manager.push_menu(mission_menu)

            elif isinstance(current_menu, MissionSelectorMenu):
                selected_mission = current_menu.get_selected_mission()

                if selected_mission:
                    # Start playtest mission
                    print(f"[PLAYTEST] Starting mission: {selected_mission}")
                    menu_manager.clear_menus()

                    # Load mission definition
                    mission_def = get_mission_registry().get_mission(selected_mission)

                    if mission_def:
                        current_play_mode = PlayMode.PLAYTEST
                        region_id = getattr(mission_def, "region", current_hub_id or "playtest")
                        region_seed = SeedDerivation.derive_region_seed(hub_manager.world_seed, region_id)
                        mission_seed = SeedDerivation.derive_mission_seed(region_seed, mission_def.mission_id)

                        print(f"[PLAYTEST] Mission: {mission_def.mission_name}")
                        print(f"[PLAYTEST] Difficulty: {mission_def.difficulty}, Rooms: {mission_def.room_count}")

                        # Start objective tracking for playtest mission
                        if objective_tracker:
                            objective_tracker.stop_mission_objectives()
                            objective_tracker.start_mission_objectives(mission_def.mission_id)

                        # Regenerate world using centralized function
                        tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                            seed=mission_seed,
                            shape=mission_def.shape,
                            rooms=mission_def.room_count,
                            hub_id=None,
                            hub_manager=hub_manager,
                            portal_manager=portal_manager,
                            collision_system=collision_system,
                            camera=camera,
                            player=player,
                            enemy_manager=enemy_manager,
                            pickup_manager=pickup_manager,
                            hazard_manager=hazard_manager,
                            level_manager=level_manager,
                            npc_manager=npc_manager,
                            bus=bus,
                            GAME_WIDTH=GAME_WIDTH,
                            GAME_HEIGHT=GAME_HEIGHT,
                            mission_def=mission_def
                        )
                        current_world_context = "mission"
                        update_replay_metadata(mission_def.mission_id)

                        if objective_tracker:
                            targets = build_objective_location_targets(
                                world, megamap, spawn_x, spawn_y, exit_x, exit_y
                            )
                            fallback_id = "exit" if exit_x is not None and exit_y is not None else None
                            objective_tracker.set_location_targets(targets, fallback_id=fallback_id)

                        # Start game
                        game_state_manager.start_game()

        # Only process game input and updates when playing
        if game_state_manager.is_playing():
            # Free camera controls (arrow keys in free mode)
            if camera.mode == CameraMode.FREE:
                if keys[pygame.K_UP]:
                    camera.move_free_camera(0, -1)
                if keys[pygame.K_DOWN]:
                    camera.move_free_camera(0, 1)
                if keys[pygame.K_LEFT]:
                    camera.move_free_camera(-1, 0)
                if keys[pygame.K_RIGHT]:
                    camera.move_free_camera(1, 0)

            player.process_input(keys)

            # Tutorial triggers (based on player actions)
            if game_state_manager.is_playing():
                # Jump tutorial (trigger when player has used jumps)
                if player.state.jumps_left < player.state.max_jumps and "jump" not in tutorial_manager.shown_tutorials:
                    tutorial_manager.trigger_tutorial("jump")

                # Dash tutorial
                if player.state.is_dashing and "dash" not in tutorial_manager.shown_tutorials:
                    tutorial_manager.trigger_tutorial("dash")

                # Wall slide tutorial
                if player.state.is_wall_sliding and "wall_slide" not in tutorial_manager.shown_tutorials:
                    tutorial_manager.trigger_tutorial("wall_slide")

                # Crouch tutorial
                if player.state.crouching and "crouch" not in tutorial_manager.shown_tutorials:
                    tutorial_manager.trigger_tutorial("crouch")

            # Update game (fixed timestep)
            game_clock.tick()
            bus.process()

            # Update story cutscenes (v0.7.0)
            if story_manager.is_cutscene_playing():
                # Update cutscene
                story_manager.update_cutscene(1.0 / FPS)

                # Handle skip input (ESC or SPACE)
                if pygame.K_ESCAPE in pressed_once or pygame.K_SPACE in pressed_once:
                    if story_manager.skip_cutscene():
                        print("[CUTSCENE] Skipped cutscene")

            if objective_tracker and objective_tracker.active_mission_id:
                player_center_x = player.state.physics.x + player.state.physics.width / 2
                player_center_y = player.state.physics.y + player.state.physics.height / 2
                bus.emit(
                    PlayerPositionUpdateEvent(
                        player_x=player_center_x,
                        player_y=player_center_y
                    ),
                    immediate=True
                )

        elif game_state_manager.is_dialogue():
            # Handle dialogue input (no gameplay updates)
            current_node = dialogue_manager.get_current_node()
            if current_node:
                available_choices = dialogue_manager.get_available_choices()
                action = dialogue_ui.handle_input(pressed_once, available_choices)
                if action == "advance":
                    dialogue_manager.advance()
                elif action and action.startswith("select_"):
                    try:
                        choice_index = int(action.split("_")[1])
                        dialogue_manager.select_choice(choice_index)
                    except ValueError:
                        pass

            if not dialogue_manager.is_active():
                game_state_manager.transition_to(GameState.PLAYING)

        elif game_state_manager.is_mission_menu():
            # Mission menu active - drive via command pipeline for determinism
            result = mission_menu_ui.handle_command(current_command, pressed_once)
            if result == "accept":
                selected = mission_menu_ui.get_selected_mission()
                if selected and selected.status != MissionStatus.LOCKED:
                    mission_def = get_mission_registry().get_mission(selected.mission_id)
                    if mission_def:
                        # Reset and start objectives for the new mission
                        objective_tracker.stop_mission_objectives()
                        objective_tracker.start_mission_objectives(mission_def.mission_id)
                        region_id = getattr(mission_def, "region", current_hub_id or "campaign")
                        region_seed = SeedDerivation.derive_region_seed(hub_manager.world_seed, region_id)
                        mission_seed = SeedDerivation.derive_mission_seed(region_seed, mission_def.mission_id)
                        tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                            seed=mission_seed,
                            shape=mission_def.shape,
                            rooms=mission_def.room_count,
                            hub_id=None,
                            hub_manager=hub_manager,
                            portal_manager=portal_manager,
                            collision_system=collision_system,
                            camera=camera,
                            player=player,
                            enemy_manager=enemy_manager,
                            pickup_manager=pickup_manager,
                            hazard_manager=hazard_manager,
                            level_manager=level_manager,
                            npc_manager=npc_manager,
                            bus=bus,
                            GAME_WIDTH=GAME_WIDTH,
                            GAME_HEIGHT=GAME_HEIGHT,
                            mission_def=mission_def
                        )
                        if objective_tracker:
                            targets = build_objective_location_targets(
                                world, megamap, spawn_x, spawn_y, exit_x, exit_y
                            )
                            fallback_id = "exit" if exit_x is not None and exit_y is not None else None
                            objective_tracker.set_location_targets(targets, fallback_id=fallback_id)
                        current_play_mode = PlayMode.CAMPAIGN
                        level_complete = False
                        current_world_context = "mission"
                        game_state_manager.transition_to(GameState.PLAYING)
                        mission_menu_ui.hide()
                        active_mission_pool = []
                        update_replay_metadata(mission_def.mission_id)
                        print(f"[MISSION] Started mission {mission_def.mission_id}")
                else:
                    print("[MISSION MENU] Selected mission is locked or missing")
            elif result == "cancel":
                mission_menu_ui.hide()
                active_mission_pool = []
                game_state_manager.transition_to(GameState.PLAYING)

        elif game_state_manager.is_shop():
            # Shop active - drive via command pipeline for determinism
            shop_action = shop_ui.handle_command(current_command, pressed_once)
            if shop_action:
                action, index = shop_action
                process_shop_action(action, index)

        # Handle moral choice input (v0.7.0 - Final battle ending choice)
        if ending_manager.state == EndingState.CHOICE_PRESENTED:
            # Check for choice selection (1 or 2 keys)
            if pygame.K_1 in pressed_once:
                # Save choice
                choice = EndingChoice.SAVE
                if ending_manager.make_choice(choice):
                    print(f"[ENDING] Player chose: {choice.value}")
                    # Trigger ending cutscene
                    ending_cutscene_data = ending_manager.get_ending_cutscene_data()
                    if ending_cutscene_data:
                        story_manager.trigger_cutscene(ending_cutscene_data["cutscene_id"])
                    ending_manager.complete_ending()
            elif pygame.K_2 in pressed_once:
                # Destroy choice
                choice = EndingChoice.DESTROY
                if ending_manager.make_choice(choice):
                    print(f"[ENDING] Player chose: {choice.value}")
                    # Trigger ending cutscene
                    ending_cutscene_data = ending_manager.get_ending_cutscene_data()
                    if ending_cutscene_data:
                        story_manager.trigger_cutscene(ending_cutscene_data["cutscene_id"])
                    ending_manager.complete_ending()

        pause_simulation = game_state_manager.is_mission_menu() or game_state_manager.is_shop()

        if not pause_simulation:
            # Track state transitions for particles
            if not last_on_ground and player.state.physics.on_ground:
                particles.emit_dust(player.state.physics.x, player.state.physics.y + player.state.physics.height // 2)
            if player.state.is_dashing and not last_is_dashing:
                facing = player.state.facing if player.state.facing != 0 else 1
                particles.emit_dash(player.state.physics.x, player.state.physics.y, facing)
            last_on_ground = player.state.physics.on_ground
            last_is_dashing = player.state.is_dashing

            # Update camera to follow player
            camera.update(player.state.physics.x, player.state.physics.y)

            # Update pickups
            pickup_manager.update(1.0 / FPS)

            # Update enemies (v0.6.0)
            enemy_manager.update(
                dt=1.0 / FPS,
                player_x=player.state.physics.x,
                player_y=player.state.physics.y,
                player_width=player.state.physics.width,
                player_height=player.state.physics.height,
                collision_system=collision_system,
                camera_rect=(camera.x, camera.y, camera.config.game_width, camera.config.game_height),
                cull_margin=0.0,
                player_state=player.state
            )
            # Decay sword attack cooldown
            if attack_timer > 0.0:
                attack_timer -= 1.0 / FPS
                player.state.attack_timer = max(0.0, player.state.attack_timer - 1.0 / FPS)
            else:
                player.state.attack_stage = 0
            if attack_fx_timer > 0.0:
                attack_fx_timer -= 1.0 / FPS
                if attack_fx_timer <= 0:
                    attack_fx_rect = None

            # Update NPCs (v0.6.0 - Phase 2) and portals
            if game_state_manager.is_playing():
                npc_manager.update(dt=1.0 / FPS)
                portal_manager.update(dt=1.0 / FPS)
                # Player combat interactions (dash/jump attacks + contact damage)
                damage_taken = combat_mechanic.check_enemy_collisions(
                    player.state,
                    enemy_manager,
                    dt=1.0 / FPS
                )
                if damage_taken and not player.damage.is_invincible(player.state):
                    died = player.damage.take_damage(player.state, damage_taken)
                    if died:
                        level_manager.increment_deaths()
                        if current_world_context == "mission":
                            regenerate_hub_for_respawn("mission failed (enemy)")
                        elif current_world_context == "hub" and current_hub_id != "central_hub":
                            regenerate_hub_for_respawn("area hub death", target_hub_id="central_hub")
                        else:
                            player.damage.respawn(player.state, spawn_x, spawn_y)
                            print(f"[DEATH] Player died from enemy contact, respawning at ({spawn_x:.0f}, {spawn_y:.0f})")

                if pygame.K_e in pressed_once:
                    # Prefer portal interaction if nearby
                    nearby_portal = portal_manager.check_interaction(
                        player_x=player.state.physics.x,
                        player_y=player.state.physics.y,
                        player_width=player.state.physics.width,
                        player_height=player.state.physics.height
                    )
                    if nearby_portal:
                        portal_manager.interact_with_portal(nearby_portal, player_id=0)
                        print(f"[PORTAL] Activated {nearby_portal.portal_id} -> {nearby_portal.destination_id}")
                    else:
                        # Find NPCs in interaction range
                        nearby_npcs = npc_manager.get_nearby_npcs(
                            player_x=player.state.physics.x,
                            player_y=player.state.physics.y,
                            player_width=player.state.physics.width,
                            player_height=player.state.physics.height
                        )

                        if nearby_npcs:
                            # Interact with the nearest NPC
                            nearby_npc = nearby_npcs[0]
                            npc_manager.interact_with_npc(nearby_npc, player_id=0)
                            print(f"[NPC] Player interacted with {nearby_npc.npc_id}")

            if game_state_manager.is_playing():
                # Check pickup collections
                collected = pickup_manager.check_collections(
                    player.state.physics.x,
                    player.state.physics.y,
                    player.state.physics.width,
                    player.state.physics.height
                )

                # Update level manager with collectibles
                if collected:
                    for pickup in collected:
                        if pickup.pickup_type == "collectible":
                            level_manager.add_collectible()
                            # Trigger collectibles tutorial on first collection
                            if "collectibles" not in tutorial_manager.shown_tutorials:
                                tutorial_manager.trigger_tutorial("collectibles")
                            # Emit mission objective event for collectibles
                            collect_item_id = getattr(pickup, "item_id", None)
                            if not collect_item_id:
                                collect_item_id = "collectible"
                                if objective_tracker and objective_tracker.active_mission_id:
                                    for obj_state in objective_tracker.get_active_objectives():
                                        if obj_state.objective_type == ObjectiveType.COLLECT_ITEMS and not obj_state.is_complete:
                                            if obj_state.item_id and obj_state.item_id != "coin":
                                                collect_item_id = obj_state.item_id
                                            break
                            bus.emit(ItemCollectedEvent(
                                item_id=collect_item_id,
                                quantity=pickup.value,
                                position=(pickup.x, pickup.y)
                            ))
                            # Add an item to inventory (objective item if provided, else treasure)
                            reward_item_id = collect_item_id if collect_item_id not in ("collectible", "coin") else "treasure_ruby"
                            try:
                                if player_inventory.add_item(reward_item_id, pickup.value):
                                    print(f"[PICKUP] Added {reward_item_id} x{pickup.value} to inventory")
                            except Exception:
                                pass
                        elif pickup.pickup_type == "health":
                            # Heal player when collecting health pickup
                            player.damage.heal(player.state, pickup.value)
                        elif pickup.pickup_type == "coin":
                            # Treat coins as currency
                            player_inventory.add_currency(pickup.value)
                            if save_manager and save_manager.data and save_manager.data.campaign:
                                save_manager.data.campaign.currency = player_inventory.currency
                                save_manager.mark_dirty()
                            bus.emit(ItemCollectedEvent(
                                item_id="coin",
                                quantity=pickup.value,
                                position=(pickup.x, pickup.y)
                            ))

                # Check hazard collisions (damage/death)
                if not level_complete:
                    hazard_collision = hazard_manager.check_hazards(
                        player.state,
                        invincible=player.damage.is_invincible(player.state)
                    )

                    if hazard_collision:
                        hazard, damage = hazard_collision

                        # Trigger hazards tutorial on first damage
                        if "hazards" not in tutorial_manager.shown_tutorials:
                            tutorial_manager.trigger_tutorial("hazards")

                        # Apply damage/death
                        died = hazard_manager.apply_damage(player.player_id, player.state, hazard)

                        if died:
                            level_manager.increment_deaths()
                            if current_world_context == "mission":
                                regenerate_hub_for_respawn("mission failed (hazard)")
                            elif current_world_context == "hub" and current_hub_id != "central_hub":
                                regenerate_hub_for_respawn("area hub death", target_hub_id="central_hub")
                            else:
                                player.damage.respawn(player.state, spawn_x, spawn_y)
                                print(f"[DEATH] Player died from {hazard.hazard_type}, respawning at ({spawn_x:.0f}, {spawn_y:.0f})")

            # Check exit detection (only if not already complete)
            if not level_complete and exit_x is not None:
                player_center_x = player.state.physics.x + player.state.physics.width / 2
                player_center_y = player.state.physics.y + player.state.physics.height / 2

                if level_manager.check_exit_reached(player_center_x, player_center_y, time.time()):
                    if current_world_context == "mission":
                        # Require objectives to be complete before finishing
                        if objective_tracker and objective_tracker.are_all_objectives_complete():
                            # Grant simple rewards from mission definition (currency only for now)
                            if objective_tracker.active_mission_id:
                                mission_def = get_mission_registry().get_mission(objective_tracker.active_mission_id)
                                if mission_def:
                                    # Currency
                                    if mission_def.rewards.currency:
                                        player_inventory.add_currency(mission_def.rewards.currency)
                                        print(f"[MISSION] Reward: +{mission_def.rewards.currency} gold")
                                    # Items
                                    for reward_item in mission_def.rewards.items:
                                        item_id = reward_item.get("id") or reward_item.get("item_id")
                                        qty = reward_item.get("quantity", 1)
                                        if item_id:
                                            player_inventory.add_item(item_id, qty)
                                            print(f"[MISSION] Reward item: {item_id} x{qty}")
                                    # Mark mission complete in campaign save
                                    if save_manager and save_manager.data and save_manager.data.campaign:
                                        completed = save_manager.data.campaign.completed_missions
                                        try:
                                            # Handle set or list
                                            if isinstance(completed, set):
                                                completed.add(mission_def.mission_id)
                                            else:
                                                if mission_def.mission_id not in completed:
                                                    completed.append(mission_def.mission_id)
                                        except Exception:
                                            pass
                                        save_manager.data.campaign.currency = player_inventory.currency
                                        save_manager.mark_dirty()

                                    # Trigger story events on mission completion (v0.7.0)
                                    story_events = story_manager.on_mission_complete(mission_def.mission_id)
                                    if story_events:
                                        print(f"[STORY] Mission {mission_def.mission_id} triggered story events: {story_events}")
                                        # Check for cutscene trigger
                                        if "cutscene_id" in story_events:
                                            cutscene_id = story_events["cutscene_id"]
                                            print(f"[STORY] Triggering cutscene: {cutscene_id}")
                                            story_manager.trigger_cutscene(cutscene_id)

                            objective_tracker.stop_mission_objectives()
                            regenerate_hub_for_respawn("mission complete")
                        else:
                            print("[MISSION] Exit locked until objectives are complete")
                    elif current_world_context == "arcade":
                        # Auto-advance arcade run to next, larger layout
                        level_complete = True
                        victory_screen.reset()
                        arcade_depth += 1
                        arcade_rooms = min(8 + arcade_depth * 2, 24)
                        arcade_seed = get_arcade_seed(arcade_depth)
                        tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = regenerate_world_state(
                            seed=arcade_seed,
                            shape="snake",
                            rooms=arcade_rooms,
                            hub_id=None,
                            hub_manager=hub_manager,
                            portal_manager=portal_manager,
                            collision_system=collision_system,
                            camera=camera,
                            player=player,
                            enemy_manager=enemy_manager,
                            pickup_manager=pickup_manager,
                            hazard_manager=hazard_manager,
                            level_manager=level_manager,
                            npc_manager=npc_manager,
                            bus=bus,
                            GAME_WIDTH=GAME_WIDTH,
                            GAME_HEIGHT=GAME_HEIGHT
                        )
                        current_seed = arcade_seed
                        level_complete = False
                        update_replay_metadata()
                        print(f"[ARCADE] Advanced to depth {arcade_depth} (rooms={arcade_rooms})")
                    else:
                        level_complete = True
                        victory_screen.reset()

                        # Save level completion to save file
                        stats = level_manager.get_stats()
                        level_id = f"{current_world_context}_seed_{current_seed if current_seed is not None else 0}"
                        save_manager.complete_level(
                            level_id,
                            stats['time'],
                            stats['collectibles'],
                            stats['deaths']
                        )
                        persist_story_state()  # Save story state (v0.7.0)
                        save_manager.save(force=True)  # Save immediately on level complete

                        print(f"\n[VICTORY] Level complete!")
                        print(f"[VICTORY] Time: {level_manager.state.completion_time:.2f}s")
                        print(f"[VICTORY] Stats: {level_manager.get_stats()}")
                        print(f"[SAVE] Progress saved!")

        frame_idx += 1

        # Render to virtual game surface
        game_surface = camera.get_game_surface()
        game_surface.fill(COLOR_BG)

        # Draw solid tiles (with camera transform and autotiled assets)
        # Determine biome for tile selection
        current_biome = 'dungeon'  # Default
        if world and megamap:
            # Get current room from player position
            player_pos = (player.state.physics.x, player.state.physics.y)
            current_room_coords = get_current_room_coords(megamap, player_pos)

            # Find the room in the world
            current_room = next(
                (r for r in world.all_rooms if (r.grid_x, r.grid_y) == current_room_coords),
                None
            )

            if current_room and hasattr(current_room, 'biome_theme'):
                biome_name = current_room.biome_theme.value.lower()
                # Map world generation biomes to tile biomes
                biome_map = {
                    'dungeon': 'dungeon',
                    'cave': 'cave',
                    'forest': 'building',  # Use building tiles for forest (placeholder)
                    'desert': 'cave',      # Use cave tiles for desert (placeholder)
                }
                current_biome = biome_map.get(biome_name, 'dungeon')

        # Use autotiling for procedural worlds (we now have megamap)
        use_autotiling = megamap is not None

        if use_autotiling:
            # Import tile constants for autotiling
            from systems.room_generation import TILE_SOLID, TILE_PLATFORM

            # OPTIMIZATION: Only render tiles within camera view + margin
            # Calculate visible tile bounds
            cam_x, cam_y = camera.x, camera.y
            screen_w, screen_h = camera.config.game_width, camera.config.game_height

            # Add margin for smooth scrolling (1 screen extra on each side)
            margin = 32 * 10  # 10 tiles margin
            min_tile_x = max(0, (cam_x - margin) // 32)
            max_tile_x = min(megamap.width_tiles, (cam_x + screen_w + margin) // 32 + 1)
            min_tile_y = max(0, (cam_y - margin) // 32)
            max_tile_y = min(megamap.height_tiles, (cam_y + screen_h + margin) // 32 + 1)

            # Draw solid tiles with culling
            for tile in tiles:
                tx, ty = tile.x // 32, tile.y // 32

                # Cull tiles outside view
                if not (min_tile_x <= tx < max_tile_x and min_tile_y <= ty < max_tile_y):
                    continue

                screen_rect = camera.apply(tile)

                # Get autotiled tile based on neighbors (use megamap as tilemap)
                tile_surface = tile_loader.get_autotiled_tile(
                    biome=current_biome,
                    tile_type='solid',
                    tilemap=megamap.tilemap,
                    x=tx, y=ty,
                    tile_id=TILE_SOLID,
                    seed=current_seed
                )
                game_surface.blit(tile_surface, screen_rect)

            # Draw platforms with culling
            for platform in platforms:
                tx, ty = platform.x // 32, platform.y // 32

                # Cull platforms outside view
                if not (min_tile_x <= tx < max_tile_x and min_tile_y <= ty < max_tile_y):
                    continue

                screen_rect = camera.apply(platform)

                tile_surface = tile_loader.get_autotiled_tile(
                    biome=current_biome,
                    tile_type='platform',
                    tilemap=megamap.tilemap,
                    x=tx, y=ty,
                    tile_id=TILE_PLATFORM,
                    seed=current_seed
                )
                game_surface.blit(tile_surface, screen_rect)

        else:
            # Fallback to simple tiling (for static levels without tilemap)
            for tile in tiles:
                screen_rect = camera.apply(tile)
                tile_index = (tile.x // 32 + tile.y // 32) % 3
                tile_surface = tile_loader.get_tile(current_biome, 'solid', tile_index)
                game_surface.blit(tile_surface, screen_rect)

            for platform in platforms:
                screen_rect = camera.apply(platform)
                tile_index = (platform.x // 32 + platform.y // 32) % 2
                tile_surface = tile_loader.get_tile(current_biome, 'platform', tile_index)
                game_surface.blit(tile_surface, screen_rect)

        # Draw particles behind player
        particles.update(1.0 / FPS)
        particles.draw(game_surface, camera)

        # Draw hazards (behind pickups and player)
        render_hazards(game_surface, hazard_manager.get_active_hazards(), camera)

        # Draw pickups (before player so they appear behind)
        render_pickups(game_surface, pickup_manager.get_alive_pickups(), camera)

        # Draw portals
        for portal in portal_manager.portals:
            draw_portal(game_surface, portal, int(camera.x), int(camera.y))

        # Draw enemies (v0.6.0)
        for enemy in enemy_manager.enemies.values():
            # Get enemy bounding box from definition
            ex, ey, ew, eh = enemy.get_rect()
            enemy_rect = pygame.Rect(ex, ey, ew, eh)
            screen_enemy_rect = camera.apply(enemy_rect)

            # Simple colored rectangle based on enemy type
            if enemy.enemy_type.value == "goblin":
                enemy_color = (100, 180, 100)  # Green
            elif enemy.enemy_type.value == "slime":
                enemy_color = (150, 100, 200)  # Purple
            elif enemy.enemy_type.value == "bat":
                enemy_color = (80, 80, 80)  # Gray
            else:
                enemy_color = (200, 100, 100)  # Red default

            # Draw enemy with shadow
            shadow_rect = pygame.Rect(
                screen_enemy_rect.centerx - screen_enemy_rect.width // 2,
                screen_enemy_rect.bottom - 4,
                screen_enemy_rect.width,
                4
            )
            pygame.draw.ellipse(game_surface, (0, 0, 0, 80), shadow_rect)

            # Draw enemy body
            pygame.draw.rect(game_surface, enemy_color, screen_enemy_rect)

            # Draw attack telegraph effects
            from entities.enemy import EnemyAttackSubState, EnemyAIState

            if enemy.ai_state == EnemyAIState.ATTACK:
                if enemy.attack_substate == EnemyAttackSubState.WINDUP:
                    # WINDUP TELEGRAPH: Red glow + pulsing exclamation mark

                    # Calculate pulse intensity (0 to 1)
                    definition = enemy.get_definition()
                    progress = enemy.attack_substate_timer / definition.attack_windup_time
                    pulse = abs(math.sin(enemy.attack_substate_timer * 10.0))  # Fast pulse

                    # Red glow overlay on enemy
                    glow_surface = pygame.Surface(screen_enemy_rect.size, pygame.SRCALPHA)
                    glow_alpha = int(120 * pulse)  # Pulsing transparency
                    glow_surface.fill((255, 50, 50, glow_alpha))
                    game_surface.blit(glow_surface, screen_enemy_rect.topleft)

                    # Exclamation mark above enemy
                    exclaim_x = screen_enemy_rect.centerx
                    exclaim_y = screen_enemy_rect.top - 30
                    exclaim_size = 8 + int(4 * pulse)  # Pulsing size

                    # Draw exclamation mark (! symbol)
                    # Vertical bar
                    pygame.draw.rect(game_surface, (255, 255, 0),
                                    pygame.Rect(exclaim_x - 2, exclaim_y, 4, exclaim_size))
                    # Dot
                    pygame.draw.circle(game_surface, (255, 255, 0),
                                      (exclaim_x, exclaim_y + exclaim_size + 3), 2)

                    # Spawn warning particles
                    if int(enemy.attack_substate_timer * 10) % 3 == 0:  # Every 0.3s
                        enemy_center = enemy.get_center()
                        # Convert world coordinates to screen coordinates
                        screen_x = enemy_center[0] - int(camera.x)
                        screen_y = enemy_center[1] - int(camera.y)
                        particles.emit_attack_warning(screen_x, screen_y, count=3)

                elif enemy.attack_substate == EnemyAttackSubState.ACTIVE:
                    # ACTIVE PHASE: Bright flash + impact particles

                    # White flash overlay
                    flash_surface = pygame.Surface(screen_enemy_rect.size, pygame.SRCALPHA)
                    flash_alpha = 200  # Very bright
                    flash_surface.fill((255, 255, 255, flash_alpha))
                    game_surface.blit(flash_surface, screen_enemy_rect.topleft)

                    # Draw hitbox outline in red
                    pygame.draw.rect(game_surface, (255, 0, 0), screen_enemy_rect, width=3)

                    # Spawn impact particles on first frame
                    if enemy.attack_substate_timer < 0.02:  # First frame
                        enemy_center = enemy.get_center()
                        # Convert world coordinates to screen coordinates
                        screen_x = enemy_center[0] - int(camera.x)
                        screen_y = enemy_center[1] - int(camera.y)
                        particles.emit_attack_impact(screen_x, screen_y, count=12)

                elif enemy.attack_substate == EnemyAttackSubState.RECOVERY:
                    # RECOVERY: Slight darkening to show enemy is vulnerable
                    recovery_surface = pygame.Surface(screen_enemy_rect.size, pygame.SRCALPHA)
                    recovery_surface.fill((0, 0, 0, 60))  # Dark overlay
                    game_surface.blit(recovery_surface, screen_enemy_rect.topleft)

            # AI state / facing indicator for debugging
            center = screen_enemy_rect.center
            dir_x = 1 if enemy.physics.vx > 0 else -1 if enemy.physics.vx < 0 else (1 if enemy.facing_right else -1)
            end = (center[0] + dir_x * 12, center[1])
            pygame.draw.line(game_surface, (255, 220, 120), center, end, 2)
            # Small text for AI state
            state_label = enemy.ai_state.value if hasattr(enemy.ai_state, "value") else str(enemy.ai_state)
            state_font = getattr(hud, "small", getattr(hud, "font", None))
            if state_font:
                state_surf = state_font.render(state_label[:3], True, (255, 255, 0))
                game_surface.blit(state_surf, (screen_enemy_rect.left, screen_enemy_rect.top - 12))
            game_surface.blit(state_surf, (screen_enemy_rect.left, screen_enemy_rect.top - 12))

            # Draw health bar above enemy
            if enemy.health_state.current_hp < enemy.health_state.max_hp:
                health_bar_width = screen_enemy_rect.width
                health_bar_height = 4
                health_bar_x = screen_enemy_rect.centerx - health_bar_width // 2
                health_bar_y = screen_enemy_rect.top - 8

                # Background (red)
                bg_rect = pygame.Rect(health_bar_x, health_bar_y, health_bar_width, health_bar_height)
                pygame.draw.rect(game_surface, (100, 0, 0), bg_rect)

                # Foreground (green, proportional to current HP)
                hp_ratio = enemy.health_state.current_hp / enemy.health_state.max_hp
                fg_width = int(health_bar_width * hp_ratio)
                fg_rect = pygame.Rect(health_bar_x, health_bar_y, fg_width, health_bar_height)
                pygame.draw.rect(game_surface, (0, 200, 0), fg_rect)

        # Draw sword attack hitbox (temporary visualizer)
        if attack_fx_rect:
            fx_rect_screen = camera.apply(attack_fx_rect)
            pulse = abs(math.sin(pygame.time.get_ticks() / 120.0))
            color = (255, int(120 + 80 * pulse), 60)
            pygame.draw.rect(game_surface, color, fx_rect_screen, width=2)

        # Draw NPCs (v0.6.0 - Phase 2)
        for npc in npc_manager.npcs:
            # Get NPC bounding box
            npc_rect = pygame.Rect(npc.x, npc.y, npc.width, npc.height)
            screen_npc_rect = camera.apply(npc_rect)

            # Get NPC definition for color
            npc_def = npc_manager.get_npc_definition(npc.npc_id)

            # Simple colored rectangle based on NPC type (placeholder for sprites)
            from entities.npc import NPCType
            if npc_def and npc_def.npc_type == NPCType.MISSION_GIVER:
                npc_color = (255, 200, 50)  # Gold for mission givers
            elif npc_def and npc_def.npc_type == NPCType.SHOP:
                npc_color = (50, 255, 100)  # Green for shop keepers
            elif npc_def and npc_def.npc_type == NPCType.TUTORIAL:
                npc_color = (100, 150, 255)  # Blue for tutorial NPCs
            else:
                npc_color = (200, 200, 200)  # Gray for others

            # Draw NPC with shadow
            shadow_rect = pygame.Rect(
                screen_npc_rect.centerx - screen_npc_rect.width // 2,
                screen_npc_rect.bottom - 4,
                screen_npc_rect.width,
                4
            )
            pygame.draw.ellipse(game_surface, (0, 0, 0, 80), shadow_rect)

            # Draw NPC body
            pygame.draw.rect(game_surface, npc_color, screen_npc_rect)

        # Draw player (with camera transform and real sprite animations)
        player_rect = player.get_rect()
        screen_player_rect = camera.apply(player_rect)
        player_state_name = get_player_render_state(player)

        # Determine sprite facing (invert when on wall so character faces away)
        sprite_facing = player.state.facing or 1
        if player.state.physics.on_wall and not player.state.physics.on_ground:
            sprite_facing = -sprite_facing  # Face away from wall

        # Get sprite frame scaled to player hitbox size
        target_size = (screen_player_rect.width, screen_player_rect.height)
        frame = sprite_manager.get_scaled_frame(
            player_state_name,
            sprite_facing,
            pygame.time.get_ticks(),
            target_size=target_size
        )
        sprite_rect = frame.surface.get_rect(center=screen_player_rect.center)
        # Teleport phase overlay: show semi-transparent ghost at cursor
        if player.state.is_teleporting_phase and getattr(player, "teleport", None):
            phase_pos = player.teleport.phase_cursor or (player.state.physics.x, player.state.physics.y)
            phase_rect = pygame.Rect(int(phase_pos[0]), int(phase_pos[1]), player_rect.width, player_rect.height)
            phase_screen = camera.apply(phase_rect)
            ghost = frame.surface.copy()
            ghost.fill((160, 120, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            game_surface.blit(ghost, phase_screen)
        # Simple shadow under player
        shadow_width = screen_player_rect.width
        shadow_height = max(4, screen_player_rect.height // 6)
        shadow_rect = pygame.Rect(
            screen_player_rect.centerx - shadow_width // 2,
            screen_player_rect.bottom - shadow_height // 2,
            shadow_width,
            shadow_height,
        )
        pygame.draw.ellipse(game_surface, (0, 0, 0, 80), shadow_rect)

        # Apply invincibility flash effect
        if player.damage.is_invincible(player.state):
            # Flash white during i-frames (on/off every 6 frames = 0.1s at 60fps)
            flash_cycle = (player.state.health_state.invincibility_frames // 6) % 2
            if flash_cycle == 0:
                # Create white flash overlay
                flash_surface = frame.surface.copy()
                flash_surface.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_ADD)
                game_surface.blit(flash_surface, sprite_rect)
            else:
                game_surface.blit(frame.surface, sprite_rect)
        else:
            game_surface.blit(frame.surface, sprite_rect)

        # Draw Yin & Yang companion orbs (v0.7.0 - The Hollowed Ninja)
        if story_manager.yin_yang_present:
            companion_orbs.update(
                1.0 / FPS,
                player.state.physics.x,
                player.state.physics.y,
                player.state.physics.width,
                player.state.physics.height
            )
            companion_orbs.render(
                game_surface,
                player.state.physics.x,
                player.state.physics.y,
                player.state.physics.width,
                player.state.physics.height,
                camera.x,
                camera.y
            )

        # Draw exit marker (if exit exists and not yet complete)
        if exit_x is not None and exit_y is not None and not level_complete:
            exit_rect = pygame.Rect(exit_x - 16, exit_y - 32, 32, 64)
            screen_exit_rect = camera.apply(exit_rect)

            # Pulsing exit portal effect
            pulse = abs(math.sin(pygame.time.get_ticks() / 500.0))
            exit_color = (int(255 * pulse), int(215 * pulse), 0)  # Gold pulsing

            # Draw exit portal (simple rectangle for now)
            pygame.draw.rect(game_surface, exit_color, screen_exit_rect, 3)
            # Inner glow
            inner_rect = screen_exit_rect.inflate(-6, -6)
            pygame.draw.rect(game_surface, exit_color + (int(128 * pulse),), inner_rect)

        # Objective compass (points toward nearest active objective target)
        def get_objective_target():
            if not objective_tracker or not objective_tracker.get_incomplete_objectives():
                return None
            # Kill objectives -> nearest living enemy
            kill_objs = [o for o in objective_tracker.get_incomplete_objectives() if o.objective_type.value == "kill_all_enemies"]
            collect_objs = [o for o in objective_tracker.get_incomplete_objectives() if o.objective_type.value == "collect_items"]
            reach_objs = [o for o in objective_tracker.get_incomplete_objectives() if o.objective_type.value == "reach_location"]

            player_center = (
                player.state.physics.x + player.state.physics.width / 2,
                player.state.physics.y + player.state.physics.height / 2
            )

            if kill_objs and enemy_manager.enemies:
                living = [e for e in enemy_manager.enemies.values() if not e.is_dead()]
                if living:
                    living.sort(key=lambda e: (e.get_center()[0] - player_center[0]) ** 2 + (e.get_center()[1] - player_center[1]) ** 2)
                    return living[0].get_center()

            if collect_objs:
                # Use collectibles first, else coins
                pickups = [p for p in pickup_manager.get_alive_pickups() if p.pickup_type in ("collectible", "coin")]
                if pickups:
                    pickups.sort(key=lambda p: (p.x - player_center[0]) ** 2 + (p.y - player_center[1]) ** 2)
                    target_pickup = pickups[0]
                    return (target_pickup.x + target_pickup.width / 2, target_pickup.y + target_pickup.height / 2)

            if reach_objs and exit_x is not None and exit_y is not None:
                return (exit_x, exit_y)

            return None

        objective_target = get_objective_target()
        if objective_target:
            px = player.state.physics.x + player.state.physics.width / 2
            py = player.state.physics.y + player.state.physics.height / 2
            tx, ty = objective_target
            angle = math.atan2(ty - py, tx - px)
            center_x = window_width // 2
            center_y = 80
            length = 36
            end_x = center_x + math.cos(angle) * length
            end_y = center_y + math.sin(angle) * length
            pygame.draw.line(game_surface, (255, 215, 0), (center_x, center_y), (end_x, end_y), 3)
            # Arrow head
            head_len = 10
            left_angle = angle + math.radians(150)
            right_angle = angle - math.radians(150)
            left_point = (end_x + math.cos(left_angle) * head_len, end_y + math.sin(left_angle) * head_len)
            right_point = (end_x + math.cos(right_angle) * head_len, end_y + math.sin(right_angle) * head_len)
            pygame.draw.polygon(game_surface, (255, 215, 0), [(end_x, end_y), left_point, right_point])

        # HUD
        mode_label = "PROCEDURAL" if use_procedural else "STATIC"
        seed_label = f"Seed: {current_seed}" if use_procedural else ""
        pickup_stats = pickup_manager.get_stats()
        if show_debug_overlay:
            hud.draw_hud(
                game_surface,
                player.state,
                camera.mode.value,
                mode_label,
                seed_label,
                clock_pygame.get_fps(),
                coins=pickup_stats['coins'],
                collectibles=pickup_stats['collectibles']
            )

        # Inventory UI overlay
        if inventory_ui.is_open():
            items_payload = []
            for slot in player_inventory.slots:
                if slot:
                    item_def = item_manager.get_item(slot.item_id) if item_manager else None
                    items_payload.append({
                        "name": item_def.display_name if item_def else slot.item_id,
                        "quantity": slot.quantity,
                        "rarity": item_def.rarity.value if item_def else "common"
                    })
            inventory_ui.draw(
                game_surface,
                items=items_payload,
                currency=player_inventory.currency,
                equipped_weapon=player_inventory.equipped_weapon,
                equipped_armor=player_inventory.equipped_armor
            )

        # Health HUD (v0.6.0) - Draw hearts in top-left
        health_x = 20
        health_y = 20
        heart_size = 24
        heart_spacing = 28

        for i in range(player.state.health_state.max_hp):
            heart_x = health_x + i * heart_spacing
            heart_rect = pygame.Rect(heart_x, health_y, heart_size, heart_size)

            if i < player.state.health_state.current_hp:
                # Full heart (red)
                pygame.draw.rect(game_surface, (220, 20, 60), heart_rect)
                # Heart shape detail (simple)
                pygame.draw.circle(game_surface, (220, 20, 60), (heart_x + 6, health_y + 6), 6)
                pygame.draw.circle(game_surface, (220, 20, 60), (heart_x + 18, health_y + 6), 6)
            else:
                # Empty heart (dark gray outline)
                pygame.draw.rect(game_surface, (60, 60, 60), heart_rect, 2)
                pygame.draw.circle(game_surface, (60, 60, 60), (heart_x + 6, health_y + 6), 6, 2)
                pygame.draw.circle(game_surface, (60, 60, 60), (heart_x + 18, health_y + 6), 6, 2)

            # Low health warning (pulse red when HP <= 1)
            if player.state.health_state.current_hp <= 1 and i < player.state.health_state.current_hp:
                pulse = abs(math.sin(pygame.time.get_ticks() / 200.0))
                warning_alpha = int(100 * pulse)
                warning_surface = pygame.Surface((heart_size, heart_size), pygame.SRCALPHA)
                warning_surface.fill((255, 0, 0, warning_alpha))
                game_surface.blit(warning_surface, (heart_x, health_y))

        # Objective HUD (v0.6.0) - Only for campaign/playtest modes
        if objective_hud_renderer and objective_tracker and objective_tracker.get_active_objectives():
            # Convert objective states to display format
            from rendering.objective_hud import ObjectiveDisplay
            objective_displays = []
            active_mission_id = getattr(objective_tracker, "active_mission_id", None)
            for obj_state in objective_tracker.get_active_objectives():
                # Use detailed description from mission data when available
                description = get_objective_display_text(obj_state, active_mission_id) if active_mission_id else "Objective"

                objective_displays.append(ObjectiveDisplay(
                    description=description,
                    current=obj_state.current_value,
                    target=obj_state.target_value,
                    completed=obj_state.is_complete,
                    objective_type=obj_state.objective_type.value
                ))

            objective_hud_renderer.draw_objectives(game_surface, objective_displays)

        # Compass indicators (nearest coin, exit direction, room type)
        if use_procedural and world and megamap:
            # Get player center position
            player_center = (
                player.state.physics.x + player.state.physics.width / 2,
                player.state.physics.y + player.state.physics.height / 2
            )

            # Find nearest coin
            nearest_coin_pos = None
            min_dist = float('inf')
            for pickup in pickup_manager.get_alive_pickups():
                if pickup.pickup_type == "coin":
                    coin_center = (pickup.x + pickup.width / 2, pickup.y + pickup.height / 2)
                    dx = coin_center[0] - player_center[0]
                    dy = coin_center[1] - player_center[1]
                    dist = (dx*dx + dy*dy) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_coin_pos = coin_center

            # Get current room type
            current_room_coords = get_current_room_coords(megamap, (player.state.physics.x, player.state.physics.y))
            current_room_type = None
            if current_room_coords:
                for room in world.all_rooms:
                    if (room.grid_x, room.grid_y) == current_room_coords:
                        current_room_type = room.room_type.value
                        break

            # Hub portal targets (for navigation compass)
            portal_targets = []
            if current_world_context == "hub" and portal_manager and portal_manager.portals:
                for portal in portal_manager.portals:
                    if portal.portal_type != PortalType.HUB:
                        continue
                    label = portal.destination_id.replace("_hub", "").replace("_", " ").title()
                    portal_center = (portal.x + portal.width / 2, portal.y + portal.height / 2)
                    portal_targets.append((f"Portal {label}", portal_center, portal.color))
                portal_targets.sort(
                    key=lambda entry: (entry[1][0] - player_center[0]) ** 2 + (entry[1][1] - player_center[1]) ** 2
                )

            # Draw compass
            hud.draw_compass_indicators(
                game_surface,
                player_center,
                nearest_coin_pos,
                (exit_x, exit_y) if exit_x and exit_y else None,
                current_room_type,
                portal_targets
            )

        # Minimap / full map toggles (for procedural worlds)
        if minimap and world and megamap:
            player_pos = (player.state.physics.x, player.state.physics.y)
            current_room_coords = get_current_room_coords(megamap, player_pos)
            if show_full_map:
                # Temporary full-map: draw overlay and render minimap scaled up
                overlay = pygame.Surface(game_surface.get_size(), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                game_surface.blit(overlay, (0, 0))
                old_scale = minimap.config.scale
                minimap.config.scale = 24
                minimap.render(game_surface, world, megamap, player_pos, current_room_coords)
                minimap.config.scale = old_scale
            elif show_minimap:
                minimap.render(game_surface, world, megamap, player_pos, current_room_coords)

        # NPC Indicators (v0.6.0 - Phase 2) - Show icons above NPCs (!, $, ?)
        npc_indicator_renderer.render(
            surface=game_surface,
            npc_manager=npc_manager,
            camera_x=camera.x,
            camera_y=camera.y
        )

        # NPC Interaction Prompts (v0.6.0 - Phase 2) - Show "Press E to talk"
        npc_prompt_renderer.render(
            surface=game_surface,
            npc_manager=npc_manager,
            player_x=player.state.physics.x,
            player_y=player.state.physics.y,
            player_width=player.state.physics.width,
            player_height=player.state.physics.height,
            camera_x=camera.x,
            camera_y=camera.y
        )

        # Dialogue UI (modal)
        if game_state_manager.is_dialogue():
            current_node = dialogue_manager.get_current_node()
            if current_node:
                dialogue_ui.render(game_surface, current_node, dialogue_manager.get_available_choices())

        # Mission menu UI (modal)
        if game_state_manager.is_mission_menu():
            mission_menu_ui.draw(game_surface)

        # Shop UI (modal)
        if game_state_manager.is_shop() and active_shop_npc_id:
            shop_inventory = trading_manager.get_shop(active_shop_npc_id)
            npc_items = []
            npc_currency = 0
            if shop_inventory:
                npc_currency = shop_inventory.currency
                for shop_item in shop_inventory.items:
                    item_def = item_manager.get_item(shop_item.item_id)
                    display_name = item_def.display_name if item_def else shop_item.item_id
                    npc_items.append({
                        "name": display_name,
                        "price": shop_item.price,
                        "quantity": shop_item.stock,
                        "item_id": shop_item.item_id
                    })

            player_items = []
            for slot in player_inventory.slots:
                if slot is None:
                    continue
                item_def = item_manager.get_item(slot.item_id)
                display_name = item_def.display_name if item_def else slot.item_id
                sell_price = 0
                if shop_inventory and item_def:
                    sell_price = shop_inventory.calculate_sell_price(item_def)
                player_items.append({
                    "name": display_name,
                    "sell_price": sell_price,
                    "quantity": slot.quantity,
                    "item_id": slot.item_id
                })

            shop_ui.draw(
                game_surface,
                npc_items=npc_items,
                player_items=player_items,
                player_currency=player_inventory.currency,
                npc_currency=npc_currency
            )

        # Victory screen (if level complete)
        if level_complete:
            victory_screen.render(game_surface, level_manager.get_stats(), 1.0 / FPS)

        # Render menu overlay on game surface (if active)
        if menu_manager.has_menu():
            menu_manager.render(game_surface)

        # Update tutorial system
        tutorial_manager.update(1.0 / FPS)
        controls_hint.update(1.0 / FPS)

        # Handle tutorial input
        tutorial_manager.handle_input(keys)

        # Render tutorial system (on top of everything)
        tutorial_manager.render(game_surface)
        controls_hint.render(game_surface)

        # Apply hub brightness overlay (v0.7.0)
        if current_world_context == "hub":
            hub_brightness = story_manager.hub_state.brightness
            hub_effects.render_brightness_overlay(game_surface, hub_brightness)

        # Render cutscene overlay (v0.7.0 - on top of everything)
        if story_manager.is_cutscene_playing():
            cutscene_text = story_manager.get_cutscene_text()
            if cutscene_text:
                # Draw semi-transparent black overlay
                overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
                overlay.set_alpha(200)
                overlay.fill((0, 0, 0))
                game_surface.blit(overlay, (0, 0))

                # Draw cutscene text box (centered bottom third)
                text_box_height = 200
                text_box_rect = pygame.Rect(100, GAME_HEIGHT - text_box_height - 50, GAME_WIDTH - 200, text_box_height)
                pygame.draw.rect(game_surface, (20, 20, 30), text_box_rect)
                pygame.draw.rect(game_surface, (100, 100, 120), text_box_rect, 3)

                # Render text (word-wrapped)
                font = pygame.font.Font(None, 28)
                words = cutscene_text.split(' ')
                lines = []
                current_line = []
                max_width = text_box_rect.width - 40

                for word in words:
                    test_line = ' '.join(current_line + [word])
                    if font.size(test_line)[0] <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(' '.join(current_line))

                # Draw lines
                y_offset = text_box_rect.y + 20
                for line in lines:
                    text_surface = font.render(line, True, (220, 220, 230))
                    game_surface.blit(text_surface, (text_box_rect.x + 20, y_offset))
                    y_offset += 35

                # Draw skip hint
                skip_font = pygame.font.Font(None, 20)
                skip_text = skip_font.render("Press SPACE or ESC to skip", True, (150, 150, 160))
                game_surface.blit(skip_text, (GAME_WIDTH - 250, GAME_HEIGHT - 30))

        # Render moral choice UI (v0.7.0 - Final battle ending choice)
        if ending_manager.state == EndingState.CHOICE_PRESENTED:
            # Draw dark overlay
            overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
            overlay.set_alpha(220)
            overlay.fill((10, 10, 20))
            game_surface.blit(overlay, (0, 0))

            # Get choice data
            choice_data = ending_manager.present_choice()

            # Draw title
            title_font = pygame.font.Font(None, 48)
            title_text = title_font.render(choice_data["title"], True, (200, 200, 220))
            title_rect = title_text.get_rect(center=(GAME_WIDTH // 2, 100))
            game_surface.blit(title_text, title_rect)

            # Draw context text (word-wrapped)
            context_font = pygame.font.Font(None, 24)
            context_y = 180
            context_words = choice_data["context"].split(' ')
            lines = []
            current_line = []
            max_width = 800

            for word in context_words:
                test_line = ' '.join(current_line + [word])
                if context_font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))

            for line in lines:
                text_surface = context_font.render(line, True, (180, 180, 200))
                text_rect = text_surface.get_rect(center=(GAME_WIDTH // 2, context_y))
                game_surface.blit(text_surface, text_rect)
                context_y += 30

            # Draw choice buttons
            choice_y = context_y + 40
            button_width = 400
            button_height = 120
            button_spacing = 50

            for idx, choice in enumerate(choice_data["choices"]):
                button_x = GAME_WIDTH // 2 - button_width // 2
                button_y = choice_y + idx * (button_height + button_spacing)
                button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

                # Draw button background
                button_color = (60, 60, 80) if idx == 0 else (80, 60, 60)
                pygame.draw.rect(game_surface, button_color, button_rect)
                pygame.draw.rect(game_surface, (120, 120, 140), button_rect, 3)

                # Draw button label
                label_font = pygame.font.Font(None, 32)
                label_text = label_font.render(choice["label"], True, (220, 220, 240))
                label_rect = label_text.get_rect(center=(button_rect.centerx, button_rect.y + 30))
                game_surface.blit(label_text, label_rect)

                # Draw description
                desc_font = pygame.font.Font(None, 20)
                desc_lines = []
                desc_words = choice["description"].split(' ')
                desc_line = []
                for word in desc_words:
                    test = ' '.join(desc_line + [word])
                    if desc_font.size(test)[0] <= button_width - 40:
                        desc_line.append(word)
                    else:
                        if desc_line:
                            desc_lines.append(' '.join(desc_line))
                        desc_line = [word]
                if desc_line:
                    desc_lines.append(' '.join(desc_line))

                desc_y = button_rect.y + 55
                for desc_line_text in desc_lines[:3]:  # Max 3 lines
                    desc_surface = desc_font.render(desc_line_text, True, (160, 160, 180))
                    game_surface.blit(desc_surface, (button_rect.x + 20, desc_y))
                    desc_y += 20

                # Draw hint
                hint_font = pygame.font.Font(None, 18)
                hint_surface = hint_font.render(f"[Press {idx + 1}] {choice['outcome_hint']}", True, (120, 120, 140))
                game_surface.blit(hint_surface, (button_rect.x + 20, button_rect.bottom - 20))

            # Draw shared outcome
            shared_font = pygame.font.Font(None, 22)
            shared_text = shared_font.render(choice_data["shared_outcome"], True, (150, 150, 170))
            shared_rect = shared_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT - 50))
            game_surface.blit(shared_text, shared_rect)

        # Auto-save periodically
        persist_story_state()  # Update story state before auto-save (v0.7.0)
        save_manager.auto_save(time.time())

        # Present game surface to window with letterboxing
        if not headless:
            camera.present(screen)

            # Render developer console overlay (DEV build only)
            if dev_console:
                dev_console.render(screen)

            pygame.display.flip()
        clock_pygame.tick(FPS)

    # Final save on exit
    if save_manager.needs_save:
        persist_story_state()  # Save story state (v0.7.0)
        save_manager.save(force=True)
        print("[SAVE] Final save on exit")

    # Cleanup
    player.cleanup()

    # Auto-open logs folder for TESTING build on exit
    if build_config.auto_open_logs_on_exit:
        from utils.platform_utils import open_folder_in_explorer
        print("\n" + "="*60)
        print("TESTING BUILD - Opening replay and log directories...")
        print("="*60)

        # Open replays folder
        replays_folder = user_data_dir / 'replays'
        if replays_folder.exists():
            print(f"Opening replays: {replays_folder}")
            open_folder_in_explorer(replays_folder)

        # Open logs folder
        logs_folder = user_data_dir / 'logs'
        if logs_folder.exists():
            print(f"Opening logs: {logs_folder}")
            open_folder_in_explorer(logs_folder)

        print("\nPlease share these files with the development team!")
        print("="*60)

    pygame.quit()

    input_pipeline.finalize()

    print("\n[OK] Game exited cleanly")
    print("="*60)


if __name__ == "__main__":
    main()
