"""
Build configuration detection for PyInstaller builds.

Detects build mode via BUILD_MODE environment variable:
- PRODUCTION: Release build, no console, minimal debug
- TESTING: Testing build, auto-record, console visible
- DEV: Development build, all debug features enabled
"""

import os
import sys
from enum import Enum
from typing import Optional
from datetime import datetime


class BuildMode(Enum):
    """Build mode enumeration"""
    PRODUCTION = "PRODUCTION"
    TESTING = "TESTING"
    DEV = "DEV"


def is_frozen() -> bool:
    """Check if running as PyInstaller executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_build_mode() -> BuildMode:
    """
    Get current build mode from environment variable.

    Fallback logic:
    - If BUILD_MODE env var set: use it
    - If frozen (PyInstaller) and no env var: PRODUCTION
    - If not frozen: DEV
    """
    env_mode = os.environ.get("BUILD_MODE", "").upper()

    if env_mode in ("PRODUCTION", "TESTING", "DEV"):
        return BuildMode[env_mode]

    # Fallback: frozen = PRODUCTION, not frozen = DEV
    if is_frozen():
        return BuildMode.PRODUCTION
    else:
        return BuildMode.DEV


class BuildConfig:
    """Configuration settings based on build mode"""

    def __init__(self):
        self.mode = get_build_mode()
        self._configure()

        # Debug output
        print(f"[BUILD CONFIG] Mode: {self.mode.value}")
        print(f"[BUILD CONFIG] Frozen: {is_frozen()}")
        print(f"[BUILD CONFIG] Auto-record: {self.auto_record}")
        print(f"[BUILD CONFIG] Auto-open logs: {self.auto_open_logs_on_exit}")

    def _configure(self):
        """Configure settings based on build mode"""
        if self.mode == BuildMode.PRODUCTION:
            # Production: clean, minimal
            self.show_console = False
            self.auto_record = False
            self.debug_overlay_default = False
            self.show_fps_default = False
            self.show_hitboxes_default = False
            self.enable_hot_reload = False
            self.enable_dev_console = False
            self.auto_open_logs_on_exit = False

        elif self.mode == BuildMode.TESTING:
            # Testing: auto-record, visible console for errors
            self.show_console = True
            self.auto_record = True
            self.debug_overlay_default = True
            self.show_fps_default = False
            self.show_hitboxes_default = False
            self.enable_hot_reload = False
            self.enable_dev_console = False
            self.auto_open_logs_on_exit = True

        elif self.mode == BuildMode.DEV:
            # Development: all debug features enabled
            self.show_console = True
            self.auto_record = False
            self.debug_overlay_default = True
            self.show_fps_default = True
            self.show_hitboxes_default = False
            self.enable_hot_reload = True
            self.enable_dev_console = True
            self.auto_open_logs_on_exit = False

    def get_auto_record_filename(self) -> Optional[str]:
        """Generate auto-record filename for testing build"""
        if not self.auto_record:
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"test_session_{timestamp}.json"

    def __repr__(self):
        return f"BuildConfig(mode={self.mode.value})"


# Global instance
_build_config: Optional[BuildConfig] = None


def get_build_config() -> BuildConfig:
    """Get global build config instance"""
    global _build_config
    if _build_config is None:
        _build_config = BuildConfig()
    return _build_config
