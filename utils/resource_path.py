"""
Resource path helpers for bundled builds.

Use get_resource_path() to locate assets/data/config regardless of
running from source or a PyInstaller build (onedir/onefile).
"""

from pathlib import Path
import sys


def get_resource_path(*parts: str) -> Path:
    """
    Resolve a resource path that works for source and PyInstaller builds.

    Args:
        *parts: Path segments relative to the project root (e.g., "data", "items.json")

    Returns:
        Absolute Path to the resource.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).parent.parent
    return base_dir.joinpath(*parts)
