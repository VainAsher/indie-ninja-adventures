"""
Settings Management System

Provides persistent game settings stored in user_data/settings/
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class GameSettings:
    """
    Manage game settings with persistent storage

    Settings are stored in user_data/settings/settings.json

    Usage:
        settings = GameSettings()
        settings.set("volume_music", 0.8)
        settings.set("fullscreen", True)
        volume = settings.get("volume_music", default=1.0)
        settings.save()
    """

    DEFAULT_SETTINGS = {
        # Audio
        "volume_master": 1.0,
        "volume_music": 0.7,
        "volume_sfx": 0.8,

        # Display
        "fullscreen": False,
        "vsync": True,
        "window_width": 1280,
        "window_height": 720,

        # Gameplay
        "screenshake": True,
        "particles": True,
        "camera_smoothing": 0.1,

        # Controls
        "key_left": "left",
        "key_right": "right",
        "key_jump": "space",
        "key_dash": "shift",
        "key_crouch": "down",

        # Developer
        "show_fps": False,
        "show_hitboxes": False,
        "log_level": "INFO",
    }

    def __init__(self, user_data_dir: Optional[Path] = None):
        """
        Initialize settings manager

        Args:
            user_data_dir: Custom user data directory (uses env/default if None)
        """
        self.user_data_dir = user_data_dir or self._get_user_data_dir()
        self.settings_dir = self.user_data_dir / "settings"
        self.settings_dir.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.settings_dir / "settings.json"
        self.settings: Dict[str, Any] = {}

        self.load()

    def _get_user_data_dir(self) -> Path:
        """Get user data directory (project-local by default)"""
        env_dir = os.environ.get("NINJADASH_USER_DATA")
        if env_dir:
            return Path(env_dir)

        # Default: project-local user_data directory
        project_root = Path(__file__).parent.parent
        return project_root / 'user_data'

    def load(self):
        """Load settings from disk (creates default if not exists)"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                # Merge with defaults (in case new settings were added)
                self.settings = {**self.DEFAULT_SETTINGS, **loaded}
            except Exception as e:
                print(f"Warning: Failed to load settings from {self.settings_file}: {e}")
                print("Using default settings")
                self.settings = self.DEFAULT_SETTINGS.copy()
        else:
            # First run - create default settings
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save()

    def save(self):
        """Save settings to disk"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error: Failed to save settings to {self.settings_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """
        Set setting value (does not auto-save, call save() to persist)

        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.save()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings as dictionary"""
        return self.settings.copy()

    def update(self, new_settings: Dict[str, Any]):
        """
        Update multiple settings at once

        Args:
            new_settings: Dictionary of settings to update
        """
        self.settings.update(new_settings)

    def __repr__(self):
        return f"GameSettings(file={self.settings_file}, settings={len(self.settings)} keys)"
