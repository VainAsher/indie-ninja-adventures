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
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=30"
GAME_EXE_NAME = "ninja_dash.exe"
VERSION_FILE = "version.json"
LAUNCHER_VERSION = "1.0.0"
WINDOW_TITLE = "Indie Ninja Adventures"
WINDOW_SIZE = "480x300"

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


def _version_label(tag: str, local_version: str, is_latest: bool) -> str:
    """Build the display string shown in the version combobox."""
    ver = tag.lstrip("v")
    parts = []
    if is_latest:
        parts.append("latest")
    if ver == local_version:
        parts.append("installed")
    suffix = f"  ({', '.join(parts)})" if parts else ""
    return f"{tag}{suffix}"


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

        # Centre window on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 480) // 2
        y = (sh - 300) // 2
        self.root.geometry(f"480x300+{x}+{y}")

        self._local_version = _read_local_version()
        self._all_releases: list[dict] = []
        self._selected_release: dict | None = None
        self._downloading = False

        self._build_ui()

        # Kick off release list fetch immediately in background
        threading.Thread(target=self._fetch_releases, daemon=True).start()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root

        # Title row
        title_frame = tk.Frame(root, bg=BG_DARK)
        title_frame.pack(fill="x", padx=24, pady=(18, 0))

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

        # Installed version
        tk.Label(
            root,
            text=f"Installed:  {self._local_version}",
            font=("Segoe UI", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(6, 0))

        # Status label
        self._status_var = tk.StringVar(value="Fetching release list…")
        self._status_label = tk.Label(
            root,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_DARK,
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=24, pady=(6, 0))

        # Version picker row
        picker_frame = tk.Frame(root, bg=BG_DARK)
        picker_frame.pack(fill="x", padx=24, pady=(8, 0))

        tk.Label(
            picker_frame,
            text="Version:",
            font=("Segoe UI", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Launcher.TCombobox",
            fieldbackground=BG_MID,
            background=BG_MID,
            foreground=TEXT_PRIMARY,
            selectbackground=BG_CARD,
            selectforeground=TEXT_PRIMARY,
            arrowcolor=TEXT_DIM,
        )
        style.configure(
            "Launcher.Horizontal.TProgressbar",
            troughcolor=BG_MID,
            background=PROGRESS_FG,
            bordercolor=BG_MID,
            lightcolor=PROGRESS_FG,
            darkcolor=PROGRESS_FG,
        )

        self._version_var = tk.StringVar()
        self._version_combo = ttk.Combobox(
            picker_frame,
            textvariable=self._version_var,
            state="disabled",
            style="Launcher.TCombobox",
            width=30,
            font=("Segoe UI", 9),
        )
        self._version_combo.pack(side="left", padx=(8, 0))
        self._version_combo.bind("<<ComboboxSelected>>", self._on_version_selected)

        # Progress bar
        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress = ttk.Progressbar(
            root,
            variable=self._progress_var,
            maximum=100.0,
            style="Launcher.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self._progress.pack(fill="x", padx=24, pady=(10, 4))
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

        self._download_btn = tk.Button(
            btn_frame,
            text="↓  Install",
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
        self._download_btn.pack(side="left", padx=(8, 0))

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

    # ── Release list fetch ────────────────────────────────────────────────────

    def _fetch_releases(self) -> None:
        """Background thread — fetches all releases and populates the picker."""
        try:
            req = urllib.request.Request(
                RELEASES_API_URL,
                headers={
                    "User-Agent": f"indie-ninja-launcher/{LAUNCHER_VERSION}",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                releases = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self.root.after(0, self._on_fetch_done, [], f"Could not fetch releases ({exc.code})")
            return
        except Exception as exc:
            self.root.after(0, self._on_fetch_done, [], f"Could not fetch releases: {exc}")
            return

        # Filter out drafts; pre-releases shown but labelled
        visible = [r for r in releases if not r.get("draft", False)]
        self.root.after(0, self._on_fetch_done, visible, None)

    def _on_fetch_done(self, releases: list[dict], error: str | None) -> None:
        """Main thread — populate picker and update status once fetch completes."""
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress_var.set(0.0)

        if error:
            self._status_var.set(f"⚠  {error}")
            return

        if not releases:
            self._status_var.set("No releases found on GitHub.")
            return

        self._all_releases = releases
        latest_tag = releases[0].get("tag_name", "")

        # Build combobox entries: newest first
        labels = [
            _version_label(r["tag_name"], self._local_version, i == 0)
            for i, r in enumerate(releases)
        ]
        self._version_combo.configure(values=labels, state="readonly")

        # Pre-select the latest release
        self._version_combo.current(0)
        self._selected_release = releases[0]
        self._refresh_download_btn()

        # Status line
        latest_ver = latest_tag.lstrip("v")
        if _is_newer(latest_ver, self._local_version):
            self._status_var.set(f"Update available: {latest_tag}")
        else:
            self._status_var.set("✓  You have the latest version.")

    # ── Version picker ────────────────────────────────────────────────────────

    def _on_version_selected(self, _event=None) -> None:
        """Called when the user picks a different version in the combobox."""
        idx = self._version_combo.current()
        if idx < 0 or idx >= len(self._all_releases):
            return
        self._selected_release = self._all_releases[idx]
        self._refresh_download_btn()

        tag = self._selected_release.get("tag_name", "")
        ver = tag.lstrip("v")
        if ver == self._local_version:
            self._status_var.set(f"  {tag} is currently installed.")
        elif _is_newer(ver, self._local_version):
            self._status_var.set(f"↑  {tag} is newer than your installed version.")
        else:
            self._status_var.set(f"↓  {tag} is older than your installed version.")

    def _refresh_download_btn(self) -> None:
        """Update download button label and enabled state for the selected release."""
        if not self._selected_release or self._downloading:
            return

        tag = self._selected_release.get("tag_name", "")
        ver = tag.lstrip("v")
        assets = self._selected_release.get("assets", [])
        has_exe = any(a.get("name") == GAME_EXE_NAME for a in assets)

        if not has_exe:
            self._download_btn.configure(state="disabled", text="↓  No exe asset")
            return

        if ver == self._local_version:
            label = f"↓  Reinstall {tag}"
        elif _is_newer(ver, self._local_version):
            label = f"↑  Update to {tag}"
        else:
            label = f"↓  Downgrade to {tag}"

        self._download_btn.configure(state="normal", text=label)

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self) -> None:
        if self._downloading or not self._selected_release:
            return

        assets = self._selected_release.get("assets", [])
        exe_asset = next((a for a in assets if a.get("name") == GAME_EXE_NAME), None)
        if not exe_asset:
            messagebox.showwarning(
                "No Asset",
                f"The selected release has no {GAME_EXE_NAME} asset.\n"
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
                with urllib.request.urlopen(
                    sha_asset["browser_download_url"], timeout=10
                ) as r:
                    expected_sha = r.read().decode().strip().split()[0]
            except Exception:
                pass  # proceed without verification if sha file unavailable

        self._downloading = True
        self._download_btn.configure(state="disabled", text="Downloading…")
        self._status_var.set("Downloading…")

        threading.Thread(
            target=self._download_worker,
            args=(
                exe_asset["browser_download_url"],
                exe_asset.get("size", 0),
                expected_sha,
                self._selected_release,
            ),
            daemon=True,
        ).start()

    def _download_worker(
        self,
        url: str,
        total_size: int,
        expected_sha: str | None,
        release: dict,
    ) -> None:
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
                    self.root.after(
                        0,
                        self._on_download_error,
                        "Checksum mismatch — download corrupt. Try again.",
                    )
                    return

            # Atomic-ish replace
            game_exe = _get_game_exe()
            if game_exe.exists() and game_exe.suffix == ".exe":
                bak = game_exe.with_suffix(".bak")
                bak.unlink(missing_ok=True)
                game_exe.rename(bak)
            dest.rename(game_exe)

            # Update local version.json to match installed release
            tag = release.get("tag_name", "")
            ver = tag.lstrip("v")
            if ver:
                vpath = _get_version_path()
                try:
                    data = json.loads(vpath.read_text(encoding="utf-8"))
                    data["version"] = ver
                    vpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception:
                    pass

            self.root.after(0, self._on_download_done, tag)

        except Exception as exc:
            dest.unlink(missing_ok=True)
            self.root.after(0, self._on_download_error, str(exc))

    def _on_download_done(self, tag: str) -> None:
        self._downloading = False
        self._local_version = tag.lstrip("v")
        self._progress_var.set(100.0)
        self._status_var.set(f"✓  {tag} installed. Ready to play.")

        # Refresh combobox labels so "(installed)" badge moves to new version
        labels = [
            _version_label(r["tag_name"], self._local_version, i == 0)
            for i, r in enumerate(self._all_releases)
        ]
        self._version_combo.configure(values=labels)
        self._refresh_download_btn()

    def _on_download_error(self, message: str) -> None:
        self._downloading = False
        self._progress_var.set(0.0)
        self._status_var.set(f"✗  {message}")
        self._refresh_download_btn()

    # ── Launch ────────────────────────────────────────────────────────────────

    def _launch_game(self) -> None:
        game_path = _get_game_exe()

        if game_path.suffix == ".py":
            cmd = [sys.executable, str(game_path)]
        else:
            cmd = [str(game_path)]

        try:
            subprocess.Popen(cmd)
            self.root.after(200, self.root.destroy)
        except FileNotFoundError:
            messagebox.showerror(
                "Game Not Found",
                f"Could not find the game at:\n{game_path}\n\n"
                "Please download a version first.",
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
