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

from .clock import GameClock, Timer
from .entity_system import (
    Component,
    ComponentRegistry,
    Entity,
    EntityDestroyedEvent,
    EntityManager,
    EntitySpawnedEvent,
    EntityType,
)
from .event_bus import (
    CollisionEvent,
    Event,
    EventBus,
    InputCommandEvent,
    PickupCollectedEvent,
    PlayerDamagedEvent,
    RenderEvent,
    StateTransitionEvent,
    TickEvent,
    VelocityChangeEvent,
)
from .logger import GameLogger, LoggerFactory, MechanicLogger
from .mod_system import GameContext, ModInterface, ModLoader, ModMetadata
from .state import GameState, PhysicsState, PlayerState, StateManager

__all__ = [
    # Event Bus
    "EventBus",
    "Event",
    "TickEvent",
    "RenderEvent",
    "InputCommandEvent",
    "CollisionEvent",
    "VelocityChangeEvent",
    "PickupCollectedEvent",
    "PlayerDamagedEvent",
    "StateTransitionEvent",
    # Logger
    "GameLogger",
    "MechanicLogger",
    "LoggerFactory",
    # Clock
    "GameClock",
    "Timer",
    # State
    "PhysicsState",
    "PlayerState",
    "GameState",
    "StateManager",
    # Entity System
    "Entity",
    "EntityType",
    "EntityManager",
    "Component",
    "ComponentRegistry",
    "EntitySpawnedEvent",
    "EntityDestroyedEvent",
    # Mod System
    "ModInterface",
    "ModMetadata",
    "ModLoader",
    "GameContext",
]
