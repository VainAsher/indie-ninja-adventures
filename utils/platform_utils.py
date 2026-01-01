"""
Platform-specific utilities for file operations.
"""

import os
import subprocess
import sys
from pathlib import Path


def open_folder_in_explorer(folder_path: Path):
    """
    Open a folder in the system file explorer.

    Works on Windows, macOS, and Linux.

    Args:
        folder_path: Path to the folder to open
    """
    folder_path = Path(folder_path).resolve()

    if not folder_path.exists():
        print(f"Warning: Folder does not exist: {folder_path}")
        return

    try:
        if sys.platform == "win32":
            # Windows: use explorer
            os.startfile(str(folder_path))
        elif sys.platform == "darwin":
            # macOS: use open
            subprocess.Popen(["open", str(folder_path)])
        else:
            # Linux: try xdg-open
            subprocess.Popen(["xdg-open", str(folder_path)])
    except Exception as e:
        print(f"Warning: Could not open folder {folder_path}: {e}")
