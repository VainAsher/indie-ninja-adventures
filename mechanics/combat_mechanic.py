"""
Combat Mechanic - Player Combat Actions

This module provides player combat mechanics:
- Dash attack: Damage enemies while dashing
- Jump attack: Damage enemies by landing on them from above
- Contact damage: Take damage when touching enemies
- Enemy knockback and stun effects

Version: v0.6.0
"""

from typing import Optional, List, Tuple
import math
from config.physics_constants import TILE_SIZE

from core.event_bus import EventBus
from core.logger import GameLogger
from core.state import PlayerState


# ============================================================
# Combat Constants
# ============================================================

# Dash attack
DASH_ATTACK_DAMAGE = 1  # Damage dealt during dash
DASH_ATTACK_KNOCKBACK = 300.0  # Knockback velocity (pixels/sec)
DASH_ATTACK_STUN = 0.5  # Stun duration (seconds)

# Jump attack
JUMP_ATTACK_DAMAGE = 2  # Damage dealt when landing on enemy from above
JUMP_ATTACK_BOUNCE_VELOCITY = -400.0  # Bounce up after successful jump attack
JUMP_ATTACK_ANGLE_THRESHOLD = 45.0  # Degrees from directly above to count as jump attack

# Contact damage
ENEMY_CONTACT_DAMAGE = 1  # Damage taken from touching enemy
ENEMY_CONTACT_KNOCKBACK = 200.0  # Knockback velocity when hit


# ============================================================
# Combat Mechanic
# ============================================================

class CombatMechanic:
    """
    Handles player combat interactions with enemies.

    Processes:
    - Dash attacks
    - Jump attacks
    - Contact damage
    - Knockback effects
    """

    def __init__(self, entity_id: int, event_bus: EventBus, logger: GameLogger):
        """
        Initialize combat mechanic.

        Args:
            entity_id: Entity ID
            event_bus: Event bus for emitting combat events
            logger: Logger instance
        """
        self.entity_id = entity_id
        self.event_bus = event_bus
        self.logger = logger

        # Combat state
        self.last_damaged_enemy_id: Optional[str] = None
        self.last_damage_time: float = 0.0
        self.damage_cooldown: float = 0.2  # Can't damage same enemy again for 200ms

    def check_enemy_collisions(self, state: PlayerState, enemy_manager,
                               dt: float) -> int:
        """
        Check collisions with enemies and process combat interactions.

        Args:
            state: Player state
            enemy_manager: Enemy manager instance
            dt: Delta time

        Returns:
            Damage taken this frame
        """
        from entities.enemy_manager import get_enemy_manager

        if enemy_manager is None:
            enemy_manager = get_enemy_manager()

        if enemy_manager is None:
            return 0

        # Update cooldown timer
        if self.last_damage_time > 0:
            self.last_damage_time -= dt
            if self.last_damage_time <= 0:
                self.last_damaged_enemy_id = None

        # Get player rect
        player_rect = state.physics.get_rect()
        player_x = player_rect.x
        player_y = player_rect.y
        player_w = player_rect.width
        player_h = player_rect.height

        # Check collisions with all enemies
        colliding_enemies = enemy_manager.check_player_enemy_collision(
            player_x, player_y, player_w, player_h
        )

        damage_taken = 0

        for enemy_id in colliding_enemies:
            enemy = enemy_manager.get_enemy(enemy_id)
            if enemy is None or enemy.is_dead():
                continue

            # Determine combat interaction type
            if state.is_dashing:
                # Dash attack
                self._perform_dash_attack(state, enemy, enemy_manager)

            elif self._is_jump_attack(state, enemy):
                # Jump attack
                damage_taken += self._perform_jump_attack(state, enemy, enemy_manager)

            else:
                # Contact damage (player takes damage)
                if not state.health_state.is_invincible():
                    damage_taken += self._take_contact_damage(state, enemy)

        return damage_taken

    # ============================================================
    # Attack Methods
    # ============================================================

    def _perform_dash_attack(self, state: PlayerState, enemy, enemy_manager):
        """
        Perform dash attack on enemy.

        Args:
            state: Player state
            enemy: Enemy entity
            enemy_manager: Enemy manager
        """
        # Check if on cooldown for this enemy
        if (self.last_damaged_enemy_id == enemy.enemy_id and
            self.last_damage_time > 0):
            return

        # Calculate knockback direction
        player_center_x = state.physics.x + state.physics.width / 2
        enemy_center_x, enemy_center_y = enemy.get_center()

        # Knockback away from player
        if enemy_center_x > player_center_x:
            knockback_x = DASH_ATTACK_KNOCKBACK
        else:
            knockback_x = -DASH_ATTACK_KNOCKBACK

        knockback_y = -100.0  # Slight upward knock

        # Clamp knockback to avoid launching enemies out of bounds
        max_kx = TILE_SIZE * 4
        max_ky = TILE_SIZE * 3
        knockback_x = max(-max_kx, min(max_kx, knockback_x))
        knockback_y = max(-max_ky, min(max_ky, knockback_y))

        # Deal damage with knockback and stun
        died = enemy_manager.damage_enemy(
            enemy.enemy_id,
            DASH_ATTACK_DAMAGE,
            knockback_x,
            knockback_y,
            DASH_ATTACK_STUN
        )

        # Immediately resolve any penetration after knockback
        from systems import CollisionSystem  # lazy import guard
        try:
            cs = CollisionSystem.get_instance() if hasattr(CollisionSystem, "get_instance") else None
            if cs:
                cs.check_and_resolve(enemy)
                enemy.sync_from_physics()
        except Exception:
            # If no global collision system, skip; main loop resolution will handle
            pass

        # Set cooldown
        self.last_damaged_enemy_id = enemy.enemy_id
        self.last_damage_time = self.damage_cooldown

        self.logger.info(
            f"Dash attack: dealt {DASH_ATTACK_DAMAGE} damage to {enemy.enemy_type.value} "
            f"(died: {died})"
        )

    def _perform_jump_attack(self, state: PlayerState, enemy, enemy_manager) -> int:
        """
        Perform jump attack (stomp) on enemy.

        Args:
            state: Player state
            enemy: Enemy entity
            enemy_manager: Enemy manager

        Returns:
            Damage taken (0 for successful jump attack)
        """
        # Deal damage to enemy
        died = enemy_manager.damage_enemy(
            enemy.enemy_id,
            JUMP_ATTACK_DAMAGE,
            0.0,  # No horizontal knockback for jump attacks
            0.0,
            0.0   # No stun
        )

        # Resolve positioning after jump attack in case of overlap
        from systems import CollisionSystem  # lazy import guard
        try:
            cs = CollisionSystem.get_instance() if hasattr(CollisionSystem, "get_instance") else None
            if cs:
                cs.check_and_resolve(enemy)
                enemy.sync_from_physics()
        except Exception:
            pass

        # Bounce player upward
        state.physics.vy = JUMP_ATTACK_BOUNCE_VELOCITY

        # Restore jumps for combo potential
        state.jumps_left = state.max_jumps

        self.logger.info(
            f"Jump attack: dealt {JUMP_ATTACK_DAMAGE} damage to {enemy.enemy_type.value} "
            f"(died: {died})"
        )

        # Successful jump attack = no damage taken
        return 0

    def _take_contact_damage(self, state: PlayerState, enemy) -> int:
        """
        Take contact damage from enemy.

        CRITICAL: Only applies damage during enemy's ATTACK_ACTIVE sub-state.
        This prevents instant contact damage and enforces telegraphed attacks.

        Args:
            state: Player state
            enemy: Enemy entity

        Returns:
            Damage taken
        """
        from entities.enemy import EnemyAttackSubState, EnemyAIState

        # CRITICAL: Only take damage if enemy is in ACTIVE attack phase
        if enemy.ai_state != EnemyAIState.ATTACK:
            return 0  # Not attacking, no damage

        if enemy.attack_substate != EnemyAttackSubState.ACTIVE:
            return 0  # Not in damage window (windup or recovery), no damage

        # Enemy is in active attack phase - apply damage
        definition = enemy.get_definition()

        # Apply damage to player health
        died = state.health_state.take_damage(definition.base_damage, defense=0)

        # Calculate knockback direction
        player_center_x = state.physics.x + state.physics.width / 2
        enemy_center_x, enemy_center_y = enemy.get_center()

        # Knockback away from enemy
        if player_center_x > enemy_center_x:
            knockback_x = ENEMY_CONTACT_KNOCKBACK
        else:
            knockback_x = -ENEMY_CONTACT_KNOCKBACK

        knockback_y = -150.0  # Slight upward knock

        # Apply knockback to player
        state.physics.vx = knockback_x
        state.physics.vy = knockback_y

        self.logger.info(
            f"Contact damage: took {definition.base_damage} damage from {enemy.enemy_type.value} "
            f"(HP: {state.health_state.current_hp}/{state.health_state.max_hp}, died: {died}) "
            f"[ATTACK_ACTIVE phase]"
        )

        if died:
            # Player died - will be handled by damage mechanic
            pass

        return definition.base_damage

    # ============================================================
    # Helper Methods
    # ============================================================

    def _is_jump_attack(self, state: PlayerState, enemy) -> bool:
        """
        Check if player is performing a jump attack (landing on enemy from above).

        Args:
            state: Player state
            enemy: Enemy entity

        Returns:
            True if jump attack conditions met
        """
        # Player must be falling
        if state.physics.vy <= 0:
            return False

        # Calculate relative position
        player_bottom = state.physics.y + state.physics.height
        player_center_x = state.physics.x + state.physics.width / 2

        enemy_center_x, enemy_center_y = enemy.get_center()
        enemy_rect = enemy.get_rect()
        enemy_top = enemy_rect[1]

        # Player must be above enemy
        # Check if player's bottom is near enemy's top (landing on them)
        vertical_diff = player_bottom - enemy_top

        # Must be landing on enemy (within small margin)
        if vertical_diff > 20:  # Player is too far below enemy top
            return False

        # Calculate angle from enemy to player
        dx = player_center_x - enemy_center_x
        dy = player_bottom - enemy_center_y

        # Angle in degrees (0 = directly above, 90 = horizontal)
        if dx == 0:
            angle = 0
        else:
            angle = abs(math.degrees(math.atan2(abs(dx), abs(dy))))

        # Must be within angle threshold (roughly from above)
        if angle > JUMP_ATTACK_ANGLE_THRESHOLD:
            return False

        return True

    def reset(self, state: PlayerState):
        """
        Reset combat state.

        Args:
            state: Player state
        """
        self.last_damaged_enemy_id = None
        self.last_damage_time = 0.0

    def cleanup(self):
        """Cleanup mechanic"""
        pass


# ============================================================
# Combat Integration Helper
# ============================================================

def integrate_combat_with_player(player, enemy_manager):
    """
    Integrate combat mechanic with existing player.

    This is a helper function to add combat to an existing player instance
    without modifying the player.py file.

    Args:
        player: Player instance
        enemy_manager: Enemy manager instance

    Returns:
        CombatMechanic instance (caller should call check_enemy_collisions each frame)
    """
    combat = CombatMechanic(
        entity_id=player.player_id,
        event_bus=player.event_bus,
        logger=player.logger
    )

    return combat


# ============================================================
# Combat Events (for future use)
# ============================================================

from dataclasses import dataclass


@dataclass
class DashAttackEvent:
    """Event emitted when player performs dash attack"""
    player_id: int
    enemy_id: str
    damage: int
    enemy_died: bool


@dataclass
class JumpAttackEvent:
    """Event emitted when player performs jump attack"""
    player_id: int
    enemy_id: str
    damage: int
    enemy_died: bool


@dataclass
class PlayerHitEvent:
    """Event emitted when player takes damage from enemy"""
    player_id: int
    enemy_id: str
    damage: int
    remaining_hp: int
    player_died: bool
