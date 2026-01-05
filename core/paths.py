"""
Path Utilities - Centralized path management for the game

This module provides a single source of truth for resolving paths,
especially critical for PyInstaller executable builds where __file__
and relative paths don't work as expected.

Usage:
    from core.paths import get_user_data_dir, get_project_root

    user_data = get_user_data_dir()
    saves_dir = user_data / "saves"
"""

import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    """
    Get the project root directory

    When running as a PyInstaller executable (frozen), this returns the
    directory containing the executable. When running as a script, this
    returns the directory containing demo_game.py.

    Returns:
        Path to project root directory
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle - use executable directory
        return Path(sys.executable).parent
    else:
        # Running as script - use project root (parent of core/)
        return Path(__file__).parent.parent


def get_user_data_dir() -> Path:
    """
    Get the user_data directory path

    Priority:
    1. NINJADASH_USER_DATA environment variable (full override)
    2. Project-local user_data directory (default)

    The path is automatically adjusted for PyInstaller executables to use
    the executable's directory instead of the frozen bundle's internal path.

    Returns:
        Path to user_data directory
    """
    env_dir = os.environ.get("NINJADASH_USER_DATA")
    if env_dir:
        return Path(env_dir)

    # Default: project-local user_data directory
    # Automatically handles both script and frozen (exe) execution
    return get_project_root() / "user_data"


def ensure_user_data_dirs() -> Path:
    """
    Ensure all user_data subdirectories exist

    Creates the following directories if they don't exist:
    - user_data/logs
    - user_data/replays
    - user_data/saves
    - user_data/settings

    Returns:
        Path to user_data directory
    """
    user_data = get_user_data_dir()
    (user_data / "logs").mkdir(parents=True, exist_ok=True)
    (user_data / "replays").mkdir(parents=True, exist_ok=True)
    (user_data / "saves").mkdir(parents=True, exist_ok=True)
    (user_data / "settings").mkdir(parents=True, exist_ok=True)
    return user_data
