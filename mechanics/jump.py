"""
Jump Mechanic - Unified jump system for all jump types

Features:
- Ground jump with coyote time (0.12s grace period)
- Double jump
- Wall jump with horizontal boost
- Jump buffering (0.14s input window)
- Crouch jump modifier (0.7x power)
- Collision response (reset jumps on landing)
- Configurable feature flags

Jump Types:
1. Ground/Coyote Jump - Jump from ground or shortly after leaving ground
2. Wall Jump - Jump from wall with horizontal boost
3. Double Jump - Air jump (if enabled)

Timers:
- coyote_time: Grace period after leaving ground (0.12s)
- jump_buffer_time: Input buffering window (0.14s)
"""

from config.physics_constants import (
    CROUCH_JUMP_MULT,
    DOUBLE_JUMP_POWER,
    JUMP_BUFFER_TIME,
    JUMP_POWER,
    WALL_JUMP_POWER_X,
    WALL_JUMP_POWER_Y,
)
from core.event_bus import CollisionEvent, EventBus, VelocityChangeEvent
from core.logger import MechanicLogger
from core.state import PlayerState
from mechanics.base import BaseMechanic


class JumpMechanic(BaseMechanic):
    """
    Handles all jump types in one unified module

    Jump priority:
    1. Ground/Coyote jump (if on ground or coyote active)
    2. Wall jump (if on wall)
    3. Double jump (if jumps remaining)

    State managed:
    - PlayerState.jumps_left (remaining air jumps)
    - PlayerState.coyote_time (grace period timer)
    - PlayerState.jump_buffer_time (input buffer timer)
    - PlayerState.wall_jump_lock (input lock after wall jump)

    NOTE: All constants imported from config.physics_constants
    """

    MAX_JUMPS = 2  # Maximum air jumps allowed
    WALL_JUMP_INPUT_LOCK = 0.12  # Input lock duration after wall jump

    def __init__(
        self,
        entity_id: int,
        event_bus: EventBus,
        logger: MechanicLogger,
        feature_flags: dict = None,
    ):
        """
        Initialize jump mechanic

        Args:
            entity_id: Entity this mechanic is attached to
            event_bus: Event bus for emitting velocity changes
            logger: Logger for this mechanic
            feature_flags: Feature flags (double_jump, wall_jump)
        """
        super().__init__(entity_id, event_bus, logger)

        self.feature_flags = feature_flags or {}
        self.double_jump_enabled = self.feature_flags.get("double_jump", True)
        self.wall_jump_enabled = self.feature_flags.get("wall_jump", True)

        # Subscribe to collision events to reset jumps
        self.event_bus.subscribe(CollisionEvent, self._on_collision_event)

        # Track jump input request
        self.jump_requested = False

        self.logger.info(
            f"JumpMechanic initialized (entity={entity_id}, "
            f"double_jump={self.double_jump_enabled}, "
            f"wall_jump={self.wall_jump_enabled})"
        )

    def request_jump(self):
        """
        Request a jump (called by input system)

        Jump will be buffered for JUMP_BUFFER_TIME if conditions aren't met
        """
        self.jump_requested = True
        self.logger.debug(f"Jump requested for entity {self.entity_id}")

    def on_tick(self, state: PlayerState, dt: float):
        """
        Process jump mechanics every tick

        Updates:
        - Coyote time (grace period after leaving ground)
        - Jump buffer time (input buffering)
        - Wall jump lock (input lock after wall jump)
        - Jump execution (if requested and conditions met)

        Args:
            state: Player state to modify
            dt: Delta time (always 1/60 = 0.0167s)
        """
        if not self.enabled:
            return

        # Update timers (countdown towards 0)
        if state.coyote_time > 0.0:
            old_coyote = state.coyote_time
            state.coyote_time = max(0.0, state.coyote_time - dt)
            if state.coyote_time == 0.0:
                self.logger.debug(f"Coyote time expired (was {old_coyote:.3f}s)")

        if state.jump_buffer_time > 0.0:
            old_buffer = state.jump_buffer_time
            state.jump_buffer_time = max(0.0, state.jump_buffer_time - dt)
            if state.jump_buffer_time == 0.0:
                self.logger.debug(f"Jump buffer expired (was {old_buffer:.3f}s)")

        if state.wall_jump_lock > 0.0:
            state.wall_jump_lock = max(0.0, state.wall_jump_lock - dt)

        # Handle jump request
        if self.jump_requested:
            # Buffer the jump input
            state.jump_buffer_time = JUMP_BUFFER_TIME
            self.logger.debug(f"Jump buffered ({JUMP_BUFFER_TIME:.3f}s window)")
            self.jump_requested = False

        # Try to execute buffered jump
        if state.jump_buffer_time > 0.0:
            jump_executed = self._try_execute_jump(state)
            if jump_executed:
                state.jump_buffer_time = 0.0  # Clear buffer on success

    def _try_execute_jump(self, state: PlayerState) -> bool:
        """
        Try to execute a jump (checks all jump types in priority order)

        Priority:
        1. Ground/Coyote jump (highest priority)
        2. Wall jump (if enabled)
        3. Double jump (if enabled and jumps remaining)

        Args:
            state: Player state to check and modify

        Returns:
            True if jump executed, False otherwise
        """
        # Try ground/coyote jump first
        if self._try_ground_or_coyote_jump(state):
            return True

        # Try wall jump (if enabled)
        if self.wall_jump_enabled and self._try_wall_jump(state):
            return True

        # Try double jump (if enabled)
        if self.double_jump_enabled and self._try_double_jump(state):
            return True

        return False

    def _try_ground_or_coyote_jump(self, state: PlayerState) -> bool:
        """
        Try ground jump or coyote jump

        Conditions:
        - On ground OR coyote time active

        Effects:
        - Set vertical velocity to -JUMP_POWER (modified by crouch)
        - Clear coyote time
        - Reset double jump counter

        Args:
            state: Player state to modify

        Returns:
            True if jump executed
        """
        if state.physics.on_ground or state.coyote_time > 0.0:
            # Calculate jump power (reduced when crouching)
            power = JUMP_POWER * (CROUCH_JUMP_MULT if state.crouching else 1.0)

            # Determine jump type before modifying state
            jump_type = "ground_jump" if state.physics.on_ground else "coyote_jump"

            # Apply jump (use impulse to preserve upward momentum)
            old_vy = state.physics.vy
            # If already moving upward, preserve that momentum
            state.physics.vy = min(old_vy - power, -power)
            state.physics.on_ground = False
            state.coyote_time = 0.0
            state.jumps_left = self.MAX_JUMPS - 1  # Reset double jump
            self.logger.info(f"Executed {jump_type}: vy {old_vy:.2f} -> {state.physics.vy:.2f}")

            # Emit velocity change event
            self.event_bus.emit(
                VelocityChangeEvent(
                    entity_id=self.entity_id,
                    old_vx=state.physics.vx,
                    old_vy=old_vy,
                    new_vx=state.physics.vx,
                    new_vy=state.physics.vy,
                    reason=jump_type,
                )
            )

            return True

        return False

    def _try_wall_jump(self, state: PlayerState) -> bool:
        """
        Try wall jump

        Conditions:
        - On wall

        Effects:
        - Set vertical velocity to -WALL_JUMP_POWER_Y
        - Set horizontal velocity away from wall (WALL_JUMP_POWER_X)
        - Flip facing direction away from wall
        - Reset double jump counter
        - Cancel dash
        - Lock horizontal input briefly

        Args:
            state: Player state to modify

        Returns:
            True if jump executed
        """
        on_wall_now = state.physics.on_wall
        if on_wall_now or state.wall_coyote_time > 0.0:
            if hasattr(state, "stamina") and state.stamina < 3.0:
                return False
            old_vx = state.physics.vx
            old_vy = state.physics.vy

            # Determine wall direction (fallback to last wall dir or facing)
            wall_dir_effective = (
                state.physics.wall_dir
                if state.physics.wall_dir != 0
                else getattr(state, "last_wall_dir", 0)
            )
            if wall_dir_effective == 0:
                if abs(state.physics.vx) > 0.1:
                    wall_dir_effective = 1 if state.physics.vx > 0 else -1
                else:
                    wall_dir_effective = -1 if state.facing >= 0 else 1
            state.last_wall_dir = wall_dir_effective

            # Flip facing away from wall
            state.facing = -wall_dir_effective

            # Apply wall jump velocities: force upward when sliding, soften horizontal
            base_power = WALL_JUMP_POWER_Y * (CROUCH_JUMP_MULT if state.crouching else 1.0)
            if on_wall_now and state.physics.vy > 0:
                state.physics.vy = -base_power * 1.6
            else:
                vy_boost = max(base_power * 1.6, abs(state.physics.vy) + base_power * 0.4)
                state.physics.vy = -vy_boost
            state.physics.vx = -wall_dir_effective * (WALL_JUMP_POWER_X * 0.5)

            # Detach from wall immediately
            state.is_wall_sliding = False  # Prevent slide logic from overriding jump impulse
            state.physics.on_wall = False
            state.physics.wall_dir = 0
            state.wall_coyote_time = 0.0

            # Reset states
            state.jumps_left = self.MAX_JUMPS - 1  # Reset double jump
            state.is_dashing = False
            state.wall_jump_lock = self.WALL_JUMP_INPUT_LOCK
            if hasattr(state, "stamina"):
                state.stamina = max(0.0, state.stamina - 3.0)

            self.logger.info(
                f"Executed wall_jump (wall_dir={wall_dir_effective}): "
                f"v ({old_vx:.2f}, {old_vy:.2f}) -> "
                f"({state.physics.vx:.2f}, {state.physics.vy:.2f})"
            )

            # Emit velocity change event
            self.event_bus.emit(
                VelocityChangeEvent(
                    entity_id=self.entity_id,
                    old_vx=old_vx,
                    old_vy=old_vy,
                    new_vx=state.physics.vx,
                    new_vy=state.physics.vy,
                    reason="wall_jump",
                )
            )

            return True

        return False

    def _try_double_jump(self, state: PlayerState) -> bool:
        """
        Try double jump (air jump)

        Conditions:
        - Jumps remaining > 0
        - Not crouching

        Effects:
        - Set vertical velocity to -JUMP_POWER
        - Decrement jumps_left

        Args:
            state: Player state to modify

        Returns:
            True if jump executed
        """
        if state.jumps_left > 0:
            # Stamina gate
            if hasattr(state, "stamina") and state.stamina < 3.0:
                return False
            old_vy = state.physics.vy
            power = DOUBLE_JUMP_POWER * (CROUCH_JUMP_MULT if state.crouching else 1.0)
            # Use impulse to preserve upward momentum (don't override if already rising faster)
            state.physics.vy = min(old_vy - power, -power)
            state.jumps_left -= 1
            if hasattr(state, "stamina"):
                state.stamina = max(0.0, state.stamina - 3.0)

            self.logger.debug(
                f"Executed double_jump (jumps_left={state.jumps_left}): "
                f"vy {old_vy:.2f} -> {state.physics.vy:.2f}"
            )

            # Emit velocity change event
            self.event_bus.emit(
                VelocityChangeEvent(
                    entity_id=self.entity_id,
                    old_vx=state.physics.vx,
                    old_vy=old_vy,
                    new_vx=state.physics.vx,
                    new_vy=state.physics.vy,
                    reason="double_jump",
                )
            )

            return True

        return False

    def can_activate(self, state: PlayerState) -> bool:
        """
        Check if jump can activate

        Returns:
            True if any jump type can activate
        """
        # Can jump if on ground or coyote active
        if state.physics.on_ground or state.coyote_time > 0.0:
            return True

        # Can wall jump if on wall/coyote buffer and enabled
        if self.wall_jump_enabled and (state.physics.on_wall or state.wall_coyote_time > 0.0):
            return True

        # Can double jump if enabled and jumps remaining
        if self.double_jump_enabled and state.jumps_left > 0:
            return True

        return False

    def _on_collision_event(self, event: CollisionEvent):
        """
        Handle collision events (reset jumps on ground landing)

        Args:
            event: Collision event
        """
        # Only respond to collisions for this entity
        if event.entity_id != self.entity_id:
            return

        # Reset jumps on ground landing
        if event.collision_type == "ground":
            self.logger.debug(f"Ground collision detected, resetting jumps to {self.MAX_JUMPS}")

    def on_collision(self, state: PlayerState, collision_event: CollisionEvent):
        """
        Handle collision (called by collision system)

        Reset jumps on ground landing
        Start coyote time on leaving ground

        Args:
            state: Player state to modify
            collision_event: Collision event details
        """
        if collision_event.collision_type == "ground":
            # Reset jumps on landing
            state.jumps_left = self.MAX_JUMPS
            self.logger.debug(f"Landed on ground, reset jumps to {self.MAX_JUMPS}")

    def reset(self, state: PlayerState):
        """
        Reset jump mechanic (on respawn)

        Args:
            state: Player state to reset
        """
        state.jumps_left = self.MAX_JUMPS
        state.coyote_time = 0.0
        state.jump_buffer_time = 0.0
        state.wall_jump_lock = 0.0
        self.jump_requested = False

        self.logger.info(f"JumpMechanic reset for entity {self.entity_id}")

    def cleanup(self):
        """
        Cleanup mechanic (unsubscribe from events)
        """
        # Unsubscribe from collision events to prevent memory leak
        self.event_bus.unsubscribe(CollisionEvent, self._on_collision_event)
