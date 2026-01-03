"""
Enemy Manager - Enemy Spawning, Updates, and Loot System

This module provides enemy management:
- Enemy spawning at anchor positions
- AI updates for all enemies
- Player-enemy collision detection
- Enemy death handling with loot drops
- Event emission for objective tracking

Version: v0.6.0
"""

import math
from dataclasses import dataclass

from config.physics_constants import FALL_GRAVITY_MULT, GRAVITY, MAX_FALL_SPEED
from core import EventBus
from entities.ai_random import AIRandom, derive_ai_seed
from entities.enemy import Enemy, EnemyAIState, EnemyType, get_enemy_definition
from entities.enemy_ai import EnemyAI, create_patrol_waypoints_horizontal
from game.health_system import HealthState
from game.loot_system import LootGenerator, get_loot_table_database
from game.objective_tracker import EnemyDeathEvent

# ============================================================
# Enemy Spawn Anchor
# ============================================================


@dataclass
class EnemySpawnAnchor:
    """
    Enemy spawn location and configuration.

    Defines where and what type of enemy should spawn.
    """

    anchor_id: str
    enemy_type: EnemyType
    x: float
    y: float

    # Patrol configuration
    patrol_type: str = "horizontal"  # "horizontal", "vertical", "circle", "stationary"
    patrol_distance: float = 100.0
    patrol_points: int = 2

    # Spawn seed for deterministic loot
    spawn_seed: int = 0


# ============================================================
# Item Pickup Entity
# ============================================================


@dataclass
class ItemPickup:
    """
    Item pickup entity in the world.

    Represents a collectible item dropped by enemies or placed in the level.
    """

    pickup_id: str
    item_id: str
    quantity: int
    x: float
    y: float
    width: int = 24
    height: int = 24

    # Visual
    pulse_timer: float = 0.0

    # Lifetime (optional, for temporary pickups)
    lifetime: float | None = None
    time_alive: float = 0.0

    def get_rect(self) -> tuple[float, float, int, int]:
        """Get pickup bounding box"""
        return (self.x, self.y, self.width, self.height)

    def update(self, dt: float):
        """Update pickup (visual effects, lifetime)"""
        self.pulse_timer += dt

        if self.lifetime is not None:
            self.time_alive += dt

    def is_expired(self) -> bool:
        """Check if pickup has expired"""
        if self.lifetime is None:
            return False
        return self.time_alive >= self.lifetime

    def get_pulse_scale(self) -> float:
        """Get pulsing scale for visual effect"""
        import math

        return 1.0 + 0.1 * math.sin(self.pulse_timer * 4)


@dataclass
class CurrencyPickup:
    """
    Currency (gold/coins) pickup entity.

    Represents money dropped by enemies or found in the level.
    """

    pickup_id: str
    amount: int
    x: float
    y: float
    width: int = 20
    height: int = 20

    # Visual
    pulse_timer: float = 0.0

    # Lifetime
    lifetime: float | None = 30.0  # Auto-collect or expire after 30 seconds
    time_alive: float = 0.0

    def get_rect(self) -> tuple[float, float, int, int]:
        """Get pickup bounding box"""
        return (self.x, self.y, self.width, self.height)

    def update(self, dt: float):
        """Update pickup"""
        self.pulse_timer += dt
        if self.lifetime is not None:
            self.time_alive += dt

    def is_expired(self) -> bool:
        """Check if pickup has expired"""
        if self.lifetime is None:
            return False
        return self.time_alive >= self.lifetime

    def get_pulse_scale(self) -> float:
        """Get pulsing scale for visual effect"""
        import math

        return 1.0 + 0.15 * math.sin(self.pulse_timer * 5)


# ============================================================
# Enemy Manager
# ============================================================


class EnemyManager:
    """
    Manages all enemies in the current level.

    Handles spawning, updates, collisions, death, and loot drops.
    """

    def __init__(self, event_bus: EventBus, level_seed: int):
        """
        Initialize enemy manager.

        Args:
            event_bus: Event bus for emitting events
            level_seed: Level seed for deterministic loot generation
        """
        self.event_bus = event_bus
        self.level_seed = level_seed

        # Active entities
        self.enemies: dict[str, Enemy] = {}
        self.enemy_ai: dict[str, EnemyAI] = {}
        self.item_pickups: dict[str, ItemPickup] = {}
        self.currency_pickups: dict[str, CurrencyPickup] = {}

        # Spawn tracking
        self.spawn_anchors: list[EnemySpawnAnchor] = []
        self.next_enemy_id = 0
        self.next_pickup_id = 0

    def clear(self):
        """Clear all enemies and pickups"""
        self.enemies.clear()
        self.enemy_ai.clear()
        self.item_pickups.clear()
        self.currency_pickups.clear()
        self.spawn_anchors.clear()
        self.next_enemy_id = 0
        self.next_pickup_id = 0

    # ============================================================
    # Enemy Spawning
    # ============================================================

    def register_spawn_anchor(self, anchor: EnemySpawnAnchor):
        """Register an enemy spawn anchor"""
        self.spawn_anchors.append(anchor)

    def spawn_all_enemies(self):
        """Spawn all enemies from registered anchors"""
        for anchor in self.spawn_anchors:
            self.spawn_enemy_from_anchor(anchor)

    def spawn_enemy_from_anchor(self, anchor: EnemySpawnAnchor) -> str:
        """
        Spawn an enemy from an anchor.

        Args:
            anchor: Spawn anchor

        Returns:
            Enemy ID
        """
        # Generate enemy ID
        enemy_id = f"enemy_{self.next_enemy_id}"
        self.next_enemy_id += 1

        # Get enemy definition
        definition = get_enemy_definition(anchor.enemy_type)
        if definition is None:
            print(f"[ERROR] Unknown enemy type: {anchor.enemy_type}")
            return enemy_id

        # Create health state
        health = HealthState(current_hp=definition.max_hp, max_hp=definition.max_hp)

        # Derive loot seed from level seed and anchor position
        loot_seed = self._derive_loot_seed(anchor.spawn_seed, anchor.x, anchor.y)

        # Create enemy entity
        enemy = Enemy(
            enemy_id=enemy_id,
            enemy_type=anchor.enemy_type,
            x=anchor.x,
            y=anchor.y,
            health_state=health,
            ai_state=EnemyAIState.PATROL,  # start moving immediately
            loot_table_id=definition.loot_table_id,
            loot_seed=loot_seed,
        )

        # Set up patrol waypoints
        if anchor.patrol_type == "horizontal":
            waypoints = create_patrol_waypoints_horizontal(
                anchor.x, anchor.y, anchor.patrol_distance, anchor.patrol_points
            )
            enemy.set_patrol_waypoints(waypoints)

        elif anchor.patrol_type == "vertical":
            from entities.enemy_ai import create_patrol_waypoints_vertical

            waypoints = create_patrol_waypoints_vertical(
                anchor.x, anchor.y, anchor.patrol_distance, anchor.patrol_points
            )
            enemy.set_patrol_waypoints(waypoints)

        elif anchor.patrol_type == "circle":
            from entities.enemy_ai import create_patrol_waypoints_circle

            waypoints = create_patrol_waypoints_circle(
                anchor.x, anchor.y, anchor.patrol_distance, anchor.patrol_points
            )
            enemy.set_patrol_waypoints(waypoints)

        elif anchor.patrol_type == "stationary":
            # No patrol waypoints
            pass

        # Create deterministic AI random generator
        ai_seed = derive_ai_seed(self.level_seed, enemy_id)
        ai_random = AIRandom(ai_seed)

        # Create AI controller with deterministic timing
        ai = EnemyAI(enemy, ai_random)

        # Register enemy
        self.enemies[enemy_id] = enemy
        self.enemy_ai[enemy_id] = ai

        return enemy_id

    def spawn_enemy(
        self, enemy_type: EnemyType, x: float, y: float, patrol_distance: float = 100.0
    ) -> str:
        """
        Spawn an enemy directly (without anchor).

        Args:
            enemy_type: Type of enemy
            x: X position
            y: Y position
            patrol_distance: Patrol distance

        Returns:
            Enemy ID
        """
        anchor = EnemySpawnAnchor(
            anchor_id=f"manual_{self.next_enemy_id}",
            enemy_type=enemy_type,
            x=x,
            y=y,
            patrol_distance=patrol_distance,
            spawn_seed=self.next_enemy_id,
        )
        return self.spawn_enemy_from_anchor(anchor)

    # ============================================================
    # Enemy Updates
    # ============================================================

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        player_state=None,
        collision_system=None,
        camera_rect: tuple[float, float, float, float] | None = None,
        cull_margin: float = 800.0,
    ) -> int:
        """
        Update all enemies.

        Args:
            dt: Delta time
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            Total damage dealt to player this frame
        """
        total_damage = 0
        dead_enemies = []

        # Update each enemy
        # Detection multiplier based on player movement/stealth
        detection_mult = 1.0
        if player_state:
            if getattr(player_state, "is_running", False):
                detection_mult = 1.5
            elif player_state.crouching:
                detection_mult = 0.6
            else:
                detection_mult = 1.0

        for enemy_id, enemy in self.enemies.items():
            # Update health (invincibility frames)
            enemy.update_health(dt)

            # Update animation
            enemy.update_animation(dt)

            # Update AI
            ai = self.enemy_ai.get(enemy_id)
            if ai:
                damage = ai.update(
                    dt,
                    player_x,
                    player_y,
                    player_width,
                    player_height,
                    detection_mult,
                    collision_system,
                )
                if damage:
                    total_damage += damage

            # Kickstart patrol if stalled on waypoint (prevents stuck idle)
            if (
                enemy.ai_state == EnemyAIState.PATROL
                and enemy.patrol_waypoints
                and abs(enemy.physics.vx) < 1.0
            ):
                target = enemy.get_current_waypoint()
                if target:
                    dx = target[0] - enemy.physics.x
                    if abs(dx) > 4.0:
                        # Convert move_speed from px/sec to px/tick (move_speed * dt)
                        speed_px_per_tick = enemy.get_definition().move_speed * dt * 0.5
                        enemy.physics.vx = speed_px_per_tick if dx > 0 else -speed_px_per_tick

            # Lightweight hover behavior for flying enemies (bats)
            definition = enemy.get_definition()
            if definition.can_fly:
                if enemy.ai_state in (EnemyAIState.PATROL, EnemyAIState.IDLE):
                    # Hover amplitude in px/tick (convert 20 px/sec to px/tick)
                    hover_amplitude = 20.0 * dt
                    hover = math.sin(enemy.ai_state_timer * 2.0) * hover_amplitude
                    enemy.physics.vy = hover
                elif enemy.ai_state in (EnemyAIState.CHASE, EnemyAIState.ATTACK):
                    # Nudge toward player's vertical position
                    player_center_y = player_y + player_height / 2
                    enemy.physics.vy += (
                        (player_center_y - (enemy.physics.y + definition.height / 2)) * 0.05 * dt
                    )
                    # Clamp to move_speed converted from px/sec to px/tick
                    max_speed_px_tick = definition.move_speed * dt
                    enemy.physics.vy = max(
                        min(enemy.physics.vy, max_speed_px_tick), -max_speed_px_tick
                    )

            # Note: AI and movement component write directly to physics, no sync needed

            # Apply gravity (unless flying)
            definition = enemy.get_definition()
            if not definition.can_fly:
                enemy.physics.vy += GRAVITY * definition.gravity_scale
                if enemy.physics.vy > 0:
                    enemy.physics.vy += (
                        GRAVITY * (FALL_GRAVITY_MULT - 1.0) * definition.gravity_scale
                    )
                if enemy.physics.vy > MAX_FALL_SPEED:
                    enemy.physics.vy = MAX_FALL_SPEED

            # Integrate velocity
            enemy.physics.x += enemy.physics.vx
            enemy.physics.y += enemy.physics.vy

            # Collision resolution (optional if collision system provided)
            if collision_system:
                collision_system.check_and_resolve(enemy)

            # Sync physics back to scalar fields for rendering/AI
            enemy.sync_from_physics()

            # Clamp to non-negative world coordinates to avoid falling through origin
            if enemy.physics.x < 0:
                enemy.physics.x = 0
            if enemy.physics.y < 0:
                enemy.physics.y = 0
            enemy.sync_from_physics()

            # If still embedded after resolution, a second resolve should separate without killing velocity
            if collision_system:
                collision_system.check_and_resolve(enemy)
                enemy.sync_from_physics()

            # Check if dead
            if enemy.is_dead():
                dead_enemies.append(enemy_id)

        # Remove dead enemies and spawn loot
        for enemy_id in dead_enemies:
            self._handle_enemy_death(enemy_id)

        # Update pickups
        self._update_pickups(dt)

        return total_damage

    def _update_pickups(self, dt: float):
        """Update all pickups"""
        expired_items = []
        expired_currency = []

        # Update item pickups
        for pickup_id, pickup in self.item_pickups.items():
            pickup.update(dt)
            if pickup.is_expired():
                expired_items.append(pickup_id)

        # Update currency pickups
        for pickup_id, pickup in self.currency_pickups.items():
            pickup.update(dt)
            if pickup.is_expired():
                expired_currency.append(pickup_id)

        # Remove expired pickups
        for pickup_id in expired_items:
            del self.item_pickups[pickup_id]

        for pickup_id in expired_currency:
            del self.currency_pickups[pickup_id]

    # ============================================================
    # Collision Detection
    # ============================================================

    def check_player_enemy_collision(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> list[str]:
        """
        Check for collisions between player and enemies.

        Args:
            player_x: Player X
            player_y: Player Y
            player_width: Player width
            player_height: Player height

        Returns:
            List of enemy IDs player is colliding with
        """
        colliding_enemies = []

        player_rect = (player_x, player_y, player_width, player_height)

        for enemy_id, enemy in self.enemies.items():
            if enemy.is_dead():
                continue

            enemy_rect = enemy.get_rect()
            if self._rects_overlap(player_rect, enemy_rect):
                colliding_enemies.append(enemy_id)

        return colliding_enemies

    def check_attack_collision(self, attack_rect: tuple[float, float, float, float]) -> list[str]:
        """
        Check which enemies overlap a custom attack rectangle.

        Args:
            attack_rect: (x, y, w, h) for the attack hitbox

        Returns:
            List of enemy IDs hit by the attack
        """
        ax, ay, aw, ah = attack_rect
        attack_box = (ax, ay, aw, ah)
        hit = []
        for enemy_id, enemy in self.enemies.items():
            if enemy.is_dead():
                continue
            if self._rects_overlap(attack_box, enemy.get_rect()):
                hit.append(enemy_id)
        return hit

    def check_pickup_collection(
        self,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        player_inventory,
    ) -> bool:
        """
        Check for pickup collection.

        Args:
            player_x: Player X
            player_y: Player Y
            player_width: Player width
            player_height: Player height
            player_inventory: Player inventory to add items to

        Returns:
            True if any pickups were collected
        """
        collected_items = []
        collected_currency = []

        player_rect = (player_x, player_y, player_width, player_height)

        # Check item pickups
        for pickup_id, pickup in self.item_pickups.items():
            if self._rects_overlap(player_rect, pickup.get_rect()):
                # Try to add to inventory
                if player_inventory.add_item(pickup.item_id, pickup.quantity):
                    collected_items.append(pickup_id)
                    # Emit collection event
                    from game.objective_tracker import ItemCollectedEvent

                    self.event_bus.emit(
                        ItemCollectedEvent(
                            item_id=pickup.item_id,
                            quantity=pickup.quantity,
                            position=(pickup.x, pickup.y),
                        )
                    )

        # Check currency pickups
        for pickup_id, pickup in self.currency_pickups.items():
            if self._rects_overlap(player_rect, pickup.get_rect()):
                player_inventory.currency += pickup.amount
                collected_currency.append(pickup_id)

        # Remove collected pickups
        for pickup_id in collected_items:
            del self.item_pickups[pickup_id]

        for pickup_id in collected_currency:
            del self.currency_pickups[pickup_id]

        return len(collected_items) > 0 or len(collected_currency) > 0

    def _rects_overlap(self, rect1: tuple, rect2: tuple) -> bool:
        """Check if two rectangles overlap"""
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2

        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

    # ============================================================
    # Enemy Death & Loot
    # ============================================================

    def _handle_enemy_death(self, enemy_id: str):
        """
        Handle enemy death.

        Args:
            enemy_id: ID of dead enemy
        """
        enemy = self.enemies.get(enemy_id)
        if enemy is None:
            return

        # Generate loot
        self._generate_loot(enemy)

        # Emit death event for objective tracking
        self.event_bus.emit(
            EnemyDeathEvent(
                enemy_id=enemy.enemy_id,
                enemy_type=enemy.enemy_type.value,
                position=enemy.get_center(),
            )
        )

        # Remove enemy
        del self.enemies[enemy_id]
        if enemy_id in self.enemy_ai:
            del self.enemy_ai[enemy_id]

    def _generate_loot(self, enemy: Enemy):
        """
        Generate and spawn loot from enemy.

        Args:
            enemy: Dead enemy
        """
        # Get loot table database
        loot_db = get_loot_table_database()
        if loot_db is None:
            print("[WARNING] Loot table database not initialized")
            return

        # Get loot table
        loot_table = loot_db.get_table(enemy.loot_table_id)
        if loot_table is None:
            print(f"[WARNING] Loot table not found: {enemy.loot_table_id}")
            return

        # Generate loot using deterministic seed
        loot_gen = LootGenerator(enemy.loot_seed)
        loot_items, currency_amount = loot_gen.generate_loot(loot_table)

        # Spawn item pickups
        enemy_center_x, enemy_center_y = enemy.get_center()

        for item_id, quantity in loot_items:
            self._spawn_item_pickup(item_id, quantity, enemy_center_x, enemy_center_y)

        # Spawn currency if dropped
        if currency_amount > 0:
            self._spawn_currency_pickup(currency_amount, enemy_center_x, enemy_center_y)

    def _spawn_item_pickup(self, item_id: str, quantity: int, x: float, y: float):
        """
        Spawn an item pickup.

        Args:
            item_id: Item ID
            quantity: Quantity
            x: X position
            y: Y position
        """
        pickup_id = f"item_{self.next_pickup_id}"
        self.next_pickup_id += 1

        pickup = ItemPickup(
            pickup_id=pickup_id,
            item_id=item_id,
            quantity=quantity,
            x=x - 12,  # Center pickup (24px wide)
            y=y - 12,
            lifetime=None,  # Items don't expire
        )

        self.item_pickups[pickup_id] = pickup

    def _spawn_currency_pickup(self, amount: int, x: float, y: float):
        """
        Spawn a currency pickup.

        Args:
            amount: Currency amount
            x: X position
            y: Y position
        """
        pickup_id = f"currency_{self.next_pickup_id}"
        self.next_pickup_id += 1

        pickup = CurrencyPickup(
            pickup_id=pickup_id,
            amount=amount,
            x=x - 10,  # Center pickup (20px wide)
            y=y - 10,
            lifetime=30.0,  # Auto-expire after 30 seconds
        )

        self.currency_pickups[pickup_id] = pickup

    def _derive_loot_seed(self, spawn_seed: int, x: float, y: float) -> int:
        """
        Derive deterministic loot seed from spawn seed and position.

        Args:
            spawn_seed: Base spawn seed
            x: X position
            y: Y position

        Returns:
            Loot seed
        """
        import hashlib

        # Combine level seed, spawn seed, and position
        seed_string = f"{self.level_seed}:{spawn_seed}:{int(x)}:{int(y)}"
        hash_bytes = hashlib.sha256(seed_string.encode()).digest()

        # Convert first 4 bytes to int
        return int.from_bytes(hash_bytes[:4], byteorder="big", signed=False)

    # ============================================================
    # Enemy Damage
    # ============================================================

    def damage_enemy(
        self,
        enemy_id: str,
        damage: int,
        knockback_x: float = 0.0,
        knockback_y: float = 0.0,
        stun_duration: float = 0.0,
    ) -> bool:
        """
        Deal damage to an enemy.

        Args:
            enemy_id: Enemy ID
            damage: Damage amount
            knockback_x: Knockback velocity X
            knockback_y: Knockback velocity Y
            stun_duration: Stun duration in seconds

        Returns:
            True if enemy died
        """
        enemy = self.enemies.get(enemy_id)
        if enemy is None:
            return False

        died = enemy.take_damage(damage, knockback_x, knockback_y, stun_duration)
        return died

    # ============================================================
    # Queries
    # ============================================================

    def get_enemy(self, enemy_id: str) -> Enemy | None:
        """Get enemy by ID"""
        return self.enemies.get(enemy_id)

    def get_all_enemies(self) -> list[Enemy]:
        """Get list of all enemies"""
        return list(self.enemies.values())

    def get_living_enemy_count(self) -> int:
        """Get count of living enemies"""
        return sum(1 for enemy in self.enemies.values() if enemy.is_alive())

    def get_all_item_pickups(self) -> list[ItemPickup]:
        """Get list of all item pickups"""
        return list(self.item_pickups.values())

    def get_all_currency_pickups(self) -> list[CurrencyPickup]:
        """Get list of all currency pickups"""
        return list(self.currency_pickups.values())


# ============================================================
# Global Enemy Manager Instance
# ============================================================

_enemy_manager: EnemyManager | None = None


def initialize_enemy_manager(event_bus: EventBus, level_seed: int):
    """Initialize the global enemy manager"""
    global _enemy_manager
    _enemy_manager = EnemyManager(event_bus, level_seed)


def get_enemy_manager() -> EnemyManager | None:
    """Get the global enemy manager instance"""
    return _enemy_manager
