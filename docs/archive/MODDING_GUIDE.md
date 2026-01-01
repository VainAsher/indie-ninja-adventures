# Vain Asher Gaming's: Indie Ninja Adventures Modding Guide

Welcome to Vain Asher Gaming's: Indie Ninja Adventures modding! This guide explains how to create mods for the game.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Entity System](#entity-system)
3. [Component System](#component-system)
4. [Creating Your First Mod](#creating-your-first-mod)
5. [API Reference](#api-reference)
6. [Examples](#examples)

---

## Architecture Overview

Vain Asher Gaming's: Indie Ninja Adventures uses a **component-based entity system** that allows for extensible, reusable behaviors. The architecture is designed specifically for modding:

### Key Concepts

- **Entities**: Game objects (players, NPCs, enemies, projectiles)
- **Components**: Behaviors attached to entities (Health, AI, Movement)
- **Systems**: Update loops that process components (Physics, Collision, AI)
- **Events**: Decoupled communication between systems

### Why This Architecture?

✅ **NPCs and Enemies reuse Player mechanics** - No code duplication
✅ **Mods can add custom entities** - Full extensibility
✅ **Components are modular** - Mix and match behaviors
✅ **Event-driven** - Systems don't depend on each other

---

## Entity System

### Entity Types

```python
from core import EntityType

EntityType.PLAYER      # Controlled by player input
EntityType.NPC         # Friendly non-player characters
EntityType.ENEMY       # Hostile entities
EntityType.PROJECTILE  # Bullets, fireballs, etc.
EntityType.PICKUP      # Coins, health, powerups
EntityType.HAZARD      # Spikes, lava, etc.
EntityType.CUSTOM      # Your custom types!
```

### Creating Entities

```python
# In your mod
def on_load(self, game_context):
    entity_manager = game_context.entity_manager

    # Create an enemy with physics
    from core import PhysicsState
    physics = PhysicsState(x=100, y=100, vx=0, vy=0, width=32, height=32)

    enemy = entity_manager.create_entity(
        entity_type=EntityType.ENEMY,
        physics=physics,
        tags={"hostile", "flying"}
    )

    # Attach components
    from entities.components import HealthComponent, PatrolComponent

    health = HealthComponent(enemy.entity_id, max_health=3)
    patrol = PatrolComponent(enemy.entity_id, speed=2.0, patrol_distance=100.0)

    enemy.add_component(health)
    enemy.add_component(patrol)

    # Initialize components
    health.initialize(entity_manager)
    patrol.initialize(entity_manager)
```

---

## Component System

### Built-in Components

Vain Asher Gaming's: Indie Ninja Adventures provides reusable components in `entities/components.py`:

#### **HealthComponent**
Health management with damage, healing, and invincibility.

```python
from entities.components import HealthComponent

health = HealthComponent(
    entity_id=entity.entity_id,
    max_health=5,
    invincibility_duration=1.2
)

# Use it
health.take_damage(1, source="spike")
health.heal(2)
is_alive = health.is_alive()
```

#### **PatrolComponent**
Entity patrols back and forth.

```python
from entities.components import PatrolComponent

patrol = PatrolComponent(
    entity_id=entity.entity_id,
    speed=2.0,
    patrol_distance=100.0
)
```

#### **FollowComponent**
Entity chases another entity (e.g., enemy follows player).

```python
from entities.components import FollowComponent

follow = FollowComponent(
    entity_id=enemy.entity_id,
    target_entity_id=player.entity_id,
    speed=3.0,
    follow_distance=50.0
)
```

#### **ProjectileComponent**
Projectile with velocity and lifetime.

```python
from entities.components import ProjectileComponent

projectile_comp = ProjectileComponent(
    entity_id=projectile.entity_id,
    velocity_x=10.0,
    velocity_y=0.0,
    lifetime=5.0,
    damage=1
)
```

#### **PickupComponent**
Collectible item (coins, health, etc.).

```python
from entities.components import PickupComponent

pickup = PickupComponent(
    entity_id=coin.entity_id,
    pickup_type="coin",
    value=100,
    collection_radius=16.0
)
```

### Creating Custom Components

```python
from core import Component

class TeleportComponent(Component):
    """Custom component: Teleports entity periodically"""

    def __init__(self, entity_id: int, teleport_interval: float = 5.0):
        super().__init__(entity_id)
        self.teleport_interval = teleport_interval
        self.timer = 0.0

    def update(self, dt: float, entity_manager):
        """Called every physics tick"""
        self.timer += dt

        if self.timer >= self.teleport_interval:
            entity = entity_manager.get_entity(self.entity_id)
            if entity and entity.physics:
                import random
                entity.physics.x = random.randint(0, 800)
                entity.physics.y = random.randint(0, 600)

            self.timer = 0.0

    def cleanup(self):
        """Called when component is removed"""
        pass
```

---

## Creating Your First Mod

### Step 1: Create Mod Directory

```
user_data/mods/my_first_mod/
├── mod.json         # Mod metadata
└── main.py          # Entry point
```

### Step 2: Create `mod.json`

```json
{
  "mod_id": "my_first_mod",
  "name": "My First Mod",
  "version": "1.0.0",
  "author": "YourName",
  "description": "Adds flying enemies to the game",
  "dependencies": [],
  "entry_point": "main.py"
}
```

### Step 3: Create `main.py`

```python
from core import ModInterface, GameContext, EntityType, PhysicsState
from core import TickEvent
from entities.components import HealthComponent, PatrolComponent

class MyFirstMod(ModInterface):
    """My first mod!"""

    def __init__(self):
        super().__init__("my_first_mod")
        self.flying_enemies = []

    def on_load(self, game_context: GameContext):
        """Called when mod loads"""
        game_context.logger.info("My First Mod loading...")

        # Subscribe to tick events
        game_context.event_bus.subscribe(TickEvent, self.on_tick)

        # Register spawn hook
        game_context.register_hook("on_level_start", self.spawn_flying_enemy)

    def on_enable(self, game_context: GameContext):
        """Called when mod is enabled"""
        game_context.logger.info("My First Mod enabled!")

    def spawn_flying_enemy(self, game_context: GameContext):
        """Spawn a flying enemy"""
        entity_manager = game_context.entity_manager

        # Create enemy entity
        physics = PhysicsState(x=200, y=100, vx=0, vy=0, width=32, height=32)
        enemy = entity_manager.create_entity(
            entity_type=EntityType.ENEMY,
            physics=physics,
            tags={"hostile", "flying"}
        )

        # Add components
        health = HealthComponent(enemy.entity_id, max_health=3)
        patrol = PatrolComponent(enemy.entity_id, speed=2.0, patrol_distance=150.0)

        enemy.add_component(health)
        enemy.add_component(patrol)

        health.initialize(entity_manager)
        patrol.initialize(entity_manager)

        self.flying_enemies.append(enemy.entity_id)
        game_context.logger.info(f"Spawned flying enemy: {enemy.entity_id}")

    def on_tick(self, event: TickEvent):
        """Called every physics tick"""
        # Custom per-frame logic here
        pass

    def on_disable(self, game_context: GameContext):
        """Called when mod is disabled"""
        # Clean up entities
        entity_manager = game_context.entity_manager
        for enemy_id in self.flying_enemies:
            entity_manager.destroy_entity(enemy_id, reason="mod_disabled")
        self.flying_enemies.clear()

    def on_unload(self, game_context: GameContext):
        """Called when mod unloads"""
        game_context.logger.info("My First Mod unloaded")

# Required: Return mod instance
def get_mod():
    return MyFirstMod()
```

### Step 4: Load Your Mod

The game automatically loads mods from `user_data/mods/` on startup.

Check logs at: `user_data/logs/VainAsherGamings_IndieNinjaAdventures_YYYY-MM-DD_HH-MM-SS.log`

---

## API Reference

### GameContext

Provided to mods for accessing game systems.

```python
class GameContext:
    event_bus: EventBus            # Event system
    component_registry: ComponentRegistry  # Register custom components
    entity_manager: EntityManager  # Create/destroy entities
    logger: logging.Logger         # Logging

    def register_hook(hook_name: str, callback: Callable)
    def trigger_hook(hook_name: str, *args, **kwargs)
```

### EntityManager

```python
# Create entity
entity = entity_manager.create_entity(
    entity_type: EntityType,
    physics: Optional[PhysicsState],
    tags: Optional[Set[str]]
)

# Destroy entity
entity_manager.destroy_entity(entity_id: int, reason: str)

# Query entities
entities = entity_manager.get_entities_by_type(EntityType.ENEMY)
entities = entity_manager.get_entities_by_tag("hostile")
entities = entity_manager.get_entities_with_component(HealthComponent)

# Get entity
entity = entity_manager.get_entity(entity_id: int)
```

### Component

```python
class CustomComponent(Component):
    def __init__(self, entity_id: int, **kwargs):
        super().__init__(entity_id)
        # Custom initialization

    def initialize(self, entity_manager: EntityManager):
        # Called when attached to entity
        pass

    def update(self, dt: float, entity_manager: EntityManager):
        # Called every physics tick
        pass

    def cleanup(self):
        # Called when removed or entity destroyed
        pass
```

### Events

Subscribe to events:

```python
from core import TickEvent, CollisionEvent, PickupCollectedEvent

def on_tick(event: TickEvent):
    print(f"Tick {event.tick_number}")

game_context.event_bus.subscribe(TickEvent, on_tick)
```

Emit custom events:

```python
from core import Event

class CustomEvent(Event):
    def __init__(self, data: str):
        super().__init__()
        self.data = data

game_context.event_bus.emit(CustomEvent("Hello"))
```

---

## Examples

### Example 1: Boss Enemy

```python
from core import Component, EntityType, PhysicsState
from entities.components import HealthComponent, FollowComponent

def spawn_boss(game_context):
    entity_manager = game_context.entity_manager

    # Create boss
    physics = PhysicsState(x=400, y=100, vx=0, vy=0, width=64, height=64)
    boss = entity_manager.create_entity(
        entity_type=EntityType.ENEMY,
        physics=physics,
        tags={"boss", "hostile"}
    )

    # Big health pool
    health = HealthComponent(boss.entity_id, max_health=50)
    boss.add_component(health)

    # Chase player
    players = entity_manager.get_entities_by_type(EntityType.PLAYER)
    if players:
        follow = FollowComponent(
            boss.entity_id,
            players[0].entity_id,
            speed=4.0
        )
        boss.add_component(follow)

    health.initialize(entity_manager)
    follow.initialize(entity_manager)
```

### Example 2: Healing Pickup

```python
from entities.components import PickupComponent

def spawn_health_pickup(game_context, x, y):
    entity_manager = game_context.entity_manager

    physics = PhysicsState(x=x, y=y, vx=0, vy=0, width=16, height=16)
    pickup = entity_manager.create_entity(
        entity_type=EntityType.PICKUP,
        physics=physics
    )

    pickup_comp = PickupComponent(
        pickup.entity_id,
        pickup_type="health",
        value=2,
        collection_radius=20.0
    )
    pickup.add_component(pickup_comp)
    pickup_comp.initialize(entity_manager)
```

### Example 3: Wave Spawner

```python
class WaveSpawnerComponent(Component):
    """Spawns waves of enemies"""

    def __init__(self, entity_id: int, wave_interval: float = 10.0):
        super().__init__(entity_id)
        self.wave_interval = wave_interval
        self.timer = 0.0
        self.wave_number = 0

    def update(self, dt: float, entity_manager):
        self.timer += dt

        if self.timer >= self.wave_interval:
            self._spawn_wave(entity_manager)
            self.timer = 0.0

    def _spawn_wave(self, entity_manager):
        self.wave_number += 1
        enemy_count = 2 + self.wave_number  # More enemies each wave

        for i in range(enemy_count):
            physics = PhysicsState(
                x=100 + i * 50, y=100,
                vx=0, vy=0, width=32, height=32
            )
            enemy = entity_manager.create_entity(
                entity_type=EntityType.ENEMY,
                physics=physics,
                tags={"wave_enemy"}
            )

            from entities.components import HealthComponent
            health = HealthComponent(enemy.entity_id, max_health=2)
            enemy.add_component(health)
            health.initialize(entity_manager)
```

---

## Best Practices

1. **Always initialize components** after attaching them to entities
2. **Use tags** for efficient entity queries
3. **Clean up** in `on_disable()` and `on_unload()`
4. **Log important events** for debugging
5. **Handle missing entities** gracefully (they may be destroyed)
6. **Subscribe to events** in `on_load()`, unsubscribe in `on_unload()`
7. **Use custom_data** for mod-specific entity data

---

## Troubleshooting

**Mod not loading?**
- Check `user_data/logs/` for error messages
- Verify `mod.json` is valid JSON
- Ensure `get_mod()` function exists in entry point

**Components not working?**
- Did you call `component.initialize(entity_manager)`?
- Is the component enabled? (`component.enabled = True`)
- Check entity still exists (`entity_manager.get_entity(id)`)

**Entity disappeared?**
- Check if health reached zero
- Check collision system destroyed it
- Check logs for `EntityDestroyedEvent`

---

## Advanced Topics

### Networking

Entities are network-ready if you stick to deterministic logic:
- Avoid `random.random()` (use seeded RNG)
- Avoid `time.time()` (use tick count)
- Keep component updates deterministic

### Performance

- Use entity pools for frequently spawned entities
- Query by tag/type instead of iterating all entities
- Disable components when not needed
- Destroy entities when off-screen

---

Happy modding! Join our community at [discord/github] for help and to share your creations!
