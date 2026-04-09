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

import argparse
import json
import math
import os
import random
import sys
import time

# Add parent dir to path
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).parent))

from config.physics_constants import (
    TILE_SIZE as CONFIG_TILE_SIZE,
)
from config.settings import GameSettings as RuntimeSettings
from core.event_bus import TickEvent
from utils.resource_path import get_resource_path

# Phase 4-7: New system imports
from entities.npc import (
    DialogueStartEvent,
    MissionMenuOpenEvent,
)
from entities.npc import (
    ShopOpenEvent as NPCShopOpenEvent,
)
from game import GameState

# Phase 3: Story System (v0.7.0 - The Hollowed Ninja)
from game.ending_manager import EndingChoice, EndingState
from game.game_helpers import (
    get_arcade_seed,
    persist_player_inventory,
    persist_story_state,
    update_replay_metadata,
)

# Phase 3 Refactoring: Extracted modules (v0.7.0)
from game.game_initialization import (
    apply_shuriken_capacity_bonus,
    create_camera_system,
    create_combat_system,
    create_core_systems,
    create_game_managers,
    create_physics_and_collision,
    create_player,
    create_rendering_systems,
    initialize_audio,
    initialize_pygame,
)
from game.hub_manager import HubManager
from game.inventory_system import ItemType
from game.level_factory import (
    build_objective_location_targets,
)
from game.mission_registry import ObjectiveType, get_mission_registry
from game.objective_tracker import (
    ItemCollectedEvent,
    PlayerPositionUpdateEvent,
    get_objective_display_text,
)
from game.play_mode import PlayMode
from game.portal_system import PortalTravelEvent, PortalType, draw_portal
from game.trading_system import ShopTier
from game.world_builder import regenerate_world_state
from entities.player_render_state import compute_anim_state
from network import InputPipeline
from rendering import (
    VictoryScreen,
    get_current_room_coords,
    render_hazards,
    render_pickups,
)
from rendering.animation_system import AnimationRegistry
from rendering.enemy_renderer import draw_enemy, draw_npc as draw_npc_char
from rendering.sprite_manager import SpriteFrame
from utils.frame_profiler import FrameProfiler
from systems import (
    CameraMode,
    SaveManager,
)
from systems.seed_hierarchy import SeedDerivation
from ui import (
    LandingMenu,
    MainMenu,
    MenuAction,
    PauseMenu,
    SettingsMenu,
)
from ui.menu_system import DebugAbilityMenu

# Phase 2: Dialogue System
from ui.mission_menu import MissionDisplay, MissionStatus
from ui.mode_selection_menu import GameModeSelectionMenu, MissionSelectorMenu

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
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle - use executable directory
        project_root = Path(sys.executable).parent
    else:
        # Running as script - use script directory
        project_root = Path(__file__).parent

    return project_root / "user_data"


def ensure_user_data_dirs():
    """Ensure all user_data subdirectories exist"""
    user_data = get_user_data_dir()
    print(f"[USER DATA] Creating directories at: {user_data}")
    (user_data / "logs").mkdir(parents=True, exist_ok=True)
    (user_data / "replays").mkdir(parents=True, exist_ok=True)
    (user_data / "saves").mkdir(parents=True, exist_ok=True)
    (user_data / "settings").mkdir(parents=True, exist_ok=True)
    return user_data


# CameraEffectsHandler has been moved to game/game_initialization.py


def get_player_render_state(player):
    """Derive a simple render state string for animation selection."""
    return compute_anim_state(player)


# ==============================================================================
# EXTRACTED FUNCTIONS (Phase 3 Refactoring)
# ==============================================================================
# The following functions have been moved to modular files for better
# organization and maintainability:
#
# - create_simple_level()              → game/level_factory.py
# - create_procedural_level()          → game/level_factory.py
# - build_objective_location_targets() → game/level_factory.py
# - spawn_objective_collectibles()     → game/level_factory.py
# - regenerate_world_state()           → game/world_builder.py
#
# Import them at the top of this file to use them.
# ==============================================================================


def main():
    """Main game loop"""
    # Ensure user_data directories exist
    user_data_dir = ensure_user_data_dirs()
    runtime_settings = RuntimeSettings(user_data_dir=user_data_dir)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Vain Asher Gaming's: Indie Ninja Adventures Demo")

    # Build mode selection (for distribution builds)
    parser.add_argument(
        "--build-mode",
        type=str,
        default=None,
        choices=["production", "testing", "dev"],
        help="Build configuration mode (set by launcher scripts)",
    )

    # Game mode selection (NEW in v0.6.0)
    parser.add_argument(
        "--mode",
        type=str,
        default="arcade",
        choices=["arcade", "campaign", "playtest"],
        help="Game mode: arcade (infinite procedural), campaign (mission-based), playtest (single mission)",
    )
    parser.add_argument(
        "--mission", type=str, help="Mission ID for campaign/playtest mode (e.g., forest_1)"
    )

    # Procedural generation options (kept for compatibility but ignored)
    parser.add_argument(
        "--procedural", action="store_true", help="(ignored) Procedural is always enabled"
    )
    parser.add_argument("--seed", type=int, default=None, help="Seed for procedural generation")
    parser.add_argument(
        "--shape",
        type=str,
        default="blob",
        choices=["snake", "branchy", "blob", "spiral", "tree", "grid"],
        help="World shape style (ignored; hubs choose their own)",
    )
    parser.add_argument(
        "--rooms",
        type=int,
        default=10,
        help="Number of rooms to generate (ignored; hubs choose their own)",
    )

    # Technical options
    parser.add_argument(
        "--legacy-client",
        action="store_true",
        help="Explicitly run the Python/Pygame client (deprecated; Java client is now primary). "
        "Accepted for backwards-compatibility — has no effect on behaviour.",
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run without opening a window (SDL dummy driver)"
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable frame profiler (writes docs/perf_baseline.csv on exit)",
    )
    parser.add_argument(
        "--record", type=str, help="Record input to replay JSON file (saves to user_data/replays/)"
    )
    parser.add_argument(
        "--replay", type=str, help="Replay input from JSON file (looks in user_data/replays/)"
    )
    parser.add_argument(
        "--show-replay", action="store_true", help="Replay with window instead of headless"
    )
    parser.add_argument(
        "--log-input",
        nargs="?",
        const="input_commands.log",
        help="Log per-frame input commands to JSONL (default: user_data/logs/input_commands.log)",
    )
    parser.add_argument(
        "--host",
        type=int,
        metavar="PORT",
        help="Start as multiplayer server on this port (e.g. --host 7777)",
    )
    parser.add_argument(
        "--connect",
        type=str,
        metavar="HOST:PORT",
        help="Connect to a multiplayer server (e.g. --connect 192.168.1.5:7777)",
    )
    parser.add_argument(
        "--max-players",
        type=int,
        default=4,
        metavar="N",
        choices=range(1, 5),
        help="Maximum players when hosting (1–4, default 4)",
    )
    args = parser.parse_args()

    if getattr(args, "legacy_client", False):
        print(
            "[launcher] Note: --legacy-client flag detected. "
            "The Java/libGDX client is now the primary client. "
            "This Python/Pygame client will be removed in a future release.",
            file=sys.stderr,
        )

    if args.host and args.connect:
        print("Cannot use --host and --connect at the same time.")
        sys.exit(1)

    if args.record and args.replay:
        print("Cannot use --record and --replay at the same time.")
        sys.exit(1)

    use_procedural = True  # Always procedural (no static demo room)
    current_seed = args.seed
    world_shape = "blob"
    num_rooms = 8
    headless = args.headless
    show_replay = args.show_replay
    enable_profile = getattr(args, "profile", False)

    # Always drive startup via menu → hub generation; skip static demo path
    # (menu_driven_startup flag removed - no longer needed)

    # ============================================================
    # Play Mode Manager Setup (v0.6.0)
    # ============================================================
    # play_mode_manager = PlayModeManager()  # Removed - not yet used
    mission_definition = None
    current_play_mode = PlayMode.ARCADE  # Default
    objective_hud_renderer = None  # Only used in campaign/playtest modes
    objective_tracker = None  # Only used in campaign/playtest modes

    # Default play mode (menu selection can override)
    current_play_mode = PlayMode.CAMPAIGN
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
        os.environ["BUILD_MODE"] = args.build_mode.upper()
    build_config = get_build_config()

    if build_config.auto_record and not args.replay and not args.record:
        auto_filename = build_config.get_auto_record_filename()
        if auto_filename:
            args.record = auto_filename
            print(f"[TESTING BUILD] Auto-recording session to: {auto_filename}")

    if args.record:
        # If just a filename, save to user_data/replays/
        record_file = args.record if args.record.endswith(".json") else f"{args.record}.json"
        if not os.path.isabs(record_file):
            record_path = str(user_data_dir / "replays" / record_file)
        else:
            record_path = record_file
        log_commands = True  # auto-log when recording
        # Default log filename for recordings
        if not log_input_path:
            log_input_path = str(user_data_dir / "logs" / "input_commands.record.log")

    replay_world_seed = None
    replay_hub_id = None
    replay_world_context = None
    replay_mission_id = None

    if args.replay:
        # If just a filename, look in user_data/replays/
        replay_file = args.replay if args.replay.endswith(".json") else f"{args.replay}.json"
        if not os.path.isabs(replay_file):
            replay_path = str(user_data_dir / "replays" / replay_file)
        else:
            replay_path = replay_file
        # If logging enabled later, prefer a replay-specific default name
        if not log_input_path and args.log_input is None:
            log_input_path = str(user_data_dir / "logs" / "input_commands.replay.log")
        log_commands = True  # capture replay commands for debugging by default

    if args.log_input:
        log_commands = True
        log_file = args.log_input
        if not os.path.isabs(log_file):
            log_input_path = str(user_data_dir / "logs" / log_file)
        else:
            log_input_path = log_file

    frame_idx = 0

    if replay_path:
        with open(replay_path, encoding="utf-8") as f:
            replay_data = json.load(f)
        use_procedural = replay_data.get("procedural", use_procedural)
        # Prefer explicit world_seed/current_seed metadata for deterministic replays
        replay_world_seed = replay_data.get("world_seed", replay_data.get("seed"))
        replay_hub_id = replay_data.get("hub_id")
        replay_world_context = replay_data.get("world_context")
        _replay_mission_id = replay_data.get("mission_id")  # Unused for now
        if replay_world_seed is not None:
            current_seed = replay_world_seed
        else:
            current_seed = replay_data.get("seed", current_seed)
        if not show_replay:
            headless = True  # default to headless during playback unless overridden

        print(f"[REPLAY] Loaded commands from {replay_path}")

    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    print("\n" + "=" * 60)
    print("Vain Asher Gaming's: Indie Ninja Adventures - Modular Architecture Demo")
    print("=" * 60)
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
    print("=" * 60)

    # Initialize pygame and rendering systems
    screen, clock_pygame, window_width, window_height = initialize_pygame(headless=headless)

    # Initialize audio (silent fallback if mixer unavailable or assets missing)
    audio_manager = initialize_audio(sfx_volume=float(runtime_settings.get("volume_sfx", 0.8)))

    rendering_systems = create_rendering_systems()
    sprite_manager = rendering_systems["sprite_manager"]
    tile_loader = rendering_systems["tile_loader"]
    particles = rendering_systems["particles"]
    hud = rendering_systems["hud"]
    inventory_ui = rendering_systems["inventory_ui"]
    npc_prompt_renderer = rendering_systems["npc_prompt_renderer"]
    npc_indicator_renderer = rendering_systems["npc_indicator_renderer"]

    # Load shuriken sprite (projectile visual)
    shuriken_base = None
    shuriken_path = get_resource_path("assets", "sprites", "projectiles", "shuriken.png")
    if shuriken_path.exists():
        shuriken_base = pygame.image.load(str(shuriken_path)).convert_alpha()
    else:
        print(f"[WARN] Missing shuriken sprite: {shuriken_path}")

    # Landing background (used for launch/menu screens)
    landing_bg = None
    landing_bg_path = get_resource_path("assets", "splash", "landing.png")
    if landing_bg_path.exists():
        landing_bg = pygame.image.load(str(landing_bg_path)).convert()

    # Initialize core systems
    core_systems = create_core_systems(user_data_dir=user_data_dir)
    bus = core_systems["bus"]
    logger = core_systems["logger"]
    game_clock = core_systems["game_clock"]
    entity_manager = core_systems["entity_manager"]

    # Calculate base_hub_seed early for manager initialization
    # (needed before calling create_game_managers)
    save_manager_temp = SaveManager()
    save_manager_temp.load()
    campaign_data_temp = (
        save_manager_temp.data.campaign if save_manager_temp and save_manager_temp.data else None
    )

    # Normalize campaign world seed (treat 0 as unset)
    if campaign_data_temp and getattr(campaign_data_temp, "world_seed", 0) == 0:
        campaign_data_temp.world_seed = (
            current_seed if current_seed is not None else random.randint(1, 999999)
        )
        save_manager_temp.mark_dirty()

    if replay_world_seed is not None:
        base_hub_seed = replay_world_seed
    else:
        base_hub_seed = (
            campaign_data_temp.world_seed
            if campaign_data_temp and getattr(campaign_data_temp, "world_seed", 0) != 0
            else (current_seed if current_seed is not None else random.randint(1, 999999))
        )

    # Initialize all game managers using extracted function
    game_managers = create_game_managers(
        bus, logger, current_seed, base_hub_seed, user_data_dir=user_data_dir
    )
    save_manager = game_managers["save_manager"]
    pickup_manager = game_managers["pickup_manager"]
    hazard_manager = game_managers["hazard_manager"]
    npc_manager = game_managers["npc_manager"]
    dialogue_manager = game_managers["dialogue_manager"]
    dialogue_ui = game_managers["dialogue_ui"]
    dev_console = game_managers["dev_console"]
    hot_reload = game_managers["hot_reload"]
    mission_menu_ui = game_managers["mission_menu_ui"]
    shop_ui = game_managers["shop_ui"]
    trading_manager = game_managers["trading_manager"]
    menu_manager = game_managers["menu_manager"]
    item_manager = game_managers["item_manager"]
    player_inventory = game_managers["player_inventory"]
    campaign_data = game_managers["campaign_data"]
    hub_manager = game_managers["hub_manager"]
    portal_manager = game_managers["portal_manager"]
    gate_manager = game_managers["gate_manager"]
    objective_tracker = game_managers["objective_tracker"]
    objective_hud_renderer = game_managers["objective_hud_renderer"]
    game_state_manager = game_managers["game_state_manager"]
    story_manager = game_managers["story_manager"]
    companion_orbs = game_managers["companion_orbs"]
    hub_effects = game_managers["hub_effects"]
    ending_manager = game_managers["ending_manager"]
    tutorial_manager = game_managers["tutorial_manager"]
    controls_hint = game_managers["controls_hint"]

    # Additional variables needed in main loop
    active_mission_pool: list[str] = []
    active_shop_npc_id = None
    current_hub_id = replay_hub_id or (
        campaign_data.current_hub_id
        if campaign_data and campaign_data.current_hub_id
        else "central_hub"
    )
    current_world_context = replay_world_context or "hub"  # hub | mission | arcade
    show_minimap = True
    show_full_map = False
    show_debug_overlay = build_config.debug_overlay_default
    arcade_depth = 0
    arcade_rooms = 8

    # Local wrapper functions for game helpers (definitions in game/game_helpers.py)
    def persist_player_inventory_wrapper():
        persist_player_inventory(save_manager, player_inventory)

    def persist_story_state_wrapper():
        persist_story_state(save_manager, story_manager)

    # Track last key states for dialogue input (to detect key press, not hold)
    prev_key_state = dict.fromkeys(
        [
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_w,
            pygame.K_a,
            pygame.K_s,
            pygame.K_d,
            pygame.K_SPACE,
            pygame.K_LSHIFT,
            pygame.K_RSHIFT,
            pygame.K_p,
            pygame.K_c,
            pygame.K_ESCAPE,
            pygame.K_e,
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_j,
            pygame.K_k,
            pygame.K_f,
            pygame.K_l,
            pygame.K_q,
            pygame.K_TAB,
            pygame.K_m,
            pygame.K_r,
            pygame.K_i,
            pygame.K_F3,
            pygame.K_h,
            pygame.K_LALT,
            pygame.K_RALT,
        ],
        False,
    )

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

            missions_to_show.append(
                MissionDisplay(
                    mission_id=mission_def.mission_id,
                    mission_name=mission_def.mission_name,
                    region=mission_def.region,
                    status=status,
                    difficulty=mission_def.difficulty,
                    objectives=objectives,
                    requirements=requirements,
                    rewards=rewards,
                    best_time=best_times.get(mission_def.mission_id),
                )
            )

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
                    persist_player_inventory_wrapper()
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
                    persist_player_inventory_wrapper()
                else:
                    print(f"[SHOP] Could not sell {item_id}")
            return

    # Dynamic platform state (moving/falling platforms)
    static_platforms: list[pygame.Rect] = []
    dynamic_platforms: list[dict] = []
    platform_colliders: list[pygame.Rect] = []
    liquid_tiles: list[tuple] = (
        []
    )  # [(world_x, world_y, "lava"|"water"), ...]  — built at level load

    MOVING_PLATFORM_MAX_SCAN = 8
    MOVING_PLATFORM_SPEED_RANGE = (30.0, 70.0)  # pixels per second
    FALLING_PLATFORM_TRIGGER_DELAY = 0.35
    FALLING_PLATFORM_RESPAWN_DELAY = 2.5
    FALLING_PLATFORM_DROP_DISTANCE = 32 * 12
    FALLING_PLATFORM_GRAVITY = 1800.0
    FALLING_PLATFORM_MAX_SPEED = 800.0
    PLATFORM_CARRY_TOLERANCE = 2

    LAVA_DAMAGE_INTERVAL = 1.0
    POISON_DAMAGE_INTERVAL = 1.6
    WATER_SPEED_MULT = 0.65
    WATER_ACCEL_MULT = 0.7
    WATER_DRAG_X = 0.85
    WATER_DRAG_Y = 0.9
    WATER_MAX_FALL_SPEED = 6.0

    lava_damage_timer = 0.0
    poison_damage_timer = 0.0

    def _entity_on_platform(
        physics, platform_rect, tolerance: int = PLATFORM_CARRY_TOLERANCE
    ) -> bool:
        if not physics or not physics.on_ground:
            return False
        rect = pygame.Rect(int(physics.x), int(physics.y), physics.width, physics.height)
        if rect.right <= platform_rect.left or rect.left >= platform_rect.right:
            return False
        gap = platform_rect.top - rect.bottom
        return -1 <= gap <= tolerance

    def _scan_free_tiles(tilemap, tx: int, ty: int, step: int, max_scan: int, free_tiles: set):
        width = len(tilemap[0]) if tilemap else 0
        count = 0
        x = tx + step
        while 0 <= x < width and count < max_scan:
            if tilemap[ty][x] not in free_tiles:
                break
            count += 1
            x += step
        return count

    def refresh_platform_state():
        nonlocal static_platforms, dynamic_platforms, platform_colliders, platforms, liquid_tiles
        static_platforms = []
        dynamic_platforms = []
        platform_colliders = []
        liquid_tiles = []

        if not megamap or not getattr(megamap, "tilemap", None):
            static_platforms = platforms
            dynamic_platforms = []
            platform_colliders = platforms
            if collision_system:
                collision_system.update_platforms(platform_colliders)
            return

        from systems.room_generation import (
            TILE_EMPTY,
            TILE_LAVA,
            TILE_PLATFORM,
            TILE_PLATFORM_FALLING,
            TILE_PLATFORM_MOVING,
            TILE_WATER,
        )

        tilemap = megamap.tilemap
        height = len(tilemap)
        width = len(tilemap[0]) if height > 0 else 0
        free_tiles = {TILE_EMPTY, TILE_LAVA, TILE_WATER}
        seed_base = current_seed if current_seed is not None else 0

        for ty in range(height):
            row = tilemap[ty]
            for tx in range(width):
                tile_id = row[tx]
                world_x = tx * 32
                world_y = ty * 32
                # Cache liquid tiles so the render loop doesn't re-scan the grid every frame
                if tile_id == TILE_LAVA:
                    liquid_tiles.append((world_x, world_y, "lava"))
                elif tile_id == TILE_WATER:
                    liquid_tiles.append((world_x, world_y, "water"))
                if tile_id == TILE_PLATFORM:
                    static_platforms.append(pygame.Rect(world_x, world_y, 32, 32))
                elif tile_id == TILE_PLATFORM_FALLING:
                    rect = pygame.Rect(world_x, world_y, 32, 32)
                    dynamic_platforms.append(
                        {
                            "id": f"plat_{tx}_{ty}",
                            "type": "falling",
                            "rect": rect,
                            "origin_x": world_x,
                            "origin_y": world_y,
                            "pos_x": float(world_x),
                            "pos_y": float(world_y),
                            "state": "idle",
                            "timer": 0.0,
                            "vy": 0.0,
                            "active": True,
                            "visible": True,
                        }
                    )
                elif tile_id == TILE_PLATFORM_MOVING:
                    rect = pygame.Rect(world_x, world_y, 32, 32)
                    platform_seed = seed_base ^ (tx * 73856093) ^ (ty * 19349663)
                    rng = random.Random(platform_seed)
                    left_free = _scan_free_tiles(
                        tilemap, tx, ty, -1, MOVING_PLATFORM_MAX_SCAN, free_tiles
                    )
                    right_free = _scan_free_tiles(
                        tilemap, tx, ty, 1, MOVING_PLATFORM_MAX_SCAN, free_tiles
                    )
                    span_left = (
                        min(left_free, rng.randint(1, min(3, left_free))) if left_free > 0 else 0
                    )
                    span_right = (
                        min(right_free, rng.randint(1, min(3, right_free))) if right_free > 0 else 0
                    )
                    min_x = world_x - span_left * 32
                    max_x = world_x + span_right * 32
                    speed = rng.uniform(*MOVING_PLATFORM_SPEED_RANGE) if min_x != max_x else 0.0
                    dynamic_platforms.append(
                        {
                            "id": f"plat_{tx}_{ty}",
                            "type": "moving",
                            "rect": rect,
                            "origin_x": world_x,
                            "origin_y": world_y,
                            "pos_x": float(world_x),
                            "pos_y": float(world_y),
                            "min_x": min_x,
                            "max_x": max_x,
                            "speed": speed,
                            "dir": rng.choice([-1, 1]),
                            "active": True,
                            "visible": True,
                        }
                    )

        platforms = static_platforms + [p["rect"] for p in dynamic_platforms]
        platform_colliders = static_platforms + [
            p["rect"] for p in dynamic_platforms if p["active"]
        ]
        if collision_system:
            collision_system.update_platforms(platform_colliders)

    # ── Zone transition helper (multiplayer) ──────────────────────────────────

    def _apply_world_transition(payload: dict) -> None:
        """
        Apply a WORLD_TRANSITION payload received from the server.

        Called from the main multiplayer game loop when poll_transition()
        returns a payload.  Rebuilds the world from the server's parameters
        so the local simulation matches the authoritative zone state.
        """
        nonlocal current_hub_id, current_seed, tiles, platforms, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap, current_world_context
        _new_hub_id = payload.get("hub_id", "")
        if not _new_hub_id:
            return
        _sv_seed = payload.get("seed", current_seed)
        _sv_shape = payload.get("shape", "blob")
        _sv_rooms = int(payload.get("rooms", 8))
        _sv_world_seed = payload.get("world_seed")
        if _sv_world_seed is not None:
            hub_manager.world_seed = int(_sv_world_seed)
        _sv_spawn_x = payload.get("spawn_x")
        _sv_spawn_y = payload.get("spawn_y")
        (
            tiles,
            platforms,
            current_seed,
            spawn_x,
            spawn_y,
            exit_x,
            exit_y,
            world,
            megamap,
            minimap,
        ) = regenerate_world_state(
            seed=_sv_seed,
            shape=_sv_shape,
            rooms=_sv_rooms,
            hub_id=_new_hub_id,
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
        )
        if _sv_spawn_x is not None:
            spawn_x = float(_sv_spawn_x)
            player.state.physics.x = spawn_x
        if _sv_spawn_y is not None:
            spawn_y = float(_sv_spawn_y)
            player.state.physics.y = spawn_y
        refresh_platform_state()
        current_hub_id = _new_hub_id
        current_world_context = "hub"
        game_state_manager.transition_to(GameState.PLAYING)
        print(f"[NET] Zone transition applied: hub_id={_new_hub_id}")

    # Portal travel handler
    def on_portal_travel(event: PortalTravelEvent):
        """Handle portal travel between hubs"""
        nonlocal current_hub_id, current_seed, tiles, platforms, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap, current_world_context, current_play_mode

        # Multiplayer: delegate to server — send PORTAL_TRAVEL and wait for
        # WORLD_TRANSITION (polled in the main loop via _net_client.poll_transition()).
        if _net_client is not None and _net_client.is_connected:
            _net_client.send_portal_travel(
                destination_id=event.destination_id,
                portal_id=getattr(event, "portal_id", ""),
            )
            return

        dest_hub = event.destination_id
        if dest_hub == "arcade_loop":
            # Enter endless arcade loop from hub
            nonlocal arcade_depth, arcade_rooms
            arcade_depth = 0
            arcade_rooms = 8
            current_world_context = "arcade"
            current_play_mode = PlayMode.ARCADE
            arcade_seed = get_arcade_seed_wrapper(arcade_depth)
            (
                tiles,
                platforms,
                current_seed,
                spawn_x,
                spawn_y,
                exit_x,
                exit_y,
                world,
                megamap,
                minimap,
            ) = regenerate_world_state(
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
                GAME_HEIGHT=GAME_HEIGHT,
            )
            refresh_platform_state()
            game_state_manager.transition_to(GameState.PLAYING)
            update_replay_metadata_wrapper()
            print("[ARCADE] Entered arcade loop from hub")
            return

        hub_def = hub_manager.get_hub_definition(dest_hub)
        shape_str = "blob"
        rooms_count = hub_def.room_count if hub_def else 8
        if hub_def:
            shape_str = (
                hub_def.world_shape.value
                if hasattr(hub_def.world_shape, "value")
                else str(hub_def.world_shape)
            )

        current_hub_id = dest_hub
        (
            tiles,
            platforms,
            current_seed,
            spawn_x,
            spawn_y,
            exit_x,
            exit_y,
            world,
            megamap,
            minimap,
        ) = regenerate_world_state(
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
            GAME_HEIGHT=GAME_HEIGHT,
        )
        refresh_platform_state()
        current_world_context = "hub"

        if campaign_data:
            campaign_data.current_hub_id = current_hub_id
            campaign_data.current_hub_position = (spawn_x, spawn_y)
            save_manager.mark_dirty()

        game_state_manager.transition_to(GameState.PLAYING)
        update_replay_metadata_wrapper()
        print(f"[PORTAL] Traveled to {dest_hub}")

    bus.subscribe(PortalTravelEvent, on_portal_travel)

    # Initialize physics, collision, and enemy systems
    physics_collision = create_physics_and_collision(
        bus, entity_manager, logger, current_seed if current_seed else base_hub_seed
    )
    physics_system = physics_collision["physics_system"]
    collision_system = physics_collision["collision_system"]
    enemy_manager = physics_collision["enemy_manager"]
    boss_manager = physics_collision["boss_manager"]

    def _maybe_spawn_boss(mission_def, exit_x, exit_y):
        """Clear any previous boss and spawn one if the mission has a defeat_boss objective."""
        from entities.boss_manager import BossType
        from game.mission_registry import ObjectiveType

        boss_manager.clear()
        # Derive boss type from the defeat_boss objective (source of truth in missions.json)
        boss_field = None
        for obj in mission_def.objectives:
            if obj.objective_type == ObjectiveType.DEFEAT_BOSS and obj.boss:
                boss_field = obj.boss
                break
        if not boss_field:
            return
        try:
            boss_type = BossType[boss_field]
        except KeyError:
            print(f"[BOSS] Unknown boss type '{boss_field}' in mission {mission_def.mission_id}")
            return
        # Place boss near the exit; fall back to a fixed offset from spawn if no exit
        bx = (exit_x - 64) if exit_x is not None else 400.0
        by = (exit_y - 96) if exit_y is not None else 300.0
        # Champion system: if this boss type has been defeated before, 40% chance to spawn
        # a weaker champion version instead of the full boss
        spawn_champion = False
        if campaign_data and hasattr(campaign_data, "defeated_bosses"):
            if boss_field in campaign_data.defeated_bosses:
                import random as _random

                spawn_champion = _random.random() < 0.40
        boss_manager.spawn_boss(boss_type, bx, by, champion=spawn_champion)
        boss_manager.start_boss_battle(mission_def.mission_id)
        label = "Champion" if spawn_champion else "Boss"
        print(f"[BOSS] Spawned {label} {boss_field} for mission {mission_def.mission_id}")

    # Region → ability required to enter (None = always open)
    _REGION_GATE_ABILITY = {
        "caves_hub": "double_jump",
        "castle_hub": "dash",
        "sewer_hub": "wall_jump",
        "hollow_hub": "shuriken",
    }

    def _rebuild_hub_gates():
        """Place ability gates in front of locked-region portals in the hub."""
        from entities.ability_gate import AbilityRequirement, GateType

        gate_manager.clear()
        unlocked = (
            set(campaign_data.unlocked_abilities) if campaign_data else {"basic_movement", "jump"}
        )
        unlocked |= {"basic_movement", "jump"}

        for portal in portal_manager.portals:
            dest = portal.destination_id
            required = _REGION_GATE_ABILITY.get(dest)
            if required is None:
                continue
            if required in unlocked:
                continue
            # Place a LOCKED_DOOR gate at the portal position (player must have ability to pass)
            gate_manager.add_gate(GateType.LOCKED_DOOR, portal.x, portal.y)
            print(f"[GATE] Placed gate at {dest} portal — requires {required}")

    def _carry_entities(entities, old_rect: pygame.Rect, dx: float, dy: float = 0.0):
        if dx == 0 and dy == 0:
            return
        for entity in entities:
            if not entity.physics or not entity.active:
                continue
            if _entity_on_platform(entity.physics, old_rect):
                entity.physics.x += dx
                entity.physics.y += dy

    def _update_moving_platform(platform: dict, dt: float, entities):
        rect = platform["rect"]
        if platform["speed"] <= 0 or platform["min_x"] == platform["max_x"]:
            return
        old_rect = rect.copy()
        step = platform["speed"] * dt * platform["dir"]
        platform["pos_x"] += step
        if platform["pos_x"] < platform["min_x"]:
            platform["pos_x"] = platform["min_x"]
            platform["dir"] = 1
        elif platform["pos_x"] > platform["max_x"]:
            platform["pos_x"] = platform["max_x"]
            platform["dir"] = -1
        rect.x = int(round(platform["pos_x"]))
        dx = rect.x - old_rect.x
        if dx != 0:
            _carry_entities(entities, old_rect, dx, 0.0)

    def _update_falling_platform(platform: dict, dt: float, entities):
        rect = platform["rect"]
        supported = any(
            _entity_on_platform(entity.physics, rect)
            for entity in entities
            if entity.physics and entity.active
        )

        state = platform["state"]
        if state == "idle":
            platform["active"] = True
            platform["visible"] = True
            if supported:
                platform["state"] = "triggered"
                platform["timer"] = 0.0
        elif state == "triggered":
            platform["active"] = True
            platform["visible"] = True
            if not supported:
                platform["state"] = "idle"
                platform["timer"] = 0.0
            else:
                platform["timer"] += dt
                if platform["timer"] >= FALLING_PLATFORM_TRIGGER_DELAY:
                    platform["state"] = "falling"
                    platform["timer"] = 0.0
                    platform["vy"] = 0.0
                    platform["active"] = False
        elif state == "falling":
            platform["active"] = False
            platform["visible"] = True
            platform["vy"] = min(
                platform["vy"] + FALLING_PLATFORM_GRAVITY * dt, FALLING_PLATFORM_MAX_SPEED
            )
            platform["pos_y"] += platform["vy"] * dt
            rect.y = int(round(platform["pos_y"]))
            if platform["pos_y"] - platform["origin_y"] >= FALLING_PLATFORM_DROP_DISTANCE:
                platform["state"] = "respawn"
                platform["timer"] = 0.0
                platform["visible"] = False
                platform["pos_y"] = float(platform["origin_y"])
                rect.y = int(round(platform["pos_y"]))
        elif state == "respawn":
            platform["active"] = False
            platform["visible"] = False
            platform["timer"] += dt
            if platform["timer"] >= FALLING_PLATFORM_RESPAWN_DELAY:
                platform["state"] = "idle"
                platform["timer"] = 0.0
                platform["vy"] = 0.0
                platform["active"] = True
                platform["visible"] = True

    def on_platform_tick(event: TickEvent):
        nonlocal platform_colliders
        if not dynamic_platforms or not game_state_manager.is_playing():
            return

        entities = [
            entity
            for entity in entity_manager.entities.values()
            if entity.physics and entity.active
        ]

        for platform in dynamic_platforms:
            if platform["type"] == "moving":
                _update_moving_platform(platform, event.dt, entities)
            else:
                _update_falling_platform(platform, event.dt, entities)

        platform_colliders = static_platforms + [
            p["rect"] for p in dynamic_platforms if p["active"]
        ]
        collision_system.update_platforms(platform_colliders)

    bus.subscribe(TickEvent, on_platform_tick, priority=65)

    # Initialize objective tracker for campaign/playtest modes (v0.6.0)
    if mission_definition:  # Only if in campaign or playtest mode
        objective_tracker.start_mission_objectives(args.mission)

    # Initialize camera system
    camera = create_camera_system(window_width, window_height)

    # Apply runtime settings (live changes from Settings menu)
    show_fps_overlay = False
    _last_fullscreen = bool(runtime_settings.get("fullscreen", False))
    player = None  # forward reference — assigned after create_player()

    # Debug ability menu (F9 to open; password "devmode")
    _debug_ability_menu: DebugAbilityMenu | None = None

    # Build key bindings dict from settings (defined here so apply_runtime_settings can call it)
    def _build_key_bindings():
        """Map settings key name strings → pygame key constants."""
        _KEY_NAME_MAP = {
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
            "up": pygame.K_UP,
            "down": pygame.K_DOWN,
            "space": pygame.K_SPACE,
            "return": pygame.K_RETURN,
            "shift": pygame.K_LSHIFT,
            "lshift": pygame.K_LSHIFT,
            "rshift": pygame.K_RSHIFT,
            "ctrl": pygame.K_LCTRL,
            "alt": pygame.K_LALT,
            **{chr(c): getattr(pygame, f"K_{chr(c)}", None) for c in range(ord("a"), ord("z") + 1)},
        }
        result = {}
        for action in ("left", "right", "jump", "dash", "crouch"):
            name = runtime_settings.get(f"key_{action}", None)
            if name:
                key_code = _KEY_NAME_MAP.get(str(name).lower())
                if key_code is not None:
                    result[action] = key_code
        return result

    def apply_runtime_settings():
        nonlocal show_fps_overlay, show_debug_overlay, _last_fullscreen
        camera.config.enable_shake = bool(runtime_settings.get("screenshake", True))
        smoothing = float(runtime_settings.get("camera_smoothing", 0.1))
        smoothing = max(0.02, min(0.2, smoothing))
        camera.config.follow_speed = smoothing
        particles.enabled = bool(runtime_settings.get("particles", True))
        show_fps_overlay = bool(runtime_settings.get("show_fps", False))
        audio_manager.set_volume(float(runtime_settings.get("volume_sfx", 0.8)))
        show_debug_overlay = bool(runtime_settings.get("show_hitboxes", False))
        if player is not None:
            player.set_key_bindings(_build_key_bindings())
        desired_fs = bool(runtime_settings.get("fullscreen", False))
        if desired_fs != _last_fullscreen:
            pygame.display.toggle_fullscreen()
            _last_fullscreen = desired_fs
            # After toggle the window is a new size — update camera layout so
            # present() scales into the correct dimensions (avoids ValueError).
            new_w, new_h = pygame.display.get_surface().get_size()
            camera.handle_resize(new_w, new_h)
        if not camera.config.enable_shake:
            camera.shake_intensity = 0.0
            camera.shake_duration = 0.0
            camera.shake_offset_x = 0.0
            camera.shake_offset_y = 0.0

    apply_runtime_settings()

    # Create level containers
    world = None
    megamap = None
    minimap = None
    exit_x = None
    exit_y = None
    spawn_x = GAME_WIDTH / 2
    spawn_y = GAME_HEIGHT - 100

    # Player + level manager setup (player will be teleported after world regen)
    player, player_entity, level_manager = create_player(
        spawn_x=spawn_x,
        spawn_y=spawn_y,
        bus=bus,
        logger=logger,
        collision_system=collision_system,
        entity_manager=entity_manager,
        enemy_manager=enemy_manager,
        hazard_manager=hazard_manager,
    )

    # Attach animation state machine (shares frame data loaded by SpriteManager)
    player.anim_sm = AnimationRegistry.make_state_machine("player")

    # Apply shuriken capacity bonus based on equipped armor
    apply_shuriken_capacity_bonus(player, player_inventory, item_manager)

    player.set_key_bindings(_build_key_bindings())

    # Ability → feature-flag mapping used by sync_player_abilities()
    _ABILITY_TO_FLAG = {
        "double_jump": "double_jump",
        "wall_jump": "wall_jump",
        "dash": "dash",
        "shuriken": "shuriken",
        "teleport": "teleport",
        "ninjutsu": "ninjutsu",
        # "basic_movement" and "jump" are always on — no flag needed
        # "crouch" is always on — basic navigation, not a gated ability
    }

    def sync_player_abilities(unlocked_abilities):
        """
        Sync player.feature_flags (and JumpMechanic baked vars) from the
        campaign's unlocked_abilities set.  Call this:
          - when campaign mode starts (restricts abilities to earned ones)
          - after every ability unlock (grants the new ability immediately)
        Has no effect in arcade/playtest mode (caller should not call it).
        """
        unlocked = set(unlocked_abilities) if unlocked_abilities else set()
        for ability, flag in _ABILITY_TO_FLAG.items():
            player.feature_flags[flag] = ability in unlocked
        # JumpMechanic reads double_jump_enabled / wall_jump_enabled from
        # instance vars set at __init__ time — keep them in sync manually.
        player.jump.double_jump_enabled = player.feature_flags.get("double_jump", False)
        player.jump.wall_jump_enabled = player.feature_flags.get("wall_jump", False)
        print(
            f"[ABILITIES] Synced — unlocked: "
            f"{sorted(f for f, v in player.feature_flags.items() if v)}"
        )

    # Combat handling and camera effects
    combat_mechanic, camera_effects = create_combat_system(
        player_entity.entity_id, bus, logger, camera
    )
    attack_cooldown = 0.35  # seconds between sword swings
    attack_timer = 0.0
    attack_fx_timer = 0.0
    attack_fx_rect = None

    # Initial hub generation (central hub by default)
    initial_hub_def = hub_manager.get_hub_definition(current_hub_id)
    initial_rooms = initial_hub_def.room_count if initial_hub_def else num_rooms
    initial_shape = (
        initial_hub_def.world_shape.value
        if initial_hub_def and hasattr(initial_hub_def.world_shape, "value")
        else world_shape
    )
    initial_seed = current_seed if current_seed is not None else base_hub_seed
    current_seed = initial_seed

    tiles, platforms, current_seed, spawn_x, spawn_y, exit_x, exit_y, world, megamap, minimap = (
        regenerate_world_state(
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
            GAME_HEIGHT=GAME_HEIGHT,
        )
    )
    refresh_platform_state()
    current_world_context = "hub"

    # Create victory screen
    victory_screen = VictoryScreen(GAME_WIDTH, GAME_HEIGHT)

    # Game state
    level_complete = False

    # Death animation delay — defers hub transition so the death animation has time to play
    DEATH_ANIM_WAIT = 30  # ~0.5 s at 60 fps; covers the 5-frame 12 fps death anim
    death_anim_pending = False
    death_anim_ticks = 0
    death_anim_ctx = ""  # "mission", "hub_area", "direct"
    death_anim_hub: str | None = None

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
        hub_shape = (
            hub_def.world_shape.value
            if hub_def and hasattr(hub_def.world_shape, "value")
            else world_shape
        )
        (
            tiles,
            platforms,
            current_seed,
            spawn_x,
            spawn_y,
            exit_x,
            exit_y,
            world,
            megamap,
            minimap,
        ) = regenerate_world_state(
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
            GAME_HEIGHT=GAME_HEIGHT,
        )
        refresh_platform_state()
        _rebuild_hub_gates()
        current_world_context = "hub"
        level_complete = False
        current_hub_id = target_hub
        # Restore full health when returning to hub (death or mission complete)
        player.damage.respawn(player.state, spawn_x, spawn_y)
        if campaign_data:
            campaign_data.current_hub_id = target_hub
            campaign_data.current_hub_position = (spawn_x, spawn_y)
            save_manager.mark_dirty()
        # Always restore player health and position when returning to hub (Bug 5)
        player.damage.respawn(player.state, spawn_x, spawn_y)
        if reason:
            print(f"[RESPAWN] Returned to {target_hub} ({reason})")
        update_replay_metadata_wrapper()

    def queue_player_death(ctx: str, hub_id: str | None = None):
        """
        Defer world transition by DEATH_ANIM_WAIT frames so the death animation plays.
        No-op if a death is already pending.
        """
        nonlocal death_anim_pending, death_anim_ticks, death_anim_ctx, death_anim_hub
        if death_anim_pending:
            return
        death_anim_pending = True
        death_anim_ticks = DEATH_ANIM_WAIT
        death_anim_ctx = ctx
        death_anim_hub = hub_id

    print("\n[OK] All systems initialized")
    print(f"[OK] Player spawned at ({spawn_x}, {spawn_y})")
    if exit_x is not None and exit_y is not None:
        print(f"[OK] Exit positioned at ({exit_x:.0f}, {exit_y:.0f})")
    print(f"[OK] Level created ({len(tiles)} tiles)")
    print("\nStarting game loop...\n")

    # Frame profiler (enabled via --profile flag, zero-overhead when disabled)
    profiler = FrameProfiler(
        enabled=enable_profile,
        csv_path=str(user_data_dir / "perf_baseline.csv"),
    )

    # Wire profiler into systems for per-section timing (no-op when disabled)
    if enable_profile:
        physics_system.profiler = profiler
        collision_system.profiler = profiler

    # Pre-allocate misc overlay surfaces (avoid per-frame SRCALPHA/copy allocations)
    _player_flash_surf = pygame.Surface((256, 256))  # Player i-frame white flash
    _player_flash_surf.fill((255, 255, 255))
    _platform_overlay_surf = pygame.Surface((64, 64))  # Falling platform warning
    _platform_overlay_surf.fill((255, 200, 120))
    _heart_warn_surf = pygame.Surface((32, 32))  # Low-health heart pulse
    _heart_warn_surf.fill((255, 0, 0))
    _fullmap_overlay_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))  # Full-map dim overlay
    _fullmap_overlay_surf.fill((0, 0, 0))
    _fullmap_overlay_surf.set_alpha(180)

    # Pre-allocate attack telegraph overlay surfaces.
    # Re-using these instead of creating a new SRCALPHA surface per attacking enemy
    # per frame is the single biggest rendering performance win.
    _ATK_OVERLAY_MAX = 256
    _atk_glow_surf = pygame.Surface((_ATK_OVERLAY_MAX, _ATK_OVERLAY_MAX))
    _atk_glow_surf.fill((255, 50, 50))
    _atk_flash_surf = pygame.Surface((_ATK_OVERLAY_MAX, _ATK_OVERLAY_MAX))
    _atk_flash_surf.fill((255, 255, 255))
    _atk_recovery_surf = pygame.Surface((_ATK_OVERLAY_MAX, _ATK_OVERLAY_MAX))
    _atk_recovery_surf.fill((0, 0, 0))

    # Cache enemy state enums outside render loop (avoid repeated sys.modules lookups)
    from entities.enemy import EnemyAIState, EnemyAttackSubState, EnemyType

    running = True
    last_on_ground = player.state.physics.on_ground
    last_is_dashing = player.state.is_dashing

    # KEYS_TO_TRACK removed - no longer used (handled by input pipeline)

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

    # ── Multiplayer setup ─────────────────────────────────────────────────────
    import threading as _threading
    from entities.remote_player import RemotePlayer as _RemotePlayer
    import rendering.remote_player_renderer as _rp_renderer

    _net_client = None
    _remote_players: dict[int, _RemotePlayer] = {}  # slot → RemotePlayer

    if args.host:
        import asyncio as _asyncio
        import time as _time
        from network.server import run_server as _run_server
        from network.client import NetworkClient as _NetworkClient

        _net_seed = current_seed or random.randint(1, 999999)
        _net_thread = _threading.Thread(
            target=lambda: _asyncio.run(
                _run_server(
                    port=args.host,
                    seed=_net_seed,
                    max_players=args.max_players,
                    world_shape=initial_shape,
                    world_rooms=initial_rooms,
                    world_hub_id=current_hub_id,
                    world_seed=hub_manager.world_seed,
                )
            ),
            daemon=True,
            name="GameServer",
        )
        _net_thread.start()
        # Give the server a moment to open its socket, then connect as a client
        # so the host receives LOBBY_UPDATE and GAME_START just like a joiner.
        _time.sleep(0.3)
        _net_client = _NetworkClient(
            host="127.0.0.1",
            port=args.host,
            player_id=f"host_{random.randint(1000, 9999)}",
        )
        if not _net_client.connect():
            print("[NET] Host could not connect to own server — running solo.")
            _net_client = None
        else:
            if _net_client.server_seed is not None:
                current_seed = _net_client.server_seed

    elif args.connect:
        from network.client import NetworkClient as _NetworkClient

        try:
            _host_str, _port_str = args.connect.rsplit(":", 1)
            _net_port = int(_port_str)
        except ValueError:
            print(f"[NET] Invalid --connect value '{args.connect}'. Expected HOST:PORT.")
            _net_port = 7777
            _host_str = args.connect
        _net_client = _NetworkClient(
            host=_host_str,
            port=_net_port,
            player_id=f"player_{random.randint(1000, 9999)}",
        )
        if not _net_client.connect():
            print("[NET] Could not connect to server — running solo.")
            _net_client = None
        else:
            if _net_client.server_seed is not None:
                current_seed = _net_client.server_seed
    # ── End multiplayer setup ─────────────────────────────────────────────────

    def get_arcade_seed_wrapper(depth: int) -> int:
        return get_arcade_seed(hub_manager, depth)

    def update_replay_metadata_wrapper(mission_id: str | None = None):
        update_replay_metadata(
            input_pipeline,
            current_play_mode,
            current_hub_id,
            current_world_context,
            current_seed,
            hub_manager,
            mission_id,
        )

    update_replay_metadata_wrapper()

    # If started with replay/headless or explicit CLI mode/mission, skip menu
    skip_menu = (
        replay_path is not None or headless or "--mode" in sys.argv or "--mission" in sys.argv
    )
    if skip_menu:
        level_manager.start_level(time.time())
        game_state_manager.start_game()
        input_pipeline.set_game_start(frame_idx)  # frame_idx==0; no menu frames to skip
        menu_manager.clear_menus()
        # Sync abilities for CLI campaign launch (--mode campaign / --mission)
        if (
            current_play_mode == PlayMode.CAMPAIGN
            and save_manager.data
            and save_manager.data.campaign
        ):
            sync_player_abilities(save_manager.data.campaign.unlocked_abilities)
    else:
        if not menu_manager.has_menu():
            menu_manager.push_menu(LandingMenu(GAME_WIDTH, GAME_HEIGHT))

    # ── L2: Multiplayer lobby ─────────────────────────────────────────────────
    # When running with --host or --connect, hold here until GAME_START is
    # received (clients) or the lobby fills (host — auto-starts on full lobby).
    # Shows a pygame overlay so the player knows the game is waiting.
    if _net_client is not None or args.host:
        _is_host = bool(args.host)
        _lobby_font_title = pygame.font.SysFont("impact", 42, bold=True)
        _lobby_font_body = pygame.font.SysFont("consolas", 20)
        _lobby_font_hint = pygame.font.SysFont("consolas", 15)
        _GOLD = (255, 215, 0)
        _DIM = (140, 140, 160)
        _WHITE = (200, 200, 220)
        _lobby_running = True

        # Host: the server runs in a daemon thread; we wait for a client to
        # join and fill the lobby (auto-starts on MAX_PLAYERS connected).
        # Client: wait until game_started event fires.
        # ESC cancels and exits.
        while _lobby_running:
            for _ev in pygame.event.get():
                if _ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if _ev.type == pygame.KEYDOWN and _ev.key == pygame.K_ESCAPE:
                    if _net_client is not None:
                        _net_client.disconnect()
                    pygame.quit()
                    sys.exit()

            # Check game_started (fires when server sends GAME_START)
            if _net_client is not None and _net_client.game_started.is_set():
                if _net_client.server_seed is not None:
                    current_seed = _net_client.server_seed
                _lobby_running = False
                break

            # Draw lobby overlay directly on screen (game_surface not yet created)
            _sw, _sh = screen.get_size()
            screen.fill((10, 10, 20))
            _panel_w, _panel_h = 460, 200
            _px = (_sw - _panel_w) // 2
            _py = (_sh - _panel_h) // 2
            _panel = pygame.Surface((_panel_w, _panel_h), pygame.SRCALPHA)
            _panel.fill((15, 15, 35, 220))
            screen.blit(_panel, (_px, _py))
            pygame.draw.rect(screen, _GOLD, (_px, _py, _panel_w, _panel_h), 2)

            _title_surf = _lobby_font_title.render("LOBBY", True, _GOLD)
            screen.blit(_title_surf, (_px + (_panel_w - _title_surf.get_width()) // 2, _py + 16))

            if _is_host:
                _n = _net_client.connected_count if _net_client else 1
                _max_p = args.max_players
                _count_str = f"Lobby — {_n}/{_max_p} players"
                _hint_str = "Game starts automatically when lobby is full"
            elif _net_client is not None:
                _n = _net_client.connected_count
                _max_p = _net_client.max_players or 4
                _count_str = f"Connected — {_n}/{_max_p} players"
                _hint_str = "Waiting for host to start the game…"
            else:
                _count_str = "Connecting…"
                _hint_str = ""

            _body_surf = _lobby_font_body.render(_count_str, True, _WHITE)
            screen.blit(_body_surf, (_px + (_panel_w - _body_surf.get_width()) // 2, _py + 80))

            if _hint_str:
                _hint_surf = _lobby_font_hint.render(_hint_str, True, _DIM)
                screen.blit(_hint_surf, (_px + (_panel_w - _hint_surf.get_width()) // 2, _py + 118))

            _esc_surf = _lobby_font_hint.render("ESC — cancel", True, _DIM)
            screen.blit(_esc_surf, (_px + (_panel_w - _esc_surf.get_width()) // 2, _py + 170))

            pygame.display.flip()
            clock_pygame.tick(30)

        # Regenerate world from the server's authoritative seed/shape/rooms so
        # every client's tile layout and collision geometry matches exactly.
        # (World was built earlier from local defaults; we now rebuild it with
        # the parameters the server broadcast in GAME_START.)
        if _net_client is not None:
            _sv_seed = (
                _net_client.server_seed if _net_client.server_seed is not None else current_seed
            )
            _sv_shape = (
                _net_client.server_shape if _net_client.server_shape is not None else initial_shape
            )
            _sv_rooms = (
                _net_client.server_rooms if _net_client.server_rooms is not None else initial_rooms
            )
            _sv_hub_id = (
                _net_client.server_hub_id
                if _net_client.server_hub_id is not None
                else current_hub_id
            )
            current_hub_id = _sv_hub_id
            # Critical: sync hub_manager.world_seed to the host's value BEFORE
            # calling regenerate_world_state.  The world_builder overrides the
            # passed seed via SeedDerivation.derive_region_seed(hub_manager.world_seed,
            # hub_id) when hub_manager is present.  If world_seed differs between
            # machines (loaded from different local saves) the derived seed differs
            # and the tile/collision layout diverges cross-machine.
            if _net_client.server_world_seed is not None:
                hub_manager.world_seed = _net_client.server_world_seed
            print(
                f"[NET] Regenerating world: seed={_sv_seed} shape={_sv_shape} rooms={_sv_rooms} hub_id={_sv_hub_id} world_seed={hub_manager.world_seed}"
            )
            (
                tiles,
                platforms,
                current_seed,
                spawn_x,
                spawn_y,
                exit_x,
                exit_y,
                world,
                megamap,
                minimap,
            ) = regenerate_world_state(
                seed=_sv_seed,
                shape=_sv_shape,
                rooms=_sv_rooms,
                hub_id=_sv_hub_id,
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
            )
            refresh_platform_state()

        # Skip the main menu when entering via multiplayer — jump straight in
        level_manager.start_level(time.time())
        game_state_manager.start_game()
        input_pipeline.set_game_start(frame_idx)
        menu_manager.clear_menus()
    # ── End L2 lobby ──────────────────────────────────────────────────────────

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
        profiler.begin_frame()
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

                # F9 — toggle debug ability menu
                if event.key == pygame.K_F9:
                    if _debug_ability_menu is None:

                        def _on_ability_toggle():
                            sync_player_abilities(campaign_data.unlocked_abilities)
                            _rebuild_hub_gates()
                            print(f"[DEBUG] Abilities: {sorted(campaign_data.unlocked_abilities)}")

                        _debug_ability_menu = DebugAbilityMenu(
                            GAME_WIDTH, GAME_HEIGHT, campaign_data, _on_ability_toggle
                        )
                    else:
                        _debug_ability_menu = None
                    continue

                # Route all keyboard input to debug ability menu when it's open
                if _debug_ability_menu is not None:
                    if not _debug_ability_menu.handle_event(event):
                        _debug_ability_menu = None
                    continue

            # Suppress raw KEYDOWN events while in dialogue — actual dialogue
            # input (including ESC-to-dismiss) is handled via pressed_once below
            # so it works identically during live play and replay.
            if event.type == pygame.KEYDOWN and game_state_manager.is_dialogue():
                continue

            if event.type == pygame.KEYDOWN and not replay_path:
                if event.key == pygame.K_c:
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

        # ── Multiplayer: send input to server each frame ──────────────────────
        if _net_client is not None and _net_client.is_connected:
            _phys = player.state.physics
            _net_client.send_input(
                current_command,
                pos=(_phys.x, _phys.y),
                vel=(_phys.vx, _phys.vy),
                health=int(player.state.health_state.current_hp),
                facing=int(player.state.facing),
                is_dead=player.state.health_state.current_hp <= 0,
                anim_state=get_player_render_state(player),
            )
            # N4: parse snapshot and update remote player entities
            _snap_dict = _net_client.poll_state()
            if _snap_dict:
                from network.snapshots import MultiplayerSnapshot as _MPS

                _snap = _MPS.from_dict(_snap_dict)
                _now_ms = float(pygame.time.get_ticks())
                _local_slot = _net_client.local_slot or 0
                for _ps in _snap.players:
                    if _ps.slot == _local_slot:
                        continue
                    if _ps.slot not in _remote_players:
                        _remote_players[_ps.slot] = _RemotePlayer(
                            slot=_ps.slot, player_id=_ps.player_id
                        )
                    _rp = _remote_players[_ps.slot]
                    if _rp.anim_sm is None:
                        _rp.anim_sm = AnimationRegistry.make_state_machine("player")
                    _rp.apply_state(
                        x=_ps.pos[0],
                        y=_ps.pos[1],
                        vx=_ps.vel[0],
                        vy=_ps.vel[1],
                        health=_ps.health,
                        facing=_ps.facing,
                        is_dead=_ps.is_dead,
                        now_ms=_now_ms,
                        anim_state=_ps.anim_state,
                    )
            # Remove ghost for any player who just left
            if _net_client.last_leave_slot is not None:
                _remote_players.pop(_net_client.last_leave_slot, None)
                _net_client.last_leave_slot = None

            # Phase 4: apply zone transition if the server moved us to a new hub
            _transition = _net_client.poll_transition()
            if _transition:
                _apply_world_transition(_transition)

            # Phase 4: sync remote-player ghost roster from zone presence events
            for _zp in _net_client.poll_zone_presence():
                _zp_slot = _zp.get("slot")
                _zp_action = _zp.get("action")
                if _zp_action == "departed" and _zp_slot in _remote_players:
                    del _remote_players[_zp_slot]
                # "arrived" handled naturally: next WORLD_STATE will include the player

            # Phase 3: apply authoritative WorldSnapshot from server simulation
            _ws_dict = _net_client.poll_world_state()
            # Discard stale snapshots from a zone we've already left
            if (
                _ws_dict
                and _ws_dict.get("hub_id")
                and current_hub_id
                and _ws_dict["hub_id"] != current_hub_id
            ):
                _ws_dict = None
            if _ws_dict:
                from network.snapshots import WorldSnapshot as _WS

                _ws = _WS.from_dict(_ws_dict)
                _local_slot = _net_client.local_slot or 0
                _now_ms = float(pygame.time.get_ticks())

                # --- Players (remote ghosts + rubber-band local position) ---
                for _ps in _ws.players:
                    if _ps.slot == _local_slot:
                        # Client-authoritative movement: local physics drives
                        # the remote player's own character with no server
                        # corrections for normal drift (< 128 px).  This gives
                        # v0.7.0-level responsiveness — zero correction latency.
                        # Lerp corrections were removed because they fought the
                        # physics engine: corrected positions pushed the player
                        # into collision geometry, triggering bounces and
                        # animation state flicker ("animation lag").
                        # Hard snap kept only for genuine large divergence
                        # (respawn, OOB, zone transition).
                        # Health is always authoritative (Phase 3b).
                        _dx = _ps.pos[0] - player.state.physics.x
                        _dy = _ps.pos[1] - player.state.physics.y
                        if _dx * _dx + _dy * _dy > 128 * 128:
                            # Hard snap — respawn / OOB / zone transition only
                            player.state.physics.x = _ps.pos[0]
                            player.state.physics.y = _ps.pos[1]
                            player.state.physics.vx = _ps.vel[0]
                            player.state.physics.vy = _ps.vel[1]
                        player.state.health_state.current_hp = _ps.health
                    else:
                        if _ps.slot not in _remote_players:
                            _remote_players[_ps.slot] = _RemotePlayer(
                                slot=_ps.slot, player_id=_ps.player_id
                            )
                        _rp = _remote_players[_ps.slot]
                        if _rp.anim_sm is None:
                            _rp.anim_sm = AnimationRegistry.make_state_machine("player")
                        _rp.apply_state(
                            x=_ps.pos[0],
                            y=_ps.pos[1],
                            vx=_ps.vel[0],
                            vy=_ps.vel[1],
                            health=_ps.health,
                            facing=_ps.facing,
                            is_dead=_ps.is_dead,
                            now_ms=_now_ms,
                            anim_state=_ps.anim_state,
                        )

                # --- Enemies: overwrite local AI state with server state ---
                _server_enemy_ids = {e.enemy_id for e in _ws.enemies}
                # Remove enemies killed on server
                for _dead_id in list(enemy_manager.enemies.keys()):
                    if _dead_id not in _server_enemy_ids:
                        enemy_manager.suppress_enemy(_dead_id)
                # Update or add enemies from snapshot
                for _es in _ws.enemies:
                    _enemy = enemy_manager.enemies.get(_es.enemy_id)
                    if _enemy is not None:
                        _enemy.physics.x = _es.x
                        _enemy.physics.y = _es.y
                        _enemy.physics.vx = _es.vx
                        _enemy.physics.vy = _es.vy
                        _enemy.health_state.current_hp = _es.hp
                        _enemy.facing_right = _es.facing_right
                        try:
                            _enemy.ai_state = EnemyAIState(_es.ai_state)
                        except ValueError:
                            pass  # unknown state string — keep local state

                # --- Pickups: sync alive/dead state from server ---
                _server_alive_ids = {p.pickup_id for p in _ws.pickups if p.alive}
                for _pickup in pickup_manager.pickups:
                    if _pickup.alive and _pickup.pickup_id not in _server_alive_ids:
                        _pickup.alive = False
                        _pickup.collected = True

                # --- Falling platforms: sync state from server ---
                _plat_map = {ps.platform_id: ps for ps in _ws.platform_states}
                for _plat in dynamic_platforms:
                    _pid = _plat.get("id")
                    if _pid and _pid in _plat_map:
                        _psnap = _plat_map[_pid]
                        _plat["state"] = _psnap.state
                        _plat["pos_y"] = _psnap.pos_y
                        _plat["timer"] = _psnap.timer
                        _plat["vy"] = _psnap.vy
                        _plat["rect"].y = int(round(_psnap.pos_y))
                        _plat["active"] = _psnap.state in ("idle", "triggered")
                        _plat["visible"] = _psnap.state != "respawn"

            # Phase 2.5 fallback: apply entity events when Phase 3 WorldSnapshot
            # is not yet active (server simulator not initialised).
            elif not _ws_dict:
                for _ev in _net_client.poll_entity_events():
                    _etype = _ev.get("etype")
                    _eid = _ev.get("entity_id", "")
                    if _etype == "pickup_collect":
                        pickup_manager.suppress_by_id(_eid)
                    elif _etype == "enemy_kill":
                        enemy_manager.suppress_enemy(_eid)
        # ── End multiplayer ───────────────────────────────────────────────────

        # Track single-press keys for dialogue/menu interactions
        pressed_once = set(keydown_keys)
        for key_code in prev_key_state:
            if keys[key_code] and not prev_key_state[key_code]:
                pressed_once.add(key_code)
            prev_key_state[key_code] = bool(keys[key_code])
        if pygame.K_KP_ENTER in pressed_once:
            pressed_once.add(pygame.K_RETURN)

        # Dialogue ESC dismissal — handled here so it works during replay.
        if pygame.K_ESCAPE in pressed_once and game_state_manager.is_dialogue():
            dialogue_manager.end_dialogue()
            game_state_manager.transition_to(GameState.PLAYING)
            pressed_once.discard(pygame.K_ESCAPE)

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

        # Level advancement after victory — command-pipeline driven so it works
        # during both live play and replay (edge-detected via CommandKeyView).
        if pygame.K_SPACE in pressed_once and level_complete:
            level_complete = False
            level_manager.reset_level()
            if current_world_context == "mission":
                regenerate_hub_for_respawn("mission complete")
            elif current_world_context == "arcade":
                # Advance arcade loop with bigger room count
                arcade_depth += 1
                arcade_rooms = min(8 + arcade_depth * 2, 24)
                arcade_seed = get_arcade_seed_wrapper(arcade_depth)
                (
                    tiles,
                    platforms,
                    current_seed,
                    spawn_x,
                    spawn_y,
                    exit_x,
                    exit_y,
                    world,
                    megamap,
                    minimap,
                ) = regenerate_world_state(
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
                    GAME_HEIGHT=GAME_HEIGHT,
                )
                refresh_platform_state()
                current_seed = arcade_seed
                current_world_context = "arcade"
                update_replay_metadata_wrapper()
                print(
                    f"[ARCADE] Generated new level (depth {arcade_depth}, rooms {arcade_rooms}, seed {current_seed})"
                )
            else:
                # Hub victory (should not normally trigger) just respawns player
                player.damage.respawn(player.state, spawn_x, spawn_y)
                player.state.health_state.current_hp = player.state.health_state.max_hp

        # Sword swipe (command-driven for deterministic replay)
        if game_state_manager.is_playing() and pygame.K_j in pressed_once:
            if attack_timer <= 0.0 and player.state.stamina >= 2.0:
                sword_w = 48
                sword_h = 32
                px = player.state.physics.x
                py = player.state.physics.y
                pw = player.state.physics.width
                ph = player.state.physics.height
                facing = (
                    player.state.facing
                    if player.state.facing != 0
                    else (1 if player.state.physics.vx >= 0 else -1)
                )
                attack_x = px + pw if facing >= 0 else px - sword_w
                attack_y = py + ph / 2 - sword_h / 2
                audio_manager.play("swing")
                hits = enemy_manager.check_attack_collision((attack_x, attack_y, sword_w, sword_h))
                for enemy_id in hits:
                    knock_x = 300.0 if facing >= 0 else -300.0
                    enemy_manager.damage_enemy(
                        enemy_id,
                        damage=2,
                        knockback_x=knock_x,
                        knockback_y=-120.0,
                        stun_duration=0.35,
                    )
                if hits:
                    audio_manager.play("hit_enemy")
                # Also check boss collision (spatial overlap required)
                if boss_manager.is_boss_active():
                    _ab = boss_manager.get_active_boss()
                    if _ab:
                        _bx, _by, _bw, _bh = _ab.get_rect()
                        _sword_rect = pygame.Rect(int(attack_x), int(attack_y), sword_w, sword_h)
                        _boss_rect = pygame.Rect(int(_bx), int(_by), _bw, _bh)
                        if _sword_rect.colliderect(_boss_rect):
                            boss_manager.damage_boss(2)
                            audio_manager.play("hit_enemy")
                    # Destroy any boss projectiles the sword swing overlaps
                    destroyed = boss_manager.destroy_projectiles_in_rect(
                        attack_x, attack_y, sword_w, sword_h
                    )
                    if destroyed:
                        audio_manager.play("hit_enemy")
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
            audio_manager.play("inventory_open")
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
                persist_player_inventory_wrapper()

        # Inventory navigation/use (command-driven)
        if inventory_ui.is_open():
            activated_slot = inventory_ui.handle_command(pressed_once)
            if activated_slot is not None:
                slot = player_inventory.slots[activated_slot]
                if slot:
                    item_def = item_manager.get_item(slot.item_id) if item_manager else None
                    if item_def:
                        if item_def.item_type == ItemType.WEAPON:
                            if player_inventory.equipped_weapon == slot.item_id:
                                if player_inventory.unequip_item(slot.item_id):
                                    print(f"[INVENTORY] Unequipped weapon: {slot.item_id}")
                                    persist_player_inventory_wrapper()
                            else:
                                if player_inventory.equip_item(slot.item_id):
                                    print(f"[INVENTORY] Equipped weapon: {slot.item_id}")
                                    persist_player_inventory_wrapper()
                        elif item_def.item_type == ItemType.ARMOR:
                            if player_inventory.equipped_armor == slot.item_id:
                                if player_inventory.unequip_item(slot.item_id):
                                    print(f"[INVENTORY] Unequipped armor: {slot.item_id}")
                                    apply_shuriken_capacity_bonus(
                                        player, player_inventory, item_manager
                                    )
                                    persist_player_inventory_wrapper()
                            else:
                                if player_inventory.equip_item(slot.item_id):
                                    print(f"[INVENTORY] Equipped armor: {slot.item_id}")
                                    apply_shuriken_capacity_bonus(
                                        player, player_inventory, item_manager
                                    )
                                    persist_player_inventory_wrapper()
                        elif item_def.consumable and item_def.health_restore > 0:
                            healed = player.state.health_state.heal(item_def.health_restore)
                            if healed > 0:
                                slot.quantity -= 1
                                if slot.quantity <= 0:
                                    player_inventory.slots[activated_slot] = None
                                print(f"[INVENTORY] Used {slot.item_id}")
                                persist_player_inventory_wrapper()
                        else:
                            print(f"[INVENTORY] Item not usable: {slot.item_id}")
                    else:
                        print(f"[INVENTORY] Unknown item: {slot.item_id}")

        # Handle menu input if menu is active
        selected_mode = None
        if menu_manager.has_menu():
            # SFX: navigate on up/down; confirm on any action except NONE
            if pygame.K_UP in pressed_once or pygame.K_DOWN in pressed_once:
                audio_manager.play("menu_select")
            # Drive menus via unified command pipeline (replay-compatible)
            menu_action = menu_manager.handle_input(keys, pressed_once)
            if menu_action not in (MenuAction.NONE,):
                audio_manager.play("menu_confirm")

            if menu_action == MenuAction.START_GAME:
                # Show mode selection menu instead of starting directly
                mode_menu = GameModeSelectionMenu(GAME_WIDTH, GAME_HEIGHT)
                menu_manager.push_menu(mode_menu)
                print("[MENU] Showing game mode selection...")
            elif menu_action == MenuAction.CONTINUE:
                # Landing page continue -> show main menu
                game_state_manager.transition_to(GameState.MENU)
                menu_manager.clear_menus()
                menu_manager.push_menu(MainMenu(GAME_WIDTH, GAME_HEIGHT))
            elif menu_action == MenuAction.RESUME_GAME:
                # Resume from pause
                game_state_manager.resume()
                menu_manager.pop_menu()
            elif menu_action == MenuAction.OPEN_SETTINGS:
                # Open settings menu
                menu_manager.push_menu(
                    SettingsMenu(GAME_WIDTH, GAME_HEIGHT, runtime_settings, apply_runtime_settings)
                )
            elif menu_action == MenuAction.BACK:
                # Go back (close settings)
                if not game_state_manager.is_landing():
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
                        base_seed = (
                            hub_manager.world_seed
                            if getattr(hub_manager, "world_seed", 0) != 0
                            else (current_seed if current_seed is not None else 1)
                        )
                        campaign_seed = SeedDerivation.derive_region_seed(
                            base_seed, "campaign_world"
                        )
                        save_manager.start_new_campaign(campaign_seed)
                        hub_manager = HubManager(campaign_seed)
                        current_hub_id = "central_hub"

                    print(f"[CAMPAIGN] Generating Central Hub (seed: {campaign_seed})...")

                    hub_def = hub_manager.get_hub_definition(current_hub_id)
                    hub_rooms = hub_def.room_count if hub_def else 10
                    hub_shape = (
                        hub_def.world_shape.value
                        if hub_def and hasattr(hub_def.world_shape, "value")
                        else "blob"
                    )

                    # Regenerate world using centralized function
                    (
                        tiles,
                        platforms,
                        current_seed,
                        spawn_x,
                        spawn_y,
                        exit_x,
                        exit_y,
                        world,
                        megamap,
                        minimap,
                    ) = regenerate_world_state(
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
                        GAME_HEIGHT=GAME_HEIGHT,
                    )
                    refresh_platform_state()
                    current_world_context = "hub"
                    update_replay_metadata_wrapper()

                    # Start game
                    level_manager.start_level(time.time())
                    game_state_manager.start_game()
                    input_pipeline.set_game_start(frame_idx)
                    # Lock abilities to what the campaign has earned so far
                    sync_player_abilities(save_manager.data.campaign.unlocked_abilities)
                    _rebuild_hub_gates()

                elif selected_mode == "arcade":
                    # Start arcade mode - existing procedural generation
                    print("[MODE] Starting Arcade Mode...")
                    menu_manager.clear_menus()
                    current_play_mode = PlayMode.ARCADE
                    arcade_depth = 0

                    # Generate new arcade world
                    arcade_seed = get_arcade_seed_wrapper(arcade_depth)

                    print(f"[ARCADE] Generating procedural level (seed: {arcade_seed})...")

                    # Regenerate world using centralized function
                    (
                        tiles,
                        platforms,
                        current_seed,
                        spawn_x,
                        spawn_y,
                        exit_x,
                        exit_y,
                        world,
                        megamap,
                        minimap,
                    ) = regenerate_world_state(
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
                        GAME_HEIGHT=GAME_HEIGHT,
                    )
                    refresh_platform_state()
                    current_world_context = "arcade"
                    update_replay_metadata_wrapper()

                    # Start game
                    level_manager.start_level(time.time())
                    game_state_manager.start_game()
                    input_pipeline.set_game_start(frame_idx)

                elif selected_mode == "playtest":
                    # Show mission selector
                    print("[MODE] Opening Mission Selector...")
                    mission_menu = MissionSelectorMenu(
                        GAME_WIDTH, GAME_HEIGHT, get_mission_registry()
                    )
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
                        region_seed = SeedDerivation.derive_region_seed(
                            hub_manager.world_seed, region_id
                        )
                        mission_seed = SeedDerivation.derive_mission_seed(
                            region_seed, mission_def.mission_id
                        )

                        print(f"[PLAYTEST] Mission: {mission_def.mission_name}")
                        print(
                            f"[PLAYTEST] Difficulty: {mission_def.difficulty}, Rooms: {mission_def.room_count}"
                        )

                        # Start objective tracking for playtest mission
                        if objective_tracker:
                            objective_tracker.stop_mission_objectives()
                            objective_tracker.start_mission_objectives(mission_def.mission_id)

                        # Regenerate world using centralized function
                        (
                            tiles,
                            platforms,
                            current_seed,
                            spawn_x,
                            spawn_y,
                            exit_x,
                            exit_y,
                            world,
                            megamap,
                            minimap,
                        ) = regenerate_world_state(
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
                            mission_def=mission_def,
                        )
                        refresh_platform_state()
                        _maybe_spawn_boss(mission_def, exit_x, exit_y)
                        current_world_context = "mission"
                        update_replay_metadata_wrapper(mission_def.mission_id)

                        if objective_tracker:
                            targets = build_objective_location_targets(
                                world, megamap, spawn_x, spawn_y, exit_x, exit_y
                            )
                            fallback_id = (
                                "exit" if exit_x is not None and exit_y is not None else None
                            )
                            objective_tracker.set_location_targets(targets, fallback_id=fallback_id)

                        # Start game
                        level_manager.start_level(time.time())
                        game_state_manager.start_game()
                        input_pipeline.set_game_start(frame_idx)

        # Only process game input and updates when playing
        if game_state_manager.is_playing():
            # Death animation countdown — tick down and execute queued hub transition
            if death_anim_pending:
                death_anim_ticks -= 1
                if death_anim_ticks <= 0:
                    _ctx = death_anim_ctx
                    _hub = death_anim_hub
                    death_anim_pending = False
                    death_anim_ticks = 0
                    death_anim_ctx = ""
                    death_anim_hub = None
                    if _ctx == "mission":
                        regenerate_hub_for_respawn("mission failed")
                    elif _ctx == "hub_area":
                        regenerate_hub_for_respawn(
                            "area hub death", target_hub_id=_hub or "central_hub"
                        )
                    else:
                        player.damage.respawn(player.state, spawn_x, spawn_y)

            # Free camera controls (arrow keys in free mode)
            if camera.mode == CameraMode.FREE and not inventory_ui.is_open():
                if keys[pygame.K_UP]:
                    camera.move_free_camera(0, -1)
                if keys[pygame.K_DOWN]:
                    camera.move_free_camera(0, 1)
                if keys[pygame.K_LEFT]:
                    camera.move_free_camera(-1, 0)
                if keys[pygame.K_RIGHT]:
                    camera.move_free_camera(1, 0)

            if not inventory_ui.is_open():
                player.process_input(keys)

            # Tutorial triggers (based on player actions)
            if game_state_manager.is_playing():
                # Jump tutorial (trigger when player has used jumps)
                if (
                    player.state.jumps_left < player.state.max_jumps
                    and "jump" not in tutorial_manager.shown_tutorials
                ):
                    tutorial_manager.trigger_tutorial("jump")

                # Dash tutorial
                if player.state.is_dashing and "dash" not in tutorial_manager.shown_tutorials:
                    tutorial_manager.trigger_tutorial("dash")

                # Wall slide tutorial
                if (
                    player.state.is_wall_sliding
                    and "wall_slide" not in tutorial_manager.shown_tutorials
                ):
                    tutorial_manager.trigger_tutorial("wall_slide")

                # Crouch tutorial
                if player.state.crouching and "crouch" not in tutorial_manager.shown_tutorials:
                    tutorial_manager.trigger_tutorial("crouch")

            # Update game (fixed timestep)
            profiler.begin("update")
            # In networked play, cap the measured frame time to 1 physics tick
            # before game_clock.tick().  process_input(keys) is called once per
            # game-loop frame (outside the TickEvent loop), so if 2-3 TickEvents
            # fire due to a slow frame (GIL contention, GPU hiccup, etc.) the
            # same key state is applied 2-3× → 2-3× movement exaggeration.
            # Capping to 1 tick ensures movement is always proportional to
            # visible frames, giving the remote player the same fine-grained
            # control as the local host.
            if _net_client is not None and _net_client.is_connected:
                game_clock.tick(max_frame_time=game_clock.PHYSICS_DT)
            else:
                game_clock.tick()
            bus.process()
            profiler.end("update")

            # Reset environment modifiers each frame (overridden by water)
            player.state.environment_speed_mult = 1.0
            player.state.environment_accel_mult = 1.0

            # Environment interactions (lava, water, poison)
            if megamap and getattr(megamap, "tilemap", None):
                from systems.room_generation import TILE_LAVA, TILE_WATER

                dt = 1.0 / FPS
                player_rect = pygame.Rect(
                    int(player.state.physics.x),
                    int(player.state.physics.y),
                    player.state.physics.width,
                    player.state.physics.height,
                )
                min_tx = max(0, player_rect.left // 32)
                max_tx = min(megamap.width_tiles - 1, (player_rect.right - 1) // 32)
                min_ty = max(0, player_rect.top // 32)
                max_ty = min(megamap.height_tiles - 1, (player_rect.bottom - 1) // 32)

                in_lava = False
                in_water = False
                if max_tx >= min_tx and max_ty >= min_ty:
                    for ty in range(min_ty, max_ty + 1):
                        row = megamap.tilemap[ty]
                        for tx in range(min_tx, max_tx + 1):
                            tile_id = row[tx]
                            if tile_id == TILE_LAVA:
                                in_lava = True
                            elif tile_id == TILE_WATER:
                                in_water = True
                            if in_lava and in_water:
                                break
                        if in_lava and in_water:
                            break

                # Water slowdown + drag
                if in_water:
                    player.state.environment_speed_mult = WATER_SPEED_MULT
                    player.state.environment_accel_mult = WATER_ACCEL_MULT
                    player.state.physics.vx *= WATER_DRAG_X
                    if player.state.physics.vy > 0:
                        player.state.physics.vy *= WATER_DRAG_Y
                        player.state.physics.vy = min(player.state.physics.vy, WATER_MAX_FALL_SPEED)
                    else:
                        player.state.physics.vy *= 0.95
                else:
                    player.state.environment_speed_mult = 1.0
                    player.state.environment_accel_mult = 1.0

                # Lava damage over time
                if in_lava and not death_anim_pending:
                    lava_damage_timer += dt
                    if lava_damage_timer >= LAVA_DAMAGE_INTERVAL:
                        lava_damage_timer = 0.0
                        died = player.damage.take_damage(
                            player.state,
                            1,
                            source="lava",
                            source_pos=(player.state.physics.x, player.state.physics.y),
                        )
                        if died:
                            audio_manager.play("player_death")
                            level_manager.increment_deaths()
                            if current_world_context == "mission":
                                queue_player_death("mission")
                            elif current_world_context == "hub" and current_hub_id != "central_hub":
                                queue_player_death("hub_area", hub_id="central_hub")
                            else:
                                queue_player_death("direct")
                        else:
                            audio_manager.play("player_hurt")
                else:
                    lava_damage_timer = 0.0

                # Poison sapping zones (cleansed by Purify)
                poison_hit = None
                for hazard in hazard_manager.hazards:
                    if not hazard.active or hazard.hazard_type != "poison":
                        continue
                    if hazard.check_collision(
                        player_rect.x, player_rect.y, player_rect.width, player_rect.height
                    ):
                        poison_hit = hazard
                        break

                if poison_hit and not death_anim_pending:
                    poison_damage_timer += dt
                    if poison_damage_timer >= POISON_DAMAGE_INTERVAL:
                        poison_damage_timer = 0.0
                        died = player.damage.take_damage(
                            player.state,
                            1,
                            source="poison",
                            source_pos=(poison_hit.x, poison_hit.y),
                        )
                        if died:
                            audio_manager.play("player_death")
                            level_manager.increment_deaths()
                            if current_world_context == "mission":
                                queue_player_death("mission")
                            elif current_world_context == "hub" and current_hub_id != "central_hub":
                                queue_player_death("hub_area", hub_id="central_hub")
                            else:
                                queue_player_death("direct")
                        else:
                            audio_manager.play("player_hurt")
                else:
                    poison_damage_timer = 0.0

            # Kill player if they fall out of the world
            if megamap and not death_anim_pending:
                _world_h_bound = megamap.height_tiles * 32
                if player.state.physics.y > _world_h_bound + 200:
                    level_manager.increment_deaths()
                    if current_world_context == "mission":
                        queue_player_death("mission")
                    elif current_world_context == "hub" and current_hub_id != "central_hub":
                        queue_player_death("hub_area", hub_id="central_hub")
                    else:
                        queue_player_death("direct")

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
                    PlayerPositionUpdateEvent(player_x=player_center_x, player_y=player_center_y),
                    immediate=True,
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
                        region_seed = SeedDerivation.derive_region_seed(
                            hub_manager.world_seed, region_id
                        )
                        mission_seed = SeedDerivation.derive_mission_seed(
                            region_seed, mission_def.mission_id
                        )
                        (
                            tiles,
                            platforms,
                            current_seed,
                            spawn_x,
                            spawn_y,
                            exit_x,
                            exit_y,
                            world,
                            megamap,
                            minimap,
                        ) = regenerate_world_state(
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
                            mission_def=mission_def,
                        )
                        refresh_platform_state()
                        _maybe_spawn_boss(mission_def, exit_x, exit_y)
                        if objective_tracker:
                            targets = build_objective_location_targets(
                                world, megamap, spawn_x, spawn_y, exit_x, exit_y
                            )
                            fallback_id = (
                                "exit" if exit_x is not None and exit_y is not None else None
                            )
                            objective_tracker.set_location_targets(targets, fallback_id=fallback_id)
                        current_play_mode = PlayMode.CAMPAIGN
                        level_complete = False
                        current_world_context = "mission"
                        game_state_manager.transition_to(GameState.PLAYING)
                        mission_menu_ui.hide()
                        active_mission_pool = []
                        update_replay_metadata_wrapper(mission_def.mission_id)
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
            # Track state transitions for particles and SFX
            if not last_on_ground and player.state.physics.on_ground:
                audio_manager.play("land")
                particles.emit_dust(
                    player.state.physics.x,
                    player.state.physics.y + player.state.physics.height // 2,
                )
            if (
                last_on_ground
                and not player.state.physics.on_ground
                and player.state.physics.vy < -50
            ):
                audio_manager.play("jump")
            if player.state.is_dashing and not last_is_dashing:
                audio_manager.play("dash")
                facing = player.state.facing if player.state.facing != 0 else 1
                particles.emit_dash(player.state.physics.x, player.state.physics.y, facing)
            last_on_ground = player.state.physics.on_ground
            last_is_dashing = player.state.is_dashing

            # Update camera to follow player
            camera.update(player.state.physics.x, player.state.physics.y)

            # Update pickups
            pickup_manager.update(1.0 / FPS)

            # Update enemies (v0.6.0)
            profiler.begin("enemy_manager")
            _world_h = (megamap.height_tiles * 32) if megamap else 0
            enemy_manager.update(
                dt=1.0 / FPS,
                player_x=player.state.physics.x,
                player_y=player.state.physics.y,
                player_width=player.state.physics.width,
                player_height=player.state.physics.height,
                collision_system=collision_system,
                camera_rect=(
                    camera.x,
                    camera.y,
                    camera.config.game_width,
                    camera.config.game_height,
                ),
                cull_margin=400.0,
                player_state=player.state,
                world_h=_world_h,
                profiler=profiler,
            )
            profiler.end("enemy_manager")

            # Phase 2.5: broadcast enemy kills to remote clients
            if _net_client is not None and _net_client.is_connected:
                for _killed_id in enemy_manager.recently_killed_ids:
                    _net_client.send_entity_event("enemy_kill", _killed_id)

            # Update boss (if active)
            if boss_manager.is_boss_active():
                boss_damage = boss_manager.update(
                    dt=1.0 / FPS,
                    player_x=player.state.physics.x,
                    player_y=player.state.physics.y,
                    player_width=player.state.physics.width,
                    player_height=player.state.physics.height,
                    player_hp=player.state.health_state.current_hp,
                    player_max_hp=player.state.health_state.max_hp,
                )
                if (
                    boss_damage
                    and not player.damage.is_invincible(player.state)
                    and not death_anim_pending
                ):
                    died = player.damage.take_damage(
                        player.state,
                        boss_damage,
                        source="boss",
                        source_pos=(
                            boss_manager.get_active_boss().get_center()
                            if boss_manager.get_active_boss()
                            else None
                        ),
                    )
                    if died:
                        audio_manager.play("player_death")
                        level_manager.increment_deaths()
                        if current_world_context == "mission":
                            queue_player_death("mission")
                        elif current_world_context == "hub" and current_hub_id != "central_hub":
                            queue_player_death("hub_area", hub_id="central_hub")
                        else:
                            queue_player_death("direct")
                    else:
                        audio_manager.play("player_hurt")

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
                    player.state, enemy_manager, dt=1.0 / FPS
                )
                # Arrow damage (skeleton projectiles)
                _pr = player.state.physics
                arrow_dmg = enemy_manager.check_arrow_player_collision(
                    _pr.x, _pr.y, _pr.width, _pr.height
                )
                if arrow_dmg and not player.damage.is_invincible(player.state):
                    player.state.health_state.take_damage(arrow_dmg, defense=0)
                    player.state.physics.vy = -120.0  # slight upward nudge
                damage_taken += arrow_dmg
                if damage_taken and not player.damage.is_invincible(player.state):
                    died = player.damage.take_damage(player.state, damage_taken)
                    if died:
                        audio_manager.play("player_death")
                        level_manager.increment_deaths()
                        if current_world_context == "mission":
                            queue_player_death("mission")
                        elif current_world_context == "hub" and current_hub_id != "central_hub":
                            queue_player_death("hub_area", hub_id="central_hub")
                        else:
                            queue_player_death("direct")
                    else:
                        audio_manager.play("player_hurt")

                if pygame.K_e in pressed_once:
                    # Prefer portal interaction if nearby
                    nearby_portal = portal_manager.check_interaction(
                        player_x=player.state.physics.x,
                        player_y=player.state.physics.y,
                        player_width=player.state.physics.width,
                        player_height=player.state.physics.height,
                    )
                    if nearby_portal:
                        # Check ability gate — block portal if player lacks required ability
                        from entities.ability_gate import AbilityRequirement

                        _gate_blocked = False
                        if current_world_context == "hub":
                            _req = _REGION_GATE_ABILITY.get(nearby_portal.destination_id)
                            _unlocked = (
                                set(campaign_data.unlocked_abilities) if campaign_data else set()
                            )
                            _unlocked |= {"basic_movement", "jump"}
                            if _req and _req not in _unlocked:
                                _gate_blocked = True
                                print(
                                    f"[GATE] {nearby_portal.destination_id} locked — requires {_req}"
                                )
                        if not _gate_blocked:
                            portal_manager.interact_with_portal(nearby_portal, player_id=0)
                            print(
                                f"[PORTAL] Activated {nearby_portal.portal_id} -> {nearby_portal.destination_id}"
                            )
                    else:
                        # Find NPCs in interaction range
                        nearby_npcs = npc_manager.get_nearby_npcs(
                            player_x=player.state.physics.x,
                            player_y=player.state.physics.y,
                            player_width=player.state.physics.width,
                            player_height=player.state.physics.height,
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
                    player.state.physics.height,
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
                                        if (
                                            obj_state.objective_type == ObjectiveType.COLLECT_ITEMS
                                            and not obj_state.is_complete
                                        ):
                                            if obj_state.item_id and obj_state.item_id != "coin":
                                                collect_item_id = obj_state.item_id
                                            break
                            bus.emit(
                                ItemCollectedEvent(
                                    item_id=collect_item_id,
                                    quantity=pickup.value,
                                    position=(pickup.x, pickup.y),
                                )
                            )
                            # Add an item to inventory (objective item if provided, else treasure)
                            reward_item_id = (
                                collect_item_id
                                if collect_item_id not in ("collectible", "coin")
                                else "treasure_ruby"
                            )
                            audio_manager.play("pickup_item")
                            try:
                                if player_inventory.add_item(reward_item_id, pickup.value):
                                    print(
                                        f"[PICKUP] Added {reward_item_id} x{pickup.value} to inventory"
                                    )
                            except Exception:
                                pass
                        elif pickup.pickup_type == "health":
                            # Heal player when collecting health pickup
                            player.damage.heal(player.state, pickup.value)
                            audio_manager.play("pickup_item")
                        elif pickup.pickup_type == "coin":
                            # Treat coins as currency
                            audio_manager.play("pickup_coin")
                            player_inventory.add_currency(pickup.value)
                            if save_manager and save_manager.data and save_manager.data.campaign:
                                save_manager.data.campaign.currency = player_inventory.currency
                                save_manager.mark_dirty()
                            bus.emit(
                                ItemCollectedEvent(
                                    item_id="coin",
                                    quantity=pickup.value,
                                    position=(pickup.x, pickup.y),
                                )
                            )

                # Phase 2.5: broadcast pickup collections to remote clients
                if _net_client is not None and _net_client.is_connected and collected:
                    for _pickup in collected:
                        _net_client.send_entity_event("pickup_collect", _pickup.pickup_id)

                # Check hazard collisions (damage/death)
                if not level_complete and not death_anim_pending:
                    hazard_collision = hazard_manager.check_hazards(
                        player.state, invincible=player.damage.is_invincible(player.state)
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
                                queue_player_death("mission")
                            elif current_world_context == "hub" and current_hub_id != "central_hub":
                                queue_player_death("hub_area", hub_id="central_hub")
                            else:
                                queue_player_death("direct")

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
                                mission_def = get_mission_registry().get_mission(
                                    objective_tracker.active_mission_id
                                )
                                if mission_def:
                                    # Currency
                                    if mission_def.rewards.currency:
                                        player_inventory.add_currency(mission_def.rewards.currency)
                                        print(
                                            f"[MISSION] Reward: +{mission_def.rewards.currency} gold"
                                        )
                                    # Items
                                    for reward_item in mission_def.rewards.items:
                                        item_id = reward_item.get("id") or reward_item.get(
                                            "item_id"
                                        )
                                        qty = reward_item.get("quantity", 1)
                                        if item_id:
                                            player_inventory.add_item(item_id, qty)
                                            print(f"[MISSION] Reward item: {item_id} x{qty}")
                                    # Mark mission complete in campaign save
                                    if (
                                        save_manager
                                        and save_manager.data
                                        and save_manager.data.campaign
                                    ):
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
                                        save_manager.data.campaign.currency = (
                                            player_inventory.currency
                                        )
                                        # Track defeated bosses for champion system (v0.7.2)
                                        from game.mission_registry import ObjectiveType as _OT

                                        defeated_bosses = save_manager.data.campaign.defeated_bosses
                                        for _obj in mission_def.objectives:
                                            if _obj.objective_type == _OT.DEFEAT_BOSS and _obj.boss:
                                                if isinstance(defeated_bosses, set):
                                                    defeated_bosses.add(_obj.boss)
                                                elif _obj.boss not in defeated_bosses:
                                                    defeated_bosses.append(_obj.boss)
                                        # Grant ability unlocks from mission definition
                                        unlocked = save_manager.data.campaign.unlocked_abilities
                                        newly_unlocked = []
                                        for ability in getattr(mission_def, "unlock_abilities", []):
                                            if isinstance(unlocked, set):
                                                unlocked.add(ability)
                                            elif ability not in unlocked:
                                                unlocked.append(ability)
                                            newly_unlocked.append(ability)
                                            print(f"[MISSION] Ability unlocked: {ability}")
                                        if newly_unlocked:
                                            sync_player_abilities(
                                                save_manager.data.campaign.unlocked_abilities
                                            )
                                        save_manager.mark_dirty()

                                    # Trigger story events on mission completion (v0.7.0)
                                    story_events = story_manager.on_mission_complete(
                                        mission_def.mission_id
                                    )
                                    if story_events:
                                        print(
                                            f"[STORY] Mission {mission_def.mission_id} triggered story events: {story_events}"
                                        )
                                        # Check for cutscene trigger
                                        if "cutscene_id" in story_events:
                                            cutscene_id = story_events["cutscene_id"]
                                            print(f"[STORY] Triggering cutscene: {cutscene_id}")
                                            story_manager.trigger_cutscene(cutscene_id)

                            objective_tracker.stop_mission_objectives()
                            # Show victory screen; SPACE handler returns to hub
                            level_complete = True
                            victory_screen.reset()
                        else:
                            print("[MISSION] Exit locked until objectives are complete")
                    elif current_world_context == "arcade":
                        # Auto-advance arcade run to next, larger layout
                        level_complete = True
                        victory_screen.reset()
                        arcade_depth += 1
                        arcade_rooms = min(8 + arcade_depth * 2, 24)
                        arcade_seed = get_arcade_seed_wrapper(arcade_depth)
                        (
                            tiles,
                            platforms,
                            current_seed,
                            spawn_x,
                            spawn_y,
                            exit_x,
                            exit_y,
                            world,
                            megamap,
                            minimap,
                        ) = regenerate_world_state(
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
                            GAME_HEIGHT=GAME_HEIGHT,
                        )
                        refresh_platform_state()
                        current_seed = arcade_seed
                        level_complete = False
                        update_replay_metadata_wrapper()
                        print(f"[ARCADE] Advanced to depth {arcade_depth} (rooms={arcade_rooms})")
                    else:
                        level_complete = True
                        victory_screen.reset()

                        # Save level completion to save file
                        stats = level_manager.get_stats()
                        level_id = f"{current_world_context}_seed_{current_seed if current_seed is not None else 0}"
                        save_manager.complete_level(
                            level_id, stats["time"], stats["collectibles"], stats["deaths"]
                        )
                        persist_story_state_wrapper()  # Save story state (v0.7.0)
                        save_manager.save(force=True)  # Save immediately on level complete

                        print("\n[VICTORY] Level complete!")
                        print(f"[VICTORY] Time: {level_manager.state.completion_time:.2f}s")
                        print(f"[VICTORY] Stats: {level_manager.get_stats()}")
                        print("[SAVE] Progress saved!")

        frame_idx += 1

        # Render to virtual game surface
        profiler.begin("render")
        game_surface = camera.get_game_surface()
        game_surface.fill(COLOR_BG)

        # Draw solid tiles (with camera transform and autotiled assets)
        # Determine biome for tile selection
        current_biome = "dungeon"  # Default
        if world and megamap:
            # Get current room from player position
            player_pos = (player.state.physics.x, player.state.physics.y)
            current_room_coords = get_current_room_coords(megamap, player_pos)

            # Find the room in the world
            current_room = next(
                (r for r in world.all_rooms if (r.grid_x, r.grid_y) == current_room_coords), None
            )

            if current_room and hasattr(current_room, "biome_theme"):
                biome_name = current_room.biome_theme.value.lower()
                # Map world generation biomes to tile asset folders
                biome_map = {
                    "dungeon": "dungeon",
                    "cave": "cave",
                    "building": "building",
                    "forest": "forest",
                    "town": "town",
                    "sewer": "sewer",
                    "hollow": "hollow",
                }
                current_biome = biome_map.get(biome_name, "dungeon")

        # Use autotiling for procedural worlds (we now have megamap)
        profiler.begin("render_tiles")
        use_autotiling = megamap is not None

        if use_autotiling:
            # Import tile constants for autotiling
            from systems.room_generation import (
                TILE_LAVA,
                TILE_PLATFORM,
                TILE_SOLID,
                TILE_WATER,
            )

            # OPTIMIZATION: Only render tiles within camera view + margin
            # Calculate visible tile bounds
            cam_x, cam_y = camera.x, camera.y
            screen_w, screen_h = camera.config.game_width, camera.config.game_height

            # Add margin for smooth scrolling (1 screen extra on each side)
            margin = 32 * 10  # 10 tiles margin
            min_tile_x = int(max(0, (cam_x - margin) // 32))
            max_tile_x = int(min(megamap.width_tiles, (cam_x + screen_w + margin) // 32 + 1))
            min_tile_y = int(max(0, (cam_y - margin) // 32))
            max_tile_y = int(min(megamap.height_tiles, (cam_y + screen_h + margin) // 32 + 1))

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
                    tile_type="solid",
                    tilemap=megamap.tilemap,
                    x=tx,
                    y=ty,
                    tile_id=TILE_SOLID,
                    seed=current_seed,
                )
                game_surface.blit(tile_surface, screen_rect)

            # Draw liquid tiles (lava/water) — pre-built at level load, culled here
            _liq_rect = pygame.Rect(0, 0, 32, 32)
            for lx, ly, tile_type in liquid_tiles:
                tx, ty = lx // 32, ly // 32
                if not (min_tile_x <= tx < max_tile_x and min_tile_y <= ty < max_tile_y):
                    continue
                _liq_rect.x = lx
                _liq_rect.y = ly
                screen_rect = camera.apply(_liq_rect)
                tile_surface = tile_loader.get_tile(current_biome, tile_type, 0)
                game_surface.blit(tile_surface, screen_rect)

            # Draw static platforms with culling
            for platform in static_platforms:
                tx, ty = platform.x // 32, platform.y // 32

                # Cull platforms outside view
                if not (min_tile_x <= tx < max_tile_x and min_tile_y <= ty < max_tile_y):
                    continue

                screen_rect = camera.apply(platform)

                tile_surface = tile_loader.get_autotiled_tile(
                    biome=current_biome,
                    tile_type="platform",
                    tilemap=megamap.tilemap,
                    x=tx,
                    y=ty,
                    tile_id=TILE_PLATFORM,
                    seed=current_seed,
                )
                game_surface.blit(tile_surface, screen_rect)

            # Draw dynamic platforms (moving/falling)
            for platform_data in dynamic_platforms:
                if not platform_data.get("visible", True):
                    continue
                rect = platform_data["rect"]
                tx, ty = rect.x // 32, rect.y // 32

                if not (min_tile_x <= tx < max_tile_x and min_tile_y <= ty < max_tile_y):
                    continue

                screen_rect = camera.apply(rect)
                tile_type = (
                    "platform_moving" if platform_data["type"] == "moving" else "platform_falling"
                )
                tile_surface = tile_loader.get_tile(current_biome, tile_type, 0)
                game_surface.blit(tile_surface, screen_rect)

                if platform_data["type"] == "falling" and platform_data.get("state") == "triggered":
                    pulse = abs(math.sin(pygame.time.get_ticks() / 120.0))
                    _platform_overlay_surf.set_alpha(int(60 + 80 * pulse))
                    game_surface.blit(
                        _platform_overlay_surf,
                        screen_rect.topleft,
                        (0, 0, screen_rect.width, screen_rect.height),
                    )

        else:
            # Fallback to simple tiling (for static levels without tilemap)
            for tile in tiles:
                screen_rect = camera.apply(tile)
                tile_index = (tile.x // 32 + tile.y // 32) % 3
                tile_surface = tile_loader.get_tile(current_biome, "solid", tile_index)
                game_surface.blit(tile_surface, screen_rect)

            for platform in static_platforms:
                screen_rect = camera.apply(platform)
                tile_index = (platform.x // 32 + platform.y // 32) % 2
                tile_surface = tile_loader.get_tile(current_biome, "platform", tile_index)
                game_surface.blit(tile_surface, screen_rect)

            for platform_data in dynamic_platforms:
                if not platform_data.get("visible", True):
                    continue
                rect = platform_data["rect"]
                screen_rect = camera.apply(rect)
                tile_type = (
                    "platform_moving" if platform_data["type"] == "moving" else "platform_falling"
                )
                tile_surface = tile_loader.get_tile(current_biome, tile_type, 0)
                game_surface.blit(tile_surface, screen_rect)

        profiler.end("render_tiles")

        # Draw particles behind player
        profiler.begin("render_particles")
        particles.update(1.0 / FPS)
        particles.draw(game_surface, camera)
        profiler.end("render_particles")

        # Draw hazards (behind pickups and player)
        profiler.begin("render_hazards")
        render_hazards(game_surface, hazard_manager.get_active_hazards(), camera)
        profiler.end("render_hazards")

        # Draw pickups (before player so they appear behind)
        profiler.begin("render_pickups")
        render_pickups(game_surface, pickup_manager.get_alive_pickups(), camera)
        profiler.end("render_pickups")

        # Draw portals
        profiler.begin("render_portals")
        for portal in portal_manager.portals:
            draw_portal(game_surface, portal, int(camera.x), int(camera.y))
        profiler.end("render_portals")

        # Draw enemies (v0.6.0)
        profiler.begin("render_enemies")
        for enemy in enemy_manager.enemies.values():
            # Get enemy bounding box from definition
            ex, ey, ew, eh = enemy.get_rect()
            enemy_rect = pygame.Rect(ex, ey, ew, eh)
            screen_enemy_rect = camera.apply(enemy_rect)

            # Draw enemy with procedural character art
            draw_enemy(game_surface, enemy, screen_enemy_rect, pygame.time.get_ticks())

            # Draw attack telegraph effects
            if enemy.ai_state == EnemyAIState.ATTACK:
                if enemy.attack_substate == EnemyAttackSubState.WINDUP:
                    # WINDUP TELEGRAPH: Red glow + pulsing exclamation mark
                    pulse = abs(math.sin(enemy.attack_substate_timer * 10.0))

                    # Red glow overlay — pre-allocated surface, set_alpha avoids SRCALPHA alloc
                    _atk_glow_surf.set_alpha(int(120 * pulse))
                    game_surface.blit(
                        _atk_glow_surf,
                        screen_enemy_rect.topleft,
                        (0, 0, screen_enemy_rect.width, screen_enemy_rect.height),
                    )

                    # Exclamation mark above enemy
                    exclaim_x = screen_enemy_rect.centerx
                    exclaim_y = screen_enemy_rect.top - 30
                    exclaim_size = 8 + int(4 * pulse)  # Pulsing size

                    # Draw exclamation mark (! symbol)
                    # Vertical bar
                    pygame.draw.rect(
                        game_surface,
                        (255, 255, 0),
                        pygame.Rect(exclaim_x - 2, exclaim_y, 4, exclaim_size),
                    )
                    # Dot
                    pygame.draw.circle(
                        game_surface, (255, 255, 0), (exclaim_x, exclaim_y + exclaim_size + 3), 2
                    )

                    # Spawn warning particles
                    if int(enemy.attack_substate_timer * 10) % 3 == 0:  # Every 0.3s
                        enemy_center = enemy.get_center()
                        # Convert world coordinates to screen coordinates
                        screen_x = enemy_center[0] - int(camera.x)
                        screen_y = enemy_center[1] - int(camera.y)
                        particles.emit_attack_warning(screen_x, screen_y, count=3)

                elif enemy.attack_substate == EnemyAttackSubState.ACTIVE:
                    # ACTIVE PHASE: Bright flash + impact particles

                    # White flash overlay — pre-allocated surface
                    _atk_flash_surf.set_alpha(200)
                    game_surface.blit(
                        _atk_flash_surf,
                        screen_enemy_rect.topleft,
                        (0, 0, screen_enemy_rect.width, screen_enemy_rect.height),
                    )

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
                    # RECOVERY: Slight darkening — pre-allocated surface
                    _atk_recovery_surf.set_alpha(60)
                    game_surface.blit(
                        _atk_recovery_surf,
                        screen_enemy_rect.topleft,
                        (0, 0, screen_enemy_rect.width, screen_enemy_rect.height),
                    )

            # Draw health bar above enemy
            if enemy.health_state.current_hp < enemy.health_state.max_hp:
                health_bar_width = screen_enemy_rect.width
                health_bar_height = 4
                health_bar_x = screen_enemy_rect.centerx - health_bar_width // 2
                health_bar_y = screen_enemy_rect.top - 8

                # Background (red)
                bg_rect = pygame.Rect(
                    health_bar_x, health_bar_y, health_bar_width, health_bar_height
                )
                pygame.draw.rect(game_surface, (100, 0, 0), bg_rect)

                # Foreground (green, proportional to current HP)
                hp_ratio = enemy.health_state.current_hp / enemy.health_state.max_hp
                fg_width = int(health_bar_width * hp_ratio)
                fg_rect = pygame.Rect(health_bar_x, health_bar_y, fg_width, health_bar_height)
                pygame.draw.rect(game_surface, (0, 200, 0), fg_rect)

        # Draw sword attack hitbox (debug visualizer — F3 to toggle)
        if attack_fx_rect and show_debug_overlay:
            fx_rect_screen = camera.apply(attack_fx_rect)
            pulse = abs(math.sin(pygame.time.get_ticks() / 120.0))
            color = (255, int(120 + 80 * pulse), 60)
            pygame.draw.rect(game_surface, color, fx_rect_screen, width=2)

        # Draw goblin forward dagger hitboxes during active attack
        for enemy in enemy_manager.enemies.values():
            if (
                enemy.enemy_type == EnemyType.GOBLIN
                and enemy.ai_state == EnemyAIState.ATTACK
                and enemy.attack_substate == EnemyAttackSubState.ACTIVE
            ):
                hb = enemy.get_attack_hitbox()
                if hb:
                    hb_screen = camera.apply(
                        pygame.Rect(int(hb[0]), int(hb[1]), int(hb[2]), int(hb[3]))
                    )
                    pulse = abs(math.sin(pygame.time.get_ticks() / 80.0))
                    pygame.draw.rect(
                        game_surface, (255, int(180 + 60 * pulse), 60), hb_screen, width=2
                    )

        # Draw enemy arrows (skeleton projectiles)
        _cam_ox = camera._offset_x
        _cam_oy = camera._offset_y
        for arrow in enemy_manager.get_enemy_arrows():
            ax = int(arrow.x) + _cam_ox
            ay = int(arrow.y) + _cam_oy
            angle_rad = math.atan2(arrow.vy, arrow.vx)
            shaft_color = (180, 140, 80)
            tip_color = (200, 200, 210)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            # Shaft
            tip_x = ax + int(cos_a * arrow.width)
            tip_y = ay + int(sin_a * arrow.width)
            ay_mid = ay + arrow.height // 2
            tip_y_mid = tip_y + arrow.height // 2
            pygame.draw.line(game_surface, shaft_color, (ax, ay_mid), (tip_x, tip_y_mid), 2)
            # Tip
            pygame.draw.circle(game_surface, tip_color, (tip_x, tip_y_mid), 2)
            # Fletching (small v at tail)
            tail_x = ax - int(cos_a * 4)
            tail_y = ay_mid - int(sin_a * 4)
            perp_cos = math.cos(angle_rad + math.pi / 2)
            perp_sin = math.sin(angle_rad + math.pi / 2)
            pygame.draw.line(
                game_surface,
                (120, 80, 60),
                (tail_x, tail_y),
                (tail_x + int(perp_cos * 3), tail_y + int(perp_sin * 3)),
                1,
            )
            pygame.draw.line(
                game_surface,
                (120, 80, 60),
                (tail_x, tail_y),
                (tail_x - int(perp_cos * 3), tail_y - int(perp_sin * 3)),
                1,
            )

        # Draw active boss
        if boss_manager.is_boss_active():
            active_boss = boss_manager.get_active_boss()
            if active_boss:
                bx, by, bw, bh = active_boss.get_rect()
                boss_screen_rect = camera.apply(pygame.Rect(int(bx), int(by), bw, bh))
                # Boss body (dark crimson fill)
                pygame.draw.rect(game_surface, (120, 20, 20), boss_screen_rect)
                pygame.draw.rect(game_surface, (220, 60, 60), boss_screen_rect, width=3)
                # Health bar above boss
                defn = active_boss.get_definition()
                hp_ratio = active_boss.health / defn.max_health if defn.max_health > 0 else 0
                bar_w = boss_screen_rect.width
                bar_rect = pygame.Rect(boss_screen_rect.x, boss_screen_rect.y - 12, bar_w, 8)
                pygame.draw.rect(game_surface, (60, 0, 0), bar_rect)
                pygame.draw.rect(
                    game_surface,
                    (220, 40, 40),
                    pygame.Rect(bar_rect.x, bar_rect.y, int(bar_w * hp_ratio), 8),
                )
                # Boss name label
                _boss_font = pygame.font.Font(None, 18)
                lbl = _boss_font.render(defn.display_name, True, (255, 200, 200))
                game_surface.blit(
                    lbl, (boss_screen_rect.centerx - lbl.get_width() // 2, bar_rect.y - 14)
                )
            # Draw boss projectiles
            for proj in boss_manager.get_projectiles():
                px, py, pw, ph = proj.get_rect()
                proj_screen = camera.apply(pygame.Rect(int(px), int(py), pw, ph))
                pygame.draw.ellipse(game_surface, (255, 140, 40), proj_screen)

        profiler.end("render_enemies")

        # Draw NPCs (v0.6.0 - Phase 2)
        profiler.begin("render_npcs")
        for npc in npc_manager.npcs:
            # Get NPC bounding box
            npc_rect = pygame.Rect(npc.x, npc.y, npc.width, npc.height)
            screen_npc_rect = camera.apply(npc_rect)

            # Get NPC definition and draw with procedural character art
            npc_def = npc_manager.get_npc_definition(npc.npc_id)
            draw_npc_char(game_surface, npc, npc_def, screen_npc_rect, pygame.time.get_ticks())
        profiler.end("render_npcs")

        # Draw player (with camera transform and real sprite animations)
        profiler.begin("render_player")
        player_rect = player.get_rect()
        screen_player_rect = camera.apply(player_rect)
        player_state_name = get_player_render_state(player)

        # Determine sprite facing.
        # During attack animations, lock to committed facing; skip wall inversion so sprite doesn't flip mid-combo.
        _attack_states = {
            "attack",
            "slash1",
            "slash2",
            "slash3",
            "slash_air",
            "jump_slash",
            "throw_ground",
            "throw_crouch",
            "throw_air",
        }
        sprite_facing = player.state.facing or 1
        if player_state_name not in _attack_states:
            if player.state.physics.on_wall and not player.state.physics.on_ground:
                sprite_facing = -sprite_facing  # Face away from wall

        # Get sprite frame — use AnimationStateMachine when available (correct
        # transition reset for non-looping anims), fall back to SpriteManager.
        #
        # Attack frames (114×124px natural) are wider than the player hitbox
        # (28×56px). Squashing them to hitbox width causes heavy distortion.
        # For attack states: scale by height only (preserve aspect ratio), then
        # anchor the player-body portion of the frame over the hitbox center.
        # Idle body width ~64px at natural size; at hitbox-height scale that is
        # approximately the same width as the hitbox itself.
        _hitbox_h = screen_player_rect.height
        _hitbox_w = screen_player_rect.width
        _is_attack = player_state_name in _attack_states

        # Fetch raw (unscaled) surface so we can choose target size below
        _raw_surf: pygame.Surface | None = None
        if getattr(player, "anim_sm", None) is not None:
            player.anim_sm.transition(player_state_name)
            _raw_surf = player.anim_sm.get_frame(sprite_facing)

        if _raw_surf is not None:
            nat_w, nat_h = _raw_surf.get_size()
            if _is_attack and nat_h > 0:
                # Scale to hitbox height, let width be natural
                scale_w = max(1, int(nat_w * _hitbox_h / nat_h))
                scaled_surf = pygame.transform.scale(_raw_surf, (scale_w, _hitbox_h))
            else:
                scaled_surf = pygame.transform.scale(_raw_surf, (_hitbox_w, _hitbox_h))
            frame = SpriteFrame(surface=scaled_surf)
        else:
            if _is_attack:
                # SpriteManager path: get at natural size then scale height only
                raw_frame = sprite_manager.get_frame(
                    player_state_name, sprite_facing, pygame.time.get_ticks()
                )
                nat_w, nat_h = raw_frame.surface.get_size()
                scale_w = max(1, int(nat_w * _hitbox_h / nat_h)) if nat_h > 0 else _hitbox_w
                scaled_surf = pygame.transform.scale(raw_frame.surface, (scale_w, _hitbox_h))
                frame = SpriteFrame(surface=scaled_surf)
            else:
                frame = sprite_manager.get_scaled_frame(
                    player_state_name,
                    sprite_facing,
                    pygame.time.get_ticks(),
                    target_size=(_hitbox_w, _hitbox_h),
                )

        # Position sprite: for attack states anchor the body portion (left ~hitbox_w
        # of the frame when facing right) over the hitbox; for others center it.
        if _is_attack:
            # Estimate scaled body width as the hitbox width (idle frame scales to ≈hitbox_w)
            body_w = _hitbox_w
            if sprite_facing >= 0:
                # Facing right: body is on the left, sword extends right
                sprite_rect = frame.surface.get_rect()
                sprite_rect.centery = screen_player_rect.centery
                sprite_rect.left = screen_player_rect.left
            else:
                # Facing left: sprite is flipped — body on right, sword extends left
                sprite_rect = frame.surface.get_rect()
                sprite_rect.centery = screen_player_rect.centery
                sprite_rect.right = screen_player_rect.right
        else:
            sprite_rect = frame.surface.get_rect(center=screen_player_rect.center)
        # Teleport phase overlay: show semi-transparent ghost at cursor
        if player.state.is_teleporting_phase and getattr(player, "teleport", None):
            phase_pos = player.teleport.phase_cursor or (
                player.state.physics.x,
                player.state.physics.y,
            )
            phase_rect = pygame.Rect(
                int(phase_pos[0]), int(phase_pos[1]), player_rect.width, player_rect.height
            )
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
                # White flash: blit sprite then overlay pre-allocated white surface.
                # During attack the sprite frame is wider than the hitbox; clamp
                # the flash overlay to the hitbox area so it doesn't create a wide
                # white blob over the sword-effect region.
                game_surface.blit(frame.surface, sprite_rect)
                _player_flash_surf.set_alpha(160)
                flash_rect = screen_player_rect if _is_attack else sprite_rect
                game_surface.blit(
                    _player_flash_surf,
                    flash_rect.topleft,
                    (0, 0, flash_rect.width, flash_rect.height),
                )
            else:
                game_surface.blit(frame.surface, sprite_rect)
        else:
            game_surface.blit(frame.surface, sprite_rect)
        profiler.end("render_player")

        # Draw remote players (N4 — ghost silhouettes for networked peers)
        if _remote_players:
            _rp_renderer.draw_all(
                game_surface, _remote_players, camera, float(pygame.time.get_ticks())
            )

        # Draw Yin & Yang companion orbs (v0.7.0 - The Hollowed Ninja)
        profiler.begin("render_companions")
        if story_manager.yin_yang_present:
            companion_orbs.update(
                1.0 / FPS,
                player.state.physics.x,
                player.state.physics.y,
                player.state.physics.width,
                player.state.physics.height,
            )
            companion_orbs.render(
                game_surface,
                player.state.physics.x,
                player.state.physics.y,
                player.state.physics.width,
                player.state.physics.height,
                camera.x,
                camera.y,
            )

        profiler.end("render_companions")

        # Draw shuriken projectiles (sprite + collision box)
        profiler.begin("render_projectiles")
        if getattr(player, "shuriken", None) and player.shuriken.projectiles:
            shuriken_spin = (pygame.time.get_ticks() * 0.6) % 360
            for idx, proj in enumerate(player.shuriken.projectiles):
                proj_rect = pygame.Rect(int(proj.x), int(proj.y), proj.width, proj.height)
                screen_proj_rect = camera.apply(proj_rect)

                if shuriken_base:
                    base_w = max(1, shuriken_base.get_width())
                    scale = max(0.1, screen_proj_rect.width / base_w)
                    if proj.stuck:
                        sprite = pygame.transform.smoothscale(
                            shuriken_base, (screen_proj_rect.width, screen_proj_rect.height)
                        )
                        game_surface.blit(sprite, screen_proj_rect.topleft)
                    else:
                        angle = (shuriken_spin + idx * 45) % 360
                        sprite = pygame.transform.rotozoom(shuriken_base, angle, scale)
                        sprite_rect = sprite.get_rect(center=screen_proj_rect.center)
                        game_surface.blit(sprite, sprite_rect)
                else:
                    pygame.draw.rect(game_surface, (200, 200, 210), screen_proj_rect)

                # Collision box visualizer
                pygame.draw.rect(game_surface, (255, 0, 255), screen_proj_rect, width=1)
        profiler.end("render_projectiles")

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

            incomplete = objective_tracker.get_incomplete_objectives()

            # Boss missions: boss is always primary target while alive.
            # Other objectives are suppressed until boss is defeated.
            boss_objs = [o for o in incomplete if o.objective_type.value == "defeat_boss"]
            if boss_objs and boss_manager.is_boss_active():
                active_boss = boss_manager.get_active_boss()
                if active_boss:
                    return active_boss.get_center()
                return None  # boss obj incomplete but no entity yet — wait

            # Boss obj present but boss already dead (or not spawned) — fall through
            # to normal objective priority only for non-boss objectives.
            non_boss_incomplete = [o for o in incomplete if o.objective_type.value != "defeat_boss"]

            kill_objs = [
                o for o in non_boss_incomplete if o.objective_type.value == "kill_all_enemies"
            ]
            collect_objs = [
                o for o in non_boss_incomplete if o.objective_type.value == "collect_items"
            ]
            reach_objs = [
                o for o in non_boss_incomplete if o.objective_type.value == "reach_location"
            ]

            player_center = (
                player.state.physics.x + player.state.physics.width / 2,
                player.state.physics.y + player.state.physics.height / 2,
            )

            if kill_objs and enemy_manager.enemies:
                living = [e for e in enemy_manager.enemies.values() if not e.is_dead()]
                if living:
                    living.sort(
                        key=lambda e: (e.get_center()[0] - player_center[0]) ** 2
                        + (e.get_center()[1] - player_center[1]) ** 2
                    )
                    return living[0].get_center()

            if collect_objs:
                pickups = [
                    p
                    for p in pickup_manager.get_alive_pickups()
                    if p.pickup_type in ("collectible", "coin")
                ]
                if pickups:
                    pickups.sort(
                        key=lambda p: (p.x - player_center[0]) ** 2 + (p.y - player_center[1]) ** 2
                    )
                    target_pickup = pickups[0]
                    return (
                        target_pickup.x + target_pickup.width / 2,
                        target_pickup.y + target_pickup.height / 2,
                    )

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
            left_point = (
                end_x + math.cos(left_angle) * head_len,
                end_y + math.sin(left_angle) * head_len,
            )
            right_point = (
                end_x + math.cos(right_angle) * head_len,
                end_y + math.sin(right_angle) * head_len,
            )
            pygame.draw.polygon(
                game_surface, (255, 215, 0), [(end_x, end_y), left_point, right_point]
            )

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
                coins=pickup_stats["coins"],
                collectibles=pickup_stats["collectibles"],
            )
        elif show_fps_overlay:
            fps_text = hud.small.render(f"FPS: {clock_pygame.get_fps():.0f}", True, (220, 220, 230))
            game_surface.blit(fps_text, (12, 10))

        # Inventory UI overlay
        if inventory_ui.is_open():
            items_payload = []
            for slot in player_inventory.slots:
                if slot:
                    item_def = item_manager.get_item(slot.item_id) if item_manager else None
                    items_payload.append(
                        {
                            "name": item_def.display_name if item_def else slot.item_id,
                            "quantity": slot.quantity,
                            "rarity": item_def.rarity.value if item_def else "common",
                        }
                    )
                else:
                    items_payload.append(None)
            inventory_ui.draw(
                game_surface,
                items=items_payload,
                currency=player_inventory.currency,
                equipped_weapon=player_inventory.equipped_weapon,
                equipped_armor=player_inventory.equipped_armor,
            )

        # Health HUD (v0.6.0) - Draw hearts in top-left
        profiler.begin("render_hud")
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
            if (
                player.state.health_state.current_hp <= 1
                and i < player.state.health_state.current_hp
            ):
                pulse = abs(math.sin(pygame.time.get_ticks() / 200.0))
                warning_alpha = int(100 * pulse)
                _heart_warn_surf.set_alpha(warning_alpha)
                game_surface.blit(
                    _heart_warn_surf, (heart_x, health_y), (0, 0, heart_size, heart_size)
                )

        # Objective HUD (v0.6.0) - Only for campaign/playtest modes
        if (
            objective_hud_renderer
            and objective_tracker
            and objective_tracker.get_active_objectives()
        ):
            # Convert objective states to display format
            from rendering.objective_hud import ObjectiveDisplay

            objective_displays = []
            active_mission_id = getattr(objective_tracker, "active_mission_id", None)
            for obj_state in objective_tracker.get_active_objectives():
                # Use detailed description from mission data when available
                description = (
                    get_objective_display_text(obj_state, active_mission_id)
                    if active_mission_id
                    else "Objective"
                )

                objective_displays.append(
                    ObjectiveDisplay(
                        description=description,
                        current=obj_state.current_value,
                        target=obj_state.target_value,
                        completed=obj_state.is_complete,
                        objective_type=obj_state.objective_type.value,
                    )
                )

            objective_hud_renderer.draw_objectives(game_surface, objective_displays)

        # Compass indicators (nearest coin, exit direction, room type)
        if use_procedural and world and megamap:
            # Get player center position
            player_center = (
                player.state.physics.x + player.state.physics.width / 2,
                player.state.physics.y + player.state.physics.height / 2,
            )

            # Find nearest coin
            nearest_coin_pos = None
            min_dist = float("inf")
            for pickup in pickup_manager.get_alive_pickups():
                if pickup.pickup_type == "coin":
                    coin_center = (pickup.x + pickup.width / 2, pickup.y + pickup.height / 2)
                    dx = coin_center[0] - player_center[0]
                    dy = coin_center[1] - player_center[1]
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_coin_pos = coin_center

            # Get current room type
            current_room_coords = get_current_room_coords(
                megamap, (player.state.physics.x, player.state.physics.y)
            )
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
                    key=lambda entry: (entry[1][0] - player_center[0]) ** 2
                    + (entry[1][1] - player_center[1]) ** 2
                )

            # Draw compass
            hud.draw_compass_indicators(
                game_surface,
                player_center,
                nearest_coin_pos,
                (exit_x, exit_y) if exit_x and exit_y else None,
                current_room_type,
                portal_targets,
            )

        # Minimap / full map toggles (for procedural worlds)
        if minimap and world and megamap:
            player_pos = (player.state.physics.x, player.state.physics.y)
            current_room_coords = get_current_room_coords(megamap, player_pos)
            if show_full_map:
                # Temporary full-map: draw overlay and render minimap scaled up
                game_surface.blit(_fullmap_overlay_surf, (0, 0))
                old_scale = minimap.config.scale
                old_pos = minimap.config.position
                # Scale to occupy ~85% of screen and center
                minx, miny, maxx, maxy = world.bounds
                span_w = maxx - minx + 1
                span_h = maxy - miny + 1
                screen_w = game_surface.get_width()
                screen_h = game_surface.get_height()
                target_w = int(screen_w * 0.85)
                target_h = int(screen_h * 0.85)
                padding = 8
                scale_w = (target_w - 2 * padding) // max(1, span_w)
                scale_h = (target_h - 2 * padding) // max(1, span_h)
                minimap.config.scale = max(6, min(scale_w, scale_h))
                minimap_w = span_w * minimap.config.scale + 2 * padding
                minimap_h = span_h * minimap.config.scale + 2 * padding
                minimap.config.position = (
                    max(0, (screen_w - minimap_w) // 2),
                    max(0, (screen_h - minimap_h) // 2),
                )
                minimap.render(game_surface, world, megamap, player_pos, current_room_coords)
                minimap.config.scale = old_scale
                minimap.config.position = old_pos
            elif show_minimap:
                minimap.render(game_surface, world, megamap, player_pos, current_room_coords)

        # NPC Indicators (v0.6.0 - Phase 2) - Show icons above NPCs (!, $, ?)
        npc_indicator_renderer.render(
            surface=game_surface, npc_manager=npc_manager, camera_x=camera.x, camera_y=camera.y
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
            camera_y=camera.y,
        )

        # Dialogue UI (modal)
        if game_state_manager.is_dialogue():
            current_node = dialogue_manager.get_current_node()
            if current_node:
                dialogue_ui.render(
                    game_surface, current_node, dialogue_manager.get_available_choices()
                )

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
                    npc_items.append(
                        {
                            "name": display_name,
                            "price": shop_item.price,
                            "quantity": shop_item.stock,
                            "item_id": shop_item.item_id,
                        }
                    )

            player_items = []
            for slot in player_inventory.slots:
                if slot is None:
                    continue
                item_def = item_manager.get_item(slot.item_id)
                display_name = item_def.display_name if item_def else slot.item_id
                sell_price = 0
                if shop_inventory and item_def:
                    sell_price = shop_inventory.calculate_sell_price(item_def)
                player_items.append(
                    {
                        "name": display_name,
                        "sell_price": sell_price,
                        "quantity": slot.quantity,
                        "item_id": slot.item_id,
                    }
                )

            shop_ui.draw(
                game_surface,
                npc_items=npc_items,
                player_items=player_items,
                player_currency=player_inventory.currency,
                npc_currency=npc_currency,
            )

        # Victory screen (if level complete)
        if level_complete:
            victory_screen.render(game_surface, level_manager.get_stats(), 1.0 / FPS)

        # Cover gameplay behind launch/menu screens
        if game_state_manager.is_menu() or game_state_manager.is_landing():
            if landing_bg:
                bg = pygame.transform.smoothscale(landing_bg, (GAME_WIDTH, GAME_HEIGHT))
                game_surface.blit(bg, (0, 0))
            else:
                game_surface.fill((8, 10, 18))

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
                text_box_rect = pygame.Rect(
                    100, GAME_HEIGHT - text_box_height - 50, GAME_WIDTH - 200, text_box_height
                )
                pygame.draw.rect(game_surface, (20, 20, 30), text_box_rect)
                pygame.draw.rect(game_surface, (100, 100, 120), text_box_rect, 3)

                # Render text (word-wrapped)
                font = pygame.font.Font(None, 28)
                words = cutscene_text.split(" ")
                lines = []
                current_line = []
                max_width = text_box_rect.width - 40

                for word in words:
                    test_line = " ".join(current_line + [word])
                    if font.size(test_line)[0] <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))

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
            context_words = choice_data["context"].split(" ")
            lines = []
            current_line = []
            max_width = 800

            for word in context_words:
                test_line = " ".join(current_line + [word])
                if context_font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))

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
                desc_words = choice["description"].split(" ")
                desc_line = []
                for word in desc_words:
                    test = " ".join(desc_line + [word])
                    if desc_font.size(test)[0] <= button_width - 40:
                        desc_line.append(word)
                    else:
                        if desc_line:
                            desc_lines.append(" ".join(desc_line))
                        desc_line = [word]
                if desc_line:
                    desc_lines.append(" ".join(desc_line))

                desc_y = button_rect.y + 55
                for desc_line_text in desc_lines[:3]:  # Max 3 lines
                    desc_surface = desc_font.render(desc_line_text, True, (160, 160, 180))
                    game_surface.blit(desc_surface, (button_rect.x + 20, desc_y))
                    desc_y += 20

                # Draw hint
                hint_font = pygame.font.Font(None, 18)
                hint_surface = hint_font.render(
                    f"[Press {idx + 1}] {choice['outcome_hint']}", True, (120, 120, 140)
                )
                game_surface.blit(hint_surface, (button_rect.x + 20, button_rect.bottom - 20))

            # Draw shared outcome
            shared_font = pygame.font.Font(None, 22)
            shared_text = shared_font.render(choice_data["shared_outcome"], True, (150, 150, 170))
            shared_rect = shared_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT - 50))
            game_surface.blit(shared_text, shared_rect)

        profiler.end("render_hud")

        # Render debug ability menu on top of everything (F9)
        if _debug_ability_menu is not None:
            _debug_ability_menu.render(game_surface)

        # Auto-save periodically
        persist_story_state_wrapper()  # Update story state before auto-save (v0.7.0)
        save_manager.auto_save(time.time())

        # Present game surface to window with letterboxing
        profiler.begin("present")
        if not headless:
            camera.present(screen)

            # Render developer console overlay (DEV build only)
            if dev_console:
                dev_console.render(screen)

            pygame.display.flip()
        profiler.end("present")
        profiler.end("render")
        profiler.end_frame()
        clock_pygame.tick(FPS)

    # Profiler shutdown — print summary and write final CSV rows
    profiler.print_summary()
    profiler.close()

    # Final save on exit
    if save_manager.needs_save:
        persist_story_state_wrapper()  # Save story state (v0.7.0)
        save_manager.save(force=True)
        print("[SAVE] Final save on exit")

    # Cleanup
    player.cleanup()

    # Auto-open logs folder for TESTING build on exit
    if build_config.auto_open_logs_on_exit:
        from utils.platform_utils import open_folder_in_explorer

        print("\n" + "=" * 60)
        print("TESTING BUILD - Opening replay and log directories...")
        print("=" * 60)

        # Open replays folder
        replays_folder = user_data_dir / "replays"
        if replays_folder.exists():
            print(f"Opening replays: {replays_folder}")
            open_folder_in_explorer(replays_folder)

        # Open logs folder
        logs_folder = user_data_dir / "logs"
        if logs_folder.exists():
            print(f"Opening logs: {logs_folder}")
            open_folder_in_explorer(logs_folder)

        print("\nPlease share these files with the development team!")
        print("=" * 60)

    pygame.quit()

    if _net_client is not None:
        _net_client.disconnect()

    input_pipeline.finalize()

    print("\n[OK] Game exited cleanly")
    print("=" * 60)


if __name__ == "__main__":
    main()
