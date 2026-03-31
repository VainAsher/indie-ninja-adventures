"""
Indie Ninja Adventures — Launcher

Checks for updates via the GitHub releases API, downloads and verifies
new releases, then launches the game.

Launch modes available from the UI:
  Solo Play     — launch game without multiplayer args
  Host Game     — launch with --host <port>  (starts a server + joins it)
  Join Game     — launch with --connect <host:port>

Tab 2 — Report: pre-filled GitHub issue URL (bug / feedback / performance / crash)
Tab 3 — Dev Tools: profiler benchmark, log viewer, replay launcher

Stdlib only: tkinter for UI, urllib.request for HTTP, hashlib for SHA256.
"""

import csv
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

# Game repo (private) — source of game exe releases and update checks
GAME_REPO = "VainAsher/indie-ninja-adventures"
# Launcher repo (public) — future: launcher update checks and player guides
LAUNCHER_REPO = "VainAsher/indie-ninja-launcher"
# Feedback repo (public) — player bug reports and feature requests
FEEDBACK_REPO = "VainAsher/indie-ninja-feedback"

GITHUB_REPO = GAME_REPO  # kept for backwards compatibility
RELEASES_API_URL = f"https://api.github.com/repos/{GAME_REPO}/releases?per_page=30"
ISSUES_URL = f"https://github.com/{FEEDBACK_REPO}/issues/new"
GAME_EXE_NAME = "ninja_dash.exe"
VERSION_FILE = "version.json"
LAUNCHER_VERSION = "1.1.0"
WINDOW_TITLE = "Indie Ninja Adventures"
WINDOW_W = 640
WINDOW_H = 540
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

# Report type options and their GitHub label mappings
_REPORT_TYPES = [
    ("Bug Report",        "bug",         "bug,needs-repro"),
    ("Feedback",          "feedback",    "feedback"),
    ("Performance Issue", "performance", "performance,beta-testing"),
    ("Crash Report",      "crash",       "crash,bug"),
]

# Benchmark: run for this many seconds then terminate
_BENCHMARK_SECONDS = 10

# Max log lines to embed in a GitHub report body
_LOG_TAIL_LINES = 50


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


def _get_user_data_dir() -> Path:
    base = _get_base_dir()
    env = os.environ.get("NINJADASH_USER_DATA")
    if env:
        return Path(env)
    return base / "user_data"


def _get_profiler_csv() -> Path:
    return _get_base_dir() / "docs" / "perf_baseline.csv"


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


def _list_log_files() -> list[Path]:
    """Return log files sorted newest-first."""
    log_dir = _get_user_data_dir() / "logs"
    if not log_dir.exists():
        return []
    files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    files += sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:20]


def _list_replay_files() -> list[Path]:
    """Return replay files sorted newest-first."""
    replay_dir = _get_user_data_dir() / "replays"
    if not replay_dir.exists():
        return []
    return sorted(replay_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]


def _read_tail(path: Path, n: int = _LOG_TAIL_LINES) -> str:
    """Read the last n lines of a text file."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except OSError:
        return "(could not read log file)"


def _parse_profiler_csv(csv_path: Path) -> dict | None:
    """
    Read the profiler CSV and return summary stats, or None if no data.
    Returns: {section: {avg, p95, max}, ..., fps_avg, fps_p5, fps_min, frame_count}
    """
    if not csv_path.exists():
        return None
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        result: dict = {"frame_count": len(rows)}
        sections = [c for c in rows[0] if c not in ("frame", "fps_instantaneous")]
        for sec in sections:
            vals = [float(r[sec]) for r in rows if float(r[sec]) > 0]
            if vals:
                result[sec] = {
                    "avg": statistics.mean(vals),
                    "p95": sorted(vals)[int(len(vals) * 0.95)],
                    "max": max(vals),
                }
        fps_vals = [float(r["fps_instantaneous"]) for r in rows]
        result["fps_avg"] = statistics.mean(fps_vals)
        result["fps_p5"] = sorted(fps_vals)[int(len(fps_vals) * 0.05)]
        result["fps_min"] = min(fps_vals)
        return result
    except Exception:
        return None


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
        self._benchmark_proc: subprocess.Popen | None = None
        self._benchmark_timer: threading.Timer | None = None

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

        # ── Tab styles ────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Launcher.TNotebook",
            background=BG_DARK,
            borderwidth=0,
            tabmargins=[0, 0, 0, 0],
        )
        style.configure(
            "Launcher.TNotebook.Tab",
            background=BG_MID,
            foreground=TEXT_DIM,
            font=("Consolas", 9),
            padding=[14, 5],
            borderwidth=0,
        )
        style.map(
            "Launcher.TNotebook.Tab",
            background=[("selected", BG_CARD), ("active", BG_CARD)],
            foreground=[("selected", ACCENT), ("active", TEXT_PRIMARY)],
        )
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

        # ── Notebook ──────────────────────────────────────────────────────────
        self._notebook = ttk.Notebook(root, style="Launcher.TNotebook")
        self._notebook.pack(fill="both", expand=True)

        play_frame = tk.Frame(self._notebook, bg=BG_DARK)
        report_frame = tk.Frame(self._notebook, bg=BG_DARK)
        devtools_frame = tk.Frame(self._notebook, bg=BG_DARK)

        self._notebook.add(play_frame,     text="  Play  ")
        self._notebook.add(report_frame,   text="  Report  ")
        self._notebook.add(devtools_frame, text="  Dev Tools  ")

        self._build_play_tab(play_frame)
        self._build_report_tab(report_frame)
        self._build_devtools_tab(devtools_frame)

    # ── Tab 1: Play ───────────────────────────────────────────────────────────

    def _build_play_tab(self, parent: tk.Frame) -> None:
        ctrl = tk.Frame(parent, bg=BG_DARK)
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

        tk.Label(
            host_frame,
            text="Max:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        self._max_players_var = tk.StringVar(value="4")
        tk.Spinbox(
            host_frame,
            from_=1,
            to=4,
            textvariable=self._max_players_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            buttonbackground=BG_MID,
            relief="flat",
            width=2,
            state="readonly",
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

    # ── Tab 2: Report ─────────────────────────────────────────────────────────

    def _build_report_tab(self, parent: tk.Frame) -> None:
        pad = tk.Frame(parent, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=20, pady=(10, 8))

        # Section header
        tk.Label(
            pad,
            text="SUBMIT A REPORT",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(3, 8))

        # Report type + auto-info row
        top = tk.Frame(pad, bg=BG_DARK)
        top.pack(fill="x")

        tk.Label(
            top, text="Type:", font=("Consolas", 9), fg=TEXT_DIM, bg=BG_DARK,
        ).pack(side="left")

        self._report_type_var = tk.StringVar(value=_REPORT_TYPES[0][0])
        type_combo = ttk.Combobox(
            top,
            textvariable=self._report_type_var,
            values=[r[0] for r in _REPORT_TYPES],
            state="readonly",
            style="Launcher.TCombobox",
            width=22,
            font=("Consolas", 9),
        )
        type_combo.pack(side="left", padx=(6, 0))
        type_combo.bind("<<ComboboxSelected>>", self._on_report_type_changed)

        # Auto-fill info label
        os_str = platform.system()
        ver_str = self._local_version
        self._report_info_var = tk.StringVar(
            value=f"v{ver_str}  |  {os_str}  |  Python {sys.version.split()[0]}"
        )
        tk.Label(
            top,
            textvariable=self._report_info_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="right")

        # Title
        tk.Label(
            pad, text="Title:", font=("Consolas", 9), fg=TEXT_DIM, bg=BG_DARK, anchor="w",
        ).pack(fill="x", pady=(8, 2))

        self._report_title_var = tk.StringVar(value="[Bug] ")
        tk.Entry(
            pad,
            textvariable=self._report_title_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
        ).pack(fill="x")

        # Description
        tk.Label(
            pad,
            text="Description / Steps to reproduce:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", pady=(8, 2))

        desc_frame = tk.Frame(pad, bg=BG_MID, bd=0)
        desc_frame.pack(fill="both", expand=True)

        self._report_desc = tk.Text(
            desc_frame,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            wrap="word",
            height=5,
        )
        desc_scrollbar = tk.Scrollbar(desc_frame, command=self._report_desc.yview, bg=BG_MID)
        self._report_desc.configure(yscrollcommand=desc_scrollbar.set)
        desc_scrollbar.pack(side="right", fill="y")
        self._report_desc.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        # Options row
        opts = tk.Frame(pad, bg=BG_DARK)
        opts.pack(fill="x", pady=(6, 0))

        self._attach_log_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opts,
            text="Attach last log (tail)",
            variable=self._attach_log_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_DARK,
            activeforeground=TEXT_PRIMARY,
            selectcolor=BG_MID,
            relief="flat",
        ).pack(side="left")

        # Submit button
        tk.Button(
            opts,
            text="Open Report in Browser  ->",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._open_report,
        ).pack(side="right")

    def _on_report_type_changed(self, _event=None) -> None:
        name = self._report_type_var.get()
        prefixes = {
            "Bug Report": "[Bug] ",
            "Feedback": "[Feedback] ",
            "Performance Issue": "[Perf] ",
            "Crash Report": "[Crash] ",
        }
        self._report_title_var.set(prefixes.get(name, ""))

    def _open_report(self) -> None:
        """Build a pre-filled GitHub issue URL and open it in the browser."""
        import urllib.parse

        report_name = self._report_type_var.get()
        labels = next((r[2] for r in _REPORT_TYPES if r[0] == report_name), "bug")
        title = self._report_title_var.get().strip() or report_name
        desc_raw = self._report_desc.get("1.0", "end").strip()

        os_str = platform.system()
        py_ver = sys.version.split()[0]
        game_ver = self._local_version

        body_lines = [
            f"**Version:** v{game_ver}",
            f"**OS:** {os_str}",
            f"**Python:** {py_ver}",
            "",
            "---",
            "",
            desc_raw or "(describe the issue here)",
        ]

        if self._attach_log_var.get():
            log_files = _list_log_files()
            if log_files:
                tail = _read_tail(log_files[0])
                body_lines += [
                    "",
                    "---",
                    f"**Log tail** (`{log_files[0].name}`):",
                    "```",
                    tail,
                    "```",
                ]

        body = "\n".join(body_lines)

        params = urllib.parse.urlencode({
            "title": title,
            "labels": labels,
            "body": body,
        })
        url = f"{ISSUES_URL}?{params}"
        webbrowser.open(url)

    # ── Tab 3: Dev Tools ──────────────────────────────────────────────────────

    def _build_devtools_tab(self, parent: tk.Frame) -> None:
        pad = tk.Frame(parent, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=20, pady=(10, 8))

        # ── Profiler section ──────────────────────────────────────────────────
        tk.Label(
            pad,
            text="PROFILER",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(3, 6))

        prof_btn_row = tk.Frame(pad, bg=BG_DARK)
        prof_btn_row.pack(fill="x")

        self._bench_btn = tk.Button(
            prof_btn_row,
            text=f"Run {_BENCHMARK_SECONDS}s Benchmark",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._run_benchmark,
        )
        self._bench_btn.pack(side="left")

        self._save_baseline_btn = tk.Button(
            prof_btn_row,
            text="Save as Baseline",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._save_baseline,
        )
        self._save_baseline_btn.pack(side="left", padx=(6, 0))

        self._bench_status_var = tk.StringVar(value="")
        tk.Label(
            prof_btn_row,
            textvariable=self._bench_status_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="right")

        # Baseline selector row
        prof_btn_row2 = tk.Frame(pad, bg=BG_DARK)
        prof_btn_row2.pack(fill="x", pady=(4, 0))

        tk.Label(
            prof_btn_row2,
            text="Baseline:",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        self._baseline_var = tk.StringVar()
        self._baseline_combo = ttk.Combobox(
            prof_btn_row2,
            textvariable=self._baseline_var,
            state="readonly",
            style="Launcher.TCombobox",
            width=26,
            font=("Consolas", 8),
        )
        self._baseline_combo.pack(side="left", padx=(4, 0))

        tk.Button(
            prof_btn_row2,
            text="Compare",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._compare_to_baseline,
        ).pack(side="left", padx=(6, 0))

        # Results display — scrollable Text (read-only)
        prof_text_frame = tk.Frame(pad, bg=BG_CARD)
        prof_text_frame.pack(fill="both", expand=False, pady=(6, 0))

        self._prof_txt = tk.Text(
            prof_text_frame,
            font=("Consolas", 8),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            relief="flat",
            height=8,
            wrap="none",
            state="disabled",
        )
        _prof_ys = tk.Scrollbar(prof_text_frame, orient="vertical", command=self._prof_txt.yview)
        self._prof_txt.configure(yscrollcommand=_prof_ys.set)
        _prof_ys.pack(side="right", fill="y")
        self._prof_txt.pack(fill="both", expand=True, padx=4, pady=2)

        # Load existing CSV on open
        self._refresh_baseline_list()
        self._refresh_profiler_display()

        # ── Logs section ──────────────────────────────────────────────────────
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(10, 0))
        tk.Label(
            pad,
            text="LOGS",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", pady=(4, 4))

        log_row = tk.Frame(pad, bg=BG_DARK)
        log_row.pack(fill="x")

        self._log_var = tk.StringVar()
        self._log_combo = ttk.Combobox(
            log_row,
            textvariable=self._log_var,
            state="readonly",
            style="Launcher.TCombobox",
            width=28,
            font=("Consolas", 8),
        )
        self._log_combo.pack(side="left")

        tk.Button(
            log_row,
            text="View",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._view_log,
        ).pack(side="left", padx=(6, 0))

        tk.Button(
            log_row,
            text="Reveal",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._reveal_log,
        ).pack(side="left", padx=(4, 0))

        tk.Button(
            log_row,
            text="Refresh",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=3,
            command=self._refresh_log_list,
        ).pack(side="right")

        self._refresh_log_list()

        # ── Replays section ───────────────────────────────────────────────────
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(10, 0))
        tk.Label(
            pad,
            text="REPLAYS",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", pady=(4, 4))

        replay_row = tk.Frame(pad, bg=BG_DARK)
        replay_row.pack(fill="x")

        self._replay_meta_var = tk.StringVar(value="")
        self._replay_var = tk.StringVar()
        self._replay_combo = ttk.Combobox(
            replay_row,
            textvariable=self._replay_var,
            state="readonly",
            style="Launcher.TCombobox",
            width=28,
            font=("Consolas", 8),
        )
        self._replay_combo.pack(side="left")
        self._replay_combo.bind("<<ComboboxSelected>>", self._on_replay_selected)

        tk.Button(
            replay_row,
            text="Launch Replay",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._launch_replay,
        ).pack(side="left", padx=(6, 0))

        tk.Button(
            replay_row,
            text="Delete",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=3,
            command=self._delete_selected_replay_devtools,
        ).pack(side="left", padx=(4, 0))

        tk.Button(
            replay_row,
            text="Refresh",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=3,
            command=self._refresh_replay_list,
        ).pack(side="right")

        tk.Label(
            pad,
            textvariable=self._replay_meta_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(2, 0))

        self._refresh_replay_list()

    # ── Profiler actions ──────────────────────────────────────────────────────

    def _refresh_profiler_display(self, baseline_stats: dict | None = None) -> None:
        """Read the existing profiler CSV (if any) and show all timing sections."""
        csv_path = _get_profiler_csv()
        stats = _parse_profiler_csv(csv_path)

        self._prof_txt.configure(state="normal")
        self._prof_txt.delete("1.0", "end")

        if not stats:
            self._prof_txt.insert("end", "No profiler data — run a benchmark first.")
            self._prof_txt.configure(state="disabled")
            return

        _skip = {"fps_avg", "fps_p5", "fps_min", "frame_count"}
        header = (
            f"Frames: {stats['frame_count']}   "
            f"FPS avg={stats['fps_avg']:.1f}  p5={stats['fps_p5']:.1f}  min={stats['fps_min']:.1f}\n"
        )
        col_head = f"\n  {'Section':<22s} {'avg':>7s}  {'p95':>7s}  {'max':>7s}"
        if baseline_stats:
            col_head += "   vs baseline (avg)"
        col_head += "\n  " + "-" * (44 + (22 if baseline_stats else 0))

        rows = []
        for sec in sorted(k for k in stats if k not in _skip):
            d = stats[sec]
            row = f"  {sec:<22s} {d['avg']:>6.2f}ms  {d['p95']:>6.2f}ms  {d['max']:>6.2f}ms"
            if baseline_stats and sec in baseline_stats:
                bd = baseline_stats[sec]
                delta = d["avg"] - bd["avg"]
                pct = (delta / bd["avg"] * 100) if bd["avg"] > 0 else 0.0
                sign = "+" if delta >= 0 else ""
                row += f"   {sign}{delta:.2f}ms ({sign}{pct:.0f}%)"
            rows.append(row)

        self._prof_txt.insert("end", header + col_head + "\n" + "\n".join(rows))
        self._prof_txt.configure(state="disabled")

    def _run_benchmark(self) -> None:
        """Launch the game headless with --profile, kill after N seconds, refresh display."""
        if self._benchmark_proc is not None:
            return  # already running

        game_path = _get_game_exe()
        if not game_path.exists():
            messagebox.showerror("Game Not Found", f"Could not find:\n{game_path}", parent=self.root)
            return

        cmd = (
            [sys.executable, str(game_path)] if game_path.suffix == ".py" else [str(game_path)]
        )
        cmd += ["--headless", "--profile"]

        self._bench_btn.configure(state="disabled", text="Running…")
        self._bench_status_var.set(f"Runs for {_BENCHMARK_SECONDS}s…")

        try:
            self._benchmark_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            self._benchmark_proc = None
            self._bench_btn.configure(state="normal", text=f"Run {_BENCHMARK_SECONDS}s Benchmark")
            self._bench_status_var.set(f"Launch failed: {exc}")
            return

        def _kill_and_refresh() -> None:
            proc = self._benchmark_proc
            if proc is not None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            self._benchmark_proc = None
            self._benchmark_timer = None
            self.root.after(0, self._on_benchmark_done)

        self._benchmark_timer = threading.Timer(_BENCHMARK_SECONDS, _kill_and_refresh)
        self._benchmark_timer.daemon = True
        self._benchmark_timer.start()

    def _on_benchmark_done(self) -> None:
        self._bench_btn.configure(state="normal", text=f"Run {_BENCHMARK_SECONDS}s Benchmark")
        # Give the profiler a moment to flush then parse
        self.root.after(400, self._after_benchmark_parse)

    def _after_benchmark_parse(self) -> None:
        self._refresh_profiler_display()
        stats = _parse_profiler_csv(_get_profiler_csv())
        if stats:
            self._bench_status_var.set(
                f"Done — {stats['frame_count']} frames, avg {stats['fps_avg']:.1f} FPS"
            )
        else:
            self._bench_status_var.set("Done (no CSV written — headless may have exited early)")

    def _save_baseline(self) -> None:
        """Copy current profiler CSV to a dated baseline file."""
        import shutil
        from datetime import date

        csv_path = _get_profiler_csv()
        if not csv_path.exists():
            messagebox.showinfo("No Data", "Run a benchmark first.", parent=self.root)
            return
        dated = csv_path.parent / f"perf_baseline_{date.today().isoformat()}.csv"
        try:
            shutil.copy2(csv_path, dated)
            self._bench_status_var.set(f"Saved: {dated.name}")
            self._refresh_baseline_list()
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc), parent=self.root)

    def _refresh_baseline_list(self) -> None:
        """Scan docs/ for perf_baseline*.csv files and populate the baseline combobox."""
        docs_dir = _get_base_dir() / "docs"
        files = sorted(docs_dir.glob("perf_baseline*.csv"), key=lambda p: p.name, reverse=True)
        names = [p.name for p in files if p.name != "perf_baseline.csv"]
        self._baseline_combo.configure(values=names)
        if names and not self._baseline_var.get():
            self._baseline_combo.current(0)

    def _compare_to_baseline(self) -> None:
        """Parse the selected baseline CSV and re-render the profiler display with delta column."""
        name = self._baseline_var.get()
        if not name:
            messagebox.showinfo("No Baseline", "Select a baseline CSV first.", parent=self.root)
            return
        baseline_path = _get_base_dir() / "docs" / name
        baseline_stats = _parse_profiler_csv(baseline_path)
        if not baseline_stats:
            messagebox.showerror("Parse Error", f"Could not parse {name}", parent=self.root)
            return
        self._refresh_profiler_display(baseline_stats=baseline_stats)

    # ── Log actions ───────────────────────────────────────────────────────────

    def _refresh_log_list(self) -> None:
        files = _list_log_files()
        names = [f.name for f in files]
        self._log_combo.configure(values=names)
        if names:
            self._log_combo.current(0)
        else:
            self._log_var.set("(no logs found)")

    def _view_log(self) -> None:
        name = self._log_var.get()
        if not name or name == "(no logs found)":
            return
        log_path = _get_user_data_dir() / "logs" / name
        if not log_path.exists():
            messagebox.showerror("File Not Found", str(log_path), parent=self.root)
            return

        full_content = log_path.read_text(encoding="utf-8", errors="replace")

        win = tk.Toplevel(self.root)
        win.title(f"Log — {name}")
        win.configure(bg=BG_DARK)
        win.geometry("700x440")

        # ── Filter row ────────────────────────────────────────────────────────
        filter_row = tk.Frame(win, bg=BG_DARK)
        filter_row.pack(fill="x", padx=6, pady=(6, 2))

        tk.Label(
            filter_row, text="Level:", font=("Consolas", 8), fg=TEXT_DIM, bg=BG_DARK,
        ).pack(side="left")
        level_var = tk.StringVar(value="ALL")
        level_combo = ttk.Combobox(
            filter_row,
            textvariable=level_var,
            values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            style="Launcher.TCombobox",
            width=10,
            font=("Consolas", 8),
        )
        level_combo.pack(side="left", padx=(4, 12))

        tk.Label(
            filter_row, text="Search:", font=("Consolas", 8), fg=TEXT_DIM, bg=BG_DARK,
        ).pack(side="left")
        search_var = tk.StringVar()
        search_entry = tk.Entry(
            filter_row,
            textvariable=search_var,
            font=("Consolas", 8),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=22,
        )
        search_entry.pack(side="left", padx=(4, 6))

        # ── Log text area ─────────────────────────────────────────────────────
        text = tk.Text(
            win,
            font=("Consolas", 8),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            wrap="none",
            relief="flat",
        )
        ys = tk.Scrollbar(win, orient="vertical", command=text.yview)
        xs = tk.Scrollbar(win, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        xs.pack(side="bottom", fill="x")
        ys.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)

        def _apply_filter(*_args) -> None:
            level = level_var.get()
            search = search_var.get().lower()
            lines = full_content.splitlines()
            if level != "ALL":
                lines = [ln for ln in lines if level in ln]
            if search:
                lines = [ln for ln in lines if search in ln.lower()]
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", "\n".join(lines))
            text.see("end")
            text.configure(state="disabled")

        tk.Button(
            filter_row,
            text="Apply",
            font=("Consolas", 8),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=2,
            command=_apply_filter,
        ).pack(side="left")
        tk.Button(
            filter_row,
            text="Clear",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=2,
            command=lambda: (search_var.set(""), level_var.set("ALL"), _apply_filter()),
        ).pack(side="left", padx=(4, 0))

        search_entry.bind("<Return>", _apply_filter)
        level_combo.bind("<<ComboboxSelected>>", _apply_filter)
        _apply_filter()

    def _reveal_log(self) -> None:
        name = self._log_var.get()
        if not name or name == "(no logs found)":
            return
        log_dir = _get_user_data_dir() / "logs"
        try:
            os.startfile(str(log_dir))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(log_dir)])

    # ── Replay actions ────────────────────────────────────────────────────────

    def _refresh_replay_list(self) -> None:
        files = _list_replay_files()
        names = [f.name for f in files]
        self._replay_combo.configure(values=names)
        if names:
            self._replay_combo.current(0)
            self._on_replay_selected()
        else:
            self._replay_var.set("(no replays found)")
            self._replay_meta_var.set("")

    def _on_replay_selected(self, _event=None) -> None:
        """Read selected replay JSON and display its metadata."""
        name = self._replay_var.get()
        if not name or name.startswith("("):
            self._replay_meta_var.set("")
            return
        path = _get_user_data_dir() / "replays" / name
        if not path.exists():
            self._replay_meta_var.set("(file not found)")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._replay_meta_var.set("(could not read file)")
            return
        meta = data.get("metadata", {})
        frame_count = len(data.get("commands", []))
        parts: list[str] = []
        if "hub_id" in meta:
            parts.append(f"Hub: {meta['hub_id']}")
        if "mission_id" in meta:
            parts.append(f"Mission: {meta['mission_id']}")
        if frame_count:
            parts.append(f"Frames: {frame_count:,}")
        if "world_seed" in meta:
            parts.append(f"Seed: {meta['world_seed']}")
        self._replay_meta_var.set("  |  ".join(parts) if parts else "No metadata")

    def _delete_selected_replay_devtools(self) -> None:
        """Confirm and delete the selected replay file."""
        name = self._replay_var.get()
        if not name or name.startswith("("):
            return
        if not messagebox.askyesno("Delete Replay", f"Delete '{name}'?", parent=self.root):
            return
        path = _get_user_data_dir() / "replays" / name
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            messagebox.showerror("Delete Failed", str(exc), parent=self.root)
            return
        self._refresh_replay_list()

    def _launch_replay(self) -> None:
        name = self._replay_var.get()
        if not name or name == "(no replays found)":
            return
        self._launch_with_args("--replay", name, "--show-replay")

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
        try:
            max_players = int(self._max_players_var.get())
            if not (1 <= max_players <= 4):
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Max Players",
                "Max players must be a number between 1 and 4.",
                parent=self.root,
            )
            return
        self._launch_with_args("--host", str(port), "--max-players", str(max_players))

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
