"""
Damage Mechanic - Handles health, damage, invincibility, and death

Responsibilities:
- Apply damage to player
- Track invincibility frames (i-frames)
- Emit death events
- Health regeneration (optional)

Architecture:
- Subscribes to TickEvent for i-frame countdown
- Provides take_damage() for external systems
- Manages invincibility_time in PlayerState
"""

import logging

from core.event_bus import EventBus, TickEvent
from core.state import PlayerState
from entities.hazards import PlayerDamageEvent, PlayerDeathEvent


class DamageMechanic:
    """
    Damage and invincibility mechanic

    Features:
    - Damage application with i-frames
    - Invincibility timer countdown
    - Death detection
    - Event emission

    Usage:
        damage_mech = DamageMechanic(player_id=0, event_bus=bus)
        damage_mech.take_damage(player_state, amount=1, source="spike")
    """

    # Invincibility duration after taking damage (seconds)
    INVINCIBILITY_DURATION = 1.5  # 1.5 seconds of i-frames

    def __init__(self, entity_id: int, event_bus: EventBus, logger: logging.Logger = None):
        """
        Initialize damage mechanic

        Args:
            entity_id: Player/entity ID
            event_bus: Event bus for subscribing/emitting
            logger: Logger instance
        """
        self.entity_id = entity_id
        self.event_bus = event_bus
        self.logger = logger

        # Subscribe to tick events for i-frame countdown
        self.event_bus.subscribe(TickEvent, self._on_tick)

        # Statistics
        self.total_damage_taken = 0
        self.times_damaged = 0
        self.deaths = 0

        if self.logger:
            self.logger.info(f"DamageMechanic initialized (entity={entity_id})")

    def _on_tick(self, event: TickEvent):
        """
        Update invincibility timer

        Args:
            event: Tick event with dt
        """
        # Handled by state update in take_damage
        pass

    def is_invincible(self, state: PlayerState) -> bool:
        """
        Check if player is currently invincible

        Args:
            state: Player state

        Returns:
            True if player has active i-frames
        """
        return state.health_state.is_invincible()

    def update_invincibility(self, state: PlayerState, dt: float):
        """
        Update invincibility timer (call this each frame)

        Args:
            state: Player state to update
            dt: Delta time in seconds
        """
        # Convert dt to frames (assuming 60fps) and update invincibility frames
        # HealthState.update() decrements by 1 frame per call
        frames_to_decrement = int(dt * 60)
        for _ in range(frames_to_decrement):
            state.health_state.update()

    def take_damage(
        self,
        state: PlayerState,
        amount: int,
        source: str = "unknown",
        source_pos: tuple = (0, 0),
        force: bool = False,
    ) -> bool:
        """
        Apply damage to player

        Args:
            state: Player state to modify
            amount: Damage amount (hearts)
            source: Damage source identifier
            source_pos: Position of damage source
            force: Ignore invincibility (for instant death)

        Returns:
            True if player died, False otherwise
        """
        # Check invincibility (unless forced)
        if not force and self.is_invincible(state):
            return False

        # Apply damage using HealthState (returns True if died)
        old_hp = state.health_state.current_hp
        died = state.health_state.take_damage(amount, defense=0)

        # Only count damage if it was actually applied
        if state.health_state.current_hp < old_hp:
            self.total_damage_taken += amount
            self.times_damaged += 1

        # Emit damage event
        damage_event = PlayerDamageEvent(
            player_id=self.entity_id, damage=amount, hazard_type=source, position=source_pos
        )
        self.event_bus.emit(damage_event)

        # Check for death
        if died:
            self.deaths += 1

            # Emit death event
            death_event = PlayerDeathEvent(
                player_id=self.entity_id,
                death_type=source,
                position=(state.physics.x, state.physics.y),
            )
            self.event_bus.emit(death_event)

            if self.logger:
                self.logger.info(f"Player {self.entity_id} died from {source}")

            return True

        if self.logger:
            self.logger.debug(
                f"Player {self.entity_id} took {amount} damage from {source} "
                f"(health: {state.health_state.current_hp}/{state.health_state.max_hp})"
            )

        return False

    def instant_death(self, state: PlayerState, source: str = "void") -> bool:
        """
        Instantly kill player (ignores invincibility)

        Args:
            state: Player state
            source: Death source identifier

        Returns:
            True (always kills)
        """
        state.health_state.current_hp = 0
        self.deaths += 1

        # Emit death event
        death_event = PlayerDeathEvent(
            player_id=self.entity_id, death_type=source, position=(state.physics.x, state.physics.y)
        )
        self.event_bus.emit(death_event)

        if self.logger:
            self.logger.info(f"Player {self.entity_id} died instantly from {source}")

        return True

    def heal(self, state: PlayerState, amount: int):
        """
        Heal player (restore health)

        Args:
            state: Player state to modify
            amount: Health to restore
        """
        old_health = state.health_state.current_hp
        state.health_state.heal(amount)

        if self.logger and state.health_state.current_hp > old_health:
            self.logger.debug(
                f"Player {self.entity_id} healed {state.health_state.current_hp - old_health} "
                f"(health: {state.health_state.current_hp}/{state.health_state.max_hp})"
            )

    def respawn(self, state: PlayerState, spawn_x: float, spawn_y: float):
        """
        Respawn player at position (full health, clear velocity)

        Args:
            state: Player state to reset
            spawn_x, spawn_y: Respawn position
        """
        # Reset health
        state.health_state.current_hp = state.health_state.max_hp

        # Reset position
        state.physics.x = spawn_x
        state.physics.y = spawn_y

        # Clear velocity
        state.physics.vx = 0
        state.physics.vy = 0

        # Grant brief invincibility on spawn (2 seconds = 120 frames at 60fps)
        state.health_state.invincibility_frames = 120

        if self.logger:
            self.logger.info(f"Player {self.entity_id} respawned at ({spawn_x:.0f}, {spawn_y:.0f})")

    def get_stats(self):
        """Get damage statistics"""
        return {
            "total_damage_taken": self.total_damage_taken,
            "times_damaged": self.times_damaged,
            "deaths": self.deaths,
        }

    def cleanup(self):
        """Unsubscribe from events"""
        self.event_bus.unsubscribe(TickEvent, self._on_tick)
