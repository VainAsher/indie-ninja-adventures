"""
Indie Ninja Adventures — Launcher

Checks for updates via the GitHub releases API, downloads and verifies
new releases, then launches the game.

Launch modes available from the UI:
  Solo Play     — launch game without multiplayer args
  Host Game     — launch with --host <port>  (starts a server + joins it)
  Join Game     — launch with --connect <host:port>

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
WINDOW_H = 460
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

# Multiplayer button accent colours
BTN_HOST_BG = "#1a2e1a"     # dark green tint
BTN_JOIN_BG = "#1a1a2e"


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
                factor = max(1, (raw.width() + WINDOW_W - 1) // WINDOW_W)
                self._splash_photo = raw.subsample(factor, factor)
                self._splash_canvas.create_image(0, 0, anchor="nw", image=self._splash_photo)
            except Exception:
                self._splash_photo = None

        # Game title overlay
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
        ctrl.pack(fill="both", expand=True, padx=20, pady=(8, 6))

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

        # ── Primary button row (Solo + Download + Exit) ───────────────────────
        btn_row = tk.Frame(ctrl, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(8, 0))

        self._play_btn = tk.Button(
            btn_row,
            text=">>  Solo Play",
            font=("Consolas", 10, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=5,
            command=self._launch_solo,
        )
        self._play_btn.pack(side="left")

        self._download_btn = tk.Button(
            btn_row,
            text="v  Install",
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

        # ── Multiplayer section ───────────────────────────────────────────────
        tk.Frame(ctrl, height=1, bg=ACCENT).pack(fill="x", pady=(10, 0))

        mp_header = tk.Frame(ctrl, bg=BG_DARK)
        mp_header.pack(fill="x", pady=(4, 0))
        tk.Label(
            mp_header,
            text="MULTIPLAYER",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
        ).pack(side="left")

        mp_row = tk.Frame(ctrl, bg=BG_DARK)
        mp_row.pack(fill="x", pady=(6, 0))

        # Host side
        host_frame = tk.Frame(mp_row, bg=BG_DARK)
        host_frame.pack(side="left")

        tk.Label(
            host_frame,
            text="Port:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        self._host_port_var = tk.StringVar(value="7777")
        tk.Entry(
            host_frame,
            textvariable=self._host_port_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=6,
        ).pack(side="left", padx=(4, 6))

        tk.Button(
            host_frame,
            text="[H]  Host Game",
            font=("Consolas", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BTN_HOST_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._launch_host,
        ).pack(side="left")

        # Vertical divider
        tk.Frame(mp_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=14)

        # Join side
        join_frame = tk.Frame(mp_row, bg=BG_DARK)
        join_frame.pack(side="left")

        tk.Label(
            join_frame,
            text="Server:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        self._join_addr_var = tk.StringVar(value="")
        self._join_entry = tk.Entry(
            join_frame,
            textvariable=self._join_addr_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=16,
        )
        self._join_entry.pack(side="left", padx=(4, 6))
        self._join_entry.insert(0, "host:7777")
        self._join_entry.config(fg=TEXT_DIM)
        self._join_entry.bind("<FocusIn>", self._on_join_focus_in)
        self._join_entry.bind("<FocusOut>", self._on_join_focus_out)

        tk.Button(
            join_frame,
            text="->  Join Game",
            font=("Consolas", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BTN_JOIN_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._launch_join,
        ).pack(side="left")

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
            self._status_var.set(f"!  {error}")
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
            self._status_var.set("OK  Up to date")

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
            self._status_var.set(f"^ {tag} is newer than installed")
        else:
            self._status_var.set(f"v {tag} is older than installed")

    def _refresh_download_btn(self) -> None:
        if not self._selected_release or self._downloading:
            return

        tag = self._selected_release.get("tag_name", "")
        ver = tag.lstrip("v")
        assets = self._selected_release.get("assets", [])
        has_exe = any(a.get("name") == GAME_EXE_NAME for a in assets)

        if not has_exe:
            self._download_btn.configure(state="disabled", text="v  No exe asset")
            return

        if ver == self._local_version:
            label = f"v  Reinstall {tag}"
        elif _is_newer(ver, self._local_version):
            label = f"^  Update to {tag}"
        else:
            label = f"v  Downgrade to {tag}"

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
        self._status_var.set(f"OK  {tag} installed. Ready to play.")

        labels = [
            _version_label(r["tag_name"], self._local_version, i == 0)
            for i, r in enumerate(self._all_releases)
        ]
        self._version_combo.configure(values=labels)
        self._refresh_download_btn()

    def _on_download_error(self, message: str) -> None:
        self._downloading = False
        self._progress_var.set(0.0)
        self._status_var.set(f"X  {message}")
        self._refresh_download_btn()

    # ── Join entry placeholder behaviour ─────────────────────────────────────

    _JOIN_PLACEHOLDER = "host:7777"

    def _on_join_focus_in(self, _event=None) -> None:
        if self._join_addr_var.get() == self._JOIN_PLACEHOLDER:
            self._join_entry.delete(0, "end")
            self._join_entry.config(fg=TEXT_PRIMARY)

    def _on_join_focus_out(self, _event=None) -> None:
        if not self._join_addr_var.get().strip():
            self._join_entry.insert(0, self._JOIN_PLACEHOLDER)
            self._join_entry.config(fg=TEXT_DIM)

    # ── Launch helpers ────────────────────────────────────────────────────────

    def _launch_with_args(self, *extra_args: str) -> None:
        """Build command for the game exe + extra_args, Popen it, then close."""
        game_path = _get_game_exe()
        if not game_path.exists():
            messagebox.showerror(
                "Game Not Found",
                f"Could not find the game at:\n{game_path}\n\nPlease download a version first.",
                parent=self.root,
            )
            return
        cmd = (
            [sys.executable, str(game_path)]
            if game_path.suffix == ".py"
            else [str(game_path)]
        )
        cmd.extend(extra_args)
        try:
            subprocess.Popen(cmd)
            self.root.after(200, self.root.destroy)
        except Exception as exc:
            messagebox.showerror("Launch Error", str(exc), parent=self.root)

    def _launch_solo(self) -> None:
        """Launch the game in single-player / solo mode."""
        self._launch_with_args()

    def _launch_host(self) -> None:
        """Start a multiplayer server and join it as the host."""
        port_str = self._host_port_var.get().strip()
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Port",
                "Port must be a whole number between 1 and 65535.",
                parent=self.root,
            )
            return
        self._launch_with_args("--host", str(port))

    def _launch_join(self) -> None:
        """Connect to an existing multiplayer server."""
        addr = self._join_addr_var.get().strip()
        if not addr or addr == self._JOIN_PLACEHOLDER:
            messagebox.showerror(
                "No Server Address",
                "Enter the server address as  host:port  (e.g. 192.168.1.5:7777).",
                parent=self.root,
            )
            return
        # Accept bare IP/hostname — default port 7777
        if ":" not in addr:
            addr = f"{addr}:7777"
        self._launch_with_args("--connect", addr)

    # ── Legacy alias kept for any external callers ────────────────────────────

    def _launch_game(self) -> None:
        self._launch_solo()

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
