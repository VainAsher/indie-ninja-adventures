"""
Physics System - Applies gravity and integrates velocity

Features:
- Applies gravity to all entities with physics
- Integrates velocity (position += velocity)
- Variable gravity multipliers (fall faster, jump cut)
- Max fall speed capping
- Works with entity system

Physics Pipeline:
1. Apply gravity (this system)
2. Integrate velocity → position (this system)
3. Collision detection & resolution (collision system)
4. Mechanics respond to state (mechanics)
"""

import logging

import config.physics_constants as physics
from core.entity_system import Entity, EntityManager
from core.event_bus import EventBus, TickEvent
from core.state import PhysicsState


class PhysicsSystem:
    """
    Applies physics to all entities

    Runs every physics tick (60Hz fixed timestep):
    1. Apply gravity to vertical velocity
    2. Apply gravity multipliers (fast fall, jump cut)
    3. Cap fall speed to maximum
    4. Integrate velocity into position

    Mechanics modify velocity, physics system applies it.

    NOTE: All physics constants imported from config.physics_constants
    """

    def __init__(
        self,
        event_bus: EventBus,
        entity_manager: EntityManager,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize physics system

        Args:
            event_bus: Event bus for subscribing to ticks
            entity_manager: Entity manager for accessing entities
            logger: Optional logger
        """
        self.event_bus = event_bus
        self.entity_manager = entity_manager
        self.logger = logger

        # Expose constants for debugging/tests (dynamically reference from module)
        self.GRAVITY = physics.GRAVITY
        self.MAX_FALL_SPEED = physics.MAX_FALL_SPEED
        self.FALL_GRAVITY_MULT = physics.FALL_GRAVITY_MULT
        self.FAST_FALL_MULT = physics.FAST_FALL_MULT

        # Subscribe to tick events (priority 60 - before collision at 45)
        self.event_bus.subscribe(TickEvent, self.on_tick, priority=60)

        if self.logger:
            self.logger.info("PhysicsSystem initialized")

    def on_tick(self, event: TickEvent):
        """
        Process physics for all entities

        Called every physics tick (60Hz fixed timestep).
        Runs before collision detection.

        Args:
            event: Tick event with dt
        """
        dt = event.dt

        # Process all entities with physics
        for entity in self.entity_manager.entities.values():
            if entity.physics and entity.active:
                self._process_entity_physics(entity, dt)

    def _process_entity_physics(self, entity: Entity, dt: float):
        """
        Process physics for a single entity

        Args:
            entity: Entity to process
            dt: Delta time (always 1/60 = 0.0167s)
        """
        physics_state = entity.physics

        # Apply gravity (only if not on ground - ground entities have vy=0 from collision)
        if not physics_state.on_ground:
            self._apply_gravity(physics_state)

        # Integrate velocity into position
        physics_state.x += physics_state.vx
        physics_state.y += physics_state.vy

    def _apply_gravity(self, physics_state: PhysicsState):
        """
        Apply gravity with multipliers

        Gravity multipliers:
        - Base: GRAVITY (0.6)
        - Tile modifier: gravity_multiplier (water = 0.4, lava = 0.7, normal = 1.0)
        - Apex hang: APEX_HANG_MULT (0.6x) - reduced gravity at jump peak
        - Falling: FALL_GRAVITY_MULT (2.0x) - fall faster
        - Jump cut: JUMP_CUT_MULT (3.0x) - release jump button
        - Fast fall: FAST_FALL_MULT (2.0x) - hold down button

        Args:
            physics_state: Physics state to modify
        """
        # Get tile gravity multiplier (default 1.0 if not set)
        tile_gravity_mult = getattr(physics_state, "gravity_multiplier", 1.0)

        # Apex hang: reduce gravity at peak of jump for satisfying floaty moment
        if abs(physics_state.vy) < physics.APEX_HANG_THRESHOLD:
            physics_state.vy += physics.GRAVITY * physics.APEX_HANG_MULT * tile_gravity_mult
        else:
            # Base gravity with tile modifier
            physics_state.vy += physics.GRAVITY * tile_gravity_mult

        # Fall faster than rise (more responsive) - also affected by tile modifier
        if physics_state.vy > 0:
            physics_state.vy += physics.GRAVITY * (physics.FALL_GRAVITY_MULT - 1.0) * tile_gravity_mult

        # Cap fall speed (adjusted by tile modifier for fluids)
        max_fall = physics.MAX_FALL_SPEED * tile_gravity_mult
        if physics_state.vy > max_fall:
            physics_state.vy = max_fall

    def apply_jump_cut(self, physics_state: PhysicsState, jump_held: bool):
        """
        Apply jump cut (call from input system when jump button released)

        If player releases jump button while rising, apply extra gravity
        to make jumps more responsive (variable jump height).

        Args:
            physics_state: Physics state
            jump_held: Whether jump button is held
        """
        if physics_state.vy < 0 and not jump_held:
            physics_state.vy += physics.GRAVITY * (physics.JUMP_CUT_MULT - 1.0)

    def apply_fast_fall(self, physics_state: PhysicsState, down_held: bool):
        """
        Apply fast fall (call from input system when down button held)

        If player holds down while falling in air, apply extra gravity.

        Args:
            physics_state: Physics state
            down_held: Whether down button is held
        """
        if physics_state.vy > 0 and not physics_state.on_ground and down_held:
            physics_state.vy += physics.GRAVITY * (physics.FAST_FALL_MULT - 1.0)

    def get_stats(self) -> dict:
        """
        Get physics statistics

        Returns:
            Dictionary with stats
        """
        return {
            "entities_with_physics": sum(
                1 for e in self.entity_manager.entities.values() if e.physics and e.active
            ),
            "gravity": self.GRAVITY,
            "max_fall_speed": self.MAX_FALL_SPEED,
        }
