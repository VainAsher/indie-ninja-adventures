# Modding System

**Indie Ninja Adventures** | v0.7.1 | 2026-03-28

---

## Rationale

The modding system exists to make the game extensible without forking the source. It exposes a clean plugin API (entities, components, events, hooks) so community mods can add content without touching core code. The architecture was designed this way deliberately: the same component/event-driven decoupling that keeps systems testable also makes them safely extensible from outside.

---

## Architecture

```
user_data/mods/
└── my_mod/
    ├── mod.json     ← manifest (id, name, version, author, dependencies, entry_point)
    └── main.py      ← ModInterface subclass + get_mod() factory

ModLoader (core/mod_system.py)
  └── discover_mods()     scan user_data/mods/ for dirs containing mod.json
  └── load_mod(path)      importlib.util loads entry_point; calls on_load(context)
  └── enable_all_mods()   calls on_enable(context) for every loaded mod
```

**Key classes** in `core/mod_system.py`:

| Class | Role |
| --- | --- |
| `ModInterface` | Base class mods extend. Four lifecycle hooks: `on_load`, `on_enable`, `on_disable`, `on_unload`. |
| `ModMetadata` | Dataclass from `mod.json`. Fields: `mod_id`, `name`, `version`, `author`, `description`, `dependencies`, `entry_point`. |
| `GameContext` | Injected into all lifecycle hooks. Gateway to `event_bus`, `component_registry`, and `logger`. Custom hooks via `register_hook` / `trigger_hook`. |
| `ModLoader` | Discovers, loads, enables, and disables mods. Stores as `dict[mod_id → ModInterface]`. |

---

## Lifecycle

```
startup
  ModLoader.load_all_mods()
    → mod.on_load(context)       ← subscribe events, register hooks, register components

game running
  ModLoader.enable_all_mods()
    → mod.on_enable(context)     ← spawn entities, activate behaviors

in-game disable (future hot-reload)
    → mod.on_disable(context)    ← destroy entities, deactivate behaviors

shutdown
    → mod.on_unload(context)     ← unsubscribe events, final cleanup
```

---

## GameContext API

```python
class GameContext:
    event_bus: EventBus            # subscribe/emit events
    component_registry: ComponentRegistry  # register custom component types
    logger: logging.Logger         # mod-scoped logger

    def register_hook(hook_name: str, callback: Callable)
    def trigger_hook(hook_name: str, *args, **kwargs)
```

`entity_manager` is referenced in the archive guide but is not a direct field of `GameContext` in the current implementation — access entities via event subscribers or registered hooks that receive game objects as arguments.

---

## Built-in Components

Available from `entities/components.py`:

| Component | Purpose | Key params |
| --- | --- | --- |
| `HealthComponent` | HP, damage, heal, invincibility | `max_health`, `invincibility_duration` |
| `PatrolComponent` | Back-and-forth patrol | `speed`, `patrol_distance` |
| `FollowComponent` | Chase a target entity | `target_entity_id`, `speed`, `follow_distance` |
| `ProjectileComponent` | Moving projectile with lifetime | `velocity_x`, `velocity_y`, `lifetime`, `damage` |
| `PickupComponent` | Collectible item | `pickup_type`, `value`, `collection_radius` |

All components implement `initialize(entity_manager)`, `update(dt, entity_manager)`, and `cleanup()`.

---

## Creating a Mod

### 1. Directory structure

```
user_data/mods/my_mod/
├── mod.json
└── main.py
```

### 2. `mod.json`

```json
{
  "mod_id": "my_mod",
  "name": "My Mod",
  "version": "1.0.0",
  "author": "YourName",
  "description": "What it does",
  "dependencies": [],
  "entry_point": "main.py"
}
```

### 3. `main.py`

```python
from core.mod_system import ModInterface, GameContext
from core.event_bus import TickEvent

class MyMod(ModInterface):
    def __init__(self):
        super().__init__("my_mod")

    def on_load(self, game_context: GameContext):
        game_context.event_bus.subscribe(TickEvent, self._on_tick)
        game_context.register_hook("on_level_start", self._on_level_start)
        game_context.logger.info("MyMod loaded")

    def _on_tick(self, event: TickEvent):
        pass  # per-frame logic

    def _on_level_start(self, game_context: GameContext):
        pass  # spawn entities, etc.

    def on_disable(self, game_context: GameContext):
        pass  # clean up any entities spawned

def get_mod():
    return MyMod()
```

The `get_mod()` function is **required** — the loader calls it to get the mod instance.

---

## Custom Components

```python
from core.entity_system import Component

class MyComponent(Component):
    def __init__(self, entity_id: int, value: int = 0):
        super().__init__(entity_id)
        self.value = value

    def initialize(self, entity_manager):
        pass  # called once when attached

    def update(self, dt: float, entity_manager):
        pass  # called every physics tick

    def cleanup(self):
        pass  # called on removal or entity destruction
```

Register the type so the system knows about it:

```python
game_context.component_registry.register_component("my_component", MyComponent)
```

---

## Subscribing to Events

```python
from core.event_bus import TickEvent, CollisionEvent, PickupCollectedEvent

game_context.event_bus.subscribe(TickEvent, self._on_tick)
```

Custom events:

```python
from core.event_bus import Event

class MyEvent(Event):
    def __init__(self, data: str):
        super().__init__()
        self.data = data

game_context.event_bus.emit(MyEvent("hello"))
```

---

## Mod Loading

Mods are loaded automatically at startup from `user_data/mods/`. The game logs results to `user_data/logs/`.

**Troubleshooting**:

| Symptom | Check |
| --- | --- |
| Mod not found | `user_data/mods/<mod_id>/mod.json` must exist |
| Mod fails to load | `get_mod()` function must exist and return a `ModInterface` subclass |
| Components not updating | Call `component.initialize(entity_manager)` after `entity.add_component()` |
| Mod not in log | Check `user_data/logs/` for Python import errors |

---

## Current Status

The modding system is **fully implemented** in `core/mod_system.py`. It is not wired to a UI — there is no in-game mod browser. The `ModLoader` runs at startup and is available to the game loop. Mods can subscribe to events and register components.

The original guide lives in `docs/archive/MODDING_GUIDE.md` and remains the authoritative reference for examples. This document covers the architecture and current API state.
