# Vain Asher Gaming's: Indie Ninja Adventures Architecture Documentation

## Overview

Vain Asher Gaming's: Indie Ninja Adventures is built with a **component-based entity system** and **event-driven architecture** designed for:
-  **Multiplayer** - Client/server ready with deterministic simulation
-  **Moddability** - Plugin system for custom entities and behaviors
-  **Reusability** - Players, NPCs, and enemies share components
-  **Extensibility** - Add features without modifying core

---

## Core Architecture Principles

### 1. Component-Based Entities

**Entities** are composed of **Components** that define behavior:

```
Player Entity = Physics + Health + Input + JumpMechanic + DashMechanic + ...
Enemy Entity = Physics + Health + AI + PatrolComponent + ...
NPC Entity = Physics + Health + AI + DialogComponent + ...
```

**Benefits:**
-  No code duplication between player/NPCs/enemies
-  Easy to add new entity types
-  Mods can create custom components
-  Mix and match behaviors

### 2. Event-Driven Communication

Systems communicate via **Events** instead of direct coupling:

```
CollisionSystem  emits  CollisionEvent
                  
JumpMechanic  subscribes  resets jumps on ground collision
HealthMechanic  subscribes  takes damage on hazard collision
```

**Benefits:**
-  Systems don't know about each other
-  Easy to add new systems
-  Mods can hook into any event
-  Deterministic for networking

### 3. Fixed Timestep Physics

Physics runs at **fixed 60Hz** for deterministic simulation:

```
Game Loop (variable FPS)
   TickEvent (fixed 0.0167s)  Physics/Mechanics
   RenderEvent (variable dt)  Rendering
```

**Benefits:**
-  Deterministic for networking
-  Predictable physics behavior
-  Same result on all machines
-  Replay-friendly

---

## System Architecture

### Core Systems (Phase 1 - COMPLETE)

#### 1. Event Bus (`core/event_bus.py`)
- Pub/sub event system
- Priority-based handlers
- Queue-based processing
- Thread-safe

**Events:**
- `TickEvent` - Fixed 60Hz physics tick
- `RenderEvent` - Variable render with interpolation
- `CollisionEvent` - Entity collisions
- `VelocityChangeEvent` - Velocity modifications
- `PickupCollectedEvent` - Item collection
- `PlayerDamagedEvent` - Damage events
- `EntitySpawnedEvent` - Entity creation
- `EntityDestroyedEvent` - Entity destruction

#### 2. Logger (`core/logger.py`)
- Persistent file storage
- Session-based log files
- Platform-specific directories
- User-configurable location
- DEBUG/INFO/WARNING/ERROR levels
- Rotating file handler (10MB  3)

**Log Locations:**
- Windows: `%APPDATA%/NinjaDash/logs/`
- macOS: `~/Library/Application Support/NinjaDash/logs/`
- Linux: `~/.local/share/ninjadash/logs/`

#### 3. Game Clock (`core/clock.py`)
- Fixed 60Hz physics (Glenn Fiedler pattern)
- Variable render rate
- Interpolation alpha for smooth rendering
- Spiral of death prevention
- Performance tracking

#### 4. State Management (`core/state.py`)
- Network-serializable state
- JSON serialization
- Snapshot/restore for rollback
- State history (5 seconds @ 60Hz)

**State Classes:**
- `PhysicsState` - Position, velocity, collision flags
- `PlayerState` - Complete player state
- `GameState` - Full game state

#### 5. Entity System (`core/entity_system.py`) - NEW!
- Component-based architecture
- Entity creation/destruction
- Fast queries (by type, tag, component)
- Entity pooling ready

**Features:**
- Reusable across players/NPCs/enemies
- Tag system for queries
- Custom data for mods
- Component lifecycle management

#### 6. Mod System (`core/mod_system.py`) - NEW!
- Plugin architecture
- Component registration
- Event hooks
- Lifecycle management (load/enable/disable/unload)

**Mod Interface:**
```python
class MyMod(ModInterface):
    def on_load(self, game_context): pass
    def on_enable(self, game_context): pass
    def on_disable(self, game_context): pass
    def on_unload(self, game_context): pass
```

#### 7. Camera System (`systems/camera_system.py`) - NEW

- Multi-mode camera (world boundaries, room boundaries, free cam, locked)
- Smooth following with deadzone and lerp
- Responsive letterboxing for any window size
- Virtual resolution (1280x720) scaled to physical display
- Bounds clamping for both world and room modes

**Camera Modes:**

- `WORLD_CLAMP`: Follow player, clamp to world boundaries
- `ROOM_CLAMP`: Follow player, clamp to current room boundaries
- `FREE`: Free camera control, no following
- `LOCKED`: Camera fixed in place

**Features:**
```python
from systems.camera_system import CameraSystem, CameraMode, CameraConfig

# Create camera
config = CameraConfig(
    virtual_width=1280,
    virtual_height=720,
    follow_speed=0.1,
    deadzone_x=100,
    deadzone_y=80
)
camera = CameraSystem(config)

# Set bounds and mode
camera.set_world_bounds(5120, 5120)  # World size
camera.set_room_bounds(0, 0, 640, 640)  # Current room
camera.set_mode(CameraMode.WORLD_CLAMP)

# Update each frame
camera.update(player_x, player_y)

# Get viewport for rendering
viewport = camera.get_viewport()
letterbox_bars = camera.get_letterbox_bars(window_width, window_height)
```

---

## Reusable Components

Built-in components in `entities/components.py`:

### 1. HealthComponent
Used by: Players, NPCs, Enemies, Bosses

```python
HealthComponent(
    entity_id,
    max_health=5,
    invincibility_duration=1.2
)
```

**Features:**
- Take damage with source tracking
- Healing
- Invincibility timer
- Death detection

### 2. PatrolComponent
Used by: Enemies, NPCs

```python
PatrolComponent(
    entity_id,
    speed=2.0,
    patrol_distance=100.0
)
```

**Features:**
- Automatic back-and-forth movement
- Configurable speed and range

### 3. FollowComponent
Used by: Enemies (chase player), Pets (follow player)

```python
FollowComponent(
    entity_id,
    target_entity_id,
    speed=3.0,
    follow_distance=50.0
)
```

**Features:**
- Tracks target entity
- Stops at follow distance
- Horizontal-only movement

### 4. ProjectileComponent
Used by: Bullets, fireballs, arrows

```python
ProjectileComponent(
    entity_id,
    velocity_x, velocity_y,
    lifetime=5.0,
    damage=1
)
```

**Features:**
- Straight-line movement
- Automatic timeout
- Damage value

### 5. PickupComponent
Used by: Coins, health, lives, powerups

```python
PickupComponent(
    entity_id,
    pickup_type="coin",
    value=1,
    collection_radius=16.0
)
```

**Features:**
- Auto-collect on proximity
- Emits PickupCollectedEvent
- Auto-destroy on collection

### 6. AIComponent
Used by: NPCs, Enemies

```python
AIComponent(
    entity_id,
    ai_type="patrol"  # idle, patrol, chase, flee
)
```

**Features:**
- State machine
- Target tracking
- Extensible behaviors

---

## Example Use Cases

### Player Entity
```python
player = entity_manager.create_entity(EntityType.PLAYER, physics, {"player"})
player.add_component(HealthComponent(player.entity_id, max_health=5))
player.add_component(JumpMechanic(player.entity_id, ...))
player.add_component(DashMechanic(player.entity_id, ...))
player.add_component(InputComponent(player.entity_id, ...))
```

### Enemy Entity
```python
enemy = entity_manager.create_entity(EntityType.ENEMY, physics, {"hostile"})
enemy.add_component(HealthComponent(enemy.entity_id, max_health=3))
enemy.add_component(PatrolComponent(enemy.entity_id, speed=2.0))
enemy.add_component(FollowComponent(enemy.entity_id, player.entity_id))
```

### NPC Entity
```python
npc = entity_manager.create_entity(EntityType.NPC, physics, {"friendly"})
npc.add_component(HealthComponent(npc.entity_id, max_health=10))
npc.add_component(DialogComponent(npc.entity_id, dialog_tree))
```

### Boss Entity
```python
boss = entity_manager.create_entity(EntityType.ENEMY, physics, {"boss", "hostile"})
boss.add_component(HealthComponent(boss.entity_id, max_health=50))
boss.add_component(AIComponent(boss.entity_id, ai_type="chase"))
boss.add_component(ProjectileSpawnerComponent(boss.entity_id))
```

---

## Modding Architecture

### Mod Structure
```
user_data/mods/my_mod/
 mod.json          # Metadata
 main.py           # Entry point
 components/       # Custom components
 assets/           # Sprites, sounds
 README.md         # Documentation
```

### Mod Capabilities

 **Add Custom Entities**
- Create new entity types
- Mix built-in and custom components

 **Add Custom Components**
- Register with ComponentRegistry
- Attach to any entity

 **Hook Into Events**
- Subscribe to all game events
- Emit custom events

 **Register Custom Hooks**
- `on_player_spawn`
- `on_level_complete`
- `on_enemy_death`
- Custom hooks

 **Modify Game Rules**
- Access game context
- Modify entity behaviors
- Add custom systems

### Security Considerations

 **Current Status**: Mods run in same process (full Python access)

**Future Improvements:**
- Sandboxed Python environment
- API whitelist
- Resource limits
- Mod signing/verification

---

## Network Architecture (Planned)

### Client/Server Split

```
Client                          Server
   Input System              Input Buffer
   Render System               Physics System (authoritative)
   Prediction                  Collision System
   Interpolation               Entity Manager
                                 State Snapshots
```

### Deterministic Simulation

Requirements for network play:
1.  Fixed 60Hz timestep
2.  Seeded RNG only
3.  Input command pattern
4.  Serializable state
5.  No time.time() or random.random()

### Network Components

- `InputCommand` - Serializable input
- `SnapshotSerializer` - State sync
- `InputBuffer` - Latency handling
- `ReplaySystem` - Determinism testing

---

## Performance Considerations

### Entity System
- **Entity pooling** - Reuse destroyed entities
- **Spatial hashing** - Fast collision queries
- **Component caching** - Cache common queries
- **Dirty flags** - Only update changed state

### Rendering
- **Interpolation** - Smooth rendering at variable FPS
- **Culling** - Don't render off-screen entities
- **Batching** - Batch draw calls by type

### Networking
- **Delta compression** - Send only changed state
- **Interest management** - Only sync relevant entities
- **Priority system** - Important entities update more

---

## Testing Strategy

### Unit Tests
- Core systems (event bus, clock, state)
- Components (health, patrol, follow)
- Entity manager (create, destroy, query)

### Integration Tests
- Systems working together
- Component interactions
- Event flow

### Determinism Tests
- Record inputs
- Replay twice with same seed
- Verify identical final state

### Mod Tests
- Load/unload lifecycle
- Component registration
- Event hooking

---

## Future Enhancements

### Phase 2: Collision System  COMPLETE

-  Extract from Player class
-  Collision events
-  Advanced collision resolution (platform, wall, ground, ceiling)
-  Swept collision for high-speed movement
-  Corner detection for smooth landings
- Quadtree/spatial hashing (deferred)

### Phase 3: Mechanics  COMPLETE

-  Modular JumpMechanic
-  Modular DashMechanic
-  Modular MovementMechanic
-  Modular CrouchMechanic
-  Modular WallSlideMechanic
-  Modular HealthMechanic

### Phase 4: Systems  MOSTLY COMPLETE

-  PhysicsSystem
-  CameraSystem (multi-mode with letterboxing)
-  InputSystem (via Player class)
- PickupSystem (deferred)
- AISystem (deferred)

### Phase 5: Network
- Input command pattern
- State synchronization
- Client prediction
- Server reconciliation

### Phase 6: Polish
- Asset loading system
- Animation system
- Sound system
- Particle effects

---

## Conclusion

This architecture provides:
-  **Reusability** - Components shared across entity types
-  **Extensibility** - Mods can add anything
-  **Maintainability** - Clean separation of concerns
-  **Network-ready** - Deterministic simulation
-  **Performance** - Optimized for thousands of entities

The system is designed to scale from a simple platformer to a complex multiplayer game with mod support.
