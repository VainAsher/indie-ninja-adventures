"""
Enemy Movement Component - shared movement helper for enemies.

Provides simple acceleration/friction based movement toward targets,
reusing PhysicsState for position/velocity handling.
"""

import math

from core.state import PhysicsState


class EnemyMovementComponent:
    """
    Reusable movement component for enemies.

    Applies smooth acceleration toward a target point with basic friction.
    """

    def __init__(self, move_speed: float, can_fly: bool = False):
        self.move_speed = move_speed  # pixels per second
        self.can_fly = can_fly
        self.acceleration = 200.0  # px/s^2 baseline (increased from 120 to prevent stalling)
        self.friction = 0.92  # Applied when not moving (increased from 0.85 to reduce drag)
        self.air_control = 0.5 if not can_fly else 1.0

    def move_toward(self, physics: PhysicsState, target_x: float, target_y: float, dt: float):
        """
        Apply acceleration toward target position.

        Args:
            physics: Entity physics state
            target_x: Target X position
            target_y: Target Y position (used for flying enemies)
            dt: Delta time in seconds
        """
        dx = target_x - physics.x
        dy = target_y - physics.y
        distance = math.hypot(dx, dy)

        if distance < 1.0:
            # Apply friction when at target
            physics.vx *= self.friction
            if self.can_fly:
                physics.vy *= self.friction
            return

        dir_x = dx / distance
        dir_y = dy / distance if self.can_fly else 0.0

        target_vx = dir_x * self.move_speed
        target_vy = dir_y * self.move_speed if self.can_fly else physics.vy

        control_mult = 1.0 if physics.on_ground or self.can_fly else self.air_control
        accel_amount = self.acceleration * control_mult * dt

        # Smooth toward target velocity
        if abs(target_vx - physics.vx) > accel_amount:
            physics.vx += accel_amount * (1 if target_vx > physics.vx else -1)
        else:
            physics.vx = target_vx

        if self.can_fly:
            if abs(target_vy - physics.vy) > accel_amount:
                physics.vy += accel_amount * (1 if target_vy > physics.vy else -1)
            else:
                physics.vy = target_vy

    def stop(self, physics: PhysicsState):
        """Apply friction to stop movement."""
        physics.vx *= self.friction
        if self.can_fly:
            physics.vy *= self.friction
