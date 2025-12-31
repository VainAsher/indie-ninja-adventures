"""
Game-specific logic for Vain Asher Gaming's: Indie Ninja Adventures

High-level game coordination:
- Level management
- Game loop
- State machine (menu/play/pause)
"""

from .level_manager import LevelManager, LevelState, LevelCompletionEvent
from .game_state import GameStateManager, GameState

__all__ = [
    'LevelManager',
    'LevelState',
    'LevelCompletionEvent',
    'GameStateManager',
    'GameState',
]
