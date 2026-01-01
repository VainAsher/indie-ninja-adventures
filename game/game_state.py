"""
Game State Management - Handles different game states

States:
- MENU: Main menu (game not started)
- PLAYING: Active gameplay
- PAUSED: Game paused
- DIALOGUE: NPC conversation active
- MISSION_MENU: Mission selection menu open
- SHOP: Shop interface open
- VICTORY: Level completed (victory screen showing)

Architecture:
- GameState enum for state identification
- GameStateManager for state transitions and tracking
"""

from dataclasses import dataclass
from enum import Enum


class GameState(Enum):
    """Game state enumeration"""

    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    DIALOGUE = "dialogue"
    MISSION_MENU = "mission_menu"
    SHOP = "shop"
    VICTORY = "victory"


@dataclass
class GameStateData:
    """Data associated with current game state"""

    current_state: GameState
    previous_state: GameState | None = None
    state_time: float = 0.0  # Time spent in current state


class GameStateManager:
    """
    Manages game state transitions

    Features:
    - State tracking
    - Transition validation
    - State history
    """

    def __init__(self, initial_state: GameState = GameState.MENU):
        """
        Initialize game state manager

        Args:
            initial_state: Starting game state
        """
        self.data = GameStateData(current_state=initial_state)
        self.state_history = [initial_state]

    def get_state(self) -> GameState:
        """Get current game state"""
        return self.data.current_state

    def is_state(self, state: GameState) -> bool:
        """Check if current state matches given state"""
        return self.data.current_state == state

    def is_playing(self) -> bool:
        """Check if currently playing (not menu or paused)"""
        return self.data.current_state == GameState.PLAYING

    def is_paused(self) -> bool:
        """Check if game is paused"""
        return self.data.current_state == GameState.PAUSED

    def is_menu(self) -> bool:
        """Check if in menu"""
        return self.data.current_state == GameState.MENU

    def is_victory(self) -> bool:
        """Check if showing victory screen"""
        return self.data.current_state == GameState.VICTORY

    def is_dialogue(self) -> bool:
        """Check if in dialogue"""
        return self.data.current_state == GameState.DIALOGUE

    def is_mission_menu(self) -> bool:
        """Check if in mission menu"""
        return self.data.current_state == GameState.MISSION_MENU

    def is_shop(self) -> bool:
        """Check if in shop"""
        return self.data.current_state == GameState.SHOP

    def transition_to(self, new_state: GameState):
        """
        Transition to new game state

        Args:
            new_state: State to transition to
        """
        if new_state == self.data.current_state:
            return  # Already in this state

        # Update state data
        self.data.previous_state = self.data.current_state
        self.data.current_state = new_state
        self.data.state_time = 0.0

        # Track history
        self.state_history.append(new_state)

    def update(self, dt: float):
        """
        Update state manager (track time in state)

        Args:
            dt: Delta time in seconds
        """
        self.data.state_time += dt

    def can_pause(self) -> bool:
        """Check if game can be paused from current state"""
        return self.data.current_state == GameState.PLAYING

    def can_resume(self) -> bool:
        """Check if game can be resumed from current state"""
        return self.data.current_state == GameState.PAUSED

    def pause(self):
        """Pause game (if playing)"""
        if self.can_pause():
            self.transition_to(GameState.PAUSED)

    def resume(self):
        """Resume game (if paused)"""
        if self.can_resume():
            self.transition_to(GameState.PLAYING)

    def start_game(self):
        """Start game from menu"""
        if self.data.current_state == GameState.MENU:
            self.transition_to(GameState.PLAYING)

    def quit_to_menu(self):
        """Return to main menu"""
        self.transition_to(GameState.MENU)

    def show_victory(self):
        """Show victory screen"""
        if self.data.current_state == GameState.PLAYING:
            self.transition_to(GameState.VICTORY)

    def get_previous_state(self) -> GameState | None:
        """Get previous state (for state restoration)"""
        return self.data.previous_state
