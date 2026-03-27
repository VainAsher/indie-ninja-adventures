"""
Enemy System - Enemy Entities and AI for Combat

This module provides enemy entities and AI behavior:
- Enemy types: Goblin, Bat, Slime
- AI states: PATROL, CHASE, ATTACK, STUNNED
- Health system integration
- Loot drops on death
- Collision detection
- Event emission for objective tracking

Version: v0.6.0
"""

import math
from dataclasses import dataclass, field
from enum import Enum

from core.entity_system import EntityType
from core.state import PhysicsState
from entities.components.enemy_movement import EnemyMovementComponent
from game.health_system import HealthState

# ============================================================
# Enemy Types
# ============================================================


class EnemyType(Enum):
    """Enemy entity types"""

    GOBLIN = "goblin"  # Ground patrol enemy
    BAT = "bat"  # Flying enemy
    SLIME = "slime"  # Slow, high HP enemy
    SKELETON = "skeleton"  # Undead enemy
    WOLF = "wolf"  # Fast ground enemy


# ============================================================
# Enemy AI States
# ============================================================


class EnemyAIState(Enum):
    """Enemy AI behavior states"""

    IDLE = "idle"  # Standing still
    PATROL = "patrol"  # Moving between waypoints
    CHASE = "chase"  # Chasing player
    ATTACK = "attack"  # Attacking player
    STUNNED = "stunned"  # Stunned from player attack
    DEAD = "dead"  # Dead (before removal)


# ============================================================
# Enemy Attack Sub-States
# ============================================================


class EnemyAttackSubState(Enum):
    """Attack phase sub-states for telegraphed attacks"""

    NONE = "none"  # Not in attack sequence
    WINDUP = "windup"  # Telegraph/warning phase (no damage)
    ACTIVE = "active"  # Damage hitbox active
    RECOVERY = "recovery"  # Cooldown after attack


# ============================================================
# Enemy Definition
# ============================================================


@dataclass
class EnemyDefinition:
    """
    Static enemy definition.

    Defines enemy properties and behavior.
    """

    enemy_type: EnemyType
    display_name: str

    # Stats
    max_hp: int
    base_damage: int
    move_speed: float  # Pixels per second

    # Visual
    width: int = 32
    height: int = 48
    sprite_id: str = "enemy_default"

    # AI behavior
    detection_radius: float = 200.0  # Pixels
    attack_range: float = 32.0  # Pixels
    patrol_speed_multiplier: float = 0.5  # Slower during patrol

    # Attack timing (telegraphed attacks)
    attack_windup_time: float = 0.6  # Telegraph duration (seconds)
    attack_active_time: float = 0.15  # Damage window (seconds)
    attack_recovery_time: float = 0.4  # Recovery duration (seconds)

    # Loot
    loot_table_id: str = "enemy_common"
    exp_value: int = 10  # Experience points granted

    # Physics
    can_fly: bool = False
    gravity_scale: float = 1.0


# ============================================================
# Default Enemy Definitions
# ============================================================

ENEMY_DEFINITIONS = {
    EnemyType.GOBLIN: EnemyDefinition(
        enemy_type=EnemyType.GOBLIN,
        display_name="Goblin",
        max_hp=3,
        base_damage=1,
        move_speed=72.0,  # Reduced from 120.0 (40% reduction)
        width=32,
        height=48,
        detection_radius=200.0,
        attack_range=64.0,  # Increased for better visibility (stops earlier)
        attack_windup_time=0.5,
        attack_active_time=0.15,
        attack_recovery_time=0.4,
        loot_table_id="enemy_common",
        exp_value=10,
        can_fly=False,
    ),
    EnemyType.BAT: EnemyDefinition(
        enemy_type=EnemyType.BAT,
        display_name="Bat",
        max_hp=2,
        base_damage=1,
        move_speed=90.0,  # Reduced from 150.0 (40% reduction)
        width=24,
        height=24,
        detection_radius=250.0,
        attack_range=56.0,  # Increased for better visibility
        attack_windup_time=0.6,
        attack_active_time=0.1,
        attack_recovery_time=0.3,
        loot_table_id="enemy_common",
        exp_value=8,
        can_fly=True,
        gravity_scale=0.0,
    ),
    EnemyType.SLIME: EnemyDefinition(
        enemy_type=EnemyType.SLIME,
        display_name="Slime",
        max_hp=5,
        base_damage=1,
        move_speed=36.0,  # Reduced from 60.0 (40% reduction)
        width=40,
        height=32,
        detection_radius=150.0,
        attack_range=72.0,  # Increased for better visibility (wide enemy)
        attack_windup_time=0.7,
        attack_active_time=0.2,
        attack_recovery_time=0.5,
        loot_table_id="enemy_common",
        exp_value=15,
        can_fly=False,
    ),
    EnemyType.SKELETON: EnemyDefinition(
        enemy_type=EnemyType.SKELETON,
        display_name="Skeleton",
        max_hp=4,
        base_damage=2,
        move_speed=60.0,  # Reduced from 100.0 (40% reduction)
        width=32,
        height=56,
        detection_radius=220.0,
        attack_range=240.0,  # Ranged attacker — stops and shoots from distance
        attack_windup_time=0.6,
        attack_active_time=0.15,
        attack_recovery_time=0.4,
        loot_table_id="enemy_uncommon",
        exp_value=20,
        can_fly=False,
    ),
    EnemyType.WOLF: EnemyDefinition(
        enemy_type=EnemyType.WOLF,
        display_name="Wolf",
        max_hp=4,
        base_damage=2,
        move_speed=108.0,  # Reduced from 180.0 (40% reduction)
        width=48,
        height=32,
        detection_radius=300.0,
        attack_range=64.0,  # Increased for better visibility
        attack_windup_time=0.5,
        attack_active_time=0.12,
        attack_recovery_time=0.35,
        patrol_speed_multiplier=0.6,
        loot_table_id="enemy_uncommon",
        exp_value=18,
        can_fly=False,
    ),
}


# ============================================================
# Enemy Entity
# ============================================================


@dataclass
class Enemy:
    """
    Enemy instance in the game world.

    Represents an active enemy with position, health, AI state, and loot.
    """

    enemy_id: str
    enemy_type: EnemyType
    x: float
    y: float

    # Physics state
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    facing_right: bool = True
    on_ground: bool = False

    # Health
    health_state: HealthState = field(default_factory=lambda: HealthState(3, 3))

    # AI state
    ai_state: EnemyAIState = EnemyAIState.IDLE
    ai_state_timer: float = 0.0  # Time in current state

    # Patrol behavior
    patrol_waypoints: list[tuple[float, float]] = field(default_factory=list)
    current_waypoint_index: int = 0
    patrol_wait_time: float = 0.0  # Time to wait at waypoint

    # Chase/attack targets
    target_player_x: float | None = None
    target_player_y: float | None = None
    last_seen_player_x: float | None = None
    last_seen_player_y: float | None = None

    # Stun state
    stun_duration: float = 0.0
    knockback_velocity_x: float = 0.0
    knockback_velocity_y: float = 0.0

    # Loot
    loot_table_id: str = "enemy_common"
    loot_seed: int = 0  # Deterministic loot generation

    # Animation (legacy integer counter used by procedural renderer)
    animation_frame: int = 0
    animation_timer: float = 0.0

    # Unified animation state machine (None until EnemyManager assigns one at spawn)
    anim_sm: object = field(default=None, repr=False)

    # Ranged attack — set by AI, consumed by EnemyManager to spawn a projectile
    pending_arrow_fire: bool = False

    # Attack sub-state tracking (telegraphed attacks)
    attack_substate: "EnemyAttackSubState" = None  # Will be initialized in __post_init__
    attack_substate_timer: float = 0.0

    # Shared physics component
    physics: PhysicsState = None
    movement: EnemyMovementComponent | None = None

    def __post_init__(self):
        """Ensure physics state exists and is synced with scalar fields."""
        definition = self.get_definition()
        if self.physics is None:
            self.physics = PhysicsState(
                x=self.x,
                y=self.y,
                vx=self.velocity_x,
                vy=self.velocity_y,
                width=definition.width,
                height=definition.height,
            )
        else:
            # Sync scalars from provided physics
            self.x = self.physics.x
            self.y = self.physics.y
            self.velocity_x = self.physics.vx
            self.velocity_y = self.physics.vy
        # Entity metadata for collision logging compatibility
        self.entity_type = EntityType.ENEMY
        self.active = True
        # Initialize movement component (simple acceleration helper)
        self.movement = EnemyMovementComponent(
            move_speed=definition.move_speed, can_fly=definition.can_fly
        )
        # Initialize attack sub-state if not set
        if self.attack_substate is None:
            self.attack_substate = EnemyAttackSubState.NONE

    def sync_to_physics(self):
        """Copy scalar position/velocity into physics component."""
        self.physics.x = self.x
        self.physics.y = self.y
        self.physics.vx = self.velocity_x
        self.physics.vy = self.velocity_y

    def sync_from_physics(self):
        """Copy physics component back into scalar fields."""
        self.x = self.physics.x
        self.y = self.physics.y
        self.velocity_x = self.physics.vx
        self.velocity_y = self.physics.vy
        self.on_ground = self.physics.on_ground

    @property
    def entity_id(self):
        """Alias for collision system compatibility."""
        return self.enemy_id

    def get_definition(self) -> EnemyDefinition:
        """Get enemy definition"""
        return ENEMY_DEFINITIONS.get(self.enemy_type, ENEMY_DEFINITIONS[EnemyType.GOBLIN])

    def get_rect(self) -> tuple[float, float, float, float]:
        """Get enemy bounding box (x, y, width, height)"""
        definition = self.get_definition()
        return (self.physics.x, self.physics.y, definition.width, definition.height)

    def get_attack_hitbox(self) -> tuple[float, float, float, float] | None:
        """
        Return the forward melee hitbox for enemies that use one (goblin).
        Returns None for enemies that use body contact or projectiles.
        """
        if self.enemy_type != EnemyType.GOBLIN:
            return None
        definition = self.get_definition()
        hw, hh = 44, definition.height - 12
        if self.facing_right:
            hx = self.physics.x + definition.width - 4
        else:
            hx = self.physics.x - hw + 4
        hy = self.physics.y + 6
        return (hx, hy, hw, hh)

    def get_center(self) -> tuple[float, float]:
        """Get enemy center position"""
        definition = self.get_definition()
        return (self.physics.x + definition.width / 2, self.physics.y + definition.height / 2)

    def distance_to(self, target_x: float, target_y: float) -> float:
        """Calculate distance to target position"""
        center_x, center_y = self.get_center()
        dx = target_x - center_x
        dy = target_y - center_y
        return math.sqrt(dx * dx + dy * dy)

    def distance_to_player(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> float:
        """Calculate distance to player center"""
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2
        return self.distance_to(player_center_x, player_center_y)

    def can_see_player(
        self,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        detection_mult: float = 1.0,
    ) -> bool:
        """Check if enemy can detect player"""
        definition = self.get_definition()
        distance = self.distance_to_player(player_x, player_y, player_width, player_height)
        return distance <= definition.detection_radius * detection_mult

    def is_in_attack_range(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> bool:
        """Check if player is in attack range"""
        definition = self.get_definition()
        distance = self.distance_to_player(player_x, player_y, player_width, player_height)
        return distance <= definition.attack_range

    def take_damage(
        self,
        damage: int,
        knockback_x: float = 0.0,
        knockback_y: float = 0.0,
        stun_duration: float = 0.0,
    ) -> bool:
        """
        Take damage and apply knockback/stun.

        Args:
            damage: Damage amount
            knockback_x: Knockback velocity X
            knockback_y: Knockback velocity Y
            stun_duration: Stun duration in seconds

        Returns:
            True if enemy died
        """
        died = self.health_state.take_damage(damage, defense=0)

        if died:
            self.ai_state = EnemyAIState.DEAD
            return True

        # Apply knockback and stun
        if stun_duration > 0.0:
            self.ai_state = EnemyAIState.STUNNED
            self.stun_duration = stun_duration
            self.knockback_velocity_x = knockback_x
            self.knockback_velocity_y = knockback_y
            # Cancel attack sequence if stunned
            self.attack_substate = EnemyAttackSubState.NONE
            self.attack_substate_timer = 0.0

        return False

    def is_alive(self) -> bool:
        """Check if enemy is alive"""
        return self.health_state.is_alive() and self.ai_state != EnemyAIState.DEAD

    def is_dead(self) -> bool:
        """Check if enemy is dead"""
        return not self.is_alive()

    def set_patrol_waypoints(self, waypoints: list[tuple[float, float]]):
        """Set patrol waypoints"""
        self.patrol_waypoints = waypoints
        self.current_waypoint_index = 0

    def get_current_waypoint(self) -> tuple[float, float] | None:
        """Get current patrol waypoint"""
        if not self.patrol_waypoints:
            return None
        if self.current_waypoint_index >= len(self.patrol_waypoints):
            return None
        return self.patrol_waypoints[self.current_waypoint_index]

    def advance_waypoint(self):
        """Move to next waypoint (loops)"""
        if not self.patrol_waypoints:
            return
        self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.patrol_waypoints)

    def update_animation(self, dt: float):
        """Update animation frame"""
        self.animation_timer += dt
        if self.animation_timer >= 0.2:  # 200ms per frame
            self.animation_timer = 0.0
            self.animation_frame = (self.animation_frame + 1) % 4

    def update_health(self, dt: float):
        """Update health state (invincibility frames)"""
        self.health_state.update()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "enemy_id": self.enemy_id,
            "enemy_type": self.enemy_type.value,
            "x": self.physics.x,
            "y": self.physics.y,
            "velocity_x": self.physics.vx,
            "velocity_y": self.physics.vy,
            "facing_right": self.facing_right,
            "health_state": {
                "current_hp": self.health_state.current_hp,
                "max_hp": self.health_state.max_hp,
                "invincibility_frames": self.health_state.invincibility_frames,
            },
            "ai_state": self.ai_state.value,
            "loot_table_id": self.loot_table_id,
            "loot_seed": self.loot_seed,
        }

    @staticmethod
    def from_dict(data: dict) -> "Enemy":
        """Deserialize from dictionary"""
        health_data = data.get("health_state", {})
        health_state = HealthState(
            current_hp=health_data.get("current_hp", 3),
            max_hp=health_data.get("max_hp", 3),
            invincibility_frames=health_data.get("invincibility_frames", 0),
        )

        return Enemy(
            enemy_id=data["enemy_id"],
            enemy_type=EnemyType(data["enemy_type"]),
            x=data["x"],
            y=data["y"],
            velocity_x=data.get("velocity_x", 0.0),
            velocity_y=data.get("velocity_y", 0.0),
            facing_right=data.get("facing_right", True),
            health_state=health_state,
            ai_state=EnemyAIState(data.get("ai_state", "idle")),
            loot_table_id=data.get("loot_table_id", "enemy_common"),
            loot_seed=data.get("loot_seed", 0),
        )


def get_enemy_definition(enemy_type: EnemyType) -> EnemyDefinition | None:
    """Get enemy definition by type"""
    return ENEMY_DEFINITIONS.get(enemy_type)
