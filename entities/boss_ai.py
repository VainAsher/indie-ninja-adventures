"""
Boss AI System - Complex Boss Battle State Machine

This module provides boss AI behavior with a 10-state state machine:
- INTRO: Boss introduction/spawn animation
- IDLE: Waiting between attacks
- PHASE_1: First combat phase (100-66% health)
- PHASE_2: Second combat phase (66-33% health)
- PHASE_3: Final phase enraged (33-0% health)
- SPECIAL_ATTACK: Executing special move
- VULNERABLE: Stunned/vulnerable period
- SUMMONING: Summoning minions
- TELEPORTING: Moving to new position
- DEAD: Boss defeated

Version: v0.7.0
"""

from typing import Optional, List, Tuple
from enum import Enum, auto
import math

from entities.ai_random import AIRandom


# ============================================================
# Boss AI States
# ============================================================

class BossAIState(Enum):
    """Boss AI state machine states"""
    INTRO = auto()           # Introduction animation
    IDLE = auto()            # Waiting between attacks
    PHASE_1 = auto()         # First combat phase (100-66% HP)
    PHASE_2 = auto()         # Second combat phase (66-33% HP)
    PHASE_3 = auto()         # Final enraged phase (33-0% HP)
    SPECIAL_ATTACK = auto()  # Executing special move
    VULNERABLE = auto()      # Stunned/vulnerable period
    SUMMONING = auto()       # Summoning minions
    TELEPORTING = auto()     # Teleporting to new position
    DEAD = auto()            # Boss defeated


# ============================================================
# Boss AI Constants
# ============================================================

# Phase transitions (health percentage thresholds)
PHASE_2_HEALTH_THRESHOLD = 0.66  # 66% health triggers phase 2
PHASE_3_HEALTH_THRESHOLD = 0.33  # 33% health triggers phase 3

# Timing constants
INTRO_DURATION = 3.0              # Intro animation duration (seconds)
IDLE_DURATION_BASE = 1.0          # Base idle time between attacks
SPECIAL_ATTACK_DURATION = 2.0     # Special attack execution time
VULNERABLE_DURATION = 1.5         # Vulnerable period after special
SUMMONING_DURATION = 2.5          # Time to summon minions
TELEPORT_DURATION = 0.8           # Teleportation animation time
ATTACK_COOLDOWN_BASE = 1.5        # Base cooldown between attacks

# Combat ranges
MELEE_RANGE = 64.0                # Melee attack range (pixels)
RANGED_RANGE = 300.0              # Ranged attack range (pixels)
TELEPORT_RANGE = 150.0            # Min distance for teleport

# Phase behavior modifiers
PHASE_2_SPEED_MULT = 1.3          # 30% faster in phase 2
PHASE_3_SPEED_MULT = 1.5          # 50% faster in phase 3
PHASE_3_ATTACK_SPEED_MULT = 0.7   # 30% faster attacks in phase 3


# ============================================================
# Boss AI Controller
# ============================================================

class BossAI:
    """
    AI controller for boss behavior.

    Manages complex state machine with phase transitions, special attacks,
    minion summoning, and teleportation.
    """

    def __init__(self, boss_entity, ai_random: Optional[AIRandom] = None):
        """
        Initialize boss AI controller.

        Args:
            boss_entity: Boss entity to control
            ai_random: Seeded random generator for deterministic AI timing
        """
        self.boss = boss_entity
        self.ai_random = ai_random or AIRandom(0)

        # State machine
        self.state = BossAIState.INTRO
        self.state_timer = 0.0
        self.previous_state = None

        # Combat state
        self.attack_cooldown = 0.0
        self.current_phase = 1
        self.special_attack_count = 0
        self.minions_summoned = 0

        # Targeting
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None
        self.player_distance = 0.0

        # Attack patterns
        self.attack_pattern_index = 0
        self.attacks_in_pattern = 0

        # Teleport state
        self.teleport_cooldown = 0.0
        self.teleport_destination: Optional[Tuple[float, float]] = None

        # Pre-computed timing variations for determinism
        self.idle_duration = self._get_varied_duration(IDLE_DURATION_BASE, 0.3)
        self.attack_cooldown_base = self._get_varied_duration(ATTACK_COOLDOWN_BASE, 0.2)

    def update(self, dt: float, player_x: float, player_y: float,
               player_width: int, player_height: int) -> dict:
        """
        Update boss AI for one frame.

        Args:
            dt: Delta time in seconds
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            Dict with boss actions this frame:
            {
                'damage': Optional[int],  # Damage to deal
                'special': Optional[str], # Special attack type
                'summon': Optional[str],  # Minion type to summon
                'teleport': Optional[Tuple[float, float]]  # Teleport destination
            }
        """
        # Update timers
        self.state_timer += dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= dt

        # Update player tracking
        self._update_target(player_x, player_y, player_width, player_height)

        # Check for phase transitions based on health
        self._check_phase_transition()

        # Initialize action dict
        action = {
            'damage': None,
            'special': None,
            'summon': None,
            'teleport': None
        }

        # Update state machine
        if self.state == BossAIState.INTRO:
            self._update_intro(dt, action)
        elif self.state == BossAIState.IDLE:
            self._update_idle(dt, action)
        elif self.state == BossAIState.PHASE_1:
            self._update_phase_1(dt, action)
        elif self.state == BossAIState.PHASE_2:
            self._update_phase_2(dt, action)
        elif self.state == BossAIState.PHASE_3:
            self._update_phase_3(dt, action)
        elif self.state == BossAIState.SPECIAL_ATTACK:
            self._update_special_attack(dt, action)
        elif self.state == BossAIState.VULNERABLE:
            self._update_vulnerable(dt, action)
        elif self.state == BossAIState.SUMMONING:
            self._update_summoning(dt, action)
        elif self.state == BossAIState.TELEPORTING:
            self._update_teleporting(dt, action)
        elif self.state == BossAIState.DEAD:
            self._update_dead(dt, action)

        return action

    # ============================================================
    # State Update Methods
    # ============================================================

    def _update_intro(self, dt: float, action: dict):
        """Boss introduction state"""
        # Play intro animation, boss is invulnerable
        if self.state_timer >= INTRO_DURATION:
            self._transition_to_state(BossAIState.PHASE_1)

    def _update_idle(self, dt: float, action: dict):
        """Idle state - waiting between attacks"""
        # Wait for idle duration, then return to combat phase
        if self.state_timer >= self.idle_duration:
            phase_state = self._get_current_phase_state()
            self._transition_to_state(phase_state)

    def _update_phase_1(self, dt: float, action: dict):
        """Phase 1 combat - normal difficulty"""
        self._execute_phase_combat(dt, action, phase_mult=1.0)

    def _update_phase_2(self, dt: float, action: dict):
        """Phase 2 combat - increased difficulty"""
        self._execute_phase_combat(dt, action, phase_mult=PHASE_2_SPEED_MULT)

    def _update_phase_3(self, dt: float, action: dict):
        """Phase 3 combat - enraged, maximum difficulty"""
        self._execute_phase_combat(dt, action, phase_mult=PHASE_3_SPEED_MULT)

        # Phase 3 is more aggressive - may use special attacks more often
        if self.ai_random.random() < 0.15 * dt:  # 15% chance per second
            self._transition_to_state(BossAIState.SPECIAL_ATTACK)

    def _update_special_attack(self, dt: float, action: dict):
        """Execute special attack"""
        # Execute special attack in the middle of the duration
        if self.state_timer >= SPECIAL_ATTACK_DURATION / 2:
            if action['special'] is None:  # Only execute once
                action['special'] = self._choose_special_attack()
                self.special_attack_count += 1

        # Transition to vulnerable after attack completes
        if self.state_timer >= SPECIAL_ATTACK_DURATION:
            self._transition_to_state(BossAIState.VULNERABLE)

    def _update_vulnerable(self, dt: float, action: dict):
        """Vulnerable state - boss can take extra damage"""
        # Return to combat after vulnerable period
        if self.state_timer >= VULNERABLE_DURATION:
            phase_state = self._get_current_phase_state()
            self._transition_to_state(phase_state)

    def _update_summoning(self, dt: float, action: dict):
        """Summoning minions"""
        # Summon minions at the midpoint
        if self.state_timer >= SUMMONING_DURATION / 2:
            if action['summon'] is None:  # Only summon once
                action['summon'] = self._choose_minion_type()
                self.minions_summoned += 1

        # Return to combat after summoning
        if self.state_timer >= SUMMONING_DURATION:
            phase_state = self._get_current_phase_state()
            self._transition_to_state(phase_state)

    def _update_teleporting(self, dt: float, action: dict):
        """Teleporting to new position"""
        # Execute teleport at midpoint
        if self.state_timer >= TELEPORT_DURATION / 2:
            if action['teleport'] is None and self.teleport_destination:
                action['teleport'] = self.teleport_destination
                self.teleport_destination = None

        # Return to combat after teleport
        if self.state_timer >= TELEPORT_DURATION:
            phase_state = self._get_current_phase_state()
            self._transition_to_state(phase_state)

    def _update_dead(self, dt: float, action: dict):
        """Dead state - no behavior"""
        pass

    # ============================================================
    # Combat Logic
    # ============================================================

    def _execute_phase_combat(self, dt: float, action: dict, phase_mult: float):
        """
        Execute combat behavior for current phase.

        Args:
            dt: Delta time
            action: Action dict to populate
            phase_mult: Speed multiplier for this phase
        """
        # Check if should summon minions (phase 2+)
        if self.current_phase >= 2:
            if self.ai_random.random() < 0.05 * dt:  # 5% chance per second
                self._transition_to_state(BossAIState.SUMMONING)
                return

        # Check if should teleport (too close or too far)
        if self.teleport_cooldown <= 0:
            if self.player_distance < 50 or self.player_distance > 400:
                if self.ai_random.random() < 0.1 * dt:  # 10% chance per second
                    self._initiate_teleport()
                    return

        # Check if should use special attack
        if self.attack_cooldown <= 0:
            if self.ai_random.random() < 0.08 * dt:  # 8% chance per second
                self._transition_to_state(BossAIState.SPECIAL_ATTACK)
                return

        # Execute regular attack if in range and off cooldown
        if self.attack_cooldown <= 0:
            if self.player_distance <= MELEE_RANGE:
                # Melee attack
                action['damage'] = self._get_melee_damage()
                cooldown_mult = PHASE_3_ATTACK_SPEED_MULT if self.current_phase == 3 else 1.0
                self.attack_cooldown = self.attack_cooldown_base * cooldown_mult
                self.attacks_in_pattern += 1

                # After pattern completes, go to idle
                if self.attacks_in_pattern >= 3:
                    self.attacks_in_pattern = 0
                    self._transition_to_state(BossAIState.IDLE)

    # ============================================================
    # Helper Methods
    # ============================================================

    def _update_target(self, player_x: float, player_y: float,
                       player_width: int, player_height: int):
        """Update target position and distance"""
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        self.target_x = player_center_x
        self.target_y = player_center_y

        # Calculate distance to player
        boss_center_x, boss_center_y = self._get_boss_center()
        dx = player_center_x - boss_center_x
        dy = player_center_y - boss_center_y
        self.player_distance = math.sqrt(dx * dx + dy * dy)

    def _check_phase_transition(self):
        """Check if boss should transition to new phase based on health"""
        health_percent = self.boss.health / self.boss.max_health

        target_phase = 1
        if health_percent <= PHASE_3_HEALTH_THRESHOLD:
            target_phase = 3
        elif health_percent <= PHASE_2_HEALTH_THRESHOLD:
            target_phase = 2

        # Trigger phase transition if needed
        if target_phase > self.current_phase:
            self.current_phase = target_phase
            # Force transition to new phase state
            new_phase_state = self._get_current_phase_state()
            self._transition_to_state(new_phase_state)

    def _get_current_phase_state(self) -> BossAIState:
        """Get the state for the current phase"""
        if self.current_phase == 1:
            return BossAIState.PHASE_1
        elif self.current_phase == 2:
            return BossAIState.PHASE_2
        else:
            return BossAIState.PHASE_3

    def _transition_to_state(self, new_state: BossAIState):
        """Transition to a new AI state"""
        self.previous_state = self.state
        self.state = new_state
        self.state_timer = 0.0

    def _initiate_teleport(self):
        """Initiate teleportation to random position"""
        # Choose random teleport destination near player but not too close
        angle = self.ai_random.uniform(0, 2 * math.pi)
        distance = self.ai_random.uniform(TELEPORT_RANGE, TELEPORT_RANGE * 2)

        if self.target_x and self.target_y:
            dest_x = self.target_x + math.cos(angle) * distance
            dest_y = self.target_y + math.sin(angle) * distance
            self.teleport_destination = (dest_x, dest_y)
            self._transition_to_state(BossAIState.TELEPORTING)
            self.teleport_cooldown = 5.0  # 5 second cooldown

    def _choose_special_attack(self) -> str:
        """Choose which special attack to use"""
        specials = ['shockwave', 'laser_beam', 'ground_slam', 'projectile_barrage']
        return self.ai_random.choice(specials)

    def _choose_minion_type(self) -> str:
        """Choose which minion type to summon"""
        minions = ['imp', 'skeleton', 'ghost']
        return self.ai_random.choice(minions)

    def _get_melee_damage(self) -> int:
        """Get melee attack damage based on phase"""
        base_damage = 2
        if self.current_phase == 2:
            return base_damage + 1
        elif self.current_phase == 3:
            return base_damage + 2
        return base_damage

    def _get_boss_center(self) -> Tuple[float, float]:
        """Get boss center position"""
        return (
            self.boss.x + self.boss.width / 2,
            self.boss.y + self.boss.height / 2
        )

    def _get_varied_duration(self, base_duration: float, variation: float) -> float:
        """Get varied duration using AI random (for determinism)"""
        if not self.ai_random:
            return base_duration
        return self.ai_random.uniform(
            base_duration * (1 - variation),
            base_duration * (1 + variation)
        )

    # ============================================================
    # Public Interface
    # ============================================================

    def take_damage(self, damage: int) -> bool:
        """
        Boss takes damage. Returns True if this triggered phase transition.

        Args:
            damage: Damage amount

        Returns:
            True if phase transition occurred
        """
        old_phase = self.current_phase
        self.boss.health -= damage

        if self.boss.health <= 0:
            self.boss.health = 0
            self._transition_to_state(BossAIState.DEAD)
            return True

        self._check_phase_transition()
        return self.current_phase != old_phase

    def is_vulnerable(self) -> bool:
        """Check if boss is in vulnerable state"""
        return self.state == BossAIState.VULNERABLE

    def is_dead(self) -> bool:
        """Check if boss is dead"""
        return self.state == BossAIState.DEAD

    def get_state(self) -> BossAIState:
        """Get current AI state"""
        return self.state

    def get_phase(self) -> int:
        """Get current combat phase (1-3)"""
        return self.current_phase
