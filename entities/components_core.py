"""
Reusable Entity Components

Common components that can be shared across players, NPCs, and enemies:
- HealthComponent: Health management with damage/heal
- AIComponent: Basic AI behaviors
- PatrolComponent: Patrol movement
- FollowComponent: Follow target entity
"""

import logging

from core.entity_system import Component

# ============================================================================
# Health Component (reusable for players, NPCs, enemies)
# ============================================================================


class HealthComponent(Component):
    """
    Health component with damage/heal and invincibility

    Can be used by players, NPCs, and enemies.
    """

    def __init__(self, entity_id: int, max_health: int = 5, invincibility_duration: float = 1.2):
        super().__init__(entity_id)
        self.max_health = max_health
        self.current_health = max_health
        self.invincibility_duration = invincibility_duration
        self.invincibility_timer = 0.0
        self.logger: logging.Logger | None = None

    def initialize(self, entity_manager):
        """Initialize component with logging"""
        if entity_manager.logger:
            self.logger = entity_manager.logger

    def update(self, dt: float, entity_manager):
        """Update invincibility timer"""
        if self.invincibility_timer > 0.0:
            self.invincibility_timer = max(0.0, self.invincibility_timer - dt)

    def take_damage(self, amount: int, source: str = "unknown") -> bool:
        """
        Take damage

        Args:
            amount: Damage amount
            source: Damage source (for logging)

        Returns:
            True if damage was applied, False if invincible
        """
        if self.invincibility_timer > 0.0:
            return False

        self.current_health -= max(1, amount)
        self.invincibility_timer = self.invincibility_duration

        if self.logger:
            self.logger.info(
                f"Entity {self.entity_id} took {amount} damage from {source} "
                f"({self.current_health}/{self.max_health} HP)"
            )

        return True

    def heal(self, amount: int) -> int:
        """
        Heal entity

        Args:
            amount: Heal amount

        Returns:
            Actual amount healed
        """
        old_health = self.current_health
        self.current_health = min(self.max_health, self.current_health + max(1, amount))
        healed = self.current_health - old_health

        if self.logger and healed > 0:
            self.logger.info(
                f"Entity {self.entity_id} healed {healed} HP "
                f"({self.current_health}/{self.max_health})"
            )

        return healed

    def is_alive(self) -> bool:
        """Check if entity is alive"""
        return self.current_health > 0

    def is_invincible(self) -> bool:
        """Check if entity is currently invincible"""
        return self.invincibility_timer > 0.0

    def kill(self):
        """Kill entity instantly"""
        self.current_health = 0


# ============================================================================
# AI Component (for NPCs and enemies)
# ============================================================================


class AIComponent(Component):
    """
    Basic AI component

    Can be extended for specific AI behaviors.
    """

    def __init__(self, entity_id: int, ai_type: str = "idle"):
        super().__init__(entity_id)
        self.ai_type = ai_type  # "idle", "patrol", "chase", "flee"
        self.target_entity_id: int | None = None
        self.state: str = "idle"
        self.state_timer: float = 0.0

    def update(self, dt: float, entity_manager):
        """Update AI behavior"""
        self.state_timer += dt

        if self.ai_type == "idle":
            self._update_idle(dt, entity_manager)
        elif self.ai_type == "patrol":
            self._update_patrol(dt, entity_manager)
        elif self.ai_type == "chase":
            self._update_chase(dt, entity_manager)
        elif self.ai_type == "flee":
            self._update_flee(dt, entity_manager)

    def _update_idle(self, dt: float, entity_manager):
        """Idle behavior - do nothing"""
        pass

    def _update_patrol(self, dt: float, entity_manager):
        """Patrol behavior - implemented by PatrolComponent"""
        pass

    def _update_chase(self, dt: float, entity_manager):
        """Chase behavior - implemented by FollowComponent"""
        pass

    def _update_flee(self, dt: float, entity_manager):
        """Flee behavior - opposite of chase"""
        pass

    def set_target(self, target_entity_id: int | None):
        """Set target entity for chase/flee"""
        self.target_entity_id = target_entity_id


# ============================================================================
# Patrol Component
# ============================================================================


class PatrolComponent(Component):
    """
    Patrol movement component

    Entity moves back and forth between two points.
    """

    def __init__(self, entity_id: int, speed: float = 2.0, patrol_distance: float = 100.0):
        super().__init__(entity_id)
        self.speed = speed
        self.patrol_distance = patrol_distance
        self.start_x: float | None = None
        self.direction = 1  # 1 = right, -1 = left

    def initialize(self, entity_manager):
        """Initialize patrol start position"""
        entity = entity_manager.get_entity(self.entity_id)
        if entity and entity.physics:
            self.start_x = entity.physics.x

    def update(self, dt: float, entity_manager):
        """Update patrol movement"""
        entity = entity_manager.get_entity(self.entity_id)
        if not entity or not entity.physics or self.start_x is None:
            return

        # Move in current direction
        entity.physics.vx = self.direction * self.speed

        # Check if reached patrol limit
        distance_from_start = entity.physics.x - self.start_x
        if distance_from_start > self.patrol_distance:
            self.direction = -1
            entity.physics.x = self.start_x + self.patrol_distance
        elif distance_from_start < -self.patrol_distance:
            self.direction = 1
            entity.physics.x = self.start_x - self.patrol_distance


# ============================================================================
# Follow Component
# ============================================================================


class FollowComponent(Component):
    """
    Follow target component

    Entity follows target entity (e.g., enemy chasing player).
    """

    def __init__(
        self,
        entity_id: int,
        target_entity_id: int,
        speed: float = 3.0,
        follow_distance: float = 50.0,
    ):
        super().__init__(entity_id)
        self.target_entity_id = target_entity_id
        self.speed = speed
        self.follow_distance = follow_distance  # Stop when this close

    def update(self, dt: float, entity_manager):
        """Update follow behavior"""
        entity = entity_manager.get_entity(self.entity_id)
        target = entity_manager.get_entity(self.target_entity_id)

        if not entity or not target or not entity.physics or not target.physics:
            return

        # Calculate distance to target
        dx = target.physics.x - entity.physics.x
        dy = target.physics.y - entity.physics.y
        distance = (dx * dx + dy * dy) ** 0.5

        # If close enough, stop
        if distance <= self.follow_distance:
            entity.physics.vx = 0.0
            return

        # Move towards target
        if dx > 0:
            entity.physics.vx = self.speed
        elif dx < 0:
            entity.physics.vx = -self.speed
        else:
            entity.physics.vx = 0.0


# ============================================================================
# Projectile Component
# ============================================================================


class ProjectileComponent(Component):
    """
    Projectile component

    Entity moves in a direction until it hits something or times out.
    """

    def __init__(
        self,
        entity_id: int,
        velocity_x: float,
        velocity_y: float,
        lifetime: float = 5.0,
        damage: int = 1,
    ):
        super().__init__(entity_id)
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.lifetime = lifetime
        self.damage = damage
        self.age = 0.0

    def initialize(self, entity_manager):
        """Initialize projectile velocity"""
        entity = entity_manager.get_entity(self.entity_id)
        if entity and entity.physics:
            entity.physics.vx = self.velocity_x
            entity.physics.vy = self.velocity_y

    def update(self, dt: float, entity_manager):
        """Update projectile lifetime"""
        self.age += dt

        # Destroy projectile if lifetime exceeded
        if self.age >= self.lifetime:
            entity_manager.destroy_entity(self.entity_id, reason="timeout")


# ============================================================================
# Pickup Component
# ============================================================================


class PickupComponent(Component):
    """
    Pickup component

    Entity can be collected by player (coin, health, life, etc.)
    """

    def __init__(
        self, entity_id: int, pickup_type: str, value: int = 1, collection_radius: float = 16.0
    ):
        super().__init__(entity_id)
        self.pickup_type = pickup_type  # "coin", "health", "life", "powerup"
        self.value = value
        self.collection_radius = collection_radius
        self.collected = False

    def update(self, dt: float, entity_manager):
        """Check for collection"""
        if self.collected:
            return

        entity = entity_manager.get_entity(self.entity_id)
        if not entity or not entity.physics:
            return

        # Check distance to all players
        from core.entity_system import EntityType

        players = entity_manager.get_entities_by_type(EntityType.PLAYER)

        for player in players:
            if not player.physics:
                continue

            # Calculate distance
            dx = player.physics.x - entity.physics.x
            dy = player.physics.y - entity.physics.y
            distance = (dx * dx + dy * dy) ** 0.5

            # Check if close enough to collect
            if distance <= self.collection_radius:
                self._on_collect(player, entity_manager)
                break

    def _on_collect(self, player_entity, entity_manager):
        """Handle collection"""
        from core.event_bus import PickupCollectedEvent

        # Emit event
        entity_manager.event_bus.emit(
            PickupCollectedEvent(
                player_id=player_entity.entity_id, pickup_type=self.pickup_type, value=self.value
            )
        )

        # Mark as collected and destroy
        self.collected = True
        entity_manager.destroy_entity(self.entity_id, reason="collected")
