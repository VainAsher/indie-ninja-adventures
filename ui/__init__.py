"""
UI components for Vain Asher Gaming's: Indie Ninja Adventures

User interface elements:
- Menu system (main menu, pause menu, settings)
- Tutorial system (contextual hints, control overlays)
- Future: Dialogs, tooltips, notifications
"""

from .menu_system import (
    MenuManager,
    MainMenu,
    PauseMenu,
    SettingsMenu,
    MenuAction
)
from .tutorial_system import (
    TutorialManager,
    TutorialTrigger,
    TutorialTriggerType,
    TutorialMessage,
    ControlsHintOverlay
)

__all__ = [
    'MenuManager',
    'MainMenu',
    'PauseMenu',
    'SettingsMenu',
    'MenuAction',
    'TutorialManager',
    'TutorialTrigger',
    'TutorialTriggerType',
    'TutorialMessage',
    'ControlsHintOverlay',
]
