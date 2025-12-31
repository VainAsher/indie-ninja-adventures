"""
Mission Manager - Mission State Management for Campaign Mode

This module manages mission lifecycle:
- Mission state tracking (not started, in progress, completed, failed)
- Mission start/complete/fail flow
- Progress tracking (attempts, best time)
- Reward distribution
- Exit portal lock/unlock
- Integration with objective tracker

Version: v0.6.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import time

from game.mission_registry import (
    MissionDefinition, get_mission_registry
)
from game.inventory_system import Inventory
from core import EventBus


# ============================================================
# Mission State
# ============================================================

class MissionState(Enum):
    """Mission completion states"""
    NOT_STARTED = "not_started"  # Never attempted
    AVAILABLE = "available"      # Unlocked but not started
    IN_PROGRESS = "in_progress"  # Currently active
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Failed (death or other failure)


@dataclass
class MissionProgress:
    """
    Progress tracking for a mission.

    Tracks attempts, completion status, and best performance.
    """
    mission_id: str
    state: MissionState = MissionState.NOT_STARTED
    attempts: int = 0
    completions: int = 0
    best_time_seconds: Optional[float] = None
    last_attempt_time: Optional[float] = None

    # Current attempt tracking
    current_attempt_start_time: Optional[float] = None
    objectives_completed: List[str] = field(default_factory=list)

    def start_attempt(self):
        """Start a new mission attempt"""
        self.state = MissionState.IN_PROGRESS
        self.attempts += 1
        self.current_attempt_start_time = time.time()
        self.objectives_completed.clear()

    def complete_mission(self) -> float:
        """
        Complete mission and return completion time.

        Returns:
            Completion time in seconds
        """
        self.state = MissionState.COMPLETED
        self.completions += 1

        # Calculate completion time
        completion_time = 0.0
        if self.current_attempt_start_time is not None:
            completion_time = time.time() - self.current_attempt_start_time

        # Update best time
        if self.best_time_seconds is None or completion_time < self.best_time_seconds:
            self.best_time_seconds = completion_time

        self.last_attempt_time = completion_time
        self.current_attempt_start_time = None

        return completion_time

    def fail_mission(self):
        """Fail current mission attempt"""
        self.state = MissionState.FAILED
        self.current_attempt_start_time = None
        self.objectives_completed.clear()

    def reset_for_retry(self):
        """Reset state for retry (after failure)"""
        self.state = MissionState.AVAILABLE
        self.objectives_completed.clear()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            'mission_id': self.mission_id,
            'state': self.state.value,
            'attempts': self.attempts,
            'completions': self.completions,
            'best_time_seconds': self.best_time_seconds,
            'last_attempt_time': self.last_attempt_time,
            'objectives_completed': self.objectives_completed
        }

    @staticmethod
    def from_dict(data: dict) -> 'MissionProgress':
        """Deserialize from dictionary"""
        return MissionProgress(
            mission_id=data['mission_id'],
            state=MissionState(data.get('state', 'not_started')),
            attempts=data.get('attempts', 0),
            completions=data.get('completions', 0),
            best_time_seconds=data.get('best_time_seconds'),
            last_attempt_time=data.get('last_attempt_time'),
            objectives_completed=data.get('objectives_completed', [])
        )


# ============================================================
# Mission Events
# ============================================================

@dataclass
class MissionStartEvent:
    """Event emitted when mission starts"""
    mission_id: str
    mission_definition: MissionDefinition


@dataclass
class MissionCompleteEvent:
    """Event emitted when mission completes"""
    mission_id: str
    completion_time: float
    rewards: Dict[str, any]  # Contains items, currency, abilities


@dataclass
class MissionFailEvent:
    """Event emitted when mission fails"""
    mission_id: str
    reason: str  # "death", "timeout", "objective_failed"


@dataclass
class ObjectiveCompleteEvent:
    """Event emitted when single objective completes"""
    mission_id: str
    objective_id: str
    objective_description: str


@dataclass
class AllObjectivesCompleteEvent:
    """Event emitted when all objectives complete (exit unlocked)"""
    mission_id: str


@dataclass
class ExitLockedEvent:
    """Event emitted when exit portal is locked"""
    mission_id: str


@dataclass
class ExitUnlockedEvent:
    """Event emitted when exit portal is unlocked"""
    mission_id: str


# ============================================================
# Mission Manager
# ============================================================

class MissionManager:
    """
    Manages mission lifecycle and state.

    Handles mission start/complete/fail, progress tracking,
    reward distribution, and exit portal control.
    """

    def __init__(self, event_bus: EventBus, world_seed: int):
        """
        Initialize mission manager.

        Args:
            event_bus: Event bus for emitting events
            world_seed: World seed for deterministic rewards
        """
        self.event_bus = event_bus
        self.world_seed = world_seed

        # Mission progress tracking
        self.mission_progress: Dict[str, MissionProgress] = {}

        # Current active mission
        self.current_mission_id: Optional[str] = None
        self.exit_locked: bool = False

        # Mission registry reference
        self.mission_registry = get_mission_registry()

    def get_mission_progress(self, mission_id: str) -> MissionProgress:
        """
        Get or create mission progress.

        Args:
            mission_id: Mission identifier

        Returns:
            MissionProgress instance
        """
        if mission_id not in self.mission_progress:
            self.mission_progress[mission_id] = MissionProgress(mission_id=mission_id)
        return self.mission_progress[mission_id]

    def is_mission_available(self, mission_id: str, unlocked_abilities: set) -> bool:
        """
        Check if mission is available to start.

        Args:
            mission_id: Mission identifier
            unlocked_abilities: Player's unlocked abilities

        Returns:
            True if mission can be started
        """
        completed_missions = {
            mid for mid, progress in self.mission_progress.items()
            if progress.state == MissionState.COMPLETED
        }
        return self.mission_registry.is_mission_unlocked(
            mission_id,
            unlocked_abilities,
            completed_missions
        )

    def start_mission(self, mission_id: str) -> bool:
        """
        Start a mission.

        Args:
            mission_id: Mission identifier

        Returns:
            True if mission started successfully
        """
        # Get mission definition
        mission_def = self.mission_registry.get_mission(mission_id)
        if mission_def is None:
            print(f"[ERROR] Mission not found: {mission_id}")
            return False

        # Get or create progress
        progress = self.get_mission_progress(mission_id)

        # Start attempt
        progress.start_attempt()

        # Set as current mission
        self.current_mission_id = mission_id

        # Lock exit portal
        self.exit_locked = True

        # Emit events
        self.event_bus.emit(MissionStartEvent(
            mission_id=mission_id,
            mission_definition=mission_def
        ))

        self.event_bus.emit(ExitLockedEvent(mission_id=mission_id))

        print(f"[MISSION] Started: {mission_def.mission_name}")
        print(f"[MISSION] Objectives: {len(mission_def.objectives)}")

        return True

    def complete_objective(self, mission_id: str, objective_id: str,
                          objective_description: str):
        """
        Mark an objective as complete.

        Args:
            mission_id: Mission identifier
            objective_id: Objective identifier
            objective_description: Objective description for UI
        """
        if mission_id != self.current_mission_id:
            return

        progress = self.get_mission_progress(mission_id)

        # Add to completed objectives
        if objective_id not in progress.objectives_completed:
            progress.objectives_completed.append(objective_id)

            # Emit objective complete event
            self.event_bus.emit(ObjectiveCompleteEvent(
                mission_id=mission_id,
                objective_id=objective_id,
                objective_description=objective_description
            ))

            print(f"[OBJECTIVE] Completed: {objective_description}")

    def check_all_objectives_complete(self, mission_id: str) -> bool:
        """
        Check if all objectives are complete.

        Args:
            mission_id: Mission identifier

        Returns:
            True if all objectives complete
        """
        mission_def = self.mission_registry.get_mission(mission_id)
        if mission_def is None:
            return False

        progress = self.get_mission_progress(mission_id)

        # Check if all objectives completed
        required_objective_count = len(mission_def.objectives)
        completed_objective_count = len(progress.objectives_completed)

        return completed_objective_count >= required_objective_count

    def unlock_exit(self, mission_id: str):
        """
        Unlock exit portal.

        Args:
            mission_id: Mission identifier
        """
        if mission_id != self.current_mission_id:
            return

        if self.exit_locked:
            self.exit_locked = False

            # Emit events
            self.event_bus.emit(AllObjectivesCompleteEvent(mission_id=mission_id))
            self.event_bus.emit(ExitUnlockedEvent(mission_id=mission_id))

            print(f"[MISSION] Exit unlocked! Head to the exit portal.")

    def complete_mission(self, mission_id: str, player_inventory: Inventory) -> bool:
        """
        Complete mission and distribute rewards.

        Args:
            mission_id: Mission identifier
            player_inventory: Player's inventory for rewards

        Returns:
            True if mission completed successfully
        """
        if mission_id != self.current_mission_id:
            print(f"[ERROR] Cannot complete mission {mission_id} - not current mission")
            return False

        # Get mission definition
        mission_def = self.mission_registry.get_mission(mission_id)
        if mission_def is None:
            return False

        # Get progress
        progress = self.get_mission_progress(mission_id)

        # Complete mission and get time
        completion_time = progress.complete_mission()

        # Distribute rewards
        rewards = self._distribute_rewards(mission_def, player_inventory)

        # Unlock exit (if not already)
        self.exit_locked = False

        # Clear current mission
        self.current_mission_id = None

        # Emit completion event
        self.event_bus.emit(MissionCompleteEvent(
            mission_id=mission_id,
            completion_time=completion_time,
            rewards=rewards
        ))

        print(f"[MISSION] Completed: {mission_def.mission_name}")
        print(f"[MISSION] Time: {completion_time:.1f}s")
        print(f"[MISSION] Rewards: {rewards}")

        return True

    def _distribute_rewards(self, mission_def: MissionDefinition,
                           player_inventory: Inventory) -> Dict[str, any]:
        """
        Distribute mission rewards to player.

        Args:
            mission_def: Mission definition
            player_inventory: Player's inventory

        Returns:
            Dictionary of distributed rewards
        """
        rewards = {
            'items': [],
            'currency': 0,
            'abilities': []
        }

        # Currency reward
        if mission_def.rewards and mission_def.rewards.currency > 0:
            player_inventory.add_currency(mission_def.rewards.currency)
            rewards['currency'] = mission_def.rewards.currency

        # Direct item rewards (JSON supports dicts or plain IDs)
        if mission_def.rewards:
            for reward_item in mission_def.rewards.items:
                if isinstance(reward_item, str):
                    item_id = reward_item
                    quantity = 1
                elif isinstance(reward_item, dict):
                    item_id = reward_item.get("id") or reward_item.get("item_id")
                    quantity = reward_item.get("quantity", 1)
                else:
                    continue

                if item_id:
                    player_inventory.add_item(item_id, quantity)
                    rewards['items'].append((item_id, quantity))

        # Ability unlocks
        rewards['abilities'] = mission_def.unlock_abilities.copy()

        return rewards

    def fail_mission(self, mission_id: str, reason: str = "death") -> bool:
        """
        Fail current mission.

        Args:
            mission_id: Mission identifier
            reason: Failure reason ("death", "timeout", "objective_failed")

        Returns:
            True if mission failed successfully
        """
        if mission_id != self.current_mission_id:
            return False

        # Get progress
        progress = self.get_mission_progress(mission_id)

        # Fail mission
        progress.fail_mission()

        # Reset for retry
        progress.reset_for_retry()

        # Unlock exit (allow return to hub)
        self.exit_locked = False

        # Clear current mission
        self.current_mission_id = None

        # Emit failure event
        self.event_bus.emit(MissionFailEvent(
            mission_id=mission_id,
            reason=reason
        ))

        print(f"[MISSION] Failed: {reason}")

        return True

    def is_exit_locked(self) -> bool:
        """Check if exit portal is locked"""
        return self.exit_locked

    def get_current_mission(self) -> Optional[MissionDefinition]:
        """Get current active mission definition"""
        if self.current_mission_id is None:
            return None
        return self.mission_registry.get_mission(self.current_mission_id)

    def get_mission_stats(self, mission_id: str) -> Optional[MissionProgress]:
        """Get mission statistics"""
        return self.mission_progress.get(mission_id)

    def save_state(self) -> dict:
        """Save mission manager state"""
        return {
            'mission_progress': {
                mission_id: progress.to_dict()
                for mission_id, progress in self.mission_progress.items()
            },
            'current_mission_id': self.current_mission_id,
            'exit_locked': self.exit_locked
        }

    def load_state(self, data: dict):
        """Load mission manager state"""
        # Load mission progress
        self.mission_progress.clear()
        for mission_id, progress_data in data.get('mission_progress', {}).items():
            self.mission_progress[mission_id] = MissionProgress.from_dict(progress_data)

        # Load current mission
        self.current_mission_id = data.get('current_mission_id')
        self.exit_locked = data.get('exit_locked', False)


# ============================================================
# Global Mission Manager Instance
# ============================================================

_mission_manager: Optional[MissionManager] = None


def initialize_mission_manager(event_bus: EventBus, world_seed: int):
    """Initialize the global mission manager"""
    global _mission_manager
    _mission_manager = MissionManager(event_bus, world_seed)


def get_mission_manager() -> Optional[MissionManager]:
    """Get the global mission manager instance"""
    return _mission_manager
