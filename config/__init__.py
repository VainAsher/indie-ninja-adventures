"""
Configuration for Vain Asher Gaming's: Indie Ninja Adventures

Game configuration and settings:
- Physics constants
- Feature flags
- Logging configuration
- Persistent settings (user_data/settings/)
- Build mode detection (PRODUCTION/TESTING/DEV)
"""

from .build_config import BuildConfig, BuildMode, get_build_config, is_frozen
from .settings import GameSettings

__all__ = ["GameSettings", "BuildMode", "BuildConfig", "get_build_config", "is_frozen"]
