"""
Player Entity - Orchestrates all player mechanics

The Player class is a composition of modular mechanics:
- MovementMechanic: Ground/air acceleration
- JumpMechanic: All jump types (ground, double, wall, coyote)
- DashMechanic: Quick burst of speed
- CrouchMechanic: Stealth movement

Architecture:
- Player owns PlayerState (all game state)
- Mechanics modify state each tick
- Mechanics are independent and reusable
- Event-driven communication
"""

import pygame

from core.event_bus import EventBus, TickEvent
from core.logger import GameLogger
from core.state import PhysicsState, PlayerState
from mechanics import CrouchMechanic, DamageMechanic, DashMechanic, JumpMechanic, MovementMechanic
from mechanics.ninjutsu import NinjutsuMechanic
from mechanics.shuriken import ShurikenMechanic
from mechanics.teleport import TeleportMechanic
from mechanics.wall_slide import WallSlideMechanic


class Player:
    """
    Player entity with modular mechanics

    Coordinates all player mechanics and manages player state.
    Each mechanic is independent and can be enabled/disabled.

    Usage:
        player = Player(player_id=0, spawn_x=100, spawn_y=100, event_bus=bus, logger_factory=logger)
        player.process_input(keys)  # Each frame
        # Mechanics update on TickEvent automatically
    """

    def __init__(
        self,
        player_id: int,
        spawn_x: float,
        spawn_y: float,
        event_bus: EventBus,
        logger_factory: GameLogger,
        collision_system=None,
        feature_flags: dict = None,
    ):
        """
        Initialize player with all mechanics

        Args:
            player_id: Unique player ID
            spawn_x, spawn_y: Spawn position
            event_bus: Event bus for communication
            logger_factory: Logger factory for creating loggers
            collision_system: Optional collision system for crouch ceiling checks
            feature_flags: Feature flags (double_jump, wall_jump, dash, crouch, etc.)
        """
        self.player_id = player_id
        self.event_bus = event_bus
        self.feature_flags = feature_flags or {}
        self.collision_system = collision_system

        # Create loggers
        self.logger = logger_factory.get_logger(f"player_{player_id}")

        # Initialize player state
        # Player size: 28x56 pixels (2:1 height-to-width ratio)
        # Width: slightly under 1 tile (28/32 = 87.5%)
        # Height: slightly under 2 tiles (56/64 = 87.5%)
        # Crouch: 28x28 pixels (half height)
        # Fits through 2-tile wide (64px) by 2-tile tall (64px) doorways
        physics = PhysicsState(x=spawn_x, y=spawn_y, vx=0.0, vy=0.0, width=28, height=56)

        # Create health state
        from game.health_system import HealthState

        health_state = HealthState(current_hp=5, max_hp=5)

        self.state = PlayerState(
            player_id=player_id,
            physics=physics,
            health_state=health_state,
            facing=1,
            crouching=False,
            is_dashing=False,
            stamina=30.0,
            stamina_max=30.0,
            stamina_regen_rate=12.0,
            mana=30.0,
            mana_max=30.0,
            mana_regen_rate=6.0,
            shuriken_ammo=10,
            shuriken_max=10,
            wall_slide_stamina=3.0,
            wall_slide_stamina_max=3.0,
        )

        # Initialize mechanics (in processing order)
        self.mechanics = []

        # Movement mechanic (base horizontal movement)
        self.movement = MovementMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.movement"),
        )
        self.mechanics.append(self.movement)

        # Jump mechanic (all jump types)
        self.jump = JumpMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.jump"),
            feature_flags=feature_flags,
        )
        self.mechanics.append(self.jump)

        # Dash mechanic (quick burst)
        self.dash = DashMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.dash"),
        )
        self.mechanics.append(self.dash)

        # Crouch mechanic (stealth movement)
        self.crouch = CrouchMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.crouch"),
            collision_checker=collision_system,
        )
        self.mechanics.append(self.crouch)

        # Wall slide/hang mechanic
        self.wall_slide = WallSlideMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.wall_slide"),
        )
        self.mechanics.append(self.wall_slide)

        # Shuriken mechanic (ammo-limited ranged)
        self.shuriken = ShurikenMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.shuriken"),
            collision_system=collision_system,
        )
        self.mechanics.append(self.shuriken)

        # Teleport mechanic (phase blink)
        self.teleport = TeleportMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.teleport"),
            collision_system=collision_system,
        )
        self.mechanics.append(self.teleport)

        # Ninjutsu mechanic (purify)
        self.ninjutsu = NinjutsuMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.ninjutsu"),
        )
        self.mechanics.append(self.ninjutsu)

        # Damage mechanic (health, invincibility, death)
        self.damage = DamageMechanic(
            entity_id=player_id,
            event_bus=event_bus,
            logger=logger_factory.get_logger(f"player_{player_id}.damage"),
        )
        # Note: Damage mechanic is not in self.mechanics list
        # It's called manually when hazards are checked

        # Subscribe to tick events
        self.event_bus.subscribe(TickEvent, self.on_tick, priority=50)

        # Input tracking (for toggle detection and fast-fall)
        self._jump_key_held = False
        self._dash_key_held = False
        self._crouch_key_held = False
        self._down_key_held = False  # For fast-fall mechanic
        self._last_air_anim = "jump"

        self.logger.info(
            f"Player {player_id} initialized at ({spawn_x}, {spawn_y}) "
            f"with {len(self.mechanics)} mechanics"
        )

    def on_tick(self, event: TickEvent):
        """
        Process all mechanics each tick

        Processing order:
        1. Crouch (affects movement modifiers)
        2. Movement (base horizontal movement)
        3. Dash (overrides movement if active)
        4. Jump (vertical movement)
        5. Apply gravity (if not grounded)
        6. Integrate velocity into position
        7. Collision detection and resolution

        Args:
            event: Tick event with dt
        """
        dt = event.dt

        # Update invincibility frames
        self.damage.update_invincibility(self.state, dt)

        # Update crouch first (provides modifiers for movement)
        self.crouch.on_tick(self.state, dt)

        # Apply movement modifiers: crouch (slow/stealthy), walk (default), run (full speed)
        if self.state.crouching:
            modifiers = self.crouch.get_movement_modifier(self.state)
            self.movement.set_speed_multiplier(modifiers["speed_mult"])  # 0.6
            self.movement.set_accel_multiplier(modifiers["accel_mult"])  # 0.8
        elif getattr(self.state, "is_running", False):
            self.movement.set_speed_multiplier(1.0)  # Full speed
            self.movement.set_accel_multiplier(1.0)  # Full acceleration
        else:
            # Default walk mode - distinct from crouch (faster, more responsive)
            self.movement.set_speed_multiplier(0.75)  # 75% of max speed
            self.movement.set_accel_multiplier(0.9)   # 90% acceleration

        # Lock movement during dash or wall jump lock
        if self.state.is_dashing or self.state.wall_jump_lock > 0:
            self.movement.lock_movement(True)
        else:
            self.movement.lock_movement(False)

        # Process movement
        self.movement.on_tick(self.state, dt)

        # Process dash (overrides movement if active)
        self.dash.on_tick(self.state, dt)

        # Process jump
        self.jump.on_tick(self.state, dt)

        # Wall slide / hang (stamina-controlled)
        self.wall_slide.on_tick(self.state, dt)

        # Shuriken/projectile handling
        self.shuriken.on_tick(self.state, dt)

        # Teleport phase/cooldown
        self.teleport.on_tick(self.state, dt)

        # Ninjutsu stance/cast handling
        self.ninjutsu.on_tick(self.state, dt)

        # Variable jump height: Apply jump cut if player releases jump button while rising
        # This creates responsive "tap for short jump, hold for high jump" gameplay
        if self.state.physics.vy < 0 and not self._jump_key_held:
            # Player is rising and jump button released - apply extra gravity
            from config.physics_constants import GRAVITY, JUMP_CUT_MULT

            self.state.physics.vy += GRAVITY * (JUMP_CUT_MULT - 1.0)

        # Fast-fall: Holding down while falling applies extra gravity for snappy descent
        if (
            self.state.physics.vy > 0
            and not self.state.physics.on_ground
            and self._down_key_held
            and not self.state.crouching  # Don't fast-fall while crouching on ground
        ):
            from config.physics_constants import GRAVITY, FAST_FALL_MULT

            self.state.physics.vy += GRAVITY * (FAST_FALL_MULT - 1.0)

        # Wall friction (fallback when NOT wall sliding): damp descent when touching wall
        # Only apply if wall slide mechanic is not active to avoid conflicts
        if (
            self.state.physics.on_wall
            and not self.state.physics.on_ground
            and self.state.physics.vy > 0
            and not self.state.is_wall_sliding  # Skip if wall slide is handling this
        ):
            # Stronger damping for a quicker slowdown (fallback when stamina exhausted)
            self.state.physics.vy *= 0.7
            # Clamp max fall speed near wall
            self.state.physics.vy = min(self.state.physics.vy, 5.0)

        # Wall coyote buffer for wall jumps
        if self.state.physics.on_wall and not self.state.physics.on_ground:
            self.state.wall_coyote_time = 0.12  # 120ms buffer
        else:
            self.state.wall_coyote_time = max(0.0, self.state.wall_coyote_time - dt)

        # Ground coyote time management
        # Track when player leaves ground to enable coyote jump
        was_on_ground = getattr(self, "_was_on_ground", self.state.physics.on_ground)
        if was_on_ground and not self.state.physics.on_ground:
            # Just left ground, start coyote timer
            self.state.coyote_time = 0.12  # 120ms grace period
        self._was_on_ground = self.state.physics.on_ground

        # NOTE: Physics integration (gravity, velocity) is handled by PhysicsSystem
        # DO NOT duplicate physics processing here - it causes 2x movement speed
        # PhysicsSystem runs at priority 60, before player mechanics at priority 50

        # NOTE: Collision detection is handled by CollisionSystem
        # DO NOT duplicate collision processing here - it causes state overwrite issues
        # Execution order: PhysicsSystem (60) -> CollisionSystem (55) -> Player.on_tick (50)
        # CollisionSystem processes the player entity registered in entity_manager
        # Collision state (on_ground, on_wall, wall_dir) is updated BEFORE this function
        # Player mechanics now use CURRENT frame's collision state (not previous frame)

        # Wall/ceiling hang flags
        self.state.is_wall_hanging = (
            self.state.physics.on_wall
            and not self.state.physics.on_ground
            and abs(self.state.physics.vy) < 0.5
        )
        self.state.is_ceiling_hanging = False  # Placeholder until ceiling hang implemented
        if self.state.physics.on_wall and self.state.physics.wall_dir != 0:
            self.state.last_wall_dir = self.state.physics.wall_dir

        # Resource management (stamina/mana)
        self._update_resources(dt)

    def process_input(self, keys):
        """
        Process keyboard input and send to mechanics

        Args:
            keys: Key states from pygame.key.get_pressed() (supports both dict and sequence)
        """

        def key_down(code):
            try:
                return bool(keys[code])
            except Exception:
                return False

        # Movement input (handle both dict and sequence-like keys)
        left = key_down(pygame.K_a) or key_down(pygame.K_LEFT)
        right = key_down(pygame.K_d) or key_down(pygame.K_RIGHT)

        target_dir = (-1 if left else 0) + (1 if right else 0)
        self.movement.set_input(target_dir)

        # Jump input (with toggle detection)
        jump_key = key_down(pygame.K_SPACE) or key_down(pygame.K_w) or key_down(pygame.K_UP)

        if jump_key and not self._jump_key_held:
            self.jump.request_jump()
        self._jump_key_held = jump_key

        # Dash input (with toggle detection)
        dash_key = key_down(pygame.K_LSHIFT) or key_down(pygame.K_RSHIFT)

        if dash_key and not self._dash_key_held:
            if self.feature_flags.get("dash", True):
                self.dash.request_dash()
        self._dash_key_held = dash_key

        # Crouch input (with toggle detection)
        crouch_key = key_down(pygame.K_s) or key_down(pygame.K_DOWN)
        if self.feature_flags.get("crouch", True):
            self.crouch.set_crouch(crouch_key)
        self._crouch_key_held = crouch_key

        # Track down key for fast-fall mechanic (separate from crouch toggle)
        # Fast-fall activates when holding down in air while falling
        self._down_key_held = crouch_key

        # Run (Alt); default walk
        run_key = key_down(pygame.K_LALT) or key_down(pygame.K_RALT)
        self.state.is_running = run_key
        self.state.is_slow_walking = not run_key and not self.state.crouching

        # Shuriken throw (K) - aim with up/down keys for diagonals
        throw_key = key_down(pygame.K_k)
        aim_offset = -1 if key_down(pygame.K_UP) else 1 if key_down(pygame.K_DOWN) else 0
        if throw_key and not getattr(self, "_throw_key_held", False):
            if self.feature_flags.get("shuriken", True):
                self.shuriken.request_throw(aim_offset)
        self._throw_key_held = throw_key

        # Teleport (F)
        tele_key = key_down(pygame.K_f)
        if tele_key and not getattr(self, "_tele_key_held", False):
            if self.feature_flags.get("teleport", True):
                self.teleport.request_teleport(aim_offset)
        # Update phase steering if in phase
        if self.state.is_teleporting_phase:
            self.teleport.update_phase_direction(target_dir, aim_offset)
        self._tele_key_held = tele_key

        # Ninjutsu stance (L/Q)
        ninjutsu_key = key_down(pygame.K_l) or key_down(pygame.K_q)
        if ninjutsu_key:
            self.ninjutsu.request_stance()
        # Cast on release
        if getattr(self, "_ninjutsu_held", False) and not ninjutsu_key:
            if self.feature_flags.get("ninjutsu", True):
                self.ninjutsu.request_cast("purify")
        self._ninjutsu_held = ninjutsu_key

    def _update_resources(self, dt: float):
        """
        Simple stamina/mana drain and regeneration.
        """
        running = getattr(self.state, "is_running", False)
        if running:
            self.state.stamina = max(0.0, self.state.stamina - 4.0 * dt)
        else:
            regen_rate = self.state.stamina_regen_rate * (
                1.0 if self.state.physics.on_ground else 0.5
            )
            self.state.stamina = min(self.state.stamina_max, self.state.stamina + regen_rate * dt)

        # Mana regeneration
        self.state.mana = min(
            self.state.mana_max, self.state.mana + self.state.mana_regen_rate * dt
        )

        # Cooldowns clamp
        self.state.teleport_cooldown = max(0.0, self.state.teleport_cooldown)
        self.state.throw_cooldown = max(0.0, self.state.throw_cooldown)

    def get_rect(self) -> pygame.Rect:
        """
        Get player collision rectangle

        Returns:
            Pygame rect for rendering and collision
        """
        return self.state.physics.get_rect()

    def reset(self, spawn_x: float, spawn_y: float):
        """
        Reset player to spawn position

        Args:
            spawn_x, spawn_y: New spawn position
        """
        # Reset position
        self.state.physics.x = spawn_x
        self.state.physics.y = spawn_y
        self.state.physics.vx = 0.0
        self.state.physics.vy = 0.0

        # Reset health
        self.state.health_state.current_hp = self.state.health_state.max_hp
        self.state.health_state.invincibility_frames = 0

        # Reset resources
        self.state.stamina = self.state.stamina_max
        self.state.mana = self.state.mana_max
        self.state.shuriken_ammo = self.state.shuriken_max
        self.state.attack_stage = 0
        self.state.attack_timer = 0.0
        self.state.is_throwing = False
        self.state.teleport_cooldown = 0.0
        self.state.ninjutsu_cooldowns.clear()

        # Reset all mechanics
        for mechanic in self.mechanics:
            mechanic.reset(self.state)

        self.logger.info(f"Player {self.player_id} reset to ({spawn_x}, {spawn_y})")

    def is_alive(self) -> bool:
        """Check if player is alive"""
        return self.state.is_alive()

    def take_damage(self, amount: int, source: str = "unknown") -> bool:
        """
        Take damage (with invincibility check)

        Args:
            amount: Damage amount
            source: Damage source (for logging)

        Returns:
            True if damage was taken, False if invincible
        """
        if self.state.is_invincible():
            return False

        old_health = self.state.health_state.current_hp
        died = self.state.health_state.take_damage(amount, defense=0)

        self.logger.info(
            f"Player took {amount} damage from {source} "
            f"(health {old_health} -> {self.state.health_state.current_hp}, died: {died})"
        )

        return True

    def heal(self, amount: int) -> int:
        """
        Heal player

        Args:
            amount: Heal amount

        Returns:
            Actual amount healed
        """
        old_health = self.state.health_state.current_hp
        self.state.health_state.heal(amount)
        healed = self.state.health_state.current_hp - old_health

        if healed > 0:
            self.logger.info(
                f"Player healed {healed} (health {old_health} -> {self.state.health_state.current_hp})"
            )

        return healed

    def cleanup(self):
        """
        Cleanup player (unsubscribe from events)
        """
        # Unsubscribe from tick events
        # Note: EventBus doesn't currently support unsubscribe
        # This is a placeholder for future implementation

        # Cleanup all mechanics
        for mechanic in self.mechanics:
            mechanic.cleanup()

        self.logger.info(f"Player {self.player_id} cleaned up")
