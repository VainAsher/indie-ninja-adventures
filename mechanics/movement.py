"""
Movement Mechanic - Smooth interpolation-based movement

Features:
- Smooth interpolation to target velocity (eliminates jitter)
- Tunable acceleration constant for responsive but weighted controls
- Natural deceleration when no input (interpolates to 0)
- Speed capping at maximum run speed
- Frame-rate independent (dt-scaled)

Movement Algorithm:
- Calculate target velocity: target_vx = direction * MAX_SPEED * multiplier
- Calculate smooth factor: min(1.0, ACCEL * dt / max(MAX_SPEED, 1.0))
- Interpolate: vx += (target_vx - vx) * smooth_factor

Benefits:
- No jitter from discrete acceleration steps
- Responsive but weighted feel from tuned acceleration constant
- Smooth acceleration and deceleration curves
- Professional polish matching commercial platformers

Movement Characteristics:
- Speed limit: 8.0 units/tick (from physics_constants.py)
- Acceleration: 1200.0 (smooth interpolation constant, from physics_constants.py)
- Same behavior on ground and in air (unified physics)
"""

from config.physics_constants import MAX_RUN_SPEED, MOVEMENT_ACCEL
from core.event_bus import EventBus
from core.logger import MechanicLogger
from core.state import PlayerState
from mechanics.base import BaseMechanic


class MovementMechanic(BaseMechanic):
    """
    Handles horizontal movement with ground/air physics

    Movement model:
    - Acceleration when moving in same direction as velocity
    - Deceleration (faster) when changing direction
    - Natural slowdown when no input (friction)
    - Speed clamped to MAX_RUN_SPEED

    State modified:
    - PlayerState.physics.vx (horizontal velocity)
    - PlayerState.facing (direction player is facing)

    Constants imported from config.physics_constants:
    - MAX_RUN_SPEED: Maximum horizontal speed (8.0)
    - MOVEMENT_ACCEL: Acceleration constant for smooth interpolation (1200.0)
    """

    def __init__(self, entity_id: int, event_bus: EventBus, logger: MechanicLogger):
        """
        Initialize movement mechanic

        Args:
            entity_id: Entity this mechanic is attached to
            event_bus: Event bus for communication
            logger: Logger for this mechanic
        """
        super().__init__(entity_id, event_bus, logger)

        # Movement input (-1 = left, 0 = none, 1 = right)
        self.target_direction = 0

        # Movement modifiers
        self.speed_multiplier = 1.0  # For crouch, dash override, etc.
        self.accel_multiplier = 1.0  # For crouch acceleration penalty
        self.movement_locked = False  # For wall jump lock, dash, etc.

        self.logger.info(f"MovementMechanic initialized (entity={entity_id})")

    def set_input(self, direction: int):
        """
        Set movement input direction

        Args:
            direction: -1 (left), 0 (none), 1 (right)
        """
        if direction not in (-1, 0, 1):
            self.logger.warning(f"Invalid direction {direction}, clamping to -1/0/1")
            direction = max(-1, min(1, direction))

        self.target_direction = direction

    def set_accel_multiplier(self, multiplier: float):
        """
        Set acceleration multiplier (for crouch, etc.)

        Args:
            multiplier: Acceleration multiplier (0.0 to 1.0+)
        """
        self.accel_multiplier = multiplier

    def set_speed_multiplier(self, multiplier: float):
        """
        Set speed multiplier (for crouch, powerups, etc.)

        Args:
            multiplier: Speed multiplier (0.0 to 2.0 typical range)
        """
        self.speed_multiplier = max(0.0, multiplier)

    def lock_movement(self, locked: bool):
        """
        Lock/unlock horizontal movement (for wall jump, dash, etc.)

        Args:
            locked: True to prevent movement input
        """
        self.movement_locked = locked

    def on_tick(self, state: PlayerState, dt: float):
        """
        Process movement every tick using smooth interpolation

        Updates:
        - Horizontal velocity interpolates toward target velocity
        - Facing direction
        - Eliminates jitter through smooth acceleration/deceleration

        Algorithm (from dynamic dungeon platformer):
        - Calculate target velocity based on input and speed multiplier
        - Interpolate current velocity toward target using smooth factor
        - Smooth factor ensures responsive feel without discrete steps

        Args:
            state: Player state to modify
            dt: Delta time (always 1/60 = 0.0167s)
        """
        if not self.enabled:
            return

        # Skip if movement locked (dash, wall jump, etc. override)
        if self.movement_locked:
            return

        # Update facing direction (only when moving)
        if self.target_direction != 0:
            old_facing = state.facing
            state.facing = self.target_direction
            if old_facing != state.facing:
                self.logger.debug(f"Facing changed: {old_facing} -> {state.facing}")

        old_vx = state.physics.vx

        # Calculate target velocity
        # target_vx = direction * MAX_RUN_SPEED * speed_multiplier
        target_vx = self.target_direction * MAX_RUN_SPEED * self.speed_multiplier

        # Smooth interpolation factor
        # Formula: min(1.0, accel * accel_mult * dt / max(MAX_SPEED, 1.0))
        # This ensures:
        # - Base acceleration (MOVEMENT_ACCEL) for responsiveness
        # - Modulated by accel_multiplier (for crouch penalty, etc.)
        # - Smooth approach to target velocity (no jitter)
        # - dt scaling for frame-rate independence
        smooth_factor = min(
            1.0, MOVEMENT_ACCEL * self.accel_multiplier * dt / max(MAX_RUN_SPEED, 1.0)
        )

        # Interpolate current velocity toward target
        # vx += (target_vx - vx) * smooth_factor
        # This smoothly accelerates/decelerates toward target
        state.physics.vx += (target_vx - state.physics.vx) * smooth_factor

        # Log significant velocity changes
        if abs(state.physics.vx - old_vx) > 0.5:
            on_ground = state.physics.on_ground
            movement_type = "ground" if on_ground else "air"
            self.logger.debug(
                f"{movement_type} movement (smooth): vx {old_vx:.2f} -> {state.physics.vx:.2f} "
                f"(target={target_vx:.2f}, factor={smooth_factor:.3f})"
            )

    def can_activate(self, state: PlayerState) -> bool:
        """
        Check if movement can activate

        Returns:
            True if not locked
        """
        return not self.movement_locked

    def reset(self, state: PlayerState):
        """
        Reset movement mechanic (on respawn)

        Args:
            state: Player state to reset
        """
        self.target_direction = 0
        self.speed_multiplier = 1.0
        self.movement_locked = False
        state.physics.vx = 0.0

        self.logger.info(f"MovementMechanic reset for entity {self.entity_id}")
