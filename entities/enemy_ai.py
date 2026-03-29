"""
Enemy AI System - AI Behavior and State Machine

This module provides enemy AI behavior:
- State machine: IDLE → PATROL → CHASE → ATTACK → STUNNED
- Movement logic for each state
- Player detection and tracking
- Attack behavior
- Patrol waypoint navigation

Version: v0.6.0
"""

import math

from entities.ai_random import (
    AIRandom,
    get_varied_attack_cooldown,
    get_varied_chase_interval,
    get_varied_idle_duration,
    get_varied_patrol_wait,
)
from entities.enemy import Enemy, EnemyAIState, EnemyAttackSubState

# ============================================================
# AI Behavior Constants
# ============================================================

WAYPOINT_REACH_DISTANCE = 16.0  # Pixels from waypoint to consider "reached"
ATTACK_COOLDOWN = 0.8  # Seconds between attacks (reduced since attack has recovery time)
STUN_FRICTION = 0.9  # Knockback decay multiplier
CHASE_UPDATE_INTERVAL = 0.5  # Seconds between target updates during chase
OBSTACLE_CHECK_DISTANCE = 48.0  # Pixels ahead to check for obstacles
OBSTACLE_TURN_WAIT_TIME = 0.5  # Seconds to wait before turning around when obstacle hit


# ============================================================
# Enemy AI Controller
# ============================================================


class EnemyAI:
    """
    AI controller for enemy behavior.

    Manages state transitions and movement for a single enemy.
    """

    def __init__(self, enemy: Enemy, ai_random: AIRandom | None = None):
        """
        Initialize AI controller.

        Args:
            enemy: Enemy entity to control
            ai_random: Seeded random generator for deterministic AI timing (optional)
        """
        self.enemy = enemy
        self.ai_random = ai_random
        self.attack_cooldown_timer = 0.0
        self.chase_update_timer = 0.0
        self.detection_mult = 1.0

        # Obstacle avoidance state
        self.obstacle_ahead = False
        self.obstacle_wait_timer = 0.0

        # Pre-computed timing variations for determinism
        # These are computed once at initialization using seeded RNG
        self.idle_duration = get_varied_idle_duration(ai_random, 1.0)
        self.patrol_wait_time_base = get_varied_patrol_wait(ai_random, 1.0)
        self.chase_interval = get_varied_chase_interval(ai_random, CHASE_UPDATE_INTERVAL)
        self.attack_cooldown_base = get_varied_attack_cooldown(ai_random, ATTACK_COOLDOWN)

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        detection_mult: float = 1.0,
        collision_system=None,
    ) -> int | None:
        """
        Update enemy AI for one frame.

        Args:
            dt: Delta time in seconds
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height
            detection_mult: Detection radius multiplier
            collision_system: CollisionSystem for obstacle detection

        Returns:
            Damage to deal to player (if attacking), or None
        """
        # Update timers
        self.enemy.ai_state_timer += dt
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= dt
        if self.chase_update_timer > 0:
            self.chase_update_timer -= dt
        if self.obstacle_wait_timer > 0:
            self.obstacle_wait_timer -= dt
        # Store detection multiplier for this frame
        self.detection_mult = detection_mult

        # Check for obstacles ahead (if collision system available)
        self._check_obstacle_ahead(collision_system)

        # Process current state
        if self.enemy.ai_state == EnemyAIState.DEAD:
            return self._update_dead(dt)

        elif self.enemy.ai_state == EnemyAIState.STUNNED:
            return self._update_stunned(dt)

        elif self.enemy.ai_state == EnemyAIState.IDLE:
            return self._update_idle(dt, player_x, player_y, player_width, player_height)

        elif self.enemy.ai_state == EnemyAIState.PATROL:
            return self._update_patrol(dt, player_x, player_y, player_width, player_height)

        elif self.enemy.ai_state == EnemyAIState.CHASE:
            return self._update_chase(dt, player_x, player_y, player_width, player_height)

        elif self.enemy.ai_state == EnemyAIState.ATTACK:
            return self._update_attack(dt, player_x, player_y, player_width, player_height)

        return None

    # ============================================================
    # State Update Methods
    # ============================================================

    def _update_dead(self, dt: float) -> None:
        """Update dead state (no behavior)"""
        # Stop all movement
        self.enemy.velocity_x = 0.0
        return None

    def _update_stunned(self, dt: float) -> None:
        """Update stunned state (knockback physics)"""
        # Decrement stun duration
        self.enemy.stun_duration -= dt

        # Apply knockback velocity with friction
        self.enemy.velocity_x = self.enemy.knockback_velocity_x
        self.enemy.velocity_y = self.enemy.knockback_velocity_y

        # Apply friction to knockback
        self.enemy.knockback_velocity_x *= STUN_FRICTION
        self.enemy.knockback_velocity_y *= STUN_FRICTION

        # Exit stun when duration expires
        if self.enemy.stun_duration <= 0.0:
            self._transition_to_patrol()

        return None

    def _update_idle(
        self, dt: float, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> None:
        """Update idle state (wait, then start patrol)"""
        # Check for player detection
        det = getattr(self, "detection_mult", 1.0)
        if self.enemy.can_see_player(player_x, player_y, player_width, player_height, det):
            self._transition_to_chase(player_x, player_y, player_width, player_height)
            return None

        # Idle for varied duration, then start patrol
        if self.enemy.ai_state_timer >= self.idle_duration:
            self._transition_to_patrol()

        # No movement during idle
        self.enemy.velocity_x = 0.0
        if self.enemy.physics:
            self.enemy.physics.vx = 0.0

        return None

    def _update_patrol(
        self, dt: float, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> None:
        """Update patrol state (move between waypoints)"""
        # Check for player detection
        det = getattr(self, "detection_mult", 1.0)
        if self.enemy.can_see_player(player_x, player_y, player_width, player_height, det):
            self._transition_to_chase(player_x, player_y, player_width, player_height)
            return None

        # Get current waypoint
        waypoint = self.enemy.get_current_waypoint()
        if waypoint is None:
            # No waypoints, return to idle
            self._transition_to_idle()
            return None

        # Handle obstacle detection
        if self.obstacle_ahead and self.obstacle_wait_timer <= 0.0:
            # Obstacle detected - turn around by advancing to next waypoint
            # This makes the enemy naturally patrol back and forth
            self.enemy.advance_waypoint()
            self.obstacle_wait_timer = OBSTACLE_TURN_WAIT_TIME

            # Stop movement briefly
            if self.enemy.movement:
                self.enemy.movement.stop(self.enemy.physics)
            self.enemy.velocity_x = 0.0

            return None

        # Don't move if waiting after hitting obstacle
        if self.obstacle_wait_timer > 0.0:
            return None

        # Move toward waypoint
        definition = self.enemy.get_definition()
        patrol_speed = definition.move_speed * definition.patrol_speed_multiplier

        # Use movement component for smooth acceleration
        if self.enemy.movement:
            self.enemy.movement.move_toward(self.enemy.physics, waypoint[0], waypoint[1], dt)
        else:
            self._move_toward_target(waypoint[0], waypoint[1], patrol_speed, dt)

        # Check if reached waypoint
        if self._distance_to_point(waypoint[0], waypoint[1]) < WAYPOINT_REACH_DISTANCE:
            # Wait at waypoint
            if self.enemy.patrol_wait_time <= 0.0:
                # Start waiting (with varied timing for natural behavior)
                self.enemy.patrol_wait_time = self.patrol_wait_time_base
            else:
                # Continue waiting
                self.enemy.patrol_wait_time -= dt

                if self.enemy.patrol_wait_time <= 0.0:
                    # Done waiting, advance to next waypoint
                    self.enemy.advance_waypoint()
                    self.enemy.patrol_wait_time = 0.0

        return None

    def _update_chase(
        self, dt: float, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> None:
        """Update chase state (pursue player)"""
        # Check if player is in attack range
        if self.enemy.is_in_attack_range(player_x, player_y, player_width, player_height):
            self._transition_to_attack()
            return None

        # Check if player escaped detection radius
        det = getattr(self, "detection_mult", 1.0)
        if not self.enemy.can_see_player(player_x, player_y, player_width, player_height, det):
            # Lost sight of player, return to patrol
            self._transition_to_patrol()
            return None

        # Update target position periodically (not every frame for performance)
        if self.chase_update_timer <= 0.0:
            player_center_x = player_x + player_width / 2
            player_center_y = player_y + player_height / 2
            self.enemy.target_player_x = player_center_x
            self.enemy.target_player_y = player_center_y
            self.enemy.last_seen_player_x = player_center_x
            self.enemy.last_seen_player_y = player_center_y
            self.chase_update_timer = self.chase_interval

        # Handle obstacle during chase - enemy will slow down but keep trying
        # This prevents getting completely stuck while chasing player
        if self.obstacle_ahead:
            # Reduce movement speed when hitting obstacle during chase
            # Enemy will keep pushing forward slowly instead of stopping
            # This simulates "trying to get around" the obstacle
            definition = self.enemy.get_definition()
            if self.enemy.movement:
                # Slow down to 30% speed when hitting obstacle
                current_speed = self.enemy.movement.move_speed
                self.enemy.movement.move_speed = definition.move_speed * 0.3
                if (
                    self.enemy.target_player_x is not None
                    and self.enemy.target_player_y is not None
                ):
                    self.enemy.movement.move_toward(
                        self.enemy.physics,
                        self.enemy.target_player_x,
                        self.enemy.target_player_y,
                        dt,
                    )
                # Restore normal speed
                self.enemy.movement.move_speed = current_speed
            return None

        # Move toward last known player position (normal speed, no obstacle)
        if self.enemy.target_player_x is not None and self.enemy.target_player_y is not None:
            definition = self.enemy.get_definition()
            if self.enemy.movement:
                self.enemy.movement.move_toward(
                    self.enemy.physics, self.enemy.target_player_x, self.enemy.target_player_y, dt
                )
            else:
                self._move_toward_target(
                    self.enemy.target_player_x,
                    self.enemy.target_player_y,
                    definition.move_speed,
                    dt,
                )

        return None

    def _update_attack(
        self, dt: float, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> int | None:
        """
        Update attack state with telegraphed attack phases.

        Attack Phases:
        1. WINDUP: Warning phase, enemy glows/flashes, no damage
        2. ACTIVE: Brief damage window where contact deals damage
        3. RECOVERY: Post-attack cooldown, enemy slows down

        Special behaviours:
        - SLIME: launches a jump toward the player at end of WINDUP; body-contact
          during ACTIVE deals damage (handled by combat_mechanic).
        - BAT: swoops diagonally through the player at end of WINDUP; body-contact
          during the pass deals damage; decelerates in RECOVERY.
        - WOLF: dashes horizontally through the player at end of WINDUP; body-contact
          during the pass deals damage; skids to a stop in RECOVERY.
        - SKELETON: fires an arrow on the first frame of ACTIVE.
        - GOBLIN: forward hitbox damage is handled by combat_mechanic; AI
          returns None (no instant damage signal needed).
        """
        from entities.enemy import EnemyType

        definition = self.enemy.get_definition()
        is_slime    = self.enemy.enemy_type == EnemyType.SLIME
        is_bat      = self.enemy.enemy_type == EnemyType.BAT
        is_wolf     = self.enemy.enemy_type == EnemyType.WOLF
        is_skeleton = self.enemy.enemy_type == EnemyType.SKELETON

        # Enemies that physically travel through the player skip the range-cancel
        # while mid-movement so their arc / dash can complete.
        in_active = self.enemy.attack_substate == EnemyAttackSubState.ACTIVE
        skip_range_cancel = (is_slime or is_bat or is_wolf) and in_active
        if not skip_range_cancel:
            if not self.enemy.is_in_attack_range(player_x, player_y, player_width, player_height):
                self.enemy.attack_substate = EnemyAttackSubState.NONE
                self.enemy.attack_substate_timer = 0.0
                self._transition_to_chase(player_x, player_y, player_width, player_height)
                return None

        player_center_x = player_x + player_width / 2
        enemy_center_x  = self.enemy.x + definition.width / 2

        # Lock facing toward the player except while travelling (airborne / dashing)
        travelling = (is_slime or is_bat or is_wolf) and in_active
        if not travelling:
            self.enemy.facing_right = player_center_x > enemy_center_x

        # Stop movement during windup/idle phase — exempt travelling enemies mid-attack
        # and also RECOVERY (bat/wolf need friction, not hard-stop)
        in_recovery = self.enemy.attack_substate == EnemyAttackSubState.RECOVERY
        if not ((is_slime or is_bat or is_wolf) and (in_active or in_recovery)):
            self.enemy.velocity_x = 0.0
            if self.enemy.physics:
                self.enemy.physics.vx = 0.0

        # Initialize attack sequence if not started
        if self.enemy.attack_substate == EnemyAttackSubState.NONE:
            if self.attack_cooldown_timer <= 0.0:
                self.enemy.attack_substate = EnemyAttackSubState.WINDUP
                self.enemy.attack_substate_timer = 0.0
                self.enemy.ai_state_timer = 0.0
            else:
                return None

        # Update attack sub-state timer
        self.enemy.attack_substate_timer += dt

        damage = None

        if self.enemy.attack_substate == EnemyAttackSubState.WINDUP:
            at_end = self.enemy.attack_substate_timer >= definition.attack_windup_time

            if at_end:
                player_center_y = player_y + player_height / 2
                enemy_center_y  = self.enemy.y + definition.height / 2

                if is_slime:
                    # ── SLIME: upward jump toward player ─────────────────────
                    dx = player_center_x - enemy_center_x
                    dist = max(abs(dx), 1.0)
                    hop_vx = (dx / dist) * min(abs(dx) * 0.08, 7.0)
                    if self.enemy.physics:
                        self.enemy.physics.vx = hop_vx
                        self.enemy.physics.vy = -9.0

                elif is_bat:
                    # ── BAT: diagonal swoop straight through player ───────────
                    dx = player_center_x - enemy_center_x
                    dy = player_center_y - enemy_center_y
                    dist = max(math.sqrt(dx * dx + dy * dy), 1.0)
                    swoop_speed = 12.0
                    if self.enemy.physics:
                        self.enemy.physics.vx = (dx / dist) * swoop_speed
                        self.enemy.physics.vy = (dy / dist) * swoop_speed

                elif is_wolf:
                    # ── WOLF: fast horizontal dash + slight leap ──────────────
                    direction = 1.0 if player_center_x > enemy_center_x else -1.0
                    if self.enemy.physics:
                        self.enemy.physics.vx = direction * 10.0
                        self.enemy.physics.vy = -2.5  # small pounce

                self.enemy.attack_substate = EnemyAttackSubState.ACTIVE
                self.enemy.attack_substate_timer = 0.0

        elif self.enemy.attack_substate == EnemyAttackSubState.ACTIVE:
            if is_skeleton:
                # ── SKELETON: fire arrow on the first frame of ACTIVE ─────────
                if self.enemy.attack_substate_timer < dt * 1.5:
                    self.enemy.pending_arrow_fire = True
                damage = None
            elif is_bat or is_wolf or is_slime:
                # Body-contact damage during the travel pass — handled by
                # combat_mechanic._take_contact_damage (checks ATTACK+ACTIVE state)
                damage = None
            else:
                # Standard melee (goblin uses forward hitbox externally)
                if self.enemy.enemy_type == EnemyType.GOBLIN:
                    damage = None
                elif self.enemy.attack_substate_timer < dt * 1.5:
                    damage = definition.base_damage

            if self.enemy.attack_substate_timer >= definition.attack_active_time:
                self.enemy.attack_substate = EnemyAttackSubState.RECOVERY
                self.enemy.attack_substate_timer = 0.0

        elif self.enemy.attack_substate == EnemyAttackSubState.RECOVERY:
            # Bat / wolf bleed off their dash / swoop velocity during recovery
            if (is_bat or is_wolf) and self.enemy.physics:
                self.enemy.physics.vx *= 0.84
                if is_bat:
                    self.enemy.physics.vy *= 0.84

            if self.enemy.attack_substate_timer >= definition.attack_recovery_time:
                self.enemy.attack_substate = EnemyAttackSubState.NONE
                self.enemy.attack_substate_timer = 0.0
                self.attack_cooldown_timer = self.attack_cooldown_base

        return damage

    # ============================================================
    # State Transition Methods
    # ============================================================

    def _transition_to_idle(self):
        """Transition to IDLE state"""
        self.enemy.ai_state = EnemyAIState.IDLE
        self.enemy.ai_state_timer = 0.0
        self.enemy.velocity_x = 0.0

    def _transition_to_patrol(self):
        """Transition to PATROL state"""
        self.enemy.ai_state = EnemyAIState.PATROL
        self.enemy.ai_state_timer = 0.0
        self.enemy.target_player_x = None
        self.enemy.target_player_y = None

    def _transition_to_chase(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ):
        """Transition to CHASE state"""
        self.enemy.ai_state = EnemyAIState.CHASE
        self.enemy.ai_state_timer = 0.0

        # Set initial target
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2
        self.enemy.target_player_x = player_center_x
        self.enemy.target_player_y = player_center_y
        self.enemy.last_seen_player_x = player_center_x
        self.enemy.last_seen_player_y = player_center_y

        self.chase_update_timer = 0.0

    def _transition_to_attack(self):
        """Transition to ATTACK state"""
        self.enemy.ai_state = EnemyAIState.ATTACK
        self.enemy.ai_state_timer = 0.0
        # Attack sub-state will be initialized in _update_attack()
        self.enemy.attack_substate = EnemyAttackSubState.NONE
        self.enemy.attack_substate_timer = 0.0

    # ============================================================
    # Movement Helper Methods
    # ============================================================

    def _move_toward_target(self, target_x: float, target_y: float, speed: float, dt: float):
        """
        Move enemy toward target position.

        Args:
            target_x: Target X position
            target_y: Target Y position
            speed: Movement speed (pixels per second)
            dt: Delta time
        """
        definition = self.enemy.get_definition()
        enemy_center_x, enemy_center_y = self.enemy.get_center()

        # Calculate direction to target
        dx = target_x - enemy_center_x
        dy = target_y - enemy_center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0.0:
            # Normalize direction
            dx /= distance
            dy /= distance

            # Apply horizontal movement
            self.enemy.velocity_x = dx * speed

            # Update facing direction
            if dx > 0:
                self.enemy.facing_right = True
            elif dx < 0:
                self.enemy.facing_right = False

            # Apply vertical movement for flying enemies
            if definition.can_fly:
                self.enemy.velocity_y = dy * speed
        else:
            # Already at target
            self.enemy.velocity_x = 0.0
            if definition.can_fly:
                self.enemy.velocity_y = 0.0

    def _distance_to_point(self, x: float, y: float) -> float:
        """Calculate distance from enemy center to point"""
        enemy_center_x, enemy_center_y = self.enemy.get_center()
        dx = x - enemy_center_x
        dy = y - enemy_center_y
        return math.sqrt(dx * dx + dy * dy)

    def _check_obstacle_ahead(self, collision_system):
        """
        Check for obstacles ahead of enemy movement.

        Uses raycast to detect walls/obstacles in the direction of movement.

        Args:
            collision_system: CollisionSystem instance for raycasting
        """
        if collision_system is None:
            self.obstacle_ahead = False
            return

        # Only check for ground-based enemies (flying enemies don't need this)
        definition = self.enemy.get_definition()
        if definition.can_fly:
            self.obstacle_ahead = False
            return

        # Get enemy position
        enemy_center_x, enemy_center_y = self.enemy.get_center()

        # Determine check direction based on movement or facing
        check_direction = 1 if self.enemy.facing_right else -1
        if abs(self.enemy.physics.vx) > 0.1:
            check_direction = 1 if self.enemy.physics.vx > 0 else -1

        # Raycast ahead at enemy's center height
        check_distance = OBSTACLE_CHECK_DISTANCE
        start_x = enemy_center_x
        start_y = enemy_center_y
        end_x = enemy_center_x + (check_distance * check_direction)
        end_y = enemy_center_y

        # Perform raycast
        hit = collision_system.raycast(start_x, start_y, end_x, end_y)

        # Update obstacle state
        self.obstacle_ahead = hit is not None

    def get_attack_phase_info(self) -> tuple[str, float]:
        """
        Get current attack phase for rendering/debugging.

        Returns:
            Tuple of (phase_name, phase_progress_0_to_1)
        """
        if self.enemy.ai_state != EnemyAIState.ATTACK:
            return ("none", 0.0)

        definition = self.enemy.get_definition()
        substate = self.enemy.attack_substate
        timer = self.enemy.attack_substate_timer

        if substate == EnemyAttackSubState.WINDUP:
            progress = timer / definition.attack_windup_time
            return ("windup", min(progress, 1.0))
        elif substate == EnemyAttackSubState.ACTIVE:
            progress = timer / definition.attack_active_time
            return ("active", min(progress, 1.0))
        elif substate == EnemyAttackSubState.RECOVERY:
            progress = timer / definition.attack_recovery_time
            return ("recovery", min(progress, 1.0))
        else:
            return ("none", 0.0)


# ============================================================
# AI Utility Functions
# ============================================================


def nearest_player(
    players: list[tuple[float, float, int, int]],
    enemy_cx: float,
    enemy_cy: float,
) -> tuple[float, float, int, int]:
    """
    Return the (x, y, width, height) of the player closest to the given enemy center.

    Used by the server-authoritative simulation where multiple players are active.
    For single-player, pass a one-element list.
    """
    if len(players) == 1:
        return players[0]
    best = players[0]
    best_dist_sq = math.inf
    for p in players:
        px, py, pw, ph = p
        cx = px + pw / 2
        cy = py + ph / 2
        d_sq = (cx - enemy_cx) ** 2 + (cy - enemy_cy) ** 2
        if d_sq < best_dist_sq:
            best_dist_sq = d_sq
            best = p
    return best


def create_patrol_waypoints_horizontal(
    start_x: float, start_y: float, distance: float, num_points: int = 2
) -> list:
    """
    Create horizontal patrol waypoints.

    Args:
        start_x: Starting X position
        start_y: Y position (constant)
        distance: Distance to travel in each direction
        num_points: Number of waypoints (default 2 for back-and-forth)

    Returns:
        List of (x, y) waypoint tuples
    """
    if num_points == 2:
        return [(start_x - distance, start_y), (start_x + distance, start_y)]
    else:
        # Evenly spaced waypoints
        waypoints = []
        for i in range(num_points):
            offset = -distance + (2 * distance * i / (num_points - 1))
            waypoints.append((start_x + offset, start_y))
        return waypoints


def create_patrol_waypoints_vertical(
    start_x: float, start_y: float, distance: float, num_points: int = 2
) -> list:
    """
    Create vertical patrol waypoints.

    Args:
        start_x: X position (constant)
        start_y: Starting Y position
        distance: Distance to travel in each direction
        num_points: Number of waypoints (default 2 for up-and-down)

    Returns:
        List of (x, y) waypoint tuples
    """
    if num_points == 2:
        return [(start_x, start_y - distance), (start_x, start_y + distance)]
    else:
        # Evenly spaced waypoints
        waypoints = []
        for i in range(num_points):
            offset = -distance + (2 * distance * i / (num_points - 1))
            waypoints.append((start_x, start_y + offset))
        return waypoints


def create_patrol_waypoints_circle(
    center_x: float, center_y: float, radius: float, num_points: int = 4
) -> list:
    """
    Create circular patrol waypoints.

    Args:
        center_x: Circle center X
        center_y: Circle center Y
        radius: Circle radius
        num_points: Number of waypoints around circle

    Returns:
        List of (x, y) waypoint tuples
    """
    waypoints = []
    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        waypoints.append((x, y))
    return waypoints


def create_patrol_waypoints_rectangle(
    center_x: float, center_y: float, width: float, height: float
) -> list:
    """
    Create rectangular patrol waypoints.

    Args:
        center_x: Rectangle center X
        center_y: Rectangle center Y
        width: Rectangle width
        height: Rectangle height

    Returns:
        List of (x, y) waypoint tuples (4 corners)
    """
    half_w = width / 2
    half_h = height / 2

    return [
        (center_x - half_w, center_y - half_h),  # Top-left
        (center_x + half_w, center_y - half_h),  # Top-right
        (center_x + half_w, center_y + half_h),  # Bottom-right
        (center_x - half_w, center_y + half_h),  # Bottom-left
    ]
