"""
Hazard Entities - Damage and death mechanics

Hazard types:
- Spikes: Contact damage
- Void/Pits: Instant death zones
- Future: Moving hazards, environmental hazards

Architecture:
- BaseHazard: Abstract base for all hazards
- HazardManager: Centralized hazard spawning and collision
- Events for damage/death
"""

import math
from dataclasses import dataclass
from typing import List, Optional
from core.event_bus import EventBus


@dataclass
class PlayerDamageEvent:
    """Event emitted when player takes damage"""
    player_id: int
    damage: int
    hazard_type: str
    position: tuple  # (x, y) of hazard


@dataclass
class PlayerDeathEvent:
    """Event emitted when player dies"""
    player_id: int
    death_type: str  # "spike", "void", "fall", etc.
    position: tuple  # (x, y) of player at death


class BaseHazard:
    """
    Abstract base class for all hazards

    All hazards have:
    - Position and size (collision box)
    - Damage amount (0 = instant death)
    - Active/inactive state
    - Collision detection
    """

    def __init__(self, x: float, y: float, width: int, height: int,
                 damage: int = 1, hazard_type: str = "generic"):
        """
        Initialize base hazard

        Args:
            x, y: World position (top-left corner)
            width, height: Collision box size
            damage: Damage dealt (0 = instant death)
            hazard_type: Type identifier for events
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.damage = damage
        self.hazard_type = hazard_type
        self.active = True

    def check_collision(self, entity_x: float, entity_y: float,
                       entity_width: int, entity_height: int) -> bool:
        """
        Check if entity collides with this hazard (AABB collision)

        Args:
            entity_x, entity_y: Entity top-left position
            entity_width, entity_height: Entity size

        Returns:
            True if collision detected
        """
        if not self.active:
            return False

        # AABB collision detection
        return (self.x < entity_x + entity_width and
                self.x + self.width > entity_x and
                self.y < entity_y + entity_height and
                self.y + self.height > entity_y)

    def get_render_position(self):
        """Get position for rendering (can be overridden for animations)"""
        return (self.x, self.y)


class SpikeHazard(BaseHazard):
    """
    Spike hazard - deals damage on contact

    Visual: Upward-pointing triangular spikes
    Size: 32x16 pixels (tile-sized)
    Damage: 1 heart
    """

    def __init__(self, x: float, y: float):
        """
        Create spike hazard at position

        Args:
            x, y: World position (bottom-left of spike base)
        """
        # Spikes are 32x16 (full tile width, half tile height)
        super().__init__(x, y - 16, 32, 16, damage=1, hazard_type="spike")
        self.color = (150, 150, 150)  # Gray spikes
        self.outline_color = (80, 80, 80)  # Dark outline


class VoidHazard(BaseHazard):
    """
    Void/pit hazard - instant death zone

    Visual: Invisible kill zone (or dark void area)
    Size: Variable (usually large areas)
    Damage: 0 (instant death)
    """

    def __init__(self, x: float, y: float, width: int, height: int):
        """
        Create void hazard zone

        Args:
            x, y: World position (top-left)
            width, height: Zone size
        """
        super().__init__(x, y, width, height, damage=0, hazard_type="void")
        self.color = (20, 10, 30)  # Dark purple void


class HazardManager:
    """
    Centralized hazard management system

    Responsibilities:
    - Hazard spawning
    - Collision detection
    - Damage/death event emission
    - Hazard cleanup
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize hazard manager

        Args:
            event_bus: Event bus for emitting damage/death events
        """
        self.event_bus = event_bus
        self.hazards: List[BaseHazard] = []

        # Statistics
        self.total_spikes = 0
        self.total_voids = 0
        self.total_poison = 0
        self.damage_dealt = 0
        self.deaths_caused = 0

    def spawn_spike(self, x: float, y: float) -> SpikeHazard:
        """
        Spawn spike hazard at position

        Args:
            x, y: World position (bottom-left of spike base)

        Returns:
            Created spike hazard
        """
        spike = SpikeHazard(x, y)
        self.hazards.append(spike)
        self.total_spikes += 1
        return spike

    def spawn_void(self, x: float, y: float, width: int, height: int) -> VoidHazard:
        """
        Spawn void/pit hazard zone

        Args:
            x, y: World position (top-left)
            width, height: Zone size

        Returns:
            Created void hazard
        """
        void = VoidHazard(x, y, width, height)
        self.hazards.append(void)
        self.total_voids += 1
        return void

    def spawn_poison(self, x: float, y: float, width: int, height: int) -> BaseHazard:
        """
        Spawn poison/gas hazard zone that can be cleared by Purify ninjutsu.
        """
        poison = BaseHazard(x, y, width, height, damage=1, hazard_type="poison")
        self.hazards.append(poison)
        self.total_poison += 1
        return poison

    def check_hazards(self, player_state, invincible: bool = False) -> Optional[tuple]:
        """
        Check if player is colliding with any hazards

        Args:
            player_state: Player state with physics data
            invincible: Whether player is currently invincible

        Returns:
            (hazard, damage) tuple if collision, None otherwise
        """
        if invincible:
            return None

        player_x = player_state.physics.x
        player_y = player_state.physics.y
        player_width = player_state.physics.width
        player_height = player_state.physics.height

        for hazard in self.hazards:
            if hazard.check_collision(player_x, player_y, player_width, player_height):
                # Return first collision (hazards don't stack damage)
                return (hazard, hazard.damage)

        return None

    def apply_damage(self, player_id: int, player_state, hazard: BaseHazard) -> bool:
        """
        Apply hazard damage to player and emit events

        Args:
            player_id: Player ID
            player_state: Player state to modify
            hazard: Hazard that caused damage

        Returns:
            True if player died, False if still alive
        """
        player_pos = (player_state.physics.x, player_state.physics.y)

        # Instant death hazards (damage = 0)
        if hazard.damage == 0:
            player_state.health_state.current_hp = 0
            self.deaths_caused += 1

            # Emit death event
            event = PlayerDeathEvent(
                player_id=player_id,
                death_type=hazard.hazard_type,
                position=player_pos
            )
            self.event_bus.emit(event)
            return True

        # Regular damage - use HealthState.take_damage() for proper invincibility handling
        old_hp = player_state.health_state.current_hp
        died = player_state.health_state.take_damage(hazard.damage, defense=0)

        # Track damage if it was actually applied (not blocked by invincibility)
        damage_applied = old_hp - player_state.health_state.current_hp
        if damage_applied > 0:
            self.damage_dealt += damage_applied

        # Emit damage event
        event = PlayerDamageEvent(
            player_id=player_id,
            damage=hazard.damage,
            hazard_type=hazard.hazard_type,
            position=(hazard.x, hazard.y)
        )
        self.event_bus.emit(event)

        # Check if damage killed player
        if died:
            self.deaths_caused += 1

            death_event = PlayerDeathEvent(
                player_id=player_id,
                death_type=f"{hazard.hazard_type}_death",
                position=player_pos
            )
            self.event_bus.emit(death_event)
            return True

        return False

    def get_active_hazards(self) -> List[BaseHazard]:
        """Get list of active hazards for rendering"""
        return [h for h in self.hazards if h.active]

    def clear_poison_area(self, x: float, y: float, radius: float):
        """
        Permanently deactivate poison/gas hazards within radius.
        """
        for hazard in self.hazards:
            if not hazard.active:
                continue
            if hazard.hazard_type != "poison":
                continue
            hx = hazard.x + hazard.width / 2
            hy = hazard.y + hazard.height / 2
            dx = hx - x
            dy = hy - y
            if (dx * dx + dy * dy) ** 0.5 <= radius:
                hazard.active = False

    def clear_all(self):
        """Remove all hazards"""
        self.hazards.clear()
        self.total_spikes = 0
        self.total_voids = 0
        self.total_poison = 0

    def get_stats(self):
        """Get hazard statistics"""
        return {
            "total_spikes": self.total_spikes,
            "total_voids": self.total_voids,
            "total_poison": self.total_poison,
            "active_hazards": len(self.get_active_hazards()),
            "damage_dealt": self.damage_dealt,
            "deaths_caused": self.deaths_caused
        }
