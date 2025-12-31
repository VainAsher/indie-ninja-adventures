"""
Configuration for Vain Asher Gaming's: Indie Ninja Adventures

Game configuration and settings:
- Physics constants
- Feature flags
- Logging configuration
- Persistent settings (user_data/settings/)
- Build mode detection (PRODUCTION/TESTING/DEV)
"""

from .settings import GameSettings
from .build_config import BuildMode, BuildConfig, get_build_config, is_frozen

__all__ = ['GameSettings', 'BuildMode', 'BuildConfig', 'get_build_config', 'is_frozen']
