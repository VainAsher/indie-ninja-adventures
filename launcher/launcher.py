"""
Indie Ninja Adventures — Launcher

Checks for updates via the GitHub releases API, downloads and verifies
new releases, then launches the game.

Stdlib only: tkinter for UI, urllib.request for HTTP, hashlib for SHA256.
"""

import hashlib
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

GITHUB_REPO = "VainAsher/indie-ninja-adventures"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GAME_EXE_NAME = "ninja_dash.exe"
VERSION_FILE = "version.json"
LAUNCHER_VERSION = "1.0.0"
WINDOW_TITLE = "Indie Ninja Adventures"
WINDOW_SIZE = "480x260"

# UI colours — dark theme matching game aesthetic
BG_DARK = "#0f0f1a"
BG_MID = "#1a1a2e"
BG_CARD = "#16213e"
ACCENT = "#e94560"
TEXT_PRIMARY = "#eaeaea"
TEXT_DIM = "#888899"
BTN_PLAY = "#0f3460"
BTN_PLAY_HOVER = "#16213e"
PROGRESS_FG = "#e94560"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _get_base_dir() -> Path:
    """Return the directory that contains the launcher (and game) exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # Dev mode: launcher.py lives in <root>/launcher/, game is at <root>/
    return Path(__file__).parent.parent


def _get_version_path() -> Path:
    return _get_base_dir() / VERSION_FILE


def _get_game_exe() -> Path:
    """Return the path used to launch the game."""
    base = _get_base_dir()
    exe = base / GAME_EXE_NAME
    if exe.exists():
        return exe
    # Dev fallback: run from source
    return base / "demo_game.py"


def _read_local_version() -> str:
    """Read the installed game version from version.json."""
    path = _get_version_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("version", "unknown")
    except (OSError, json.JSONDecodeError):
        return "unknown"


def _parse_version(tag: str) -> tuple[int, ...]:
    """Convert 'v0.8.0' or '0.8.0' to (0, 8, 0)."""
    clean = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0,)


def _is_newer(remote: str, local: str) -> bool:
    """Return True if remote version is strictly newer than local."""
    return _parse_version(remote) > _parse_version(local)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# LauncherApp
# ──────────────────────────────────────────────────────────────────────────────


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Try to centre window on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 480) // 2
        y = (sh - 260) // 2
        self.root.geometry(f"480x260+{x}+{y}")

        self._local_version = _read_local_version()
        self._release_info: dict | None = None
        self._downloading = False

        self._build_ui()

        # Kick off update check immediately in background
        threading.Thread(target=self._check_for_update, daemon=True).start()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root

        # Title row
        title_frame = tk.Frame(root, bg=BG_DARK)
        title_frame.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(
            title_frame,
            text="◆  INDIE NINJA ADVENTURES",
            font=("Segoe UI", 13, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
        ).pack(side="left")

        tk.Label(
            title_frame,
            text=f"launcher v{LAUNCHER_VERSION}",
            font=("Segoe UI", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="right", anchor="s")

        # Version info
        info_frame = tk.Frame(root, bg=BG_DARK)
        info_frame.pack(fill="x", padx=24, pady=(6, 0))

        tk.Label(
            info_frame,
            text=f"Installed:  {self._local_version}",
            font=("Segoe UI", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")

        self._remote_label = tk.Label(
            info_frame,
            text="",
            font=("Segoe UI", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="e",
        )
        self._remote_label.pack(side="right")

        # Status label
        self._status_var = tk.StringVar(value="Checking for updates…")
        self._status_label = tk.Label(
            root,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_DARK,
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=24, pady=(10, 2))

        # Progress bar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Launcher.Horizontal.TProgressbar",
            troughcolor=BG_MID,
            background=PROGRESS_FG,
            bordercolor=BG_MID,
            lightcolor=PROGRESS_FG,
            darkcolor=PROGRESS_FG,
        )
        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress = ttk.Progressbar(
            root,
            variable=self._progress_var,
            maximum=100.0,
            style="Launcher.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self._progress.pack(fill="x", padx=24, pady=(0, 4))
        self._progress.start(12)

        # Separator
        tk.Frame(root, height=1, bg=BG_MID).pack(fill="x", padx=24, pady=(6, 0))

        # Button row
        btn_frame = tk.Frame(root, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=24, pady=(12, 0))

        self._play_btn = tk.Button(
            btn_frame,
            text="▶  PLAY",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BTN_PLAY,
            activebackground=BTN_PLAY_HOVER,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=20,
            pady=6,
            command=self._launch_game,
        )
        self._play_btn.pack(side="left")

        self._update_btn = tk.Button(
            btn_frame,
            text="↓  Update",
            font=("Segoe UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            state="disabled",
            command=self._start_download,
        )
        self._update_btn.pack(side="left", padx=(8, 0))

        tk.Button(
            btn_frame,
            text="Exit",
            font=("Segoe UI", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.root.destroy,
        ).pack(side="right")

    # ── Update check ─────────────────────────────────────────────────────────

    def _check_for_update(self) -> None:
        """Run in a background thread. Queries GitHub releases API."""
        try:
            req = urllib.request.Request(
                API_URL,
                headers={
                    "User-Agent": f"indie-ninja-launcher/{LAUNCHER_VERSION}",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                self._release_info = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self.root.after(0, self._on_check_done, None, f"Update check failed ({exc.code})")
            return
        except Exception as exc:
            self.root.after(0, self._on_check_done, None, f"Update check failed: {exc}")
            return

        remote_version = self._release_info.get("tag_name", "")
        self.root.after(0, self._on_check_done, remote_version, None)

    def _on_check_done(self, remote_version: str | None, error: str | None) -> None:
        """Called on the main thread once the update check finishes."""
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress_var.set(0.0)

        if error:
            self._status_var.set(f"⚠  {error}")
            return

        if not remote_version:
            self._status_var.set("No releases found. You have the latest version.")
            return

        self._remote_label.configure(text=f"Latest:  {remote_version.lstrip('v')}")

        if _is_newer(remote_version, self._local_version):
            self._status_var.set(f"Update available: {remote_version}")
            self._update_btn.configure(state="normal")
        else:
            self._status_var.set("✓  You have the latest version.")

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self) -> None:
        if self._downloading or not self._release_info:
            return
        assets = self._release_info.get("assets", [])
        exe_asset = next(
            (a for a in assets if a.get("name") == GAME_EXE_NAME), None
        )
        if not exe_asset:
            messagebox.showwarning(
                "No Asset",
                f"The latest release has no {GAME_EXE_NAME} asset.\n"
                "Check the GitHub releases page manually.",
                parent=self.root,
            )
            return

        sha_asset = next(
            (a for a in assets if a.get("name") == f"{GAME_EXE_NAME}.sha256"), None
        )
        expected_sha = None
        if sha_asset:
            try:
                with urllib.request.urlopen(sha_asset["browser_download_url"], timeout=10) as r:
                    expected_sha = r.read().decode().strip().split()[0]
            except Exception:
                pass  # proceed without verification if sha file unavailable

        self._downloading = True
        self._update_btn.configure(state="disabled", text="Downloading…")
        self._status_var.set("Downloading update…")

        threading.Thread(
            target=self._download_worker,
            args=(exe_asset["browser_download_url"], exe_asset.get("size", 0), expected_sha),
            daemon=True,
        ).start()

    def _download_worker(self, url: str, total_size: int, expected_sha: str | None) -> None:
        dest = _get_base_dir() / f"{GAME_EXE_NAME}.new"
        try:
            downloaded = 0

            def _hook(block_num: int, block_size: int, file_size: int) -> None:
                nonlocal downloaded
                downloaded = min(block_num * block_size, file_size if file_size > 0 else total_size)
                if total_size > 0:
                    pct = min(100.0, downloaded / total_size * 100)
                    self.root.after(0, self._progress_var.set, pct)
                    self.root.after(
                        0,
                        self._status_var.set,
                        f"Downloading… {downloaded // 1024:,} KB / {total_size // 1024:,} KB",
                    )

            urllib.request.urlretrieve(url, dest, reporthook=_hook)

            if expected_sha:
                self.root.after(0, self._status_var.set, "Verifying checksum…")
                actual = _sha256_file(dest)
                if actual.lower() != expected_sha.lower():
                    dest.unlink(missing_ok=True)
                    self.root.after(0, self._on_download_error, "Checksum mismatch — download corrupt. Try again.")
                    return

            # Atomic-ish replace: rename current exe to .bak, rename .new to current
            game_exe = _get_game_exe()
            if game_exe.exists() and game_exe.suffix == ".exe":
                bak = game_exe.with_suffix(".bak")
                bak.unlink(missing_ok=True)
                game_exe.rename(bak)
            dest.rename(game_exe)

            # Update local version.json
            if self._release_info:
                tag = self._release_info.get("tag_name", "")
                ver = tag.lstrip("v")
                vpath = _get_version_path()
                try:
                    data = json.loads(vpath.read_text(encoding="utf-8"))
                    data["version"] = ver
                    vpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception:
                    pass

            self.root.after(0, self._on_download_done)

        except Exception as exc:
            dest.unlink(missing_ok=True)
            self.root.after(0, self._on_download_error, str(exc))

    def _on_download_done(self) -> None:
        self._downloading = False
        self._progress_var.set(100.0)
        self._status_var.set("✓  Update installed. Ready to play.")
        self._update_btn.configure(text="↓  Update", state="disabled")

    def _on_download_error(self, message: str) -> None:
        self._downloading = False
        self._progress_var.set(0.0)
        self._status_var.set(f"✗  {message}")
        self._update_btn.configure(text="↓  Update", state="normal")

    # ── Launch ────────────────────────────────────────────────────────────────

    def _launch_game(self) -> None:
        game_path = _get_game_exe()

        if game_path.suffix == ".py":
            # Dev mode: run via Python interpreter
            cmd = [sys.executable, str(game_path)]
            kwargs = {}
        else:
            cmd = [str(game_path)]
            kwargs = {}

        try:
            subprocess.Popen(cmd, **kwargs)
            self.root.after(200, self.root.destroy)
        except FileNotFoundError:
            messagebox.showerror(
                "Game Not Found",
                f"Could not find the game at:\n{game_path}\n\n"
                "Please reinstall or check the install directory.",
                parent=self.root,
            )

    # ── Run ──────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    app = LauncherApp()
    app.run()


if __name__ == "__main__":
    main()
