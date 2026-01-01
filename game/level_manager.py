"""
Level Manager - Exit Detection & Level Completion

Manages level state, exit detection, and level completion tracking.
"""

import math
from dataclasses import dataclass
from typing import Any

from core.event_bus import EventBus


@dataclass
class LevelState:
    """State for current level"""

    level_complete: bool = False
    exit_pos: tuple[float, float] | None = None
    spawn_pos: tuple[float, float] | None = None
    completion_time: float = 0.0
    collectibles_found: int = 0
    collectibles_total: int = 0
    deaths: int = 0
    exit_locked: bool = False  # For mission mode - exit locked until objectives complete


class LevelCompletionEvent:
    """Event emitted when level is completed"""

    def __init__(self, completion_time: float, collectibles: int, deaths: int):
        self.completion_time = completion_time
        self.collectibles = collectibles
        self.deaths = deaths


class LevelManager:
    """
    Manages level state and completion logic.

    Responsibilities:
    - Track exit position
    - Detect when player reaches exit
    - Emit level completion events
    - Track level statistics
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.state = LevelState()
        self.exit_detection_radius = 32  # Pixels - one tile
        self.level_start_time = 0.0

    def set_exit_position(self, x: float, y: float):
        """Set the exit anchor position"""
        self.state.exit_pos = (x, y)

    def set_spawn_position(self, x: float, y: float):
        """Set the spawn anchor position"""
        self.state.spawn_pos = (x, y)

    def start_level(self, current_time: float):
        """Start level timer"""
        self.level_start_time = current_time
        self.state.level_complete = False
        self.state.completion_time = 0.0

    def check_exit_reached(self, player_x: float, player_y: float, current_time: float) -> bool:
        """
        Check if player has reached the exit.

        Args:
            player_x: Player x position (center)
            player_y: Player y position (center)
            current_time: Current game time in seconds

        Returns:
            True if player reached exit and level just completed
        """
        if self.state.level_complete:
            return False  # Already complete

        if self.state.exit_pos is None:
            return False  # No exit set

        # Check if exit is locked (mission mode)
        if self.state.exit_locked:
            return False  # Exit locked until objectives complete

        exit_x, exit_y = self.state.exit_pos

        # Calculate distance to exit
        distance = math.sqrt((player_x - exit_x) ** 2 + (player_y - exit_y) ** 2)

        # Check if within detection radius
        if distance < self.exit_detection_radius:
            # Level complete!
            self.state.level_complete = True
            self.state.completion_time = current_time - self.level_start_time

            # Emit completion event
            completion_event = LevelCompletionEvent(
                completion_time=self.state.completion_time,
                collectibles=self.state.collectibles_found,
                deaths=self.state.deaths,
            )
            self.event_bus.emit(completion_event)

            return True

        return False

    def lock_exit(self):
        """
        Lock the exit portal (mission mode).

        Exit will be locked until objectives are complete.
        """
        self.state.exit_locked = True

    def unlock_exit(self):
        """
        Unlock the exit portal (mission mode).

        Called when all objectives are complete.
        """
        self.state.exit_locked = False

    def is_exit_locked(self) -> bool:
        """Check if exit is currently locked"""
        return self.state.exit_locked

    def reset_level(self):
        """Reset level state for new level"""
        self.state = LevelState()

    def increment_deaths(self):
        """Track player death"""
        self.state.deaths += 1

    def add_collectible(self):
        """Track collectible found"""
        self.state.collectibles_found += 1

    def set_total_collectibles(self, total: int):
        """Set total collectibles in level"""
        self.state.collectibles_total = total

    def get_stats(self) -> dict[str, Any]:
        """Get current level statistics"""
        return {
            "complete": self.state.level_complete,
            "time": self.state.completion_time,
            "collectibles": f"{self.state.collectibles_found}/{self.state.collectibles_total}",
            "deaths": self.state.deaths,
            "exit_locked": self.state.exit_locked,
        }
