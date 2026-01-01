"""
Scripted Events System - Handle predetermined story outcomes

Manages scripted battles, cutscene triggers, and forced narrative moments.

Key Features:
- Scripted defeat battles (player cannot win)
- Cutscene triggers based on battle state
- Story event management
- Transition to special zones

Version: v0.7.0
"""

from collections.abc import Callable
from enum import Enum
from typing import Any


class ScriptedEventType(Enum):
    """Types of scripted events"""

    SCRIPTED_DEFEAT = "scripted_defeat"  # Player must lose
    SCRIPTED_VICTORY = "scripted_victory"  # Player must win
    CUTSCENE_TRIGGER = "cutscene_trigger"  # Trigger cutscene
    ZONE_TRANSITION = "zone_transition"  # Force zone change


class ScriptedBattleState(Enum):
    """State of a scripted battle"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    TRIGGERED = "triggered"  # Scripted event triggered
    COMPLETED = "completed"


class ScriptedBattle:
    """
    Manages a boss fight with a predetermined outcome.

    Used for story-critical battles where the player must lose or win
    regardless of their performance.
    """

    def __init__(
        self, boss_id: str, player_must_lose: bool = False, trigger_threshold: float = 0.3
    ):
        """
        Initialize scripted battle.

        Args:
            boss_id: ID of the boss
            player_must_lose: If True, player cannot win this fight
            trigger_threshold: HP ratio to trigger scripted event (0.0-1.0)
        """
        self.boss_id = boss_id
        self.player_must_lose = player_must_lose
        self.trigger_threshold = trigger_threshold

        self.state = ScriptedBattleState.NOT_STARTED
        self.triggered = False

        # Callbacks
        self.on_trigger_callback: Callable | None = None
        self.on_complete_callback: Callable | None = None

    def start_battle(self):
        """Mark battle as started."""
        self.state = ScriptedBattleState.IN_PROGRESS
        self.triggered = False

    def check_battle_state(
        self, player_hp: float, player_max_hp: float, boss_hp: float, boss_max_hp: float
    ) -> str | None:
        """
        Check if scripted event should trigger.

        Args:
            player_hp: Current player HP
            player_max_hp: Maximum player HP
            boss_hp: Current boss HP
            boss_max_hp: Maximum boss HP

        Returns:
            Event type if triggered, None otherwise
        """
        if self.state != ScriptedBattleState.IN_PROGRESS:
            return None

        # Calculate HP ratios
        player_hp_ratio = player_hp / max(player_max_hp, 1)
        boss_hp_ratio = boss_hp / max(boss_max_hp, 1)

        # Scripted defeat: Player must lose
        if self.player_must_lose:
            # Trigger when boss HP drops below threshold
            if boss_hp_ratio <= self.trigger_threshold and not self.triggered:
                return self._trigger_defeat()

            # Also trigger if player dies normally
            if player_hp <= 0 and not self.triggered:
                return self._trigger_defeat()

        return None

    def _trigger_defeat(self) -> str:
        """
        Trigger scripted defeat event.

        Returns:
            Event type string
        """
        self.triggered = True
        self.state = ScriptedBattleState.TRIGGERED

        if self.on_trigger_callback:
            self.on_trigger_callback()

        return "scripted_defeat"

    def complete_battle(self):
        """Mark battle as completed."""
        self.state = ScriptedBattleState.COMPLETED

        if self.on_complete_callback:
            self.on_complete_callback()

    def is_active(self) -> bool:
        """Check if battle is currently active."""
        return self.state == ScriptedBattleState.IN_PROGRESS

    def has_triggered(self) -> bool:
        """Check if scripted event has been triggered."""
        return self.triggered


class ScriptedEventManager:
    """
    Manages all scripted events in the game.

    Coordinates scripted battles, cutscenes, and story transitions.
    """

    def __init__(self):
        """Initialize scripted event manager."""
        # Active scripted battles
        self.active_scripted_battles: dict[str, ScriptedBattle] = {}

        # Event callbacks
        self.event_callbacks: dict[str, Callable] = {}

        # Current active event
        self.current_event: str | None = None

    def register_scripted_battle(
        self,
        mission_id: str,
        boss_id: str,
        player_must_lose: bool = False,
        trigger_threshold: float = 0.3,
    ) -> ScriptedBattle:
        """
        Register a scripted battle for a mission.

        Args:
            mission_id: Mission ID
            boss_id: Boss ID
            player_must_lose: Whether player must lose
            trigger_threshold: HP threshold to trigger event

        Returns:
            ScriptedBattle instance
        """
        battle = ScriptedBattle(boss_id, player_must_lose, trigger_threshold)
        self.active_scripted_battles[mission_id] = battle
        return battle

    def start_scripted_battle(self, mission_id: str) -> bool:
        """
        Start a scripted battle.

        Args:
            mission_id: Mission ID

        Returns:
            True if battle started, False if no scripted battle for mission
        """
        if mission_id in self.active_scripted_battles:
            self.active_scripted_battles[mission_id].start_battle()
            return True
        return False

    def check_scripted_battle(
        self,
        mission_id: str,
        player_hp: float,
        player_max_hp: float,
        boss_hp: float,
        boss_max_hp: float,
    ) -> str | None:
        """
        Check if scripted battle event should trigger.

        Args:
            mission_id: Current mission ID
            player_hp: Player HP
            player_max_hp: Player max HP
            boss_hp: Boss HP
            boss_max_hp: Boss max HP

        Returns:
            Event type if triggered, None otherwise
        """
        if mission_id not in self.active_scripted_battles:
            return None

        battle = self.active_scripted_battles[mission_id]
        event = battle.check_battle_state(player_hp, player_max_hp, boss_hp, boss_max_hp)

        if event:
            self.current_event = event

            # Trigger registered callback
            if event in self.event_callbacks:
                self.event_callbacks[event](mission_id)

        return event

    def complete_scripted_battle(self, mission_id: str):
        """
        Complete a scripted battle.

        Args:
            mission_id: Mission ID
        """
        if mission_id in self.active_scripted_battles:
            self.active_scripted_battles[mission_id].complete_battle()
            del self.active_scripted_battles[mission_id]

    def register_event_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for an event type.

        Args:
            event_type: Event type (e.g., "scripted_defeat")
            callback: Callback function (receives mission_id)
        """
        self.event_callbacks[event_type] = callback

    def is_scripted_battle_active(self, mission_id: str) -> bool:
        """
        Check if mission has an active scripted battle.

        Args:
            mission_id: Mission ID

        Returns:
            True if scripted battle is active
        """
        if mission_id not in self.active_scripted_battles:
            return False
        return self.active_scripted_battles[mission_id].is_active()

    def clear_current_event(self):
        """Clear the current active event."""
        self.current_event = None

    def get_current_event(self) -> str | None:
        """Get the current active event type."""
        return self.current_event


# ============================================================
# Veil Maiden Scripted Defeat Configuration
# ============================================================


def create_veil_maiden_scripted_defeat(
    event_manager: ScriptedEventManager, on_defeat_callback: Callable | None = None
):
    """
    Create the Veil Maiden scripted defeat battle for caves_1.

    Args:
        event_manager: ScriptedEventManager instance
        on_defeat_callback: Callback when defeat triggers
    """
    # Register scripted battle for caves_1
    battle = event_manager.register_scripted_battle(
        mission_id="caves_1",
        boss_id="veil_maiden",
        player_must_lose=True,
        trigger_threshold=0.25,  # Trigger at 25% boss HP
    )

    # Set callback
    if on_defeat_callback:
        battle.on_trigger_callback = on_defeat_callback

    return battle


# ============================================================
# Helper Functions
# ============================================================


def get_scripted_defeat_data() -> dict[str, Any]:
    """
    Get data for Veil Maiden scripted defeat event.

    Returns:
        Dictionary with cutscene and transition data
    """
    return {
        "mission_id": "caves_1",
        "boss_id": "veil_maiden",
        "cutscene_id": "veil_maiden_defeat",
        "cutscene_text": [
            "The Veil Maiden's power overwhelms you...",
            "Your vision fades as darkness consumes the light...",
            "Yin and Yang's gentle glow vanishes into the void...",
            "You feel yourself falling... falling into emptiness...",
        ],
        "transition_zone": "hollow_depths",
        "player_effects": {
            "hp_set": 1,  # Leave player at 1 HP
            "yin_yang_consumed": True,
            "debuff": "weakened",  # Optional gameplay debuff
        },
        "story_flags": {
            "act": 2,  # Transition to Act 2
            "veil_maiden_defeated_player": True,
            "companions_lost": True,
        },
    }
