"""
Hot reload system for configuration files (DEV builds only).

Watches settings.json and reloads when changed.
"""

from collections.abc import Callable
from pathlib import Path


class HotReloadWatcher:
    """
    File watcher for hot reloading configuration files.

    Polls file modification times and triggers reload callbacks.
    """

    def __init__(self):
        self.watched_files: dict[Path, tuple[float, Callable]] = {}
        self.check_interval = 1.0  # Check every second
        self.last_check_time = 0.0

    def watch(self, file_path: Path, reload_callback: Callable):
        """
        Watch a file for changes.

        Args:
            file_path: Path to file to watch
            reload_callback: Function to call when file changes (no args)
        """
        file_path = Path(file_path)
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            self.watched_files[file_path] = (mtime, reload_callback)
            print(f"[HOT RELOAD] Watching {file_path.name}")

    def check(self, current_time: float):
        """
        Check watched files for changes.

        Call this every frame with current time.

        Args:
            current_time: Current time in seconds (use time.time())
        """
        if current_time - self.last_check_time < self.check_interval:
            return

        self.last_check_time = current_time

        for file_path, (old_mtime, callback) in list(self.watched_files.items()):
            if not file_path.exists():
                continue

            try:
                current_mtime = file_path.stat().st_mtime
                if current_mtime > old_mtime:
                    print(f"[HOT RELOAD] Detected change in {file_path.name}")
                    try:
                        callback()
                        print(f"[HOT RELOAD] Reloaded {file_path.name}")
                        # Update mtime
                        self.watched_files[file_path] = (current_mtime, callback)
                    except Exception as e:
                        print(f"[HOT RELOAD] Error reloading {file_path.name}: {e}")
            except Exception:
                # Ignore errors reading file stats
                pass
