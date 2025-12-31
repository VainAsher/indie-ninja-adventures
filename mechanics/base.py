"""
Base Mechanic - Interface for all player mechanics

Mechanics are modular, reusable components that implement specific player abilities:
- JumpMechanic - All jump types
- DashMechanic - Dash with cooldown
- MovementMechanic - Ground/air movement
- CrouchMechanic - Crouch toggle
- WallSlideMechanic - Wall slide

Mechanics:
- Subscribe to events (collision, input, etc.)
- Update state every tick
- Can be enabled/disabled via feature flags
- Are reusable across players, NPCs, enemies
"""

from abc import ABC, abstractmethod
from typing import Optional
from core.event_bus import EventBus, Event, CollisionEvent
from core.logger import MechanicLogger
from core.state import PlayerState


class BaseMechanic(ABC):
    """
    Base class for all player mechanics

    Mechanics add gameplay functionality through composition.
    Each mechanic handles one specific ability (jump, dash, etc.)
    """

    def __init__(self, entity_id: int, event_bus: EventBus, logger: MechanicLogger):
        """
        Initialize mechanic

        Args:
            entity_id: Entity this mechanic is attached to
            event_bus: Event bus for subscribing to events
            logger: Logger for this mechanic
        """
        self.entity_id = entity_id
        self.event_bus = event_bus
        self.logger = logger
        self.enabled = True

    @abstractmethod
    def on_tick(self, state: PlayerState, dt: float):
        """
        Process physics tick (modify state)

        Called every physics tick (60Hz). Mechanics should:
        - Update internal timers
        - Check for activation conditions
        - Modify state (velocity, position, flags)

        Args:
            state: Player state to modify
            dt: Delta time (always 1/60 = 0.0167s)
        """
        pass

    @abstractmethod
    def can_activate(self, state: PlayerState) -> bool:
        """
        Check if mechanic can activate given current state

        Used to check if mechanic is allowed to activate based on:
        - Cooldown timers
        - Ground/air state
        - Other preconditions

        Args:
            state: Player state to check

        Returns:
            True if mechanic can activate
        """
        pass

    def on_collision(self, state: PlayerState, collision_event: CollisionEvent):
        """
        Handle collision event (optional override)

        Mechanics can respond to collisions:
        - Reset jumps on ground landing
        - Cancel dash on wall hit
        - Trigger wall jump on wall collision

        Args:
            state: Player state
            collision_event: Collision event details
        """
        pass

    def reset(self, state: PlayerState):
        """
        Reset mechanic state (e.g., on respawn)

        Called when entity respawns or level resets.
        Mechanics should reset all internal state.

        Args:
            state: Player state to reset
        """
        pass

    def enable(self):
        """Enable mechanic (feature flag control)"""
        self.enabled = True
        self.logger.info(f"{self.__class__.__name__} enabled")

    def disable(self):
        """Disable mechanic (feature flag control)"""
        self.enabled = False
        self.logger.info(f"{self.__class__.__name__} disabled")

    def cleanup(self):
        """
        Cleanup mechanic (unsubscribe from events)

        Called when mechanic is removed or entity destroyed.
        Mechanics should unsubscribe from all events.
        """
        pass
