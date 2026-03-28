# Vain Asher Gaming's: Indie Ninja Adventures - Complete System Overview

## Table of Contents
1. [Architecture](#architecture)
2. [Core Systems](#core-systems)
3. [Player Mechanics](#player-mechanics)
4. [Testing](#testing)
5. [Quick Start](#quick-start)
6. [API Reference](#api-reference)

---

## Architecture

Vain Asher Gaming's: Indie Ninja Adventures is built with a **modular, event-driven architecture** designed for multiplayer readiness, extensibility, and maintainability.

### Key Principles

- **Event-Driven**: Systems communicate via pub/sub events (no tight coupling)
- **Modular Mechanics**: Each ability is a self-contained, reusable component
- **Deterministic**: Fixed 60Hz physics for network synchronization
- **Component-Based Entities**: Players, NPCs, enemies share mechanics
- **Network-Ready**: Serializable state, deterministic simulation

### Project Structure

```text
indie-ninja-adventures/
├── core/                      # Engine infrastructure
│   ├── event_bus.py          # Pub/sub event system
│   ├── logger.py             # Persistent rotating logs
│   ├── clock.py              # Fixed 60Hz timestep (Glenn Fiedler pattern)
│   ├── state.py              # Serializable state (5 s history for replay/rollback)
│   ├── entity_system.py      # Component-based entity manager
│   └── mod_system.py         # Plugin architecture with lifecycle hooks
│
├── systems/                   # High-level game systems
│   ├── collision_system.py   # AABB + swept collision
│   ├── physics_system.py     # Gravity, velocity, tile effects
│   ├── camera_system.py      # Multi-mode camera with letterboxing
│   ├── world_generation.py   # Procedural world — 7 BiomeTheme values
│   ├── zone_planning.py      # 16×16 zone grid per room
│   ├── room_generation.py    # Tilemap from zone roles
│   ├── connectivity.py       # BFS + fallback spine connectivity
│   ├── autotiling.py         # 3×3 neighbor autotile detection
│   ├── save_system.py        # JSON persistence
│   ├── hazard_spawner.py     # Spike/lava/poison/void placement
│   └── pickup_spawner.py     # Coin/health/item placement
│
├── mechanics/                 # Player mechanics (modular, each extends BaseMechanic)
│   ├── base.py               # BaseMechanic interface
│   ├── movement.py           # Ground/air acceleration
│   ├── jump.py               # Ground, double, wall, coyote, buffer
│   ├── dash.py               # Dash with cooldown
│   ├── wall_slide.py         # Wall friction/cling (active — see note below)
│   ├── crouch.py             # Stealth movement
│   ├── combat.py             # Attack combo chain
│   ├── damage.py             # Hurt, death, respawn, i-frames
│   ├── shuriken.py           # Shuriken throw mechanic
│   ├── teleport.py           # Teleport mechanic
│   └── ninjutsu.py           # Ninjutsu stance/cast
│
├── entities/                  # Game entities
│   ├── player.py             # Player orchestrator (wires all mechanics)
│   ├── enemy_manager.py      # Enemy spawning and update (5 types)
│   ├── enemy_ai.py           # Enemy AI behaviours
│   ├── boss_manager.py       # Boss spawning (6 types — NOT YET WIRED)
│   ├── npc_manager.py        # Story-driven NPC spawning
│   ├── hazards.py            # Hazard entity logic
│   └── pickups.py            # Pickup entity logic
│
├── game/                      # Game loop subsystems
│   ├── game_initialization.py # All managers wired here
│   ├── game_state.py         # GameStateManager (LANDING/MENU/PLAYING/PAUSED/…)
│   ├── hub_manager.py        # Hub world generation per region
│   ├── level_factory.py      # Mission level construction
│   ├── mission_system.py     # Mission definitions (30 missions, 6 regions)
│   ├── mission_manager.py    # Mission state tracking
│   ├── objective_tracker.py  # Objective progress + exit unlock
│   ├── campaign_manager.py   # Region/ability unlock progression
│   ├── story_manager.py      # Story acts and events
│   ├── dialogue_system.py    # NPC conversation trees
│   ├── inventory_system.py   # Player items
│   ├── trading_system.py     # NPC shop trades
│   └── loot_system.py        # Loot drop logic
│
├── rendering/                 # Rendering subsystems
│   ├── animation_system.py   # Sprite sheet state machine
│   ├── tile_loader.py        # PNG tile assets — loads, scales, caches
│   ├── sprite_manager.py     # Frame extraction, flip cache
│   ├── particles.py          # Dust, dash, impact particles
│   ├── hazard_renderer.py    # Hazard visuals
│   ├── enemy_renderer.py     # Enemy visuals
│   └── pickup_renderer.py    # Pickup visuals
│
├── ui/                        # UI components
│   ├── menu_system.py        # Main, pause, settings menus
│   ├── hud.py                # Health, objectives, minimap
│   ├── inventory_ui.py       # Inventory overlay
│   ├── dialogue_ui.py        # Dialogue box
│   ├── mission_menu_ui.py    # Mission selection screen
│   └── tutorial_system.py    # Tutorial overlays
│
├── assets/                    # Game assets
│   ├── biomes/               # Tile PNGs per biome (dungeon/cave/building/forest/town/sewer/hollow)
│   ├── sprites/              # Player and NPC sprite sheets
│   └── splash/               # Splash screen assets
│
├── data/                      # Game data
│   └── missions.json         # Mission definitions (30 missions)
│
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests per module
│   └── integration/          # Integration tests
│
├── build/                     # Build scripts (PyInstaller)
├── utils/                     # Shared utilities
├── demo_game.py               # Main game executable (~3,600 lines)
└── docs/                      # Documentation
```

**Wall slide note**: `mechanics/wall_slide.py` is active — the mechanic applies light wall friction (vy clamp) when the player touches a wall. An older stamina-based implementation was previously disabled; the current implementation is a lighter, always-on version.

---

## Core Systems

### 1. Event Bus (`core/event_bus.py`)

**Central pub/sub system with priority-based handlers**

```python
from core import EventBus, TickEvent

bus = EventBus()

def on_tick(event: TickEvent):
    print(f"Tick: {event.tick_number}, dt={event.dt}")

bus.subscribe(TickEvent, on_tick, priority=50)
bus.process()  # Call once per frame
```

**Key Events:**
- `TickEvent` - Fixed 60Hz physics tick
- `RenderEvent` - Variable render with interpolation
- `CollisionEvent` - Entity collisions
- `VelocityChangeEvent` - Velocity modifications
- `PickupCollectedEvent` - Item collection
- `PlayerDamagedEvent` - Damage events

### 2. Logging System (`core/logger.py`)

**Multi-level persistent logging with user-configurable location**

```python
from core import GameLogger

logger = GameLogger()  # Default location
# Or custom: logger = GameLogger(user_data_dir=Path("C:/MyGames/NinjaDash"))

game_log = logger.get_logger("game")
game_log.info("Game started")
game_log.debug("Detailed state info")
game_log.warning("Performance issue detected")
game_log.error("Critical failure")
```

**Features:**
- **Persistent storage**: Logs saved to platform-specific directories
  - Windows: `%APPDATA%/NinjaDash/logs/`
  - macOS: `~/Library/Application Support/NinjaDash/logs/`
  - Linux: `~/.local/share/ninjadash/logs/`
- **Session files**: `VainAsherGamings_IndieNinjaAdventures_YYYY-MM-DD_HH-MM-SS.log`
- **Rotating**: 10MB per file, 3 backups (30MB total)
- **User-configurable**: Change log directory from in-game settings

### 3. Game Clock (`core/clock.py`)

**Fixed timestep physics with variable render**

```python
from core import GameClock, EventBus

bus = EventBus()
clock = GameClock(bus, target_fps=60)

while running:
    # Clock emits TickEvent (fixed 60Hz) and RenderEvent (variable)
    clock.tick()
    bus.process()
```

**Features:**
- Fixed 60Hz physics (deterministic)
- Variable render rate with interpolation
- Spiral of death prevention
- Performance tracking

### 4. Collision System (`systems/collision_system.py`)

**Universal collision detection for all entities**

```python
from systems import CollisionSystem
from core import EntityManager, EventBus

bus = EventBus()
entity_manager = EntityManager(bus, logger)
collision_system = CollisionSystem(bus, entity_manager, logger)

# Set level tiles
collision_system.set_tiles([ground_rect, wall_rect])

# Check collisions (called after movement)
collision_system.check_and_resolve(entity)

# Advanced queries
entities_nearby = collision_system.get_entities_in_radius(x, y, radius)
hit = collision_system.raycast(start_x, start_y, end_x, end_y)
```

**Features:**
- AABB collision detection
- Penetration resolution
- Collision events for all collisions
- Radius queries, raycasting
- Entity-entity collision

### 5. Entity System (`core/entity_system.py`)

**Component-based architecture for reusable behaviors**

```python
from core import EntityManager, EntityType, PhysicsState

entity_manager = EntityManager(bus, logger)

# Create entity
physics = PhysicsState(x=100, y=100, vx=0, vy=0, width=20, height=20)
player = entity_manager.create_entity(EntityType.PLAYER, physics, tags={"player"})

# Add components
player.add_component(HealthComponent(player.entity_id, max_health=5))

# Query
players = entity_manager.get_entities_by_tag("player")
entities_with_health = entity_manager.get_entities_with_component(HealthComponent)
```

### 6. Camera System (`systems/camera_system.py`)

**Multi-mode camera with smooth following and letterboxing**

```python
from systems.camera_system import CameraSystem, CameraMode, CameraConfig

# Create camera
config = CameraConfig(
    virtual_width=1280,
    virtual_height=720,
    follow_speed=0.1,  # Smooth lerp (0-1)
    deadzone_x=100,    # Horizontal deadzone
    deadzone_y=80      # Vertical deadzone
)
camera = CameraSystem(config)

# Set bounds
camera.set_world_bounds(5120, 5120)  # Total world size
camera.set_room_bounds(0, 0, 640, 640)  # Current room

# Set mode
camera.set_mode(CameraMode.WORLD_CLAMP)  # or ROOM_CLAMP, FREE, LOCKED

# Update each frame
camera.update(player.x, player.y)

# Get rendering viewport
viewport = camera.get_viewport()  # Returns (x, y, width, height)
letterbox_bars = camera.get_letterbox_bars(window_width, window_height)
```

**Features:**

- **Multi-mode support**: WORLD_CLAMP, ROOM_CLAMP, FREE, LOCKED
- **Smooth following**: Configurable lerp and deadzone
- **Responsive letterboxing**: Maintains aspect ratio at any window size
- **Virtual resolution**: 1280×720 scaled to physical display
- **Bounds clamping**: Prevents camera from showing out-of-bounds areas

**Camera Modes:**

- `WORLD_CLAMP`: Follow player, clamp to world boundaries (for large open worlds)
- `ROOM_CLAMP`: Follow player, clamp to current room (for room-based games)
- `FREE`: Manual camera control, no following (for debugging/spectating)
- `LOCKED`: Camera fixed in place (for cutscenes/fixed-screen sections)

### 7. Settings System (`config/settings.py`)

**Persistent game settings stored in user_data/settings/**

```python
from config import GameSettings

# Initialize settings (loads from user_data/settings/settings.json)
settings = GameSettings()

# Get settings
volume = settings.get("volume_music", default=0.7)
fullscreen = settings.get("fullscreen", default=False)

# Set settings
settings.set("volume_music", 0.8)
settings.set("fullscreen", True)

# Save changes to disk
settings.save()

# Reset to defaults
settings.reset_to_defaults()

# Get all settings
all_settings = settings.get_all()
```

**Features**:
- **Automatic persistence**: Settings stored in `user_data/settings/settings.json`
- **Default values**: Sensible defaults for all settings
- **Merge on load**: New settings added to defaults without losing user preferences
- **JSON format**: Human-readable and editable

**Default Settings**:
- **Audio**: `volume_master`, `volume_music`, `volume_sfx`
- **Display**: `fullscreen`, `vsync`, `window_width`, `window_height`
- **Gameplay**: `screenshake`, `particles`, `camera_smoothing`
- **Controls**: `key_left`, `key_right`, `key_jump`, `key_dash`, `key_crouch`
- **Developer**: `show_fps`, `show_hitboxes`, `log_level`

### 8. World Generation System (`systems/world_generation.py`, `zone_planning.py`, `room_generation.py`)

**Procedural metroidvania-style world generation**

```python
from systems.world_generation import WorldGenerator
from systems.zone_planning import ZonePlanner
from systems.room_generation import RoomGenerator, tilemap_to_collision_rects

# Step 1: Generate World
world_gen = WorldGenerator(seed=12345)
world = world_gen.generate(num_biomes=2, rooms_per_biome=8)

# Step 2: Plan Zones
zone_planner = ZonePlanner(seed=12345)
for room in world.all_rooms:
    room.zone_grid = zone_planner.plan_room(room)

# Step 3: Generate Tilemaps
room_gen = RoomGenerator()
for room in world.all_rooms:
    room.tilemap = room_gen.generate_tilemap(room)

# Step 4: Use in game
collision_rects = tilemap_to_collision_rects(world.start_room.tilemap, tile_size=32)
collision_system.set_tiles(collision_rects)
```

**Features:**
- Seed-based deterministic generation (same seed = same world)
- Hierarchical structure: World → Biomes → Rooms → Zones (16×16) → Tilemap (160×160)
- 7 biome themes: DUNGEON, CAVE, BUILDING, FOREST, TOWN, SEWER, HOLLOW
- Room types: START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS
- BFS connectivity validation (guarantees all critical zones are reachable)
- Door port system with proper alignment
- Performance: Generates 30-room world in ~2-5ms

**See [WORLD_GENERATION.md](WORLD_GENERATION.md) for complete API documentation**

---

## Player Mechanics

All mechanics are modular, self-contained, and reusable.

### Movement Mechanic (`mechanics/movement.py`)

**Ground/air acceleration with different physics**

```python
from mechanics import MovementMechanic

movement = MovementMechanic(entity_id=0, event_bus=bus, logger=logger)

# Set input
movement.set_input(direction=1)  # -1=left, 0=stop, 1=right

# Process tick
movement.on_tick(state, dt=1/60)

# Modifiers
movement.set_speed_multiplier(0.6)  # 60% speed (for crouch)
movement.lock_movement(True)  # Lock during dash
```

**Characteristics:**
- **Ground**: High acceleration (0.9), high deceleration (1.1) - responsive
- **Air**: Low acceleration (0.5), low deceleration (0.6) - floaty
- **Max speed**: 8.0 units/tick

### Jump Mechanic (`mechanics/jump.py`)

**All jump types in one unified module**

```python
from mechanics import JumpMechanic

jump = JumpMechanic(
    entity_id=0,
    event_bus=bus,
    logger=logger,
    feature_flags={"double_jump": True, "wall_jump": True}
)

# Request jump
jump.request_jump()

# Process tick (handles buffering, coyote time, etc.)
jump.on_tick(state, dt=1/60)

# Collision response (reset jumps on landing)
jump.on_collision(state, collision_event)
```

**Features:**
- **Ground jump**: 14.5 units/tick power
- **Coyote time**: 0.12s grace period after leaving ground
- **Jump buffering**: 0.14s input window
- **Double jump**: Air jump (configurable max jumps)
- **Wall jump**: Horizontal boost (8.5x, 14.5y)
- **Crouch modifier**: 0.7x power when crouching

### Dash Mechanic (`mechanics/dash.py`)

**Quick burst of speed with cooldown**

```python
from mechanics import DashMechanic

dash = DashMechanic(entity_id=0, event_bus=bus, logger=logger)

# Request dash
dash.request_dash()

# Process tick
dash.on_tick(state, dt=1/60)

# Check if ready
if dash.can_activate(state):
    print("Dash is ready!")
```

**Characteristics:**
- **Speed**: 16.0 units/tick (double normal)
- **Duration**: 0.16s (~10 frames)
- **Cooldown**: 0.45s (~27 frames)
- **Cancellation**: Stops on wall collision

### Wall Slide Mechanic (`mechanics/wall_slide.py`)

The wall slide mechanic applies light wall friction (a vy clamp) when the player is in contact with a wall while airborne. This gives a controlled slide-down feel. A previous stamina-gated version was replaced with the current lighter always-on approach. Wall-jump coyote time is handled in `entities/player.py`.

### Crouch Mechanic (`mechanics/crouch.py`)

**Stealth movement with distinct feel**

```python
from mechanics import CrouchMechanic

crouch = CrouchMechanic(
    entity_id=0,
    event_bus=bus,
    logger=logger,
    collision_checker=collision_system  # For ceiling checks
)

# Toggle crouch
crouch.request_crouch_toggle()

# Process tick
crouch.on_tick(state, dt=1/60)

# Get modifiers for movement
modifiers = crouch.get_movement_modifier(state)
# Returns: {'speed_mult': 0.6, 'accel_mult': 0.8}
```

**Characteristics:**
- **Speed**: 60% of normal (slower, stealthy)
- **Acceleration**: 80% of normal (more gradual)
- **Height**: 50% of normal (collision box changes)
- **Jump**: 70% power when crouched
- **Ceiling check**: Can't stand if blocked

---

## Testing

All systems have comprehensive test coverage.

### Running Tests

```bash
python -m pytest tests/ -q          # all tests
python -m pytest tests/unit/ -q     # unit tests only
python -m pytest tests/ -x -q       # stop on first failure
```

### Test Organisation

Tests live in `tests/unit/` and `tests/integration/`. CI runs all tests headlessly via `SDL_VIDEODRIVER=dummy` so no display is needed.

**Test Coverage:**
- Core systems (event bus, logger, clock, state)
- Collision detection and resolution
- All jump types (ground, double, wall, coyote, buffer)
- Movement with ground/air physics
- Dash with cooldown
- Wall interaction regression (no wall sticking, correct grounding)
- Crouch with ceiling detection
- Full gameplay scenarios

---

## Quick Start

### Creating a Player

```python
from entities.player import Player
from core import EventBus, GameLogger

# Initialize systems
bus = EventBus()
logger = GameLogger()

# Create player
player = Player(
    player_id=0,
    spawn_x=100,
    spawn_y=100,
    event_bus=bus,
    logger_factory=logger,
    feature_flags={
        "double_jump": True,
        "wall_jump": True,
        "dash": True,
        "crouch": True
    }
)

# Game loop
while running:
    # Process input
    keys = pygame.key.get_pressed()
    player.process_input(keys)

    # Update (TickEvent triggers mechanics)
    clock.tick()
    bus.process()

    # Render
    rect = player.get_rect()
    pygame.draw.rect(screen, COLOR_PLAYER, rect)
```

### Processing Input

The Player class handles input and routes it to mechanics:

```python
keys = {
    pygame.K_a: True,      # Move left
    pygame.K_d: True,      # Move right
    pygame.K_SPACE: True,  # Jump
    pygame.K_LSHIFT: True, # Dash
    pygame.K_s: True,      # Crouch toggle
}

player.process_input(keys)
```

### Accessing State

```python
# Position
x, y = player.state.physics.x, player.state.physics.y

# Velocity
vx, vy = player.state.physics.vx, player.state.physics.vy

# Collision flags
on_ground = player.state.physics.on_ground
on_wall = player.state.physics.on_wall

# Timers
dash_cooldown = player.state.dash_cooldown
wall_stamina = player.state.wall_slide_stamina

# Status
is_dashing = player.state.is_dashing
is_crouching = player.state.crouching
health = player.state.health
```

---

## API Reference

### Player Class

```python
class Player:
    def __init__(player_id, spawn_x, spawn_y, event_bus, logger_factory,
                 collision_system=None, feature_flags=None)

    def process_input(keys: dict)
    def on_tick(event: TickEvent)
    def get_rect() -> pygame.Rect
    def reset(spawn_x, spawn_y)
    def is_alive() -> bool
    def take_damage(amount: int, source: str) -> bool
    def heal(amount: int) -> int
    def cleanup()
```

### Mechanic Interface

All mechanics inherit from `BaseMechanic`:

```python
class BaseMechanic(ABC):
    def on_tick(state: PlayerState, dt: float)
    def can_activate(state: PlayerState) -> bool
    def on_collision(state: PlayerState, collision_event: CollisionEvent)
    def reset(state: PlayerState)
    def enable() / disable()
    def cleanup()
```

### State Classes

```python
@dataclass
class PhysicsState:
    x, y: float                    # Position
    vx, vy: float                  # Velocity
    width, height: int             # Collision box
    on_ground, on_wall: bool       # Collision flags
    wall_dir: int                  # Wall direction (-1, 0, 1)

@dataclass
class PlayerState:
    player_id: int
    physics: PhysicsState
    health, max_health: int
    facing: int                    # Direction facing (-1, 1)
    crouching, is_dashing: bool

    # Timers
    coyote_time: float
    jump_buffer_time: float
    dash_cooldown, dash_time: float
    wall_jump_lock: float
    invincibility_time: float

    # Jump state
    jumps_left, max_jumps: int

    # wall slide (disabled) state
    wall_slide_stamina: float
    is_wall_sliding: bool
```

---

## Performance & Optimization

### Fixed Timestep Benefits
- **Deterministic**: Same inputs → same outputs
- **Network-friendly**: Predictable for sync
- **Replay-ready**: Record/playback supported
- **Frame-independent**: Physics stable at any FPS

### Event System Benefits
- **Decoupled**: Systems don't know about each other
- **Extensible**: Add new systems without modifying existing
- **Mod-friendly**: Mods can hook into any event
- **Testable**: Easy to test systems in isolation

### Logging Benefits
- **Debugging**: Trace state transitions
- **Performance**: Identify bottlenecks
- **User reports**: Include log files with bug reports
- **Post-mortem**: Analyze what went wrong

---

## Next Steps

1. **Implement Gravity System** - Apply gravity each tick
2. **Create Physics System** - Coordinate entity movement
3. **Add Input System** - Translate raw input to commands
4. **Implement Game Loop** - Wire everything together
5. **Add Rendering** - Sprite rendering with interpolation
6. **Create Levels** - Integrate level_gen.py
7. **Add Pickups** - Coins, health, lives
8. **Implement UI** - HUD, menus, settings
9. **Network Layer** - Client/server architecture
10. **Polish** - Particles, sound, juice

---

## Additional Resources

- **ARCHITECTURE.md** - Detailed system architecture and design patterns
- **MODDING_GUIDE.md** - Complete guide for mod developers
- **Test Scripts** - Comprehensive test coverage for all systems

---

## Summary

Vain Asher Gaming's: Indie Ninja Adventures v0.3 provides a solid foundation for a multiplayer-ready platformer with:

✅ **Core Infrastructure** - Event bus, logging, clock, state management
✅ **Collision System** - Universal collision for all entities
✅ **Player Mechanics** - Jump, movement, dash, crouch; wall slide implemented but currently disabled during wall interaction rework
✅ **Component System** - Reusable behaviors for players/NPCs/enemies
✅ **Modding Support** - Plugin architecture for extensibility
✅ **Test Coverage** - Comprehensive tests for all systems
✅ **Documentation** - Complete guides and API reference

The system is designed to scale from a simple platformer to a complex multiplayer game with full mod support.
