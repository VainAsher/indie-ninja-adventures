"""
Boss Manager - Boss Spawning, Updates, and Special Mechanics

This module provides boss battle management:
- Boss spawning and initialization
- AI updates and phase transitions
- Boss-player collision detection
- Special attack execution (summons, projectiles)
- Boss death handling with rewards
- Event emission for boss progression

Version: v0.7.0
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto

from core import EventBus
from entities.ai_random import AIRandom, derive_ai_seed
from entities.boss_ai import BossAI, BossAIState
from game.scripted_events import ScriptedEventManager

# ============================================================
# Boss Types
# ============================================================


class BossType(Enum):
    """Available boss types"""

    SHADOW_LORD = auto()  # Dark knight boss
    FIRE_DEMON = auto()  # Fire-based boss
    ICE_QUEEN = auto()  # Ice-based boss
    NECROMANCER = auto()  # Summons undead minions
    DRAGON = auto()  # Flying dragon boss
    VEIL_MAIDEN = auto()  # Story boss - The Veil Maiden (Acts 1 & 4)


# ============================================================
# Boss Definition
# ============================================================


@dataclass
class BossDefinition:
    """Boss type definition with stats and behavior"""

    boss_type: BossType
    display_name: str
    max_health: int
    base_damage: int
    move_speed: float
    width: int
    height: int

    # Combat
    melee_range: float = 64.0
    ranged_range: float = 300.0

    # Special attacks
    special_attacks: list[str] = field(default_factory=list)
    minion_types: list[str] = field(default_factory=list)

    # Rewards
    currency_reward: int = 1000
    loot_table_id: str = "boss_legendary"
    exp_value: int = 500

    # Visuals
    sprite_id: str = "boss_default"


# Boss type definitions
BOSS_DEFINITIONS: dict[BossType, BossDefinition] = {
    BossType.SHADOW_LORD: BossDefinition(
        boss_type=BossType.SHADOW_LORD,
        display_name="Shadow Lord",
        max_health=500,
        base_damage=3,
        move_speed=80.0,
        width=64,
        height=96,
        melee_range=80.0,
        special_attacks=["shadow_strike", "dark_wave", "void_portal"],
        minion_types=["shadow_imp", "dark_spirit"],
        currency_reward=1500,
        loot_table_id="boss_shadow",
        exp_value=750,
        sprite_id="boss_shadow_lord",
    ),
    BossType.FIRE_DEMON: BossDefinition(
        boss_type=BossType.FIRE_DEMON,
        display_name="Fire Demon",
        max_health=600,
        base_damage=4,
        move_speed=100.0,
        width=80,
        height=96,
        melee_range=70.0,
        ranged_range=400.0,
        special_attacks=["fireball_barrage", "flame_breath", "meteor_strike"],
        minion_types=["fire_imp", "lava_elemental"],
        currency_reward=2000,
        loot_table_id="boss_fire",
        exp_value=1000,
        sprite_id="boss_fire_demon",
    ),
    BossType.NECROMANCER: BossDefinition(
        boss_type=BossType.NECROMANCER,
        display_name="Necromancer",
        max_health=400,
        base_damage=2,
        move_speed=60.0,
        width=56,
        height=88,
        melee_range=50.0,
        ranged_range=500.0,
        special_attacks=["death_ray", "soul_drain", "bone_cage"],
        minion_types=["skeleton", "zombie", "ghost"],
        currency_reward=1800,
        loot_table_id="boss_necro",
        exp_value=900,
        sprite_id="boss_necromancer",
    ),
    BossType.VEIL_MAIDEN: BossDefinition(
        boss_type=BossType.VEIL_MAIDEN,
        display_name="The Veil Maiden",
        max_health=800,  # High HP for Act 1 (scripted defeat), balanced for Act 4
        base_damage=3,
        move_speed=90.0,
        width=48,
        height=80,
        melee_range=60.0,
        ranged_range=450.0,
        special_attacks=["veil_strike", "isolation_field", "light_drain", "shadow_step"],
        minion_types=[],  # No minions - she isolates the player
        currency_reward=0,  # No reward for Act 1 scripted defeat
        loot_table_id="story_boss_veil_maiden",
        exp_value=0,  # Story boss, no XP
        sprite_id="boss_veil_maiden",
    ),
}


# ============================================================
# Boss Entity
# ============================================================


@dataclass
class Boss:
    """
    Boss entity in the game world.

    Represents an active boss with position, health, AI state, and rewards.
    """

    boss_id: str
    boss_type: BossType
    x: float
    y: float

    # Combat stats
    health: int
    max_health: int
    width: int
    height: int

    # AI state
    ai_controller: BossAI | None = None

    # Physics (simplified for bosses)
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    facing_right: bool = True
    on_ground: bool = True

    # Visual
    animation_frame: int = 0
    animation_timer: float = 0.0

    # Special mechanics
    invulnerable: bool = True  # Invulnerable during intro
    phase: int = 1

    def get_definition(self) -> BossDefinition:
        """Get boss type definition"""
        return BOSS_DEFINITIONS.get(self.boss_type, BOSS_DEFINITIONS[BossType.SHADOW_LORD])

    def get_rect(self) -> tuple[float, float, int, int]:
        """Get boss bounding box"""
        return (self.x, self.y, self.width, self.height)

    def get_center(self) -> tuple[float, float]:
        """Get boss center position"""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def take_damage(self, damage: int) -> bool:
        """
        Take damage. Returns True if boss died.

        Args:
            damage: Damage amount

        Returns:
            True if boss died from this damage
        """
        if self.invulnerable:
            return False

        # Double damage during vulnerable state
        if self.ai_controller and self.ai_controller.is_vulnerable():
            damage *= 2

        old_health = self.health
        self.health = max(0, self.health - damage)

        # Notify AI of damage taken
        if self.ai_controller:
            self.ai_controller.take_damage(damage)

        return self.health == 0 and old_health > 0


# ============================================================
# Boss Projectile
# ============================================================


@dataclass
class BossProjectile:
    """Projectile fired by boss"""

    projectile_id: str
    projectile_type: str  # 'fireball', 'shadow_bolt', etc.
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    damage: int
    width: int = 16
    height: int = 16
    lifetime: float = 5.0  # Max lifetime in seconds
    time_alive: float = 0.0

    def update(self, dt: float):
        """Update projectile position"""
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        self.time_alive += dt

    def is_expired(self) -> bool:
        """Check if projectile should be removed"""
        return self.time_alive >= self.lifetime

    def get_rect(self) -> tuple[float, float, int, int]:
        """Get projectile bounding box"""
        return (self.x, self.y, self.width, self.height)


# ============================================================
# Boss Manager
# ============================================================


class BossManager:
    """
    Manages boss battles in the game.

    Handles boss spawning, AI updates, collision, and special mechanics.
    """

    def __init__(
        self,
        event_bus: EventBus,
        level_seed: int = 0,
        scripted_event_manager: ScriptedEventManager | None = None,
    ):
        """
        Initialize boss manager.

        Args:
            event_bus: Event bus for game events
            level_seed: Seed for deterministic behavior
            scripted_event_manager: Manager for scripted battles (optional)
        """
        self.event_bus = event_bus
        self.level_seed = level_seed
        self.scripted_event_manager = scripted_event_manager

        # Boss tracking
        self.active_boss: Boss | None = None
        self.boss_ai: BossAI | None = None

        # Special mechanics
        self.projectiles: list[BossProjectile] = []
        self.summoned_minions: list[str] = []  # List of minion IDs
        self.next_projectile_id = 0

        # Boss event tracking
        self.boss_defeated = False
        self.boss_phase_transitions: list[int] = []

        # Scripted battle tracking
        self.current_mission_id: str | None = None
        self.scripted_event_triggered = False

    def spawn_boss(
        self, boss_type: BossType, x: float, y: float, boss_id: str | None = None
    ) -> Boss:
        """
        Spawn a boss at the specified position.

        Args:
            boss_type: Type of boss to spawn
            x: X position
            y: Y position
            boss_id: Optional custom boss ID

        Returns:
            Spawned boss entity
        """
        definition = BOSS_DEFINITIONS[boss_type]

        # Generate boss ID if not provided
        if boss_id is None:
            boss_id = f"boss_{boss_type.name.lower()}"

        # Create boss entity
        boss = Boss(
            boss_id=boss_id,
            boss_type=boss_type,
            x=x,
            y=y,
            health=definition.max_health,
            max_health=definition.max_health,
            width=definition.width,
            height=definition.height,
            invulnerable=True,  # Invulnerable during intro
        )

        # Create AI controller with deterministic seed
        ai_seed = derive_ai_seed(self.level_seed, boss_id)
        ai_random = AIRandom(ai_seed)
        boss.ai_controller = BossAI(boss, ai_random)

        self.active_boss = boss
        self.boss_ai = boss.ai_controller

        # Emit boss spawn event
        self.event_bus.emit(
            "boss_spawned", {"boss_id": boss_id, "boss_type": boss_type.name, "position": (x, y)}
        )

        return boss

    def start_boss_battle(self, mission_id: str):
        """
        Start a boss battle for a mission.

        Args:
            mission_id: Mission ID
        """
        self.current_mission_id = mission_id
        self.scripted_event_triggered = False

        # Start scripted battle if configured
        if self.scripted_event_manager:
            self.scripted_event_manager.start_scripted_battle(mission_id)

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        player_hp: float = 0.0,
        player_max_hp: float = 1.0,
    ) -> int | None:
        """
        Update boss AI and mechanics.

        Args:
            dt: Delta time in seconds
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            Damage to deal to player (if any)
        """
        if not self.active_boss or not self.boss_ai:
            return None

        boss = self.active_boss

        # Boss is no longer invulnerable after intro
        if self.boss_ai.get_state() != BossAIState.INTRO:
            boss.invulnerable = False

        # Update AI
        action = self.boss_ai.update(dt, player_x, player_y, player_width, player_height)

        # Handle AI actions
        damage_to_player = action.get("damage")

        # Handle special attacks
        if action.get("special"):
            self._execute_special_attack(action["special"], player_x, player_y)

        # Handle minion summoning
        if action.get("summon"):
            self._summon_minion(action["summon"])

        # Handle teleportation
        if action.get("teleport"):
            dest_x, dest_y = action["teleport"]
            boss.x = dest_x - boss.width / 2
            boss.y = dest_y - boss.height / 2
            self.event_bus.emit(
                "boss_teleported", {"boss_id": boss.boss_id, "position": (dest_x, dest_y)}
            )

        # Update projectiles
        self._update_projectiles(dt)

        # Track phase transitions
        current_phase = self.boss_ai.get_phase()
        if current_phase not in self.boss_phase_transitions:
            self.boss_phase_transitions.append(current_phase)
            self.event_bus.emit(
                "boss_phase_change", {"boss_id": boss.boss_id, "phase": current_phase}
            )

        # Check for scripted events (e.g., scripted defeat)
        if (
            self.scripted_event_manager
            and self.current_mission_id
            and not self.scripted_event_triggered
        ):
            scripted_event = self.scripted_event_manager.check_scripted_battle(
                self.current_mission_id, player_hp, player_max_hp, boss.health, boss.max_health
            )

            if scripted_event:
                self.scripted_event_triggered = True
                # Emit scripted event
                self.event_bus.emit(
                    "scripted_event_triggered",
                    {
                        "mission_id": self.current_mission_id,
                        "event_type": scripted_event,
                        "boss_id": boss.boss_id,
                    },
                )

        return damage_to_player

    def check_player_collision(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> int | None:
        """
        Check if player collides with boss or projectiles.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            Damage to deal to player (if any)
        """
        damage = 0

        # Check boss melee collision
        if self.active_boss and not self.boss_ai.is_dead():
            if self._check_rect_collision(
                player_x, player_y, player_width, player_height, *self.active_boss.get_rect()
            ):
                # Contact damage
                definition = self.active_boss.get_definition()
                damage += 1  # Contact damage

        # Check projectile collisions
        for projectile in self.projectiles[:]:
            if self._check_rect_collision(
                player_x, player_y, player_width, player_height, *projectile.get_rect()
            ):
                damage += projectile.damage
                self.projectiles.remove(projectile)

        return damage if damage > 0 else None

    def damage_boss(self, damage: int) -> bool:
        """
        Deal damage to the boss.

        Args:
            damage: Damage amount

        Returns:
            True if boss was defeated
        """
        if not self.active_boss:
            return False

        boss_died = self.active_boss.take_damage(damage)

        if boss_died:
            self._handle_boss_death()
            return True

        return False

    def _handle_boss_death(self):
        """Handle boss death - emit events and rewards"""
        if not self.active_boss:
            return

        boss = self.active_boss
        definition = boss.get_definition()

        # Emit boss defeated event
        self.event_bus.emit(
            "boss_defeated",
            {
                "boss_id": boss.boss_id,
                "boss_type": boss.boss_type.name,
                "currency_reward": definition.currency_reward,
                "exp_reward": definition.exp_value,
            },
        )

        self.boss_defeated = True

    def _execute_special_attack(self, special_type: str, player_x: float, player_y: float):
        """Execute a special attack"""
        if not self.active_boss:
            return

        boss = self.active_boss
        boss_center = boss.get_center()

        # Create projectiles based on attack type
        if special_type == "fireball_barrage":
            self._create_projectile_barrage(boss_center, player_x, player_y, count=5)
        elif special_type == "shadow_strike":
            self._create_homing_projectile(boss_center, player_x, player_y)

        # Veil Maiden attacks
        elif special_type == "veil_strike":
            # Dark projectiles in a spread pattern
            self._create_veil_strike(boss_center, player_x, player_y)
        elif special_type == "isolation_field":
            # Creates zone that slows player (emits event for game logic)
            self._create_isolation_field(boss_center)
        elif special_type == "light_drain":
            # Visual effect attack (emits event for companion draining)
            self._create_light_drain(boss_center, player_x, player_y)
        elif special_type == "shadow_step":
            # Teleportation handled separately by AI teleport action
            pass

        # Emit event
        self.event_bus.emit(
            "boss_special_attack", {"boss_id": boss.boss_id, "attack_type": special_type}
        )

    def _create_projectile_barrage(
        self, origin: tuple[float, float], target_x: float, target_y: float, count: int = 5
    ):
        """Create multiple projectiles in a spread pattern"""
        origin_x, origin_y = origin

        for i in range(count):
            # Spread projectiles in an arc
            angle_offset = (i - count // 2) * 0.3  # 0.3 radians spread
            dx = target_x - origin_x
            dy = target_y - origin_y
            base_angle = math.atan2(dy, dx)
            angle = base_angle + angle_offset

            speed = 200.0
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed

            projectile = BossProjectile(
                projectile_id=f"proj_{self.next_projectile_id}",
                projectile_type="fireball",
                x=origin_x,
                y=origin_y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                damage=2,
            )
            self.projectiles.append(projectile)
            self.next_projectile_id += 1

    def _create_homing_projectile(
        self, origin: tuple[float, float], target_x: float, target_y: float
    ):
        """Create a single homing projectile"""
        origin_x, origin_y = origin
        dx = target_x - origin_x
        dy = target_y - origin_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            speed = 250.0
            velocity_x = (dx / distance) * speed
            velocity_y = (dy / distance) * speed

            projectile = BossProjectile(
                projectile_id=f"proj_{self.next_projectile_id}",
                projectile_type="shadow_bolt",
                x=origin_x,
                y=origin_y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                damage=3,
            )
            self.projectiles.append(projectile)
            self.next_projectile_id += 1

    def _create_veil_strike(self, origin: tuple[float, float], target_x: float, target_y: float):
        """
        Veil Maiden's signature attack - dark projectiles in a triple spread.

        Creates three dark energy projectiles aimed at the player.
        """
        origin_x, origin_y = origin

        # Create 3 projectiles in a spread
        for i in range(3):
            angle_offset = (i - 1) * 0.4  # -0.4, 0, 0.4 radians
            dx = target_x - origin_x
            dy = target_y - origin_y
            base_angle = math.atan2(dy, dx)
            angle = base_angle + angle_offset

            speed = 220.0
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed

            projectile = BossProjectile(
                projectile_id=f"proj_{self.next_projectile_id}",
                projectile_type="veil_strike",
                x=origin_x,
                y=origin_y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                damage=2,
                width=20,
                height=20,
            )
            self.projectiles.append(projectile)
            self.next_projectile_id += 1

    def _create_isolation_field(self, origin: tuple[float, float]):
        """
        Veil Maiden's isolation field - creates a zone that slows the player.

        Emits event for game logic to create the slowing zone.
        """
        if not self.active_boss:
            return

        origin_x, origin_y = origin

        # Emit event for game logic to handle
        self.event_bus.emit(
            "veil_maiden_isolation_field",
            {
                "boss_id": self.active_boss.boss_id,
                "center_x": origin_x,
                "center_y": origin_y,
                "radius": 200.0,  # Field radius
                "duration": 5.0,  # Field duration in seconds
                "slow_factor": 0.5,  # Player speed reduced to 50%
            },
        )

    def _create_light_drain(self, origin: tuple[float, float], target_x: float, target_y: float):
        """
        Veil Maiden's light drain - drains player's "light" (Yin/Yang).

        Creates a beam-like projectile that drains visual effects.
        """
        origin_x, origin_y = origin
        dx = target_x - origin_x
        dy = target_y - origin_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # Fast-moving beam
            speed = 300.0
            velocity_x = (dx / distance) * speed
            velocity_y = (dy / distance) * speed

            projectile = BossProjectile(
                projectile_id=f"proj_{self.next_projectile_id}",
                projectile_type="light_drain",
                x=origin_x,
                y=origin_y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                damage=1,  # Low damage but triggers special effect
                width=24,
                height=24,
                lifetime=3.0,
            )
            self.projectiles.append(projectile)
            self.next_projectile_id += 1

            # Emit event for visual effects (dim Yin/Yang)
            if self.active_boss:
                self.event_bus.emit(
                    "veil_maiden_light_drain",
                    {
                        "boss_id": self.active_boss.boss_id,
                        "projectile_id": projectile.projectile_id,
                    },
                )

    def _summon_minion(self, minion_type: str):
        """Summon a minion (delegates to enemy system)"""
        if not self.active_boss:
            return

        minion_id = f"minion_{len(self.summoned_minions)}"
        self.summoned_minions.append(minion_id)

        # Emit event for enemy system to spawn minion
        self.event_bus.emit(
            "boss_summon_minion",
            {
                "boss_id": self.active_boss.boss_id,
                "minion_type": minion_type,
                "minion_id": minion_id,
                "spawn_position": self.active_boss.get_center(),
            },
        )

    def _update_projectiles(self, dt: float):
        """Update all boss projectiles"""
        for projectile in self.projectiles[:]:
            projectile.update(dt)
            if projectile.is_expired():
                self.projectiles.remove(projectile)

    def _check_rect_collision(
        self, x1: float, y1: float, w1: int, h1: int, x2: float, y2: float, w2: int, h2: int
    ) -> bool:
        """Check if two rectangles collide"""
        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

    def is_boss_active(self) -> bool:
        """Check if a boss is currently active"""
        return self.active_boss is not None and not self.boss_ai.is_dead()

    def get_active_boss(self) -> Boss | None:
        """Get the currently active boss"""
        return self.active_boss

    def get_projectiles(self) -> list[BossProjectile]:
        """Get list of active projectiles"""
        return self.projectiles

    def has_scripted_event_triggered(self) -> bool:
        """Check if a scripted event has been triggered in current battle"""
        return self.scripted_event_triggered

    def get_current_mission_id(self) -> str | None:
        """Get the current mission ID for this boss battle"""
        return self.current_mission_id

    def clear(self):
        """Clear all boss data"""
        self.active_boss = None
        self.boss_ai = None
        self.projectiles.clear()
        self.summoned_minions.clear()
        self.boss_defeated = False
        self.boss_phase_transitions.clear()
        self.current_mission_id = None
        self.scripted_event_triggered = False
