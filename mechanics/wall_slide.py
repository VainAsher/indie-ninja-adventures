"""
Wall Slide Mechanic - Cling to walls and slow descent with stamina

Features:
- Cling to wall when against it in air
- Slow descent while wall sliding (2.2 units/tick vs normal fall)
- Stamina system (3.0s max cling time)
- Stamina regenerates when not on wall (2.0s to full)
- Visual/audio feedback for low stamina
- Can't cling again until some stamina recovered

Wall Slide Characteristics:
- Slide speed: 2.2 (slow controlled descent)
- Max cling time: 3.0s continuous
- Stamina regen: 2.0s to full (when off wall)
- Min stamina to cling: 0.3s (can't spam wall cling)
"""

from mechanics.base import BaseMechanic
from core.event_bus import EventBus
from core.logger import MechanicLogger
from core.state import PlayerState


class WallSlideMechanic(BaseMechanic):
    """
    Handles wall sliding with stamina system

    Wall Slide States:
    - Can cling: on_wall, in air, stamina > MIN_STAMINA
    - Clinging: actively sliding down wall slowly
    - Exhausted: stamina = 0, can't cling until regen
    - Recovering: off wall, stamina regenerating

    State managed:
    - PlayerState.wall_slide_stamina (stamina remaining)
    - PlayerState.is_wall_sliding (actively sliding)
    - PlayerState.physics.vy (velocity capped during slide)
    """

    # Wall slide constants (from settings.py + new stamina system)
    WALL_SLIDE_SPEED = 3.0  # Max fall speed while sliding (slightly faster to ensure descent)
    MAX_STAMINA = 3.0  # Maximum cling time (seconds)
    STAMINA_REGEN_TIME = 2.0  # Time to fully regenerate stamina
    MIN_STAMINA_TO_CLING = 0.3  # Minimum stamina required to start cling
    EXHAUST_THRESHOLD = 0.5  # Stamina level where slide stops
    EXHAUST_PENALTY = 0.25  # Additional stamina removed on exhaust
    SLIDE_DRAIN_MULT = 1.6  # Drain faster while sliding
    WALL_FRICTION_FALL_SPEED = 6.0  # When touching wall but not sliding, cap fall speed slightly

    def __init__(self, entity_id: int, event_bus: EventBus, logger: MechanicLogger):
        """
        Initialize wall slide mechanic

        Args:
            entity_id: Entity this mechanic is attached to
            event_bus: Event bus for communication
            logger: Logger for this mechanic
        """
        super().__init__(entity_id, event_bus, logger)

        self.logger.info(f"WallSlideMechanic initialized (entity={entity_id})")
        self.await_ground_after_exhaust = False
        self._exhaust_detach_frames = 0

    def on_tick(self, state: PlayerState, dt: float):
        """
        Process wall slide every tick

        Updates:
        - Wall slide state (clinging or not)
        - Stamina (drain when clinging, regen when off wall)
        - Vertical velocity (cap to slide speed)

        Args:
            state: Player state to modify
            dt: Delta time (always 1/60 = 0.0167s)
        """
        if not self.enabled:
            return

        touching_wall = state.physics.on_wall and not state.physics.on_ground
        if touching_wall:
            if state.physics.wall_dir == 0:
                inferred = state.last_wall_dir or (1 if state.facing >= 0 else -1)
                state.physics.wall_dir = inferred
            state.last_wall_dir = state.physics.wall_dir

        # If currently sliding, prefer to stay sliding while on wall until stamina/exhaustion forces exit.
        if state.is_wall_sliding:
            touching_wall = state.physics.on_wall and not state.physics.on_ground
            if state.physics.wall_dir != 0:
                state.last_wall_dir = state.physics.wall_dir
            # Exit conditions
            if (not touching_wall) or state.wall_slide_stamina <= self.EXHAUST_THRESHOLD:
                # Exhaust
                state.wall_slide_stamina = max(0.0, state.wall_slide_stamina - self.EXHAUST_PENALTY)
                state.is_wall_sliding = False
                self.await_ground_after_exhaust = True
                self._exhaust_detach_frames = 6  # temporarily ignore wall contact to force drop
                state.physics.on_wall = False
                state.physics.wall_dir = 0
                state.physics.vy = max(state.physics.vy, 2.0)
                self.logger.info("Wall slide stamina exhausted, falling")
            else:
                # Continue sliding: drain stamina and cap fall speed
                old_stamina = state.wall_slide_stamina
                drain = dt * self.SLIDE_DRAIN_MULT
                state.wall_slide_stamina = max(0.0, state.wall_slide_stamina - drain)
                state.physics.vy = min(state.physics.vy + 0.3, self.WALL_SLIDE_SPEED)

                if old_stamina >= 1.0 and state.wall_slide_stamina < 1.0:
                    self.logger.info("Wall slide stamina low (< 1.0s remaining)")
                elif old_stamina >= 0.5 and state.wall_slide_stamina < 0.5:
                    self.logger.warning("Wall slide stamina critical (< 0.5s remaining)")
            # No further processing when already sliding
            return

        # Not currently sliding: consider starting a slide
        can_slide = (
            touching_wall
            and state.wall_slide_stamina >= self.MIN_STAMINA_TO_CLING
            and not self.await_ground_after_exhaust
        )

        if can_slide:
            state.is_wall_sliding = True
            self.logger.info(f"Started wall sliding (stamina={state.wall_slide_stamina:.2f}s)")
            # Initial gentle slow-down
            state.physics.vy = min(state.physics.vy + 0.3, self.WALL_SLIDE_SPEED)
            return

        # Not sliding: manage regen/exhaust cooldown
        if state.is_wall_sliding:
            state.is_wall_sliding = False

        # Regen gating: require ground contact before regen after exhaustion, and pause regen if back on wall
        if touching_wall and self.await_ground_after_exhaust:
            pass
        elif state.physics.on_ground:
            self.await_ground_after_exhaust = False
            self._exhaust_detach_frames = 0

        if (not touching_wall) and (not self.await_ground_after_exhaust) and state.wall_slide_stamina < self.MAX_STAMINA:
            old_stamina = state.wall_slide_stamina
            regen_rate = self.MAX_STAMINA / self.STAMINA_REGEN_TIME
            state.wall_slide_stamina = min(
                self.MAX_STAMINA,
                state.wall_slide_stamina + regen_rate * dt
            )
            if old_stamina < self.MIN_STAMINA_TO_CLING and state.wall_slide_stamina >= self.MIN_STAMINA_TO_CLING:
                self.logger.debug("Wall slide stamina recharged (can cling again)")
            elif state.wall_slide_stamina == self.MAX_STAMINA:
                self.logger.debug("Wall slide stamina fully recharged")

        # Apply wall friction when merely touching wall (not sliding) and not exhausted
        if touching_wall and not self.await_ground_after_exhaust:
            state.physics.vy = min(state.physics.vy + 0.3, self.WALL_FRICTION_FALL_SPEED)

        # If exhausted and collision keeps flagging wall contact, nudge off the wall for a few frames
        if self._exhaust_detach_frames > 0:
            if state.physics.wall_dir != 0:
                # Move 1px away from wall per frame to break contact
                state.physics.x += 1.0 * (-state.physics.wall_dir)
            state.physics.on_wall = False
            state.physics.wall_dir = 0
            state.physics.vy = max(state.physics.vy, 2.0)
            self._exhaust_detach_frames -= 1

    def can_activate(self, state: PlayerState) -> bool:
        """
        Check if wall slide can activate

        Conditions:
        - On wall
        - In air (not grounded)
        - Sufficient stamina

        Returns:
            True if can wall slide
        """
        return (
            state.physics.on_wall and
            not state.physics.on_ground and
            state.wall_slide_stamina >= self.MIN_STAMINA_TO_CLING
        )

    def reset(self, state: PlayerState):
        """
        Reset wall slide mechanic (on respawn)

        Args:
            state: Player state to reset
        """
        state.is_wall_sliding = False
        state.wall_slide_stamina = self.MAX_STAMINA  # Start with full stamina

        self.logger.info(f"WallSlideMechanic reset for entity {self.entity_id}")

    def get_stamina_percentage(self, state: PlayerState) -> float:
        """
        Get stamina as percentage (for UI display)

        Args:
            state: Player state

        Returns:
            Stamina percentage (0.0 to 1.0)
        """
        return state.wall_slide_stamina / self.MAX_STAMINA

    def is_stamina_low(self, state: PlayerState) -> bool:
        """
        Check if stamina is critically low (for warning effects)

        Args:
            state: Player state

        Returns:
            True if stamina < 0.5s
        """
        return state.wall_slide_stamina < 0.5

    def is_stamina_exhausted(self, state: PlayerState) -> bool:
        """
        Check if stamina is completely exhausted

        Args:
            state: Player state

        Returns:
            True if stamina = 0
        """
        return state.wall_slide_stamina <= 0.0
