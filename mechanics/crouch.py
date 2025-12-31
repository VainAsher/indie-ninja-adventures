"""
Crouch Mechanic - Stealth movement with distinct feel

Features:
- Crouching reduces player height (collision box changes)
- Stealth movement: slower but more controlled
- Reduced jump power when crouching
- Can't stand up if blocked by ceiling/platform
- Different movement characteristics:
  - Standing: Fast, responsive, high acceleration
  - Crouching: Slow, precise, stealthy (60% speed, 80% acceleration)
  - Distinct feel for stealth gameplay

Crouch Characteristics:
- Height: 50% of normal (20 -> 10 pixels typical)
- Speed: 60% of normal
- Acceleration: 80% of normal (more gradual)
- Jump power: 70% of normal
- Used for: stealth, fitting through tight spaces, precise movement
"""

from mechanics.base import BaseMechanic
from core.event_bus import EventBus
from core.logger import MechanicLogger
from core.state import PlayerState
import pygame


class CrouchMechanic(BaseMechanic):
    """
    Handles crouching with collision checking and movement modifiers

    Crouch States:
    - Standing: normal height, full speed
    - Crouching: reduced height, slower/more controlled movement
    - Blocked: can't stand (ceiling above)

    State managed:
    - PlayerState.crouching (currently crouched)
    - PlayerState.physics.height (collision box height)
    - Movement modifiers via callback
    """

    # Crouch constants (from settings.py + new stealth system)
    CROUCH_SPEED_MULT = 0.6  # Movement speed when crouched
    CROUCH_ACCEL_MULT = 0.8  # Acceleration when crouched (more gradual)
    CROUCH_JUMP_MULT = 0.7  # Jump power when crouched
    CROUCH_HEIGHT_RATIO = 0.5  # Height when crouched (50% of normal)

    def __init__(self, entity_id: int, event_bus: EventBus, logger: MechanicLogger,
                 collision_checker=None):
        """
        Initialize crouch mechanic

        Args:
            entity_id: Entity this mechanic is attached to
            event_bus: Event bus for communication
            logger: Logger for this mechanic
            collision_checker: Optional collision system for ceiling checks
        """
        super().__init__(entity_id, event_bus, logger)

        self.collision_checker = collision_checker

        # Store normal height (set on first tick)
        self.normal_height = None
        self.crouch_height = None

        # Track desired crouch state (hold-based)
        self.desired_crouch = False

        self.logger.info(f"CrouchMechanic initialized (entity={entity_id})")

    def set_crouch(self, active: bool):
        """Set desired crouch state (hold input)."""
        self.desired_crouch = active

    def on_tick(self, state: PlayerState, dt: float):
        """
        Process crouch mechanics every tick

        Updates:
        - Crouch state (standing/crouching)
        - Collision box height
        - Movement modifiers

        Args:
            state: Player state to modify
            dt: Delta time (always 1/60 = 0.0167s)
        """
        if not self.enabled:
            return

        # Initialize heights on first tick
        if self.normal_height is None:
            self.normal_height = state.physics.height
            self.crouch_height = int(self.normal_height * self.CROUCH_HEIGHT_RATIO)
            self.logger.info(
                f"Crouch heights set: normal={self.normal_height}, "
                f"crouch={self.crouch_height}"
            )

        # Apply desired crouch (hold)
        if self.desired_crouch:
            if not state.crouching and state.physics.on_ground:
                self._enter_crouch(state)
        else:
            if state.crouching:
                if state.physics.on_ground:
                    self._try_exit_crouch(state)
                else:
                    self._force_exit_crouch(state)

    def _enter_crouch(self, state: PlayerState):
        """
        Enter crouch state

        Args:
            state: Player state to modify
        """
        if state.crouching:
            return

        # Adjust position (move down to keep bottom at same position)
        height_diff = self.normal_height - self.crouch_height
        state.physics.y += height_diff
        state.physics.height = self.crouch_height
        state.crouching = True

        self.logger.info(
            f"Entered crouch (height {self.normal_height} -> {self.crouch_height})"
        )

    def _try_exit_crouch(self, state: PlayerState):
        """
        Try to exit crouch (check for ceiling)

        Args:
            state: Player state to modify
        """
        if not state.crouching:
            return

        # Check if there's space to stand up
        height_diff = self.normal_height - self.crouch_height

        # Create test rect at standing position
        test_rect = pygame.Rect(
            int(state.physics.x),
            int(state.physics.y - height_diff),
            state.physics.width,
            self.normal_height
        )

        # Check collision with ceiling/platforms
        if self.collision_checker:
            blocked = self._check_ceiling_collision(test_rect)
            if blocked:
                self.logger.debug("Can't stand up (blocked by ceiling)")
                return

        # Safe to stand up
        state.physics.y -= height_diff
        state.physics.height = self.normal_height
        state.crouching = False

        self.logger.info(
            f"Exited crouch (height {self.crouch_height} -> {self.normal_height})"
        )

    def _force_exit_crouch(self, state: PlayerState):
        """
        Force exit crouch without ceiling check (used when airborne)

        Args:
            state: Player state to modify
        """
        if not state.crouching:
            return

        # Restore normal height
        height_diff = self.normal_height - self.crouch_height
        state.physics.y -= height_diff
        state.physics.height = self.normal_height
        state.crouching = False

    def _check_ceiling_collision(self, test_rect: pygame.Rect) -> bool:
        """
        Check if standing position would collide with ceiling

        Args:
            test_rect: Rectangle to test

        Returns:
            True if collision detected
        """
        # Use collision checker if available
        if hasattr(self.collision_checker, 'tiles'):
            for tile in self.collision_checker.tiles:
                if test_rect.colliderect(tile):
                    return True
        return False

    def can_activate(self, state: PlayerState) -> bool:
        """
        Check if crouch can activate

        Conditions:
        - On ground (enter crouch)

        Returns:
            True if can toggle crouch
        """
        return state.physics.on_ground

    def get_movement_modifier(self, state: PlayerState) -> dict:
        """
        Get movement modifiers for other mechanics

        Returns:
            Dictionary with speed_mult and accel_mult
        """
        if state.crouching:
            return {
                'speed_mult': self.CROUCH_SPEED_MULT,
                'accel_mult': self.CROUCH_ACCEL_MULT,
            }
        else:
            return {
                'speed_mult': 1.0,
                'accel_mult': 1.0,
            }

    def reset(self, state: PlayerState):
        """
        Reset crouch mechanic (on respawn)

        Args:
            state: Player state to reset
        """
        if state.crouching and self.normal_height:
            # Force exit crouch
            height_diff = self.normal_height - self.crouch_height
            state.physics.y -= height_diff
            state.physics.height = self.normal_height

        state.crouching = False
        self.crouch_key_pressed = False

        self.logger.info(f"CrouchMechanic reset for entity {self.entity_id}")
