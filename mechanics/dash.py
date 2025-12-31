"""
Dash Mechanic - Quick burst of speed with cooldown

Features:
- Fast horizontal movement (16.0 units/tick)
- Fixed duration (0.16s)
- Cooldown after dash (0.45s)
- Overrides normal movement during dash
- Directional based on facing

Dash Characteristics:
- Speed: 16.0 (double normal max speed)
- Duration: 0.16s (~10 frames at 60Hz)
- Cooldown: 0.45s (~27 frames)
- Cancels on wall collision
"""

from mechanics.base import BaseMechanic
from core.event_bus import EventBus, CollisionEvent, VelocityChangeEvent
from core.logger import MechanicLogger
from core.state import PlayerState


class DashMechanic(BaseMechanic):
    """
    Handles dash ability with cooldown

    Dash States:
    - Ready: cooldown = 0, not dashing
    - Dashing: is_dashing = True, dash_time > 0
    - Cooldown: is_dashing = False, dash_cooldown > 0

    State managed:
    - PlayerState.is_dashing (currently dashing)
    - PlayerState.dash_time (time remaining in dash)
    - PlayerState.dash_cooldown (cooldown timer)
    - PlayerState.physics.vx (velocity during dash)
    """

    # Dash constants (from settings.py)
    DASH_SPEED = 16.0
    DASH_DURATION = 0.16
    DASH_COOLDOWN = 0.45

    def __init__(self, entity_id: int, event_bus: EventBus, logger: MechanicLogger):
        """
        Initialize dash mechanic

        Args:
            entity_id: Entity this mechanic is attached to
            event_bus: Event bus for emitting velocity changes
            logger: Logger for this mechanic
        """
        super().__init__(entity_id, event_bus, logger)

        # Subscribe to collision events to cancel dash on wall hit
        self.event_bus.subscribe(CollisionEvent, self._on_collision_event)

        # Track dash input request
        self.dash_requested = False

        self.logger.info(f"DashMechanic initialized (entity={entity_id})")

    def request_dash(self):
        """
        Request a dash (called by input system)

        Dash will execute if cooldown is complete and not currently dashing
        """
        self.dash_requested = True
        self.logger.debug(f"Dash requested for entity {self.entity_id}")

    def on_tick(self, state: PlayerState, dt: float):
        """
        Process dash mechanics every tick

        Updates:
        - Dash time (countdown during dash)
        - Dash cooldown (countdown after dash)
        - Velocity override during dash
        - Dash activation (if requested and ready)

        Args:
            state: Player state to modify
            dt: Delta time (always 1/60 = 0.0167s)
        """
        if not self.enabled:
            return

        # Update dash state
        if state.is_dashing:
            # Currently dashing - countdown duration
            state.dash_time -= dt

            if state.dash_time <= 0:
                # Dash finished
                state.is_dashing = False
                state.dash_cooldown = self.DASH_COOLDOWN
                state.dash_time = 0.0

                self.logger.info(
                    f"Dash finished, cooldown started ({self.DASH_COOLDOWN:.3f}s)"
                )

            else:
                # Continue dashing - override velocity
                old_vx = state.physics.vx
                state.physics.vx = state.facing * self.DASH_SPEED

                if abs(old_vx - state.physics.vx) > 1.0:  # Log only significant changes
                    self.logger.debug(
                        f"Dash velocity: vx {old_vx:.2f} -> {state.physics.vx:.2f}"
                    )

        elif state.dash_cooldown > 0:
            # On cooldown - countdown
            old_cooldown = state.dash_cooldown
            state.dash_cooldown = max(0.0, state.dash_cooldown - dt)

            if state.dash_cooldown == 0.0:
                self.logger.debug(f"Dash cooldown finished (was {old_cooldown:.3f}s)")

        # Handle dash request
        if self.dash_requested:
            if self.can_activate(state):
                self._activate_dash(state)
            else:
                self.logger.debug(
                    f"Dash request denied (dashing={state.is_dashing}, "
                    f"cooldown={state.dash_cooldown:.3f}s)"
                )

            self.dash_requested = False

    def _activate_dash(self, state: PlayerState):
        """
        Activate dash (internal)

        Args:
            state: Player state to modify
        """
        # Ensure facing direction is set
        if state.facing == 0:
            state.facing = 1
            self.logger.debug("No facing direction, defaulting to right")

        old_vx = state.physics.vx

        # Start dash
        state.is_dashing = True
        state.dash_time = self.DASH_DURATION
        state.physics.vx = state.facing * self.DASH_SPEED

        self.logger.info(
            f"Dash activated (facing={state.facing}, duration={self.DASH_DURATION:.3f}s): "
            f"vx {old_vx:.2f} -> {state.physics.vx:.2f}"
        )

        # Emit velocity change event
        self.event_bus.emit(VelocityChangeEvent(
            entity_id=self.entity_id,
            old_vx=old_vx,
            old_vy=state.physics.vy,
            new_vx=state.physics.vx,
            new_vy=state.physics.vy,
            reason="dash"
        ))

    def can_activate(self, state: PlayerState) -> bool:
        """
        Check if dash can activate

        Conditions:
        - Not currently dashing
        - Cooldown complete

        Returns:
            True if dash can activate
        """
        return not state.is_dashing and state.dash_cooldown <= 0.0

    def _on_collision_event(self, event: CollisionEvent):
        """
        Handle collision events (cancel dash on wall hit)

        Args:
            event: Collision event
        """
        # Only respond to collisions for this entity
        if event.entity_id != self.entity_id:
            return

        # Cancel dash on wall collision
        if event.collision_type in ('wall_left', 'wall_right'):
            self.logger.debug(
                f"Wall collision during dash, canceling dash early"
            )

    def on_collision(self, state: PlayerState, collision_event: CollisionEvent):
        """
        Handle collision (called by collision system)

        Cancel dash on wall hit

        Args:
            state: Player state to modify
            collision_event: Collision event details
        """
        # Cancel dash on wall collision
        if state.is_dashing and collision_event.collision_type in ('wall_left', 'wall_right'):
            state.is_dashing = False
            state.dash_cooldown = self.DASH_COOLDOWN
            state.dash_time = 0.0

            self.logger.info(
                f"Dash cancelled by {collision_event.collision_type}, "
                f"cooldown started"
            )

    def reset(self, state: PlayerState):
        """
        Reset dash mechanic (on respawn)

        Args:
            state: Player state to reset
        """
        state.is_dashing = False
        state.dash_time = 0.0
        state.dash_cooldown = 0.0
        self.dash_requested = False

        self.logger.info(f"DashMechanic reset for entity {self.entity_id}")

    def cleanup(self):
        """
        Cleanup mechanic (unsubscribe from events)
        """
        # Unsubscribe from collision events to prevent memory leak
        self.event_bus.unsubscribe(CollisionEvent, self._on_collision_event)
