"""
Core infrastructure for Vain Asher Gaming's: Indie Ninja Adventures

This package contains the fundamental systems that power the game engine:
- Event bus for decoupled communication
- Logging with persistent storage
- Fixed-timestep game clock
- Serializable game state
- Entity system with component architecture
- Mod system for extensibility
"""

from .event_bus import (
    EventBus,
    Event,
    TickEvent,
    RenderEvent,
    InputCommandEvent,
    CollisionEvent,
    VelocityChangeEvent,
    PickupCollectedEvent,
    PlayerDamagedEvent,
    StateTransitionEvent
)
from .logger import GameLogger, MechanicLogger, LoggerFactory
from .clock import GameClock, Timer
from .state import PhysicsState, PlayerState, GameState, StateManager
from .entity_system import (
    Entity,
    EntityType,
    EntityManager,
    Component,
    ComponentRegistry,
    EntitySpawnedEvent,
    EntityDestroyedEvent
)
from .mod_system import (
    ModInterface,
    ModMetadata,
    ModLoader,
    GameContext
)

__all__ = [
    # Event Bus
    'EventBus',
    'Event',
    'TickEvent',
    'RenderEvent',
    'InputCommandEvent',
    'CollisionEvent',
    'VelocityChangeEvent',
    'PickupCollectedEvent',
    'PlayerDamagedEvent',
    'StateTransitionEvent',

    # Logger
    'GameLogger',
    'MechanicLogger',
    'LoggerFactory',

    # Clock
    'GameClock',
    'Timer',

    # State
    'PhysicsState',
    'PlayerState',
    'GameState',
    'StateManager',

    # Entity System
    'Entity',
    'EntityType',
    'EntityManager',
    'Component',
    'ComponentRegistry',
    'EntitySpawnedEvent',
    'EntityDestroyedEvent',

    # Mod System
    'ModInterface',
    'ModMetadata',
    'ModLoader',
    'GameContext',
]
