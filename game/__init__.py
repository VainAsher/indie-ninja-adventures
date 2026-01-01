"""
Game-specific logic for Vain Asher Gaming's: Indie Ninja Adventures

High-level game coordination:
- Level management
- Game loop
- State machine (menu/play/pause)
"""

from .game_state import GameState, GameStateManager
from .level_manager import LevelCompletionEvent, LevelManager, LevelState

__all__ = [
    "LevelManager",
    "LevelState",
    "LevelCompletionEvent",
    "GameStateManager",
    "GameState",
]
