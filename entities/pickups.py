"""
Pickup Entities - Collectibles and Power-ups

Defines various pickup types including coins, health, and collectibles.
"""

import math

import pygame


class PickupCollectedEvent:
    """Event emitted when a pickup is collected"""

    def __init__(self, pickup_type: str, value: int, position: tuple[float, float]):
        self.pickup_type = pickup_type
        self.value = value
        self.position = position


class BasePickup:
    """
    Base class for all pickups.

    Features:
    - Auto-collection radius
    - Visual bobbing animation
    - Collision detection
    - Collection events
    """

    def __init__(
        self, x: float, y: float, pickup_type: str, value: int, auto_collect_radius: float = 24.0
    ):
        self.x = x
        self.y = y
        self.pickup_type = pickup_type
        self.value = value
        self.auto_collect_radius = auto_collect_radius

        # Visual state
        self.bob_offset = 0.0
        self.bob_speed = 2.0  # radians per second
        self.bob_amplitude = 4.0  # pixels
        self.rotation = 0.0
        self.rotation_speed = 2.0  # radians per second

        # Collection state
        self.collected = False
        self.alive = True

        # Size
        self.width = 16
        self.height = 16

    def update(self, dt: float):
        """Update pickup animation"""
        if not self.collected:
            # Bobbing animation
            self.bob_offset = (
                math.sin(pygame.time.get_ticks() / 1000.0 * self.bob_speed) * self.bob_amplitude
            )

            # Rotation animation
            self.rotation += self.rotation_speed * dt
            if self.rotation > 2 * math.pi:
                self.rotation -= 2 * math.pi

    def check_collection(
        self, player_x: float, player_y: float, player_width: float, player_height: float
    ) -> bool:
        """
        Check if player is close enough to collect this pickup.

        Args:
            player_x, player_y: Player top-left position
            player_width, player_height: Player dimensions

        Returns:
            True if pickup should be collected
        """
        if self.collected:
            return False

        # Calculate player center
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        # Calculate pickup center
        pickup_center_x = self.x + self.width / 2
        pickup_center_y = self.y + self.height / 2

        # Calculate distance
        distance = math.sqrt(
            (player_center_x - pickup_center_x) ** 2 + (player_center_y - pickup_center_y) ** 2
        )

        # Check if within collection radius
        return distance < self.auto_collect_radius

    def collect(self):
        """Mark this pickup as collected"""
        self.collected = True
        self.alive = False

    def get_rect(self) -> pygame.Rect:
        """Get collision rectangle (with bobbing offset)"""
        return pygame.Rect(int(self.x), int(self.y + self.bob_offset), self.width, self.height)

    def get_render_position(self) -> tuple[float, float]:
        """Get position for rendering (with bobbing)"""
        return (self.x, self.y + self.bob_offset)


class CoinPickup(BasePickup):
    """
    Coin collectible - basic currency/score.

    Properties:
    - Value: 1 point
    - Color: Gold
    - Auto-collect radius: 24px
    """

    def __init__(self, x: float, y: float, value: int = 1):
        super().__init__(x, y, "coin", value, auto_collect_radius=24.0)
        self.color = (255, 215, 0)  # Gold
        self.width = 12
        self.height = 12


class HealthPickup(BasePickup):
    """
    Health pickup - restores player health.

    Properties:
    - Value: 1 heart
    - Color: Red
    - Auto-collect radius: 20px
    """

    def __init__(self, x: float, y: float, value: int = 1):
        super().__init__(x, y, "health", value, auto_collect_radius=20.0)
        self.color = (255, 50, 50)  # Red
        self.width = 16
        self.height = 16


class CollectiblePickup(BasePickup):
    """
    Special collectible - optional challenge items.

    Properties:
    - Value: 1 collectible
    - Color: Cyan
    - Auto-collect radius: 20px
    - Tracked for 100% completion
    """

    def __init__(self, x: float, y: float, value: int = 1):
        super().__init__(x, y, "collectible", value, auto_collect_radius=20.0)
        self.color = (0, 255, 255)  # Cyan
        self.width = 14
        self.height = 14
        self.bob_amplitude = 6.0  # More prominent bobbing


class PickupManager:
    """
    Manages all pickups in the game.

    Responsibilities:
    - Spawn pickups
    - Update animations
    - Check collections
    - Track statistics
    - Emit collection events
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.pickups = []

        # Statistics
        self.coins_collected = 0
        self.health_collected = 0
        self.collectibles_collected = 0
        self.total_collectibles = 0

    def spawn_coin(self, x: float, y: float, value: int = 1):
        """Spawn a coin at the given position"""
        coin = CoinPickup(x, y, value)
        self.pickups.append(coin)
        return coin

    def spawn_health(self, x: float, y: float, value: int = 1):
        """Spawn a health pickup at the given position"""
        health = HealthPickup(x, y, value)
        self.pickups.append(health)
        return health

    def spawn_collectible(self, x: float, y: float, value: int = 1):
        """Spawn a special collectible at the given position"""
        collectible = CollectiblePickup(x, y, value)
        self.pickups.append(collectible)
        self.total_collectibles += 1
        return collectible

    def update(self, dt: float):
        """Update all pickups"""
        for pickup in self.pickups:
            if pickup.alive:
                pickup.update(dt)

    def check_collections(
        self, player_x: float, player_y: float, player_width: float, player_height: float
    ):
        """
        Check if player collected any pickups.

        Returns:
            List of collected pickups
        """
        collected = []

        for pickup in self.pickups:
            if pickup.alive and pickup.check_collection(
                player_x, player_y, player_width, player_height
            ):
                pickup.collect()
                collected.append(pickup)

                # Update statistics
                if pickup.pickup_type == "coin":
                    self.coins_collected += pickup.value
                elif pickup.pickup_type == "health":
                    self.health_collected += pickup.value
                elif pickup.pickup_type == "collectible":
                    self.collectibles_collected += pickup.value

                # Emit collection event
                event = PickupCollectedEvent(
                    pickup_type=pickup.pickup_type,
                    value=pickup.value,
                    position=(pickup.x, pickup.y),
                )
                self.event_bus.emit(event)

        return collected

    def get_alive_pickups(self):
        """Get list of pickups that haven't been collected"""
        return [p for p in self.pickups if p.alive]

    def get_stats(self):
        """Get pickup collection statistics"""
        return {
            "coins": self.coins_collected,
            "health": self.health_collected,
            "collectibles": f"{self.collectibles_collected}/{self.total_collectibles}",
        }

    def reset(self):
        """Reset all pickups and statistics"""
        self.pickups.clear()
        self.coins_collected = 0
        self.health_collected = 0
        self.collectibles_collected = 0
        self.total_collectibles = 0
