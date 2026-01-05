"""
Game Initialization Module

This module contains all initialization logic for Indie Ninja Adventures,
extracted from demo_game.py to reduce its size and improve modularity.

Functions:
- initialize_pygame(): Set up pygame and rendering systems
- create_core_systems(): Create EventBus, Logger, Clock, EntityManager
- create_game_managers(): Create all game-level managers (save, pickup, NPC, etc.)
- create_physics_and_collision(): Create physics, collision, and enemy systems
- create_camera_system(): Create camera with configuration
- create_player(): Create player entity with all mechanics
- create_combat_system(): Create combat mechanics and effects
"""

import json
import os
from typing import Any

import pygame

from config.build_config import get_build_config
from core import EntityManager, EntityType, EventBus, GameClock, GameLogger
from entities import HazardManager, PickupManager
from entities.companions import CompanionOrbs
from entities.enemy_manager import EnemyManager
from entities.npc import NPCManager
from entities.player import Player
from game.dialogue_system import DialogueManager
from game.game_state import GameState, GameStateManager
from game.hub_manager import HubManager
from game.inventory_system import Inventory, get_item_manager, initialize_item_manager
from game.level_manager import LevelManager
from game.objective_tracker import ObjectiveTracker
from game.portal_system import PortalManager
from game.story_manager import StoryManager
from game.trading_system import TradingManager
from mechanics.combat_mechanic import CombatMechanic
from rendering import HUDRenderer, ParticleSystem, SpriteManager
from rendering.hub_effects import HubEffectsRenderer
from rendering.npc_prompt import NPCIndicatorRenderer, NPCPromptRenderer
from rendering.objective_hud import ObjectiveHUDRenderer
from rendering.tile_loader import TileLoader
from systems import CollisionSystem, PhysicsSystem, SaveManager
from systems.camera_system import CameraConfig, CameraSystem
from ui import ControlsHintOverlay, MenuManager, TutorialManager
from ui.dialogue_ui import DialogueUI
from ui.inventory_ui import InventoryUI
from ui.mission_menu import MissionMenuUI
from ui.shop_ui import ShopUI

# Get build config instance
build_config = get_build_config()

# Display settings (virtual game resolution)
GAME_WIDTH = 1280
GAME_HEIGHT = 720

# Import event types for CameraEffectsHandler
from core.event_bus import CollisionEvent, VelocityChangeEvent


class CameraEffectsHandler:
    """Handles camera effects triggered by game events"""

    def __init__(self, camera: CameraSystem, event_bus: EventBus, player_id: int):
        self.camera = camera
        self.event_bus = event_bus
        self.player_id = player_id

        # Track previous state to detect transitions
        self.was_on_ground = False
        self.was_on_wall = False

        # Subscribe to events (Phase 4.1: with owner tracking)
        event_bus.subscribe(CollisionEvent, self._on_collision, owner=self)
        event_bus.subscribe(VelocityChangeEvent, self._on_velocity_change, owner=self)

    def _on_collision(self, event: CollisionEvent):
        """Handle collision events for camera effects"""
        if event.entity_id != self.player_id:
            return

        # Screen shake on ground landing (only if falling)
        if event.collision_type == "ground" and not self.was_on_ground:
            # Shake intensity based on impact (placeholder - could use fall speed)
            self.camera.add_screen_shake(intensity=3.0, duration=0.1)
            self.was_on_ground = True
        elif event.collision_type != "ground":
            self.was_on_ground = False

    def _on_velocity_change(self, event: VelocityChangeEvent):
        """Handle velocity changes for camera effects"""
        if event.entity_id != self.player_id:
            return

        # Camera pan on wall jump (push camera away from wall)
        if event.reason == "wall_jump":
            # Determine wall direction from velocity change
            if event.new_vx > 0:  # Jumping right
                self.camera.add_camera_pan(offset_x=30, offset_y=0)
            elif event.new_vx < 0:  # Jumping left
                self.camera.add_camera_pan(offset_x=-30, offset_y=0)

    def cleanup(self):
        """Cleanup event subscriptions (Phase 4.1 - prevent memory leaks)"""
        self.event_bus.unsubscribe_all(self)


def get_recommended_window_size() -> tuple[int, int]:
    """Get recommended window size based on display."""
    display_info = pygame.display.Info()
    screen_width, screen_height = display_info.current_w, display_info.current_h

    # Target aspect ratio (16:9 for GAME_WIDTH:GAME_HEIGHT)
    target_aspect = GAME_WIDTH / GAME_HEIGHT

    # Try to use 80% of screen height
    window_height = int(screen_height * 0.8)
    window_width = int(window_height * target_aspect)

    # If too wide, constrain by width instead
    if window_width > screen_width * 0.9:
        window_width = int(screen_width * 0.9)
        window_height = int(window_width / target_aspect)

    return window_width, window_height


def initialize_pygame(headless: bool = False) -> tuple[pygame.Surface, pygame.time.Clock, int, int]:
    """
    Initialize pygame and create display surface.

    Args:
        headless: If True, use SDL dummy driver for headless mode

    Returns:
        Tuple of (screen, clock, window_width, window_height)
    """
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()

    if headless:
        window_width, window_height = GAME_WIDTH, GAME_HEIGHT
        screen = pygame.Surface((window_width, window_height))
        clock_pygame = pygame.time.Clock()
    else:
        window_width, window_height = get_recommended_window_size()
        screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Vain Asher Gaming's: Indie Ninja Adventures - Responsive Demo")
        clock_pygame = pygame.time.Clock()

    return screen, clock_pygame, window_width, window_height


def create_rendering_systems() -> dict[str, Any]:
    """
    Create all rendering-related systems.

    Returns:
        Dict with keys: sprite_manager, tile_loader, particles, hud, inventory_ui,
                       npc_prompt_renderer, npc_indicator_renderer
    """
    return {
        "sprite_manager": SpriteManager(),
        "tile_loader": TileLoader(),
        "particles": ParticleSystem(),
        "hud": HUDRenderer(),
        "inventory_ui": InventoryUI(),
        "npc_prompt_renderer": NPCPromptRenderer(),
        "npc_indicator_renderer": NPCIndicatorRenderer(),
    }


def create_core_systems(logger_name: str = "game") -> dict[str, Any]:
    """
    Create core game systems (EventBus, Logger, Clock, EntityManager).

    Args:
        logger_name: Name for the game logger

    Returns:
        Dict with keys: bus, logger, game_clock, entity_manager
    """
    bus = EventBus()
    logger = GameLogger()
    game_clock = GameClock(bus, logger=logger.get_logger("clock"))
    entity_manager = EntityManager(bus, logger.get_logger("entity_manager"))

    return {
        "bus": bus,
        "logger": logger,
        "game_clock": game_clock,
        "entity_manager": entity_manager,
    }


def create_game_managers(
    bus: EventBus,
    logger: GameLogger,
    current_seed: int | None,
    base_hub_seed: int,
) -> dict[str, Any]:
    """
    Create all game-level managers (save, pickup, NPC, dialogue, etc.).

    Args:
        bus: EventBus instance
        logger: GameLogger instance
        current_seed: Current world seed (optional)
        base_hub_seed: Base hub seed for campaign

    Returns:
        Dict with all manager instances and related data
    """
    # Initialize save system early (needed for campaign data/inventory)
    save_manager = SaveManager()
    save_manager.load()  # Load existing save or create new

    # Initialize managers
    pickup_manager = PickupManager(bus)
    hazard_manager = HazardManager(bus)
    npc_manager = NPCManager(bus)

    # Initialize tile physics system
    from systems.tile_physics import TilePhysicsManager

    tile_physics_manager = TilePhysicsManager()

    # Initialize dialogue system
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
        print("[DEV BUILD] Hot reload enabled")

    # Initialize UI systems
    mission_menu_ui = MissionMenuUI()
    shop_ui = ShopUI()
    trading_manager = TradingManager(bus, current_seed if current_seed else 0)
    menu_manager = MenuManager(GAME_WIDTH, GAME_HEIGHT)

    # Initialize item system
    initialize_item_manager()
    item_manager = get_item_manager()
    try:
        with open("data/items.json", encoding="utf-8") as f:
            items_data = json.load(f)
            item_manager.load_from_dict(items_data)
    except FileNotFoundError:
        print("[WARNING] items.json not found; shop items will be empty")

    # Load or create player inventory
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

    # Hub/portal systems
    hub_manager = HubManager(base_hub_seed)
    portal_manager = PortalManager(bus)

    # Objective tracking
    objective_tracker = ObjectiveTracker(bus)
    objective_hud_renderer = ObjectiveHUDRenderer()

    # Game state manager
    game_state_manager = GameStateManager(initial_state=GameState.PLAYING)

    # Story system
    if (
        save_manager
        and save_manager.data
        and save_manager.data.campaign
        and save_manager.data.campaign.story_state
    ):
        story_manager = StoryManager.from_dict(save_manager.data.campaign.story_state)
        print(f"[STORY] Loaded story state: Act {story_manager.current_act}")
    else:
        story_manager = StoryManager()
        print("[STORY] No saved story state, starting fresh")

    story_manager.event_bus = bus
    companion_orbs = CompanionOrbs()
    hub_effects = HubEffectsRenderer()
    ending_manager = story_manager.ending_manager

    print("[STORY] Story systems initialized")

    # Tutorial system
    first_run = not save_manager.data.player_progress.tutorials_seen
    tutorial_manager = TutorialManager(GAME_WIDTH, GAME_HEIGHT, save_manager)
    controls_hint = ControlsHintOverlay(
        GAME_WIDTH, GAME_HEIGHT, start_visible=first_run, auto_fade=first_run
    )

    if first_run:
        tutorial_manager.trigger_tutorial("welcome")

    return {
        "save_manager": save_manager,
        "pickup_manager": pickup_manager,
        "hazard_manager": hazard_manager,
        "tile_physics_manager": tile_physics_manager,
        "npc_manager": npc_manager,
        "dialogue_manager": dialogue_manager,
        "dialogue_ui": dialogue_ui,
        "dev_console": dev_console,
        "hot_reload": hot_reload,
        "mission_menu_ui": mission_menu_ui,
        "shop_ui": shop_ui,
        "trading_manager": trading_manager,
        "menu_manager": menu_manager,
        "item_manager": item_manager,
        "player_inventory": player_inventory,
        "campaign_data": campaign_data,
        "hub_manager": hub_manager,
        "portal_manager": portal_manager,
        "objective_tracker": objective_tracker,
        "objective_hud_renderer": objective_hud_renderer,
        "game_state_manager": game_state_manager,
        "story_manager": story_manager,
        "companion_orbs": companion_orbs,
        "hub_effects": hub_effects,
        "ending_manager": ending_manager,
        "tutorial_manager": tutorial_manager,
        "controls_hint": controls_hint,
    }


def create_physics_and_collision(
    bus: EventBus, entity_manager: EntityManager, logger: GameLogger, current_seed: int
) -> dict[str, Any]:
    """
    Create physics, collision, and enemy systems.

    Args:
        bus: EventBus instance
        entity_manager: EntityManager instance
        logger: GameLogger instance
        current_seed: Current world seed

    Returns:
        Dict with keys: physics_system, collision_system, enemy_manager
    """
    physics_system = PhysicsSystem(bus, entity_manager, logger.get_logger("physics"))
    collision_system = CollisionSystem(bus, entity_manager, logger.get_logger("collision"))
    enemy_manager = EnemyManager(bus, current_seed if current_seed else 0)

    return {
        "physics_system": physics_system,
        "collision_system": collision_system,
        "enemy_manager": enemy_manager,
    }


def create_camera_system(window_width: int, window_height: int) -> CameraSystem:
    """
    Create camera system with default configuration.

    Args:
        window_width: Window width in pixels
        window_height: Window height in pixels

    Returns:
        Configured CameraSystem instance
    """
    camera_config = CameraConfig(
        game_width=GAME_WIDTH,
        game_height=GAME_HEIGHT,
        follow_speed=0.1,
        deadzone_width=200,
        deadzone_height=150,
    )
    camera = CameraSystem(camera_config)
    camera.handle_resize(window_width, window_height)
    return camera


def create_player(
    spawn_x: float,
    spawn_y: float,
    bus: EventBus,
    logger: GameLogger,
    collision_system: CollisionSystem,
    entity_manager: EntityManager,
    enemy_manager: EnemyManager,
    hazard_manager: HazardManager,
    unlocked_abilities: set[str] | None = None,
) -> tuple[Player, Any]:
    """
    Create player entity with progression-based mechanics.

    Args:
        spawn_x: Player spawn X position
        spawn_y: Player spawn Y position
        bus: EventBus instance
        logger: GameLogger instance
        collision_system: CollisionSystem instance
        entity_manager: EntityManager instance
        enemy_manager: EnemyManager instance
        hazard_manager: HazardManager instance
        unlocked_abilities: Set of unlocked ability names (defaults to starter abilities)

    Returns:
        Tuple of (Player instance, player_entity from EntityManager, level_manager)
    """
    level_manager = LevelManager(bus)

    # Default to starter abilities if none provided
    if unlocked_abilities is None:
        unlocked_abilities = {"basic_movement", "jump"}

    # Build feature_flags dynamically from unlocked abilities
    feature_flags = {
        "double_jump": "double_jump" in unlocked_abilities,
        "wall_jump": "wall_jump" in unlocked_abilities,
        "dash": "dash" in unlocked_abilities,
        "crouch": "crouch" in unlocked_abilities,
        "shuriken": "shuriken" in unlocked_abilities,
        "teleport": "teleport" in unlocked_abilities,
        "ninjutsu": "ninjutsu" in unlocked_abilities,
    }

    player = Player(
        player_id=0,
        spawn_x=spawn_x,
        spawn_y=spawn_y,
        event_bus=bus,
        logger_factory=logger,
        collision_system=collision_system,
        feature_flags=feature_flags,
    )

    # Wire mechanic contexts
    player.shuriken.set_context(enemy_manager=enemy_manager)
    player.teleport.set_collision_system(collision_system)
    player.ninjutsu.set_hazard_manager(hazard_manager)

    # Add player entity to entity manager so PhysicsSystem can process it
    player_entity = entity_manager.create_entity(
        entity_type=EntityType.PLAYER, physics=player.state.physics
    )

    return player, player_entity, level_manager


def create_combat_system(
    player_entity_id: int, bus: EventBus, logger: GameLogger, camera: CameraSystem
) -> tuple[CombatMechanic, CameraEffectsHandler]:
    """
    Create combat mechanic and camera effects handler.

    Args:
        player_entity_id: Player entity ID from EntityManager
        bus: EventBus instance
        logger: GameLogger instance
        camera: CameraSystem instance

    Returns:
        Tuple of (CombatMechanic, CameraEffectsHandler)
    """
    combat_mechanic = CombatMechanic(player_entity_id, bus, logger.get_logger("combat"))
    camera_effects = CameraEffectsHandler(camera, bus, player_entity_id)

    return combat_mechanic, camera_effects


def apply_shuriken_capacity_bonus(player: Player, player_inventory: Inventory, item_manager):
    """
    Set shuriken max capacity based on equipped armor.

    Args:
        player: Player instance
        player_inventory: Player's inventory
        item_manager: ItemManager instance
    """
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
