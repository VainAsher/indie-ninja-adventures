"""
Boss System - Boss Entities and Multi-Phase Behavior

This module provides boss encounters:
- 5 boss types: Forest Guardian, Corrupt Mayor, Crystal Golem, Dark Knight, Plague Rat
- Multi-phase behavior (changes at 75%, 50%, 25% HP)
- Special attacks with telegraphs
- Large health pools (10-20 HP)
- Guaranteed rare loot drops
- Boss-specific arenas

Version: v0.6.0
"""

import math
from dataclasses import dataclass, field
from enum import Enum

from game.health_system import HealthState

# ============================================================
# Boss Types
# ============================================================


class BossType(Enum):
    """Boss entity types"""

    FOREST_GUARDIAN = "forest_guardian"  # Giant tree boss
    CORRUPT_MAYOR = "corrupt_mayor"  # Human with minions
    CRYSTAL_GOLEM = "crystal_golem"  # Rock boss with shields
    DARK_KNIGHT = "dark_knight"  # Sword combos
    PLAGUE_RAT = "plague_rat"  # Fast, poison-based


# ============================================================
# Boss AI States
# ============================================================


class BossAIState(Enum):
    """Boss AI behavior states"""

    INTRO = "intro"  # Introduction sequence
    IDLE = "idle"  # Waiting between attacks
    MOVE = "move"  # Moving toward player
    ATTACK_MELEE = "attack_melee"  # Melee attack
    ATTACK_RANGED = "attack_ranged"  # Ranged attack
    ATTACK_SPECIAL = "attack_special"  # Special/ultimate attack
    VULNERABLE = "vulnerable"  # Vulnerable after attack
    STUNNED = "stunned"  # Stunned from player attack
    PHASE_TRANSITION = "phase_transition"  # Transitioning between phases
    DEAD = "dead"  # Dead (before removal)


# ============================================================
# Boss Phases
# ============================================================


class BossPhase(Enum):
    """Boss combat phases"""

    PHASE_1 = 1  # 100% - 75% HP
    PHASE_2 = 2  # 75% - 50% HP
    PHASE_3 = 3  # 50% - 25% HP
    PHASE_4 = 4  # 25% - 0% HP


# ============================================================
# Boss Attack Patterns
# ============================================================


@dataclass
class BossAttackPattern:
    """
    Boss attack pattern definition.

    Defines a specific attack the boss can perform.
    """

    attack_id: str
    attack_type: str  # "melee", "ranged", "special"
    damage: int
    range: float  # Attack range in pixels
    telegraph_duration: float  # Telegraph time before attack (seconds)
    attack_duration: float  # Attack animation duration (seconds)
    cooldown: float  # Cooldown after attack (seconds)
    vulnerable_after: bool = False  # Boss vulnerable after this attack


# ============================================================
# Boss Definition
# ============================================================


@dataclass
class BossDefinition:
    """
    Static boss definition.

    Defines boss properties and behavior.
    """

    boss_type: BossType
    display_name: str
    description: str

    # Stats
    max_hp: int
    base_damage: int
    move_speed: float  # Pixels per second

    # Visual
    width: int = 64
    height: int = 96
    sprite_id: str = "boss_default"

    # Arena
    arena_min_size: tuple[int, int] = (3, 3)  # Minimum room size (in rooms)

    # Behavior
    detection_radius: float = 400.0  # Always sees player in arena
    phase_transition_invincible: bool = True  # Invincible during phase transition

    # Attacks per phase
    phase_1_attacks: list[str] = field(default_factory=list)
    phase_2_attacks: list[str] = field(default_factory=list)
    phase_3_attacks: list[str] = field(default_factory=list)
    phase_4_attacks: list[str] = field(default_factory=list)

    # Loot
    loot_table_id: str = "boss_legendary"
    exp_value: int = 100  # Experience points granted

    # Physics
    can_fly: bool = False
    gravity_scale: float = 1.0


# ============================================================
# Boss Attack Definitions
# ============================================================

BOSS_ATTACKS = {
    # Forest Guardian attacks
    "root_slam": BossAttackPattern(
        attack_id="root_slam",
        attack_type="melee",
        damage=2,
        range=80.0,
        telegraph_duration=0.5,
        attack_duration=0.3,
        cooldown=2.0,
        vulnerable_after=False,
    ),
    "vine_whip": BossAttackPattern(
        attack_id="vine_whip",
        attack_type="ranged",
        damage=1,
        range=200.0,
        telegraph_duration=0.3,
        attack_duration=0.5,
        cooldown=1.5,
        vulnerable_after=False,
    ),
    "nature_wrath": BossAttackPattern(
        attack_id="nature_wrath",
        attack_type="special",
        damage=3,
        range=300.0,
        telegraph_duration=1.0,
        attack_duration=1.0,
        cooldown=5.0,
        vulnerable_after=True,
    ),
    # Corrupt Mayor attacks
    "sword_slash": BossAttackPattern(
        attack_id="sword_slash",
        attack_type="melee",
        damage=1,
        range=60.0,
        telegraph_duration=0.2,
        attack_duration=0.3,
        cooldown=1.0,
        vulnerable_after=False,
    ),
    "summon_minion": BossAttackPattern(
        attack_id="summon_minion",
        attack_type="special",
        damage=0,
        range=0.0,
        telegraph_duration=0.8,
        attack_duration=0.5,
        cooldown=8.0,
        vulnerable_after=True,
    ),
    # Crystal Golem attacks
    "crystal_punch": BossAttackPattern(
        attack_id="crystal_punch",
        attack_type="melee",
        damage=2,
        range=70.0,
        telegraph_duration=0.4,
        attack_duration=0.4,
        cooldown=1.5,
        vulnerable_after=False,
    ),
    "shard_volley": BossAttackPattern(
        attack_id="shard_volley",
        attack_type="ranged",
        damage=1,
        range=250.0,
        telegraph_duration=0.6,
        attack_duration=0.8,
        cooldown=3.0,
        vulnerable_after=False,
    ),
    "earth_shatter": BossAttackPattern(
        attack_id="earth_shatter",
        attack_type="special",
        damage=3,
        range=400.0,
        telegraph_duration=1.2,
        attack_duration=1.0,
        cooldown=6.0,
        vulnerable_after=True,
    ),
    # Dark Knight attacks
    "quick_strike": BossAttackPattern(
        attack_id="quick_strike",
        attack_type="melee",
        damage=1,
        range=65.0,
        telegraph_duration=0.1,
        attack_duration=0.2,
        cooldown=0.8,
        vulnerable_after=False,
    ),
    "shadow_dash": BossAttackPattern(
        attack_id="shadow_dash",
        attack_type="special",
        damage=2,
        range=200.0,
        telegraph_duration=0.5,
        attack_duration=0.4,
        cooldown=3.0,
        vulnerable_after=False,
    ),
    "dark_blade": BossAttackPattern(
        attack_id="dark_blade",
        attack_type="special",
        damage=4,
        range=300.0,
        telegraph_duration=1.5,
        attack_duration=0.8,
        cooldown=8.0,
        vulnerable_after=True,
    ),
    # Plague Rat attacks
    "bite": BossAttackPattern(
        attack_id="bite",
        attack_type="melee",
        damage=1,
        range=50.0,
        telegraph_duration=0.15,
        attack_duration=0.25,
        cooldown=1.0,
        vulnerable_after=False,
    ),
    "poison_spit": BossAttackPattern(
        attack_id="poison_spit",
        attack_type="ranged",
        damage=1,
        range=180.0,
        telegraph_duration=0.4,
        attack_duration=0.3,
        cooldown=2.0,
        vulnerable_after=False,
    ),
    "plague_burst": BossAttackPattern(
        attack_id="plague_burst",
        attack_type="special",
        damage=2,
        range=350.0,
        telegraph_duration=0.8,
        attack_duration=1.2,
        cooldown=5.0,
        vulnerable_after=True,
    ),
}


# ============================================================
# Boss Definitions
# ============================================================

BOSS_DEFINITIONS = {
    BossType.FOREST_GUARDIAN: BossDefinition(
        boss_type=BossType.FOREST_GUARDIAN,
        display_name="Forest Guardian",
        description="An ancient tree spirit corrupted by dark magic.",
        max_hp=15,
        base_damage=2,
        move_speed=80.0,
        width=80,
        height=120,
        arena_min_size=(3, 3),
        phase_1_attacks=["root_slam", "vine_whip"],
        phase_2_attacks=["root_slam", "vine_whip", "vine_whip"],  # More vine whips
        phase_3_attacks=["root_slam", "vine_whip", "nature_wrath"],
        phase_4_attacks=["nature_wrath", "root_slam", "vine_whip", "nature_wrath"],  # Enraged
        loot_table_id="boss_forest",
        exp_value=100,
        can_fly=False,
    ),
    BossType.CORRUPT_MAYOR: BossDefinition(
        boss_type=BossType.CORRUPT_MAYOR,
        display_name="Corrupt Mayor",
        description="The town's leader, twisted by greed and dark pacts.",
        max_hp=12,
        base_damage=1,
        move_speed=100.0,
        width=48,
        height=72,
        arena_min_size=(3, 2),
        phase_1_attacks=["sword_slash"],
        phase_2_attacks=["sword_slash", "summon_minion"],
        phase_3_attacks=["sword_slash", "summon_minion", "summon_minion"],
        phase_4_attacks=["summon_minion", "sword_slash", "summon_minion"],  # Desperate summoning
        loot_table_id="boss_town",
        exp_value=100,
        can_fly=False,
    ),
    BossType.CRYSTAL_GOLEM: BossDefinition(
        boss_type=BossType.CRYSTAL_GOLEM,
        display_name="Crystal Golem",
        description="A massive golem formed from living crystal.",
        max_hp=20,
        base_damage=2,
        move_speed=60.0,
        width=96,
        height=128,
        arena_min_size=(3, 3),
        phase_1_attacks=["crystal_punch"],
        phase_2_attacks=["crystal_punch", "shard_volley"],
        phase_3_attacks=["crystal_punch", "shard_volley", "earth_shatter"],
        phase_4_attacks=["earth_shatter", "shard_volley", "crystal_punch", "earth_shatter"],
        loot_table_id="boss_caves",
        exp_value=120,
        can_fly=False,
    ),
    BossType.DARK_KNIGHT: BossDefinition(
        boss_type=BossType.DARK_KNIGHT,
        display_name="Dark Knight",
        description="A fallen warrior consumed by darkness.",
        max_hp=18,
        base_damage=2,
        move_speed=120.0,
        width=56,
        height=80,
        arena_min_size=(4, 2),
        phase_1_attacks=["quick_strike"],
        phase_2_attacks=["quick_strike", "shadow_dash"],
        phase_3_attacks=["quick_strike", "shadow_dash", "dark_blade"],
        phase_4_attacks=["shadow_dash", "quick_strike", "dark_blade", "shadow_dash"],  # Aggressive
        loot_table_id="boss_castle",
        exp_value=150,
        can_fly=False,
    ),
    BossType.PLAGUE_RAT: BossDefinition(
        boss_type=BossType.PLAGUE_RAT,
        display_name="Plague Rat King",
        description="The bloated king of the sewer rats, spreading disease.",
        max_hp=14,
        base_damage=1,
        move_speed=140.0,
        width=64,
        height=56,
        arena_min_size=(3, 2),
        phase_1_attacks=["bite", "poison_spit"],
        phase_2_attacks=["bite", "poison_spit", "poison_spit"],  # More poison
        phase_3_attacks=["bite", "poison_spit", "plague_burst"],
        phase_4_attacks=["plague_burst", "poison_spit", "bite", "plague_burst"],  # Desperate
        loot_table_id="boss_sewer",
        exp_value=140,
        can_fly=False,
    ),
}


# ============================================================
# Boss Entity
# ============================================================


@dataclass
class Boss:
    """
    Boss instance in the game world.

    Represents an active boss with position, health, AI state, and phase tracking.
    """

    boss_id: str
    boss_type: BossType
    x: float
    y: float

    # Physics state
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    facing_right: bool = True
    on_ground: bool = False

    # Health
    health_state: HealthState = field(default_factory=lambda: HealthState(15, 15))

    # AI state
    ai_state: BossAIState = BossAIState.INTRO
    ai_state_timer: float = 0.0  # Time in current state

    # Phase tracking
    current_phase: BossPhase = BossPhase.PHASE_1
    phase_transition_active: bool = False
    invulnerable: bool = False  # Invulnerable during phase transition

    # Attack state
    current_attack: str | None = None
    attack_timer: float = 0.0
    attack_telegraph_complete: bool = False
    attack_cooldown_timer: float = 0.0

    # Target tracking
    target_player_x: float | None = None
    target_player_y: float | None = None

    # Stun state
    stun_duration: float = 0.0
    knockback_velocity_x: float = 0.0
    knockback_velocity_y: float = 0.0

    # Loot
    loot_table_id: str = "boss_legendary"
    loot_seed: int = 0  # Deterministic loot generation

    # Animation
    animation_frame: int = 0
    animation_timer: float = 0.0

    def get_definition(self) -> BossDefinition:
        """Get boss definition"""
        return BOSS_DEFINITIONS.get(self.boss_type, BOSS_DEFINITIONS[BossType.FOREST_GUARDIAN])

    def get_rect(self) -> tuple[float, float, float, float]:
        """Get boss bounding box (x, y, width, height)"""
        definition = self.get_definition()
        return (self.x, self.y, definition.width, definition.height)

    def get_center(self) -> tuple[float, float]:
        """Get boss center position"""
        definition = self.get_definition()
        return (self.x + definition.width / 2, self.y + definition.height / 2)

    def distance_to(self, target_x: float, target_y: float) -> float:
        """Calculate distance to target position"""
        center_x, center_y = self.get_center()
        dx = target_x - center_x
        dy = target_y - center_y
        return math.sqrt(dx * dx + dy * dy)

    def get_health_percentage(self) -> float:
        """Get health as percentage (0.0 to 1.0)"""
        return self.health_state.current_hp / self.health_state.max_hp

    def should_transition_phase(self) -> bool:
        """Check if boss should transition to next phase"""
        hp_pct = self.get_health_percentage()

        if self.current_phase == BossPhase.PHASE_1 and hp_pct <= 0.75:
            return True
        elif self.current_phase == BossPhase.PHASE_2 and hp_pct <= 0.50:
            return True
        elif self.current_phase == BossPhase.PHASE_3 and hp_pct <= 0.25:
            return True

        return False

    def advance_phase(self):
        """Advance to next phase"""
        if self.current_phase == BossPhase.PHASE_1:
            self.current_phase = BossPhase.PHASE_2
        elif self.current_phase == BossPhase.PHASE_2:
            self.current_phase = BossPhase.PHASE_3
        elif self.current_phase == BossPhase.PHASE_3:
            self.current_phase = BossPhase.PHASE_4

    def get_available_attacks(self) -> list[str]:
        """Get available attacks for current phase"""
        definition = self.get_definition()

        if self.current_phase == BossPhase.PHASE_1:
            return definition.phase_1_attacks
        elif self.current_phase == BossPhase.PHASE_2:
            return definition.phase_2_attacks
        elif self.current_phase == BossPhase.PHASE_3:
            return definition.phase_3_attacks
        elif self.current_phase == BossPhase.PHASE_4:
            return definition.phase_4_attacks

        return []

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
            True if boss died
        """
        # Check if invulnerable
        if self.invulnerable:
            return False

        died = self.health_state.take_damage(damage, defense=0)

        if died:
            self.ai_state = BossAIState.DEAD
            return True

        # Check for phase transition
        if self.should_transition_phase():
            self.phase_transition_active = True
            self.ai_state = BossAIState.PHASE_TRANSITION
            self.invulnerable = True

        # Apply knockback and stun (bosses have reduced stun)
        if stun_duration > 0.0 and not self.phase_transition_active:
            self.ai_state = BossAIState.STUNNED
            self.stun_duration = stun_duration * 0.5  # Bosses have 50% stun reduction
            self.knockback_velocity_x = knockback_x * 0.7  # Reduced knockback
            self.knockback_velocity_y = knockback_y * 0.7

        return False

    def is_alive(self) -> bool:
        """Check if boss is alive"""
        return self.health_state.is_alive() and self.ai_state != BossAIState.DEAD

    def is_dead(self) -> bool:
        """Check if boss is dead"""
        return not self.is_alive()

    def update_animation(self, dt: float):
        """Update animation frame"""
        self.animation_timer += dt
        if self.animation_timer >= 0.15:  # 150ms per frame (faster than regular enemies)
            self.animation_timer = 0.0
            self.animation_frame = (self.animation_frame + 1) % 8  # 8 frames for bosses

    def update_health(self, dt: float):
        """Update health state (invincibility frames)"""
        self.health_state.update()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "boss_id": self.boss_id,
            "boss_type": self.boss_type.value,
            "x": self.x,
            "y": self.y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "facing_right": self.facing_right,
            "health_state": {
                "current_hp": self.health_state.current_hp,
                "max_hp": self.health_state.max_hp,
                "invincibility_frames": self.health_state.invincibility_frames,
            },
            "ai_state": self.ai_state.value,
            "current_phase": self.current_phase.value,
            "loot_table_id": self.loot_table_id,
            "loot_seed": self.loot_seed,
        }

    @staticmethod
    def from_dict(data: dict) -> "Boss":
        """Deserialize from dictionary"""
        health_data = data.get("health_state", {})
        health_state = HealthState(
            current_hp=health_data.get("current_hp", 15),
            max_hp=health_data.get("max_hp", 15),
            invincibility_frames=health_data.get("invincibility_frames", 0),
        )

        return Boss(
            boss_id=data["boss_id"],
            boss_type=BossType(data["boss_type"]),
            x=data["x"],
            y=data["y"],
            velocity_x=data.get("velocity_x", 0.0),
            velocity_y=data.get("velocity_y", 0.0),
            facing_right=data.get("facing_right", True),
            health_state=health_state,
            ai_state=BossAIState(data.get("ai_state", "intro")),
            current_phase=BossPhase(data.get("current_phase", 1)),
            loot_table_id=data.get("loot_table_id", "boss_legendary"),
            loot_seed=data.get("loot_seed", 0),
        )


def get_boss_definition(boss_type: BossType) -> BossDefinition | None:
    """Get boss definition by type"""
    return BOSS_DEFINITIONS.get(boss_type)
