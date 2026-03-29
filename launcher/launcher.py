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
WINDOW_W = 640
WINDOW_H = 360
SPLASH_H = 200      # canvas height — crops the 640×320 scaled image to top portion

# Colours — matched to game's menu_system.py palette
BG_DARK = "#0a0a14"         # (10, 10, 20)  — game bg_color
BG_MID = "#1a1a2e"
BG_CARD = "#16213e"
ACCENT = "#ffd700"          # gold — game title_color (255, 215, 0)
TEXT_PRIMARY = "#c8c8dc"    # game item_color (200, 200, 220)
TEXT_DIM = "#888899"
TEXT_SELECTED = "#ffff64"   # game selected_color (255, 255, 100)
BTN_PLAY_BG = "#1a1a2e"
PROGRESS_FG = "#ffd700"     # gold progress bar


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
    base = _get_base_dir()
    exe = base / GAME_EXE_NAME
    if exe.exists():
        return exe
    return base / "demo_game.py"


def _get_splash_path() -> Path | None:
    """Locate landing.png — works in both frozen and dev mode."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundles assets next to the exe under assets/splash/
        p = Path(sys.executable).parent / "assets" / "splash" / "landing.png"
        if p.exists():
            return p
        # Also check _MEIPASS for onefile builds
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            p = Path(meipass) / "assets" / "splash" / "landing.png"
            if p.exists():
                return p
        return None
    # Dev mode
    p = Path(__file__).parent.parent / "assets" / "splash" / "landing.png"
    return p if p.exists() else None


def _read_local_version() -> str:
    try:
        data = json.loads(_get_version_path().read_text(encoding="utf-8"))
        return data.get("version", "unknown")
    except (OSError, json.JSONDecodeError):
        return "unknown"


def _parse_version(tag: str) -> tuple[int, ...]:
    clean = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0,)


def _is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _version_label(tag: str, local_version: str, is_latest: bool) -> str:
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
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        self._local_version = _read_local_version()
        self._all_releases: list[dict] = []
        self._selected_release: dict | None = None
        self._downloading = False
        self._splash_photo: tk.PhotoImage | None = None

        self._build_ui()

        # Centre window after UI is built (so winfo_reqwidth is accurate)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - WINDOW_W) // 2
        y = (sh - WINDOW_H) // 2
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

        threading.Thread(target=self._fetch_releases, daemon=True).start()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root

        # ── Splash canvas ─────────────────────────────────────────────────────
        self._splash_canvas = tk.Canvas(
            root,
            width=WINDOW_W,
            height=SPLASH_H,
            bd=0,
            highlightthickness=0,
            bg="#060610",
        )
        self._splash_canvas.pack()

        # Load + scale splash (subsample 2× assumes 1280×640 source → 640×320)
        splash_path = _get_splash_path()
        if splash_path:
            try:
                raw = tk.PhotoImage(file=str(splash_path))
                # Determine subsample factor so result fits WINDOW_W
                factor = max(1, (raw.width() + WINDOW_W - 1) // WINDOW_W)
                self._splash_photo = raw.subsample(factor, factor)
                self._splash_canvas.create_image(0, 0, anchor="nw", image=self._splash_photo)
            except Exception:
                self._splash_photo = None

        # Game title overlay — shadow then gold text (matches Impact/gold in-game style)
        tx, ty = 22, SPLASH_H - 16
        self._splash_canvas.create_text(
            tx + 2, ty + 2,
            text="INDIE NINJA ADVENTURES",
            font=("Impact", 18),
            fill="#050510",
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx, ty,
            text="INDIE NINJA ADVENTURES",
            font=("Impact", 18),
            fill=ACCENT,
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx, ty - 22,
            text="Vain Asher Gaming",
            font=("Consolas", 9),
            fill=TEXT_DIM,
            anchor="sw",
        )
        self._splash_canvas.create_text(
            WINDOW_W - 8, SPLASH_H - 6,
            text=f"launcher v{LAUNCHER_VERSION}",
            font=("Consolas", 8),
            fill=TEXT_DIM,
            anchor="se",
        )

        # ── Gold accent separator ─────────────────────────────────────────────
        tk.Frame(root, height=2, bg=ACCENT).pack(fill="x")

        # ── Controls area ─────────────────────────────────────────────────────
        ctrl = tk.Frame(root, bg=BG_DARK)
        ctrl.pack(fill="both", expand=True, padx=20, pady=(8, 0))

        # Installed version + status on one row
        top_row = tk.Frame(ctrl, bg=BG_DARK)
        top_row.pack(fill="x")

        tk.Label(
            top_row,
            text=f"Installed:  v{self._local_version}",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")

        self._status_var = tk.StringVar(value="Fetching releases…")
        tk.Label(
            top_row,
            textvariable=self._status_var,
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_DARK,
            anchor="e",
        ).pack(side="right")

        # Version picker row
        picker_row = tk.Frame(ctrl, bg=BG_DARK)
        picker_row.pack(fill="x", pady=(6, 0))

        tk.Label(
            picker_row,
            text="Version:",
            font=("Consolas", 9),
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
            selectforeground=TEXT_SELECTED,
            arrowcolor=ACCENT,
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
            picker_row,
            textvariable=self._version_var,
            state="disabled",
            style="Launcher.TCombobox",
            width=32,
            font=("Consolas", 9),
        )
        self._version_combo.pack(side="left", padx=(8, 0))
        self._version_combo.bind("<<ComboboxSelected>>", self._on_version_selected)

        # Progress bar
        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress = ttk.Progressbar(
            ctrl,
            variable=self._progress_var,
            maximum=100.0,
            style="Launcher.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self._progress.pack(fill="x", pady=(8, 0))
        self._progress.start(12)

        # Thin separator
        tk.Frame(ctrl, height=1, bg=BG_MID).pack(fill="x", pady=(8, 0))

        # Button row
        btn_row = tk.Frame(ctrl, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(8, 0))

        self._play_btn = tk.Button(
            btn_row,
            text="▶  PLAY",
            font=("Consolas", 10, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=5,
            command=self._launch_game,
        )
        self._play_btn.pack(side="left")

        self._download_btn = tk.Button(
            btn_row,
            text="↓  Install",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            state="disabled",
            command=self._start_download,
        )
        self._download_btn.pack(side="left", padx=(8, 0))

        tk.Button(
            btn_row,
            text="Exit",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            command=self.root.destroy,
        ).pack(side="right")

    # ── Release list fetch ────────────────────────────────────────────────────

    def _fetch_releases(self) -> None:
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

        visible = [r for r in releases if not r.get("draft", False)]
        self.root.after(0, self._on_fetch_done, visible, None)

    def _on_fetch_done(self, releases: list[dict], error: str | None) -> None:
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress_var.set(0.0)

        if error:
            self._status_var.set(f"⚠  {error}")
            return

        if not releases:
            self._status_var.set("No releases found.")
            return

        self._all_releases = releases
        latest_tag = releases[0].get("tag_name", "")

        labels = [
            _version_label(r["tag_name"], self._local_version, i == 0)
            for i, r in enumerate(releases)
        ]
        self._version_combo.configure(values=labels, state="readonly")
        self._version_combo.current(0)
        self._selected_release = releases[0]
        self._refresh_download_btn()

        latest_ver = latest_tag.lstrip("v")
        if _is_newer(latest_ver, self._local_version):
            self._status_var.set(f"Update available: {latest_tag}")
        else:
            self._status_var.set("✓  Up to date")

    # ── Version picker ────────────────────────────────────────────────────────

    def _on_version_selected(self, _event=None) -> None:
        idx = self._version_combo.current()
        if idx < 0 or idx >= len(self._all_releases):
            return
        self._selected_release = self._all_releases[idx]
        self._refresh_download_btn()

        tag = self._selected_release.get("tag_name", "")
        ver = tag.lstrip("v")
        if ver == self._local_version:
            self._status_var.set(f"  {tag} — currently installed")
        elif _is_newer(ver, self._local_version):
            self._status_var.set(f"↑  {tag} is newer than installed")
        else:
            self._status_var.set(f"↓  {tag} is older than installed")

    def _refresh_download_btn(self) -> None:
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
                pass

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

            game_exe = _get_game_exe()
            if game_exe.exists() and game_exe.suffix == ".exe":
                bak = game_exe.with_suffix(".bak")
                bak.unlink(missing_ok=True)
                game_exe.rename(bak)
            dest.rename(game_exe)

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

        # Refresh combobox so (installed) badge moves to the new version
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
                f"Could not find the game at:\n{game_path}\n\nPlease download a version first.",
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
