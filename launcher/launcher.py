"""
Shadow Ascent: The Hollowed Ninja — Launcher

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

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import uuid
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
SERVER_JAR_NAME = "ninja-server-all.jar"
CLIENT_JAR_NAME = "ninja-client-all.jar"
VERSION_FILE = "version.json"
LAUNCHER_VERSION = "1.8.0"
JAVA_MIN_VERSION = 21
WINDOW_TITLE = "Shadow Ascent: The Hollowed Ninja"
WINDOW_W = 760
WINDOW_H = 640
SPLASH_W = 640  # splash image/text stays fixed at 640; window can be wider
SPLASH_H = 200  # canvas height — crops the 640×320 scaled image to top portion
PLAYER_EXPECTATIONS_REL_PATH = Path("docs") / "PLAYER_EXPECTATIONS.md"

# Colours — matched to game's menu_system.py palette
BG_DARK = "#0a0a14"  # (10, 10, 20)  — game bg_color
BG_MID = "#1a1a2e"
BG_CARD = "#16213e"
ACCENT = "#ffd700"  # gold — game title_color (255, 215, 0)
TEXT_PRIMARY = "#c8c8dc"  # game item_color (200, 200, 220)
TEXT_DIM = "#888899"
TEXT_SELECTED = "#ffff64"  # game selected_color (255, 255, 100)
BTN_PLAY_BG = "#1a1a2e"
PROGRESS_FG = "#ffd700"  # gold progress bar

# Multiplayer button accent colours
BTN_HOST_BG = "#1a2e1a"  # dark green tint
BTN_JOIN_BG = "#1a1a2e"

# Report type options and their GitHub label mappings
_REPORT_TYPES = [
    ("Bug Report", "bug", "bug,needs-repro"),
    ("Feedback", "feedback", "feedback"),
    ("Performance Issue", "performance", "performance,beta-testing"),
    ("Crash Report", "crash", "crash,bug"),
]

# Max log lines to embed in a GitHub report body
_LOG_TAIL_LINES = 50


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _get_launcher_exe_dir() -> Path:
    """The directory containing the launcher executable (or launcher.py in dev mode).
    This is where launcher_config.json is always stored — independent of game_dir."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # Dev mode: launcher.py lives in <root>/launcher/
    return Path(__file__).parent


def _get_launcher_config_path() -> Path:
    return _get_launcher_exe_dir() / "launcher_config.json"


def _read_launcher_config() -> dict:
    try:
        return json.loads(_get_launcher_config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_launcher_config(cfg: dict) -> None:
    path = _get_launcher_config_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(path)


def _default_game_dir() -> Path:
    """The game directory used when no launcher_config.json exists."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # Dev mode: launcher.py in <root>/launcher/, game at <root>/
    return Path(__file__).parent.parent


# Module-level current game directory — initialised lazily on first call to _get_base_dir().
# Update this (and write launcher_config.json) whenever the user changes the game directory.
_GAME_DIR: Path | None = None


def _get_base_dir() -> Path:
    """Return the configured game directory (game exe + user_data + mods live here)."""
    global _GAME_DIR
    if _GAME_DIR is None:
        cfg = _read_launcher_config()
        candidate = cfg.get("game_dir")
        if candidate:
            p = Path(candidate)
            if p.is_dir():
                _GAME_DIR = p
        if _GAME_DIR is None:
            _GAME_DIR = _default_game_dir()
    return _GAME_DIR


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


def _get_profiles_path() -> Path:
    return _get_user_data_dir() / "profiles" / "profiles.json"


def _format_bytes(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n // 1024} KB"
    return f"{n} B"


def _get_saves_dir() -> Path:
    return _get_user_data_dir() / "saves"


def _format_playtime(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


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
    """Return replay files sorted newest-first.

    Accepts both .json (Python replay format) and .ndjson (Java InputRecorder format).
    """
    replay_dir = _get_user_data_dir() / "replays"
    if not replay_dir.exists():
        return []
    files = list(replay_dir.glob("*.json")) + list(replay_dir.glob("*.ndjson"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:20]


def _read_replay_meta(path: Path) -> dict:
    """Read a replay file and return its metadata.

    Supports two formats:
      .json   — Python format: single JSON object with a 'commands' list.
      .ndjson — Java InputRecorder format: first line is a header JSON object
                {"type":"header","seed":<long>,"entries":<int>}, subsequent lines
                are per-frame input records.
    """
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".ndjson":
            # Only the first line contains metadata; rest are input frames.
            header = json.loads(text.splitlines()[0])
            return {
                "world_seed": header.get("seed", ""),
                "entries": header.get("entries", ""),
                "format": "ndjson",
            }
        data = json.loads(text)
        return {k: v for k, v in data.items() if k != "commands"}
    except Exception:
        return {}


def _read_tail(path: Path, n: int = _LOG_TAIL_LINES) -> str:
    """Read the last n lines of a text file."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except OSError:
        return "(could not read log file)"


def _get_server_jar() -> Path:
    return _get_base_dir() / SERVER_JAR_NAME


def _get_client_jar() -> Path:
    return _get_base_dir() / CLIENT_JAR_NAME


def _find_java_exe() -> str | None:
    """Return path to a java executable (>= JAVA_MIN_VERSION), or None."""
    # 1. java on PATH
    java = shutil.which("java")
    if java:
        return java
    # 2. Common Windows install locations
    if platform.system() == "Windows":
        import glob as _glob

        patterns = [
            r"C:\Program Files\Java\*\bin\java.exe",
            r"C:\Program Files\Eclipse Adoptium\*\bin\java.exe",
            r"C:\Program Files\Microsoft\*\bin\java.exe",
            r"C:\Program Files\Eclipse Foundation\*\bin\java.exe",
        ]
        for pat in patterns:
            hits = sorted(_glob.glob(pat), reverse=True)
            if hits:
                return hits[0]
    return None


def _detect_java() -> tuple[bool, str]:
    """Return (ok, message) — ok=True if Java >= JAVA_MIN_VERSION is available."""
    exe = _find_java_exe()
    if not exe:
        return False, f"Java not found — Java {JAVA_MIN_VERSION}+ required"
    try:
        result = subprocess.run(
            [exe, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stderr or result.stdout  # java -version writes to stderr
        # Parse: 'openjdk version "21.0.2" ...' or 'java version "1.8.0_...'
        m = re.search(r'"(\d+)(?:\.(\d+))?', output)
        if not m:
            return False, "Java found but version unreadable"
        major = int(m.group(1))
        if major == 1:
            # Old-style: 1.8 → 8
            major = int(m.group(2) or 0)
        if major < JAVA_MIN_VERSION:
            return False, f"Java {major} found — Java {JAVA_MIN_VERSION}+ required"
        # Grab the full quoted version string for display
        vm = re.search(r'"([^"]+)"', output)
        ver_str = vm.group(1) if vm else str(major)
        return True, f"Java {ver_str}"
    except Exception as exc:
        return False, f"Java check failed: {exc}"


def _find_jar_asset(assets: list[dict], prefix: str) -> dict | None:
    """Return the first release asset whose name starts with prefix and ends with -all.jar."""
    for a in assets:
        name = a.get("name", "")
        if name.startswith(prefix) and name.endswith("-all.jar"):
            return a
    return None


def _is_port_in_use(port: int) -> bool:
    """Return True if something is already listening on the given TCP port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def _kill_process_on_port(port: int) -> bool:
    """Terminate whatever process is listening on the given port.
    Returns True if the port is free afterwards, False on failure."""
    import platform, time

    try:
        if platform.system() == "Windows":
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        subprocess.run(["taskkill", "/F", "/PID", parts[-1]], capture_output=True)
                        break
        else:
            subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
    except Exception:
        pass
    time.sleep(0.3)
    return not _is_port_in_use(port)


# ──────────────────────────────────────────────────────────────────────────────
# LauncherApp
# ──────────────────────────────────────────────────────────────────────────────


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.resizable(True, True)
        self.root.minsize(640, 540)
        self.root.configure(bg=BG_DARK)

        self._local_version = _read_local_version()
        self._all_releases: list[dict] = []
        self._selected_release: dict | None = None
        self._downloading = False
        self._download_cancel = threading.Event()
        self._splash_photo: tk.PhotoImage | None = None
        self._java_server_proc: subprocess.Popen | None = None
        self._record_var = tk.IntVar(value=0)
        self._record_name_var = tk.StringVar(value="")
        self._settings_vars: dict[str, tk.Variable] = {}
        self._save_fields: dict[str, tk.StringVar] = {}
        self._java_ok, self._java_version_str = _detect_java()
        # Initialise _GAME_DIR before UI is built so the first call to _get_base_dir()
        # inside any tab builder picks up the configured path.
        _get_base_dir()
        self._game_dir_var = tk.StringVar(value=str(_get_base_dir()))

        self._build_ui()

        # Centre window after UI is built (so winfo_reqwidth is accurate)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - WINDOW_W) // 2
        y = (sh - WINDOW_H) // 2
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

        threading.Thread(target=self._fetch_releases, daemon=True).start()
        self._schedule_periodic_check()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root

        # ── Splash canvas ─────────────────────────────────────────────────────
        self._splash_canvas = tk.Canvas(
            root,
            width=SPLASH_W,
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
            tx + 2,
            ty + 2,
            text="SHADOW ASCENT",
            font=("Impact", 21),
            fill="#050510",
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx,
            ty,
            text="SHADOW ASCENT",
            font=("Impact", 21),
            fill=ACCENT,
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx,
            ty + 18,
            text="THE HOLLOWED NINJA",
            font=("Consolas", 9, "bold"),
            fill=TEXT_PRIMARY,
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx,
            ty - 22,
            text="Vain Asher Gaming  |  Code name: Indie Ninja Adventures",
            font=("Consolas", 9),
            fill=TEXT_DIM,
            anchor="sw",
        )
        self._splash_canvas.create_text(
            SPLASH_W - 8,
            SPLASH_H - 6,
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
        style.configure(
            "Replay.Treeview",
            background=BG_CARD,
            foreground=TEXT_PRIMARY,
            fieldbackground=BG_CARD,
            rowheight=20,
            font=("Consolas", 8),
            borderwidth=0,
        )
        style.configure(
            "Replay.Treeview.Heading",
            background=BG_MID,
            foreground=ACCENT,
            font=("Consolas", 8, "bold"),
            relief="flat",
        )
        style.map(
            "Replay.Treeview",
            background=[("selected", BG_MID)],
            foreground=[("selected", TEXT_SELECTED)],
        )

        # ── Notebook ──────────────────────────────────────────────────────────
        self._notebook = ttk.Notebook(root, style="Launcher.TNotebook")
        self._notebook.pack(fill="both", expand=True)

        play_frame = tk.Frame(self._notebook, bg=BG_DARK)
        report_frame = tk.Frame(self._notebook, bg=BG_DARK)
        devtools_frame = tk.Frame(self._notebook, bg=BG_DARK)
        replays_frame = tk.Frame(self._notebook, bg=BG_DARK)
        saves_frame = tk.Frame(self._notebook, bg=BG_DARK)
        settings_frame = tk.Frame(self._notebook, bg=BG_DARK)

        self._notebook.add(play_frame, text="  Play  ")
        self._notebook.add(report_frame, text="  Report  ")
        self._notebook.add(devtools_frame, text="  Dev Tools  ")
        self._notebook.add(replays_frame, text="  Replays  ")
        self._notebook.add(saves_frame, text="  Saves  ")
        self._notebook.add(settings_frame, text="  Settings  ")

        self._build_play_tab(play_frame)
        self._build_report_tab(report_frame)
        self._build_devtools_tab(devtools_frame)
        self._build_replays_tab(replays_frame)
        self._build_saves_tab(saves_frame)
        self._build_settings_tab(settings_frame)

    # ── Tab 1: Play ───────────────────────────────────────────────────────────

    def _build_play_tab(self, parent: tk.Frame) -> None:
        ctrl = tk.Frame(parent, bg=BG_DARK)
        ctrl.pack(fill="both", expand=True, padx=20, pady=(8, 6))

        # Installed version + status on one row
        top_row = tk.Frame(ctrl, bg=BG_DARK)
        top_row.pack(fill="x")

        self._installed_label_var = tk.StringVar(value=f"Installed:  v{self._local_version}")
        tk.Label(
            top_row,
            textvariable=self._installed_label_var,
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

        # ── Profile row ───────────────────────────────────────────────────────
        prof_row = tk.Frame(ctrl, bg=BG_DARK)
        prof_row.pack(fill="x", pady=(6, 0))

        tk.Label(
            prof_row,
            text="Profile:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        self._profile_var = tk.StringVar()
        self._profile_combo = ttk.Combobox(
            prof_row,
            textvariable=self._profile_var,
            state="readonly",
            style="Launcher.TCombobox",
            width=18,
            font=("Consolas", 9),
        )
        self._profile_combo.pack(side="left", padx=(8, 0))
        self._profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        tk.Button(
            prof_row,
            text="+ New",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._on_new_profile,
        ).pack(side="left", padx=(8, 0))

        self._load_profiles()

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

        # ── Play / Install / Exit button row ──────────────────────────────────
        btn_row = tk.Frame(ctrl, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(8, 0))

        self._play_btn = tk.Button(
            btn_row,
            text=">>  Play",
            font=("Consolas", 10, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=5,
            command=self._launch_java_solo,
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

        self._cancel_btn = tk.Button(
            btn_row,
            text="Cancel",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._cancel_download,
        )
        # Not packed here — shown only during an active download

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

        # ── Runtime status row ────────────────────────────────────────────────
        tk.Frame(ctrl, height=1, bg=ACCENT).pack(fill="x", pady=(10, 0))

        java_header = tk.Frame(ctrl, bg=BG_DARK)
        java_header.pack(fill="x", pady=(4, 0))
        tk.Label(
            java_header,
            text="RUNTIME",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
        ).pack(side="left")

        # Status row: Java runtime + JAR state
        java_status_row = tk.Frame(ctrl, bg=BG_DARK)
        java_status_row.pack(fill="x", pady=(4, 0))

        java_color = "#4caf50" if self._java_ok else "#e53935"
        self._java_runtime_var = tk.StringVar(value=self._java_version_str)
        tk.Label(
            java_status_row,
            textvariable=self._java_runtime_var,
            font=("Consolas", 8),
            fg=java_color,
            bg=BG_DARK,
        ).pack(side="left")

        if not self._java_ok:
            tk.Button(
                java_status_row,
                text="Get Java",
                font=("Consolas", 8),
                fg=ACCENT,
                bg=BG_DARK,
                activebackground=BG_MID,
                activeforeground=TEXT_SELECTED,
                relief="flat",
                cursor="hand2",
                padx=6,
                pady=1,
                command=lambda: webbrowser.open("https://adoptium.net/"),
            ).pack(side="left", padx=(8, 0))

        tk.Frame(java_status_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=10)

        self._java_jar_var = tk.StringVar()
        self._java_jar_label = tk.Label(
            java_status_row,
            textvariable=self._java_jar_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        )
        self._java_jar_label.pack(side="left")

        # ── Multiplayer section ───────────────────────────────────────────────
        tk.Frame(ctrl, height=1, bg=ACCENT).pack(fill="x", pady=(10, 0))
        tk.Label(
            ctrl,
            text="MULTIPLAYER",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        # Host row: Port + Max + Host+Play + Start Server Only
        host_row = tk.Frame(ctrl, bg=BG_DARK)
        host_row.pack(fill="x", pady=(6, 0))

        tk.Label(host_row, text="Port:", font=("Consolas", 9), fg=TEXT_DIM, bg=BG_DARK).pack(
            side="left"
        )
        self._host_port_var = tk.StringVar(value="7777")
        tk.Entry(
            host_row,
            textvariable=self._host_port_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=6,
        ).pack(side="left", padx=(4, 8))

        tk.Label(host_row, text="Max:", font=("Consolas", 9), fg=TEXT_DIM, bg=BG_DARK).pack(
            side="left"
        )
        self._max_players_var = tk.StringVar(value="4")
        tk.Spinbox(
            host_row,
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
        ).pack(side="left", padx=(4, 10))

        self._java_host_play_btn = tk.Button(
            host_row,
            text="[H]  Host + Play",
            font=("Consolas", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BTN_HOST_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._launch_java_host_play,
        )
        self._java_host_play_btn.pack(side="left")

        tk.Frame(host_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=10)

        self._java_server_btn = tk.Button(
            host_row,
            text="[S]  Start Server",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BTN_HOST_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._launch_java_server,
        )
        self._java_server_btn.pack(side="left")

        # Join row: server address + Join + Ping
        join_row = tk.Frame(ctrl, bg=BG_DARK)
        join_row.pack(fill="x", pady=(6, 0))

        tk.Label(join_row, text="Server:", font=("Consolas", 9), fg=TEXT_DIM, bg=BG_DARK).pack(
            side="left"
        )
        self._java_addr_var = tk.StringVar(value="")
        self._java_addr_entry = tk.Entry(
            join_row,
            textvariable=self._java_addr_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_DIM,
            insertbackground=ACCENT,
            relief="flat",
            width=16,
        )
        self._java_addr_entry.pack(side="left", padx=(4, 6))
        self._java_addr_entry.insert(0, "host:7777")
        self._java_addr_entry.bind("<FocusIn>", self._on_java_addr_focus_in)
        self._java_addr_entry.bind("<FocusOut>", self._on_java_addr_focus_out)

        self._java_join_btn = tk.Button(
            join_row,
            text="->  Join",
            font=("Consolas", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BTN_JOIN_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._launch_java_join,
        )
        self._java_join_btn.pack(side="left")

        tk.Frame(join_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=10)

        tk.Button(
            join_row,
            text="Ping",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._ping_server_addr,
        ).pack(side="left")
        self._ping_result_var = tk.StringVar(value="")
        self._ping_result_label_widget = tk.Label(
            join_row,
            textvariable=self._ping_result_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        )
        self._ping_result_label_widget.pack(side="left", padx=(4, 0))

        # ── Changelog / News Feed ─────────────────────────────────────────────
        tk.Frame(ctrl, height=1, bg=BG_MID).pack(fill="x", pady=(12, 0))
        changelog_header = tk.Frame(ctrl, bg=BG_DARK)
        changelog_header.pack(fill="x", pady=(4, 0))
        tk.Label(
            changelog_header,
            text="LATEST RELEASE",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
        ).pack(side="left")
        self._changelog_tag_var = tk.StringVar(value="")
        tk.Label(
            changelog_header,
            textvariable=self._changelog_tag_var,
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left", padx=(8, 0))

        cl_frame = tk.Frame(ctrl, bg=BG_CARD)
        cl_frame.pack(fill="x", pady=(4, 0))
        self._changelog_txt = tk.Text(
            cl_frame,
            font=("Consolas", 8),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            wrap="word",
            relief="flat",
            height=5,
            state="disabled",
        )
        cl_ys = ttk.Scrollbar(cl_frame, orient="vertical", command=self._changelog_txt.yview)
        self._changelog_txt.configure(yscrollcommand=cl_ys.set)
        cl_ys.pack(side="right", fill="y")
        self._changelog_txt.pack(fill="both", expand=True)

        # All play-tab buttons now exist — safe to update states
        self._refresh_java_section()

    # ── Profile actions ───────────────────────────────────────────────────────

    def _read_profiles(self) -> dict:
        from datetime import date

        _default: dict = {
            "active_profile": "Player1",
            "profiles": {"Player1": {"created": str(date.today()), "save_slot": "savegame.json"}},
        }
        path = _get_profiles_path()
        if not path.exists():
            return _default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return _default

    def _write_profiles(self, data: dict) -> None:
        path = _get_profiles_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _load_profiles(self) -> None:
        data = self._read_profiles()
        names = list(data.get("profiles", {}).keys()) or ["Player1"]
        active = data.get("active_profile", names[0])
        self._profile_combo.configure(values=names)
        if active in names:
            self._profile_var.set(active)
        else:
            self._profile_combo.current(0)

    def _ensure_profile_player_id(self, profile_name: str) -> str:
        data = self._read_profiles()
        profiles = data.setdefault("profiles", {})
        profile = profiles.setdefault(profile_name, {"created": "", "save_slot": "savegame.json"})
        pid = str(profile.get("player_id", "")).strip()
        try:
            pid = str(uuid.UUID(pid))
        except Exception:
            pid = str(uuid.uuid4())
            profile["player_id"] = pid
            self._write_profiles(data)
        return pid

    def _on_profile_selected(self, _event=None) -> None:
        name = self._profile_var.get()
        if not name:
            return
        data = self._read_profiles()
        data["active_profile"] = name
        self._write_profiles(data)

    def _on_new_profile(self) -> None:
        from tkinter import simpledialog
        from datetime import date

        name = simpledialog.askstring("New Profile", "Profile name:", parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        data = self._read_profiles()
        if name in data.get("profiles", {}):
            messagebox.showwarning("Exists", f"Profile '{name}' already exists.", parent=self.root)
            return
        data.setdefault("profiles", {})[name] = {
            "created": str(date.today()),
            "save_slot": "savegame.json",
        }
        data["active_profile"] = name
        self._write_profiles(data)
        self._load_profiles()

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
            top,
            text="Type:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
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
            value=f"v{ver_str}  |  {os_str}  |  {self._java_version_str}"
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
            pad,
            text="Title:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
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
        game_ver = self._local_version

        body_lines = [
            f"**Version:** v{game_ver}",
            f"**OS:** {os_str}",
            f"**Java:** {self._java_version_str}",
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

        params = urllib.parse.urlencode(
            {
                "title": title,
                "labels": labels,
                "body": body,
            }
        )
        url = f"{ISSUES_URL}?{params}"
        webbrowser.open(url)

    # ── Tab 3: Dev Tools ──────────────────────────────────────────────────────

    def _build_devtools_tab(self, parent: tk.Frame) -> None:
        pad = tk.Frame(parent, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=20, pady=(10, 8))

        # ── JAR Info section ──────────────────────────────────────────────────
        tk.Label(
            pad,
            text="JAR INFO",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(3, 6))

        jar_info_frame = tk.Frame(pad, bg=BG_CARD)
        jar_info_frame.pack(fill="x", pady=(0, 4))
        self._jar_info_var = tk.StringVar(value="(click Refresh to check JARs)")
        tk.Label(
            jar_info_frame,
            textvariable=self._jar_info_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_CARD,
            anchor="w",
            justify="left",
            padx=6,
            pady=4,
        ).pack(fill="x")

        jar_btn_row = tk.Frame(pad, bg=BG_DARK)
        jar_btn_row.pack(fill="x", pady=(2, 0))
        tk.Button(
            jar_btn_row,
            text="Refresh JAR Info",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=3,
            command=self._refresh_jar_info,
        ).pack(side="left")
        tk.Button(
            jar_btn_row,
            text="Verify SHA256",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=3,
            command=self._verify_jar_sha256,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            jar_btn_row,
            text="Open Game Dir",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=3,
            command=self._reveal_game_dir,
        ).pack(side="right")

        self._refresh_jar_info()

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
            activeforeground="#e53935",
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

        # Metadata display
        self._replay_meta_var = tk.StringVar(value="")
        tk.Label(
            pad,
            textvariable=self._replay_meta_var,
            font=("Consolas", 7),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(2, 0))

        self._refresh_replay_list()

    # ── Tab 4: Replays ────────────────────────────────────────────────────────

    def _build_replays_tab(self, parent: tk.Frame) -> None:
        pad = tk.Frame(parent, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=16, pady=(8, 6))

        tk.Label(
            pad,
            text="REPLAYS",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(3, 6))

        # Treeview
        tree_frame = tk.Frame(pad, bg=BG_CARD)
        tree_frame.pack(fill="both", expand=True)

        cols = ("name", "mode", "hub", "frames", "date")
        self._replay_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            style="Replay.Treeview",
            height=8,
            selectmode="browse",
        )
        for col, width, label in [
            ("name", 180, "Name"),
            ("mode", 70, "Mode"),
            ("hub", 90, "Hub"),
            ("frames", 60, "Frames"),
            ("date", 82, "Date"),
        ]:
            self._replay_tree.heading(col, text=label, anchor="w")
            self._replay_tree.column(col, width=width, minwidth=40, stretch=(col == "name"))

        tree_ys = tk.Scrollbar(tree_frame, orient="vertical", command=self._replay_tree.yview)
        self._replay_tree.configure(yscrollcommand=tree_ys.set)
        tree_ys.pack(side="right", fill="y")
        self._replay_tree.pack(fill="both", expand=True)
        self._replay_tree.bind("<<TreeviewSelect>>", self._on_replay_tree_select)

        # Detail panel
        detail_frame = tk.Frame(pad, bg=BG_CARD)
        detail_frame.pack(fill="x", pady=(6, 0))

        self._replay_detail_var = tk.StringVar(value="Select a replay to see details.")
        tk.Label(
            detail_frame,
            textvariable=self._replay_detail_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_CARD,
            anchor="w",
            justify="left",
            padx=6,
            pady=4,
        ).pack(fill="x")

        # Action buttons
        btn_row = tk.Frame(pad, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(8, 0))

        _b = dict(font=("Consolas", 9), relief="flat", cursor="hand2", padx=10, pady=4)
        tk.Button(
            btn_row,
            text=">>  Launch",
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            command=self._launch_selected_replay,
            **_b,
        ).pack(side="left")
        tk.Button(
            btn_row,
            text="Delete",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._delete_selected_replay,
            **_b,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Rename",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._rename_selected_replay,
            **_b,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Open Folder",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._reveal_replay_dir,
            **_b,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Refresh",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._refresh_replays_tab,
            **_b,
        ).pack(side="right")

        # Record on next launch
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(10, 0))
        rec_row = tk.Frame(pad, bg=BG_DARK)
        rec_row.pack(fill="x", pady=(6, 0))

        tk.Checkbutton(
            rec_row,
            text="Record on next launch:",
            variable=self._record_var,
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_DARK,
            activeforeground=TEXT_PRIMARY,
            selectcolor=BG_MID,
            relief="flat",
        ).pack(side="left")
        tk.Entry(
            rec_row,
            textvariable=self._record_name_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=20,
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            rec_row,
            text=".json",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left", padx=(2, 0))

        self._refresh_replays_tab()

    # ── Replays tab actions ───────────────────────────────────────────────────

    def _refresh_replays_tab(self) -> None:
        for row in self._replay_tree.get_children():
            self._replay_tree.delete(row)
        files = _list_replay_files()
        for path in files:
            meta = _read_replay_meta(path)
            mode = meta.get("mode", "")
            hub = meta.get("hub_id", "")
            frames = meta.get("terminated_frame", "")
            try:
                date_str = time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime))
            except OSError:
                date_str = ""
            self._replay_tree.insert(
                "",
                "end",
                iid=str(path),
                values=(path.name, mode, hub, str(frames), date_str),
            )
        if files:
            first = self._replay_tree.get_children()[0]
            self._replay_tree.selection_set(first)
            self._replay_tree.focus(first)
            self._on_replay_tree_select()
        else:
            self._replay_detail_var.set("No replays found in user_data/replays/")
        # Keep Dev Tools replay combo in sync
        self._refresh_replay_list()

    def _on_replay_tree_select(self, _event=None) -> None:
        sel = self._replay_tree.selection()
        if not sel:
            return
        meta = _read_replay_meta(Path(sel[0]))
        world_seed = meta.get("world_seed", "—")
        current_seed = meta.get("current_seed", "—")
        start = meta.get("game_start_frame", "—")
        end = meta.get("terminated_frame", "—")
        procedural = "Yes" if meta.get("procedural") else "No"
        mission = meta.get("mission_id") or "—"
        self._replay_detail_var.set(
            f"World seed: {world_seed}   Current seed: {current_seed}   "
            f"Procedural: {procedural}   Mission: {mission}\n"
            f"Frame range: {start} → {end}"
        )

    def _launch_selected_replay(self) -> None:
        sel = self._replay_tree.selection()
        if not sel:
            messagebox.showwarning(
                "No Replay Selected", "Select a replay in the list first.", parent=self.root
            )
            return
        self._launch_with_args("--replay", Path(sel[0]).name, "--show-replay")

    def _delete_selected_replay(self) -> None:
        sel = self._replay_tree.selection()
        if not sel:
            return
        path = Path(sel[0])
        if not messagebox.askyesno(
            "Delete Replay",
            f"Delete '{path.name}'?\n\nThis cannot be undone.",
            parent=self.root,
        ):
            return
        try:
            path.unlink()
        except OSError as exc:
            messagebox.showerror("Delete Failed", str(exc), parent=self.root)
            return
        self._refresh_replays_tab()

    def _rename_selected_replay(self) -> None:
        from tkinter import simpledialog

        sel = self._replay_tree.selection()
        if not sel:
            return
        path = Path(sel[0])
        new_name = simpledialog.askstring(
            "Rename Replay", "New name:", initialvalue=path.stem, parent=self.root
        )
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        if not new_name.endswith(".json"):
            new_name += ".json"
        dest = path.parent / new_name
        if dest.exists():
            messagebox.showwarning("Exists", f"'{new_name}' already exists.", parent=self.root)
            return
        try:
            path.rename(dest)
        except OSError as exc:
            messagebox.showerror("Rename Failed", str(exc), parent=self.root)
            return
        self._refresh_replays_tab()

    def _reveal_replay_dir(self) -> None:
        replay_dir = _get_user_data_dir() / "replays"
        replay_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(replay_dir))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(replay_dir)])

    # ── Tab 5: Saves ──────────────────────────────────────────────────────────
    # (renumbered; Mods is Tab 7 added below Tab 6 Settings)

    def _build_saves_tab(self, parent: tk.Frame) -> None:
        pad = tk.Frame(parent, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=16, pady=(8, 6))

        # Header
        hdr_row = tk.Frame(pad, bg=BG_DARK)
        hdr_row.pack(fill="x")
        tk.Label(
            hdr_row,
            text="SAVE FILE",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")
        self._save_status_var = tk.StringVar(value="—")
        tk.Label(
            hdr_row,
            textvariable=self._save_status_var,
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="e",
        ).pack(side="right")
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(3, 6))

        # File info
        info_row = tk.Frame(pad, bg=BG_DARK)
        info_row.pack(fill="x")
        self._save_path_var = tk.StringVar(value="—")
        tk.Label(
            info_row,
            textvariable=self._save_path_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")
        self._save_date_var = tk.StringVar(value="")
        tk.Label(
            info_row,
            textvariable=self._save_date_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="e",
        ).pack(side="right")

        # Data panels
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(8, 4))
        data_row = tk.Frame(pad, bg=BG_DARK)
        data_row.pack(fill="x")

        camp_frame = tk.Frame(data_row, bg=BG_DARK)
        camp_frame.pack(side="left", fill="both", expand=True)
        stats_frame = tk.Frame(data_row, bg=BG_DARK)
        stats_frame.pack(side="left", fill="both", expand=True)

        tk.Label(
            camp_frame,
            text="CAMPAIGN",
            font=("Consolas", 8, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            stats_frame,
            text="STATISTICS",
            font=("Consolas", 8, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")

        def _field(parent_f: tk.Frame, key: str, label: str) -> None:
            var = tk.StringVar(value="—")
            self._save_fields[key] = var
            row = tk.Frame(parent_f, bg=BG_DARK)
            row.pack(fill="x")
            tk.Label(
                row,
                text=f"{label}:",
                font=("Consolas", 8),
                fg=TEXT_DIM,
                bg=BG_DARK,
                width=16,
                anchor="w",
            ).pack(side="left")
            tk.Label(
                row,
                textvariable=var,
                font=("Consolas", 8),
                fg=TEXT_PRIMARY,
                bg=BG_DARK,
                anchor="w",
            ).pack(side="left")

        _field(camp_frame, "hub", "Hub")
        _field(camp_frame, "currency", "Currency")
        _field(camp_frame, "abilities", "Abilities")
        _field(camp_frame, "missions", "Missions done")
        _field(camp_frame, "bosses", "Bosses beaten")
        _field(camp_frame, "c_playtime", "Playtime")

        _field(stats_frame, "deaths", "Deaths")
        _field(stats_frame, "jumps", "Jumps")
        _field(stats_frame, "dashes", "Dashes")
        _field(stats_frame, "coins", "Coins collected")
        _field(stats_frame, "s_playtime", "Playtime")
        _field(stats_frame, "perf_runs", "Perfect runs")

        # Action buttons
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(10, 0))
        btn_row = tk.Frame(pad, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(6, 0))
        _b = dict(font=("Consolas", 9), relief="flat", cursor="hand2", padx=10, pady=4)
        tk.Button(
            btn_row,
            text="Backup Now",
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            command=self._backup_save_now,
            **_b,
        ).pack(side="left")
        tk.Button(
            btn_row,
            text="Restore Selected",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._restore_selected_backup,
            **_b,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Delete Save",
            fg="#e05252",
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground="#e05252",
            command=self._delete_save,
            **_b,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Refresh",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._refresh_saves_display,
            **_b,
        ).pack(side="right")

        # Backups list
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(10, 0))
        bak_hdr = tk.Frame(pad, bg=BG_DARK)
        bak_hdr.pack(fill="x", pady=(4, 4))
        tk.Label(
            bak_hdr,
            text="BACKUPS",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")

        bak_frame = tk.Frame(pad, bg=BG_CARD)
        bak_frame.pack(fill="both", expand=True)
        self._backups_tree = ttk.Treeview(
            bak_frame,
            columns=("name", "date", "size"),
            show="headings",
            style="Replay.Treeview",
            height=4,
            selectmode="browse",
        )
        for col, width, label in [
            ("name", 200, "Filename"),
            ("date", 140, "Date"),
            ("size", 70, "Size"),
        ]:
            self._backups_tree.heading(col, text=label, anchor="w")
            self._backups_tree.column(col, width=width, minwidth=40, stretch=(col == "name"))
        bak_ys = tk.Scrollbar(bak_frame, orient="vertical", command=self._backups_tree.yview)
        self._backups_tree.configure(yscrollcommand=bak_ys.set)
        bak_ys.pack(side="right", fill="y")
        self._backups_tree.pack(fill="both", expand=True)

        self._refresh_saves_display()

    # ── Saves tab actions ─────────────────────────────────────────────────────

    def _refresh_saves_display(self) -> None:
        saves_dir = _get_saves_dir()
        save_path = saves_dir / "savegame.json"
        if not save_path.exists():
            self._save_status_var.set("Status:  (no save file)")
            self._save_path_var.set("savegame.json  —  not found")
            self._save_date_var.set("")
            for var in self._save_fields.values():
                var.set("—")
            self._refresh_backups_list()
            return
        try:
            wrapper = json.loads(save_path.read_text(encoding="utf-8"))
        except Exception:
            self._save_status_var.set("Status:  ✗ Parse error")
            self._save_path_var.set("savegame.json  —  corrupted?")
            self._save_date_var.set("")
            self._refresh_backups_list()
            return

        inner = wrapper.get("data", wrapper)  # flat or wrapped format
        status = "OK" if inner else "? Unknown format"
        self._save_status_var.set(f"Status:  {status}")

        ver = wrapper.get("version", "?")
        self._save_path_var.set(f"savegame.json   version: {ver}")
        self._save_date_var.set(f"Saved: {inner.get('save_date', '')}")

        camp = inner.get("campaign", {})
        self._save_fields["hub"].set(camp.get("current_hub_id", "—"))
        self._save_fields["currency"].set(str(camp.get("currency", 0)))
        abilities = camp.get("unlocked_abilities", [])
        ab_str = ", ".join(abilities[:3]) + ("…" if len(abilities) > 3 else "")
        self._save_fields["abilities"].set(f"{len(abilities)}  ({ab_str})" if abilities else "0")
        self._save_fields["missions"].set(str(len(camp.get("completed_missions", []))))
        self._save_fields["bosses"].set(str(len(camp.get("defeated_bosses", []))))
        self._save_fields["c_playtime"].set(_format_playtime(camp.get("total_play_time", 0.0)))

        stats = inner.get("statistics", {})
        self._save_fields["deaths"].set(str(stats.get("total_deaths", 0)))
        self._save_fields["jumps"].set(str(stats.get("total_jumps", 0)))
        self._save_fields["dashes"].set(str(stats.get("total_dashes", 0)))
        self._save_fields["coins"].set(str(stats.get("total_coins_collected", 0)))
        self._save_fields["s_playtime"].set(_format_playtime(stats.get("total_playtime", 0.0)))
        self._save_fields["perf_runs"].set(str(stats.get("perfect_runs", 0)))

        self._refresh_backups_list()

    def _refresh_backups_list(self) -> None:
        for row in self._backups_tree.get_children():
            self._backups_tree.delete(row)
        backups_dir = _get_saves_dir() / "backups"
        if not backups_dir.exists():
            return
        files = sorted(backups_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[:30]:
            try:
                st = path.stat()
                date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                size_str = _format_bytes(st.st_size)
            except OSError:
                date_str = ""
                size_str = ""
            self._backups_tree.insert(
                "",
                "end",
                iid=str(path),
                values=(path.name, date_str, size_str),
            )

    def _backup_save_now(self, *, silent: bool = False) -> "Path | None":
        save_path = _get_saves_dir() / "savegame.json"
        if not save_path.exists():
            if not silent:
                messagebox.showwarning("No Save", "No savegame.json found.", parent=self.root)
            return None
        backups_dir = _get_saves_dir() / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        dest = backups_dir / f"savegame_{ts}.json"
        dest.write_bytes(save_path.read_bytes())
        if not silent:
            self._refresh_backups_list()
            messagebox.showinfo("Backup Created", f"Saved as:\n{dest.name}", parent=self.root)
        return dest

    def _restore_selected_backup(self) -> None:
        sel = self._backups_tree.selection()
        if not sel:
            messagebox.showwarning(
                "No Backup Selected", "Select a backup from the list first.", parent=self.root
            )
            return
        path = Path(sel[0])
        if not messagebox.askyesno(
            "Restore Backup",
            f"Restore '{path.name}' as the current save?\n\nThe current save will be backed up first.",
            parent=self.root,
        ):
            return
        self._backup_save_now(silent=True)
        dest = _get_saves_dir() / "savegame.json"
        dest.write_bytes(path.read_bytes())
        self._refresh_saves_display()
        messagebox.showinfo("Restored", f"Restore complete: {path.name}", parent=self.root)

    def _delete_save(self) -> None:
        save_path = _get_saves_dir() / "savegame.json"
        if not save_path.exists():
            messagebox.showwarning("No Save", "savegame.json not found.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Delete Save",
            "Delete savegame.json?\n\nA backup will be created automatically before deletion.",
            parent=self.root,
        ):
            return
        bak = self._backup_save_now(silent=True)
        save_path.unlink()
        self._refresh_saves_display()
        note = f"\nBackup saved as: {bak.name}" if bak else ""
        messagebox.showinfo("Deleted", f"Save file deleted.{note}", parent=self.root)

    # ── Tab 6: Settings ───────────────────────────────────────────────────────

    def _build_settings_tab(self, parent: tk.Frame) -> None:
        # Fixed button row at bottom
        btn_frame = tk.Frame(parent, bg=BG_DARK)
        btn_frame.pack(side="bottom", fill="x", padx=16, pady=(0, 8))
        tk.Frame(parent, height=1, bg=BG_MID).pack(side="bottom", fill="x")

        _b = dict(font=("Consolas", 9), relief="flat", cursor="hand2", padx=10, pady=4)
        tk.Button(
            btn_frame,
            text="Save",
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            command=self._save_launcher_config_from_ui,
            **_b,
        ).pack(side="left")
        tk.Button(
            btn_frame,
            text="Open Config File",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._open_launcher_config_file,
            **_b,
        ).pack(side="right")

        # Scrollable body
        inner = self._build_scrollable_frame(parent)
        pad = tk.Frame(inner, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=16, pady=4)

        def _sec(label: str) -> None:
            tk.Label(
                pad,
                text=label,
                font=("Consolas", 9, "bold"),
                fg=ACCENT,
                bg=BG_DARK,
                anchor="w",
            ).pack(fill="x", pady=(10, 2))
            tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(0, 4))

        # ── PATHS ────────────────────────────────────────────────────────────
        _sec("PATHS")
        tk.Label(
            pad,
            text=(
                "Game directory — folder containing the JARs, user_data/, and version.json.\n"
                "Default: same folder as the launcher."
            ),
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        game_dir_row = tk.Frame(pad, bg=BG_DARK)
        game_dir_row.pack(fill="x", pady=2)
        tk.Label(
            game_dir_row,
            text="Game Dir:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            width=10,
            anchor="w",
        ).pack(side="left")
        self._game_dir_entry = tk.Entry(
            game_dir_row,
            textvariable=self._game_dir_var,
            font=("Consolas", 8),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
        )
        self._game_dir_entry.pack(side="left", fill="x", expand=True, padx=(4, 4))
        tk.Button(
            game_dir_row,
            text="Browse…",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._browse_game_dir,
        ).pack(side="left")
        tk.Button(
            game_dir_row,
            text="Apply",
            font=("Consolas", 9),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._apply_game_dir,
        ).pack(side="left", padx=(4, 0))

        self._game_dir_status_var = tk.StringVar(value="")
        tk.Label(
            pad,
            textvariable=self._game_dir_status_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", pady=(2, 6))

        # ── JVM ───────────────────────────────────────────────────────────────
        _sec("JVM")
        tk.Label(
            pad,
            text="Heap sizes apply to both client and server JARs unless overridden per-JAR.",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        cfg = _read_launcher_config()

        def _int_entry(parent_f, key: str, default: int, width: int = 6) -> tk.StringVar:
            var = tk.StringVar(value=str(cfg.get(key, default)))
            self._settings_vars[key] = var
            tk.Entry(
                parent_f,
                textvariable=var,
                font=("Consolas", 9),
                bg=BG_MID,
                fg=TEXT_PRIMARY,
                insertbackground=ACCENT,
                relief="flat",
                width=width,
            ).pack(side="left", padx=(4, 6))
            return var

        def _row_int(label: str, key: str, default: int, unit: str = "MB") -> None:
            r = tk.Frame(pad, bg=BG_DARK)
            r.pack(fill="x", pady=2)
            tk.Label(
                r, text=label, font=("Consolas", 9), fg=TEXT_DIM, bg=BG_DARK, width=22, anchor="w"
            ).pack(side="left")
            _int_entry(r, key, default)
            tk.Label(r, text=unit, font=("Consolas", 8), fg=TEXT_DIM, bg=BG_DARK).pack(side="left")

        _row_int("Client heap min:", "jvm_client_xms", 128)
        _row_int("Client heap max:", "jvm_client_xmx", 512)
        _row_int("Server heap min:", "jvm_server_xms", 256)
        _row_int("Server heap max:", "jvm_server_xmx", 1024)

        extra_row = tk.Frame(pad, bg=BG_DARK)
        extra_row.pack(fill="x", pady=2)
        tk.Label(
            extra_row,
            text="Extra JVM args:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            width=22,
            anchor="w",
        ).pack(side="left")
        self._jvm_extra_var = tk.StringVar(value=cfg.get("jvm_extra_args", ""))
        self._settings_vars["jvm_extra_args"] = self._jvm_extra_var
        tk.Entry(
            extra_row,
            textvariable=self._jvm_extra_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ── LAUNCHER ─────────────────────────────────────────────────────────
        _sec("LAUNCHER")

        on_exit_row = tk.Frame(pad, bg=BG_DARK)
        on_exit_row.pack(fill="x", pady=2)
        tk.Label(
            on_exit_row,
            text="On game exit:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            width=22,
            anchor="w",
        ).pack(side="left")
        self._on_exit_var = tk.StringVar(value=cfg.get("on_game_exit", "restore"))
        self._settings_vars["on_game_exit"] = self._on_exit_var
        ttk.Combobox(
            on_exit_row,
            textvariable=self._on_exit_var,
            values=["restore", "minimize", "quit"],
            state="readonly",
            style="Launcher.TCombobox",
            width=12,
            font=("Consolas", 9),
        ).pack(side="left", padx=(4, 0))

        autoupdate_row = tk.Frame(pad, bg=BG_DARK)
        autoupdate_row.pack(fill="x", pady=2)
        self._autoupdate_var = tk.BooleanVar(value=cfg.get("auto_update_check", True))
        self._settings_vars["auto_update_check"] = self._autoupdate_var
        tk.Checkbutton(
            autoupdate_row,
            text="Check for updates on launch",
            variable=self._autoupdate_var,
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_DARK,
            activebackground=BG_DARK,
            activeforeground=TEXT_SELECTED,
            selectcolor=BG_MID,
            relief="flat",
            bd=0,
        ).pack(anchor="w")

    def _build_scrollable_frame(self, parent: tk.Frame) -> tk.Frame:
        """Return an inner tk.Frame inside a canvas+scrollbar; mousewheel scrolls on hover."""
        canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_DARK)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_cfg(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner.bind("<Configure>", _on_inner_cfg)

        def _on_canvas_cfg(e):
            canvas.itemconfig(win_id, width=e.width)

        canvas.bind("<Configure>", _on_canvas_cfg)

        def _on_wheel(e):
            canvas.yview_scroll(-1 * (e.delta // 120), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        return inner

    # ── Settings tab actions ──────────────────────────────────────────────────

    def _save_launcher_config_from_ui(self) -> None:
        cfg = _read_launcher_config()
        int_keys = {"jvm_client_xms", "jvm_client_xmx", "jvm_server_xms", "jvm_server_xmx"}
        bool_keys = {"auto_update_check"}
        for key, var in self._settings_vars.items():
            raw = var.get()
            if key in int_keys:
                try:
                    cfg[key] = int(raw)
                except ValueError:
                    pass
            elif key in bool_keys:
                cfg[key] = bool(raw)
            else:
                cfg[key] = raw
        try:
            _write_launcher_config(cfg)
            messagebox.showinfo("Saved", "Launcher config saved.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc), parent=self.root)

    def _open_launcher_config_file(self) -> None:
        path = _get_launcher_config_path()
        if not path.exists():
            _write_launcher_config({})
        try:
            os.startfile(str(path))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(path)])

    # ── Game directory config ─────────────────────────────────────────────────

    def _browse_game_dir(self) -> None:
        from tkinter import filedialog

        current = self._game_dir_var.get() or str(_get_base_dir())
        chosen = filedialog.askdirectory(
            title="Select Game Directory",
            initialdir=current,
            parent=self.root,
        )
        if chosen:
            self._game_dir_var.set(chosen)

    def _apply_game_dir(self) -> None:
        """Validate and apply the new game directory, then refresh all data tabs."""
        global _GAME_DIR
        raw = self._game_dir_var.get().strip()
        if not raw:
            self._game_dir_status_var.set("Path cannot be empty.")
            return
        p = Path(raw)
        if not p.is_dir():
            self._game_dir_status_var.set(f"Directory not found: {p}")
            return

        _GAME_DIR = p
        cfg = _read_launcher_config()
        cfg["game_dir"] = str(p)
        try:
            _write_launcher_config(cfg)
        except Exception as exc:
            self._game_dir_status_var.set(f"Could not save config: {exc}")
            return

        self._game_dir_var.set(str(p))
        self._game_dir_status_var.set(f"Applied — {p.name}/")
        self._refresh_all_data_tabs()

    def _refresh_all_data_tabs(self) -> None:
        """Reload every data-driven tab after the game directory changes."""
        self._refresh_saves_display()
        self._refresh_backups_list()
        self._refresh_replays_tab()
        self._refresh_replay_list()
        self._refresh_log_list()
        self._refresh_jar_info()
        # Also re-read the local game version from the new directory
        self._local_version = _read_local_version()

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

        win = tk.Toplevel(self.root)
        win.title(f"Log — {name}")
        win.configure(bg=BG_DARK)
        win.geometry("700x440")

        # Filter / search bar
        filter_row = tk.Frame(win, bg=BG_DARK)
        filter_row.pack(fill="x", padx=6, pady=(6, 2))

        tk.Label(filter_row, text="Level:", font=("Consolas", 8), fg=TEXT_DIM, bg=BG_DARK).pack(
            side="left"
        )
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
        level_combo.pack(side="left", padx=(4, 10))

        tk.Label(filter_row, text="Search:", font=("Consolas", 8), fg=TEXT_DIM, bg=BG_DARK).pack(
            side="left"
        )
        search_var = tk.StringVar()
        tk.Entry(
            filter_row,
            textvariable=search_var,
            font=("Consolas", 8),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=22,
        ).pack(side="left", padx=(4, 6))

        full_content = log_path.read_text(encoding="utf-8", errors="replace")

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
            command=lambda: (level_var.set("ALL"), search_var.set(""), _apply_filter()),
        ).pack(side="left", padx=(4, 0))

        level_var.trace_add("write", _apply_filter)

        xs.pack(side="bottom", fill="x")
        ys.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)

        text.insert("1.0", full_content)
        text.see("end")
        text.configure(state="disabled")

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
        """Show metadata for the currently selected replay in the Dev Tools combo."""
        name = self._replay_var.get()
        if not name or name == "(no replays found)":
            self._replay_meta_var.set("")
            return
        path = _get_user_data_dir() / "replays" / name
        meta = _read_replay_meta(path)
        if not meta:
            self._replay_meta_var.set("(no metadata)")
            return
        hub = meta.get("hub_id", "—")
        mode = meta.get("mode", "—")
        seed = meta.get("world_seed", "—")
        frames = meta.get("total_frames", meta.get("frame_count", "—"))
        self._replay_meta_var.set(f"hub={hub}  mode={mode}  seed={seed}  frames={frames}")

    def _delete_selected_replay_devtools(self) -> None:
        """Delete the replay selected in the Dev Tools combobox."""
        name = self._replay_var.get()
        if not name or name == "(no replays found)":
            return
        path = _get_user_data_dir() / "replays" / name
        if not messagebox.askyesno("Delete Replay", f"Delete '{name}'?", parent=self.root):
            return
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

    # ── Release list fetch + periodic re-check ───────────────────────────────

    _PERIODIC_CHECK_MS = 15 * 60 * 1000  # re-check every 15 minutes

    def _schedule_periodic_check(self) -> None:
        """Schedule a silent update check in 15 minutes."""
        self.root.after(self._PERIODIC_CHECK_MS, self._run_periodic_check)

    def _run_periodic_check(self) -> None:
        """Silently re-fetch releases and update status if a newer version is found."""
        if not self._downloading:
            threading.Thread(target=self._fetch_releases, daemon=True).start()
        self._schedule_periodic_check()

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
        if not self._game_exe_installed():
            self._status_var.set(f"v  Game not installed — click  Install {latest_tag}  to set up")
        elif _is_newer(latest_ver, self._local_version):
            self._status_var.set(f"^  Update available: {latest_tag}")
        else:
            self._status_var.set("OK  Up to date")

        self._update_changelog(releases[0])

    def _update_changelog(self, release: dict) -> None:
        """Populate the changelog Text widget with the latest release body."""
        tag = release.get("tag_name", "")
        self._changelog_tag_var.set(f"— {tag}")
        body = release.get("body") or "(no release notes)"
        # Strip markdown headings, bold/italic markers, and HTML tags for plain display
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"^#{1,6}\s*", "", body, flags=re.MULTILINE)
        body = re.sub(r"\*\*(.+?)\*\*", r"\1", body)
        body = re.sub(r"\*(.+?)\*", r"\1", body)
        body = re.sub(r"`(.+?)`", r"\1", body)
        body = body.strip()
        self._changelog_txt.configure(state="normal")
        self._changelog_txt.delete("1.0", "end")
        self._changelog_txt.insert("1.0", body)
        self._changelog_txt.configure(state="disabled")

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

    def _game_exe_installed(self) -> bool:
        """Return True if ninja_dash.exe exists in the current game directory."""
        return (_get_base_dir() / GAME_EXE_NAME).exists()

    def _refresh_download_btn(self) -> None:
        if not self._selected_release or self._downloading:
            return

        tag = self._selected_release.get("tag_name", "")
        ver = tag.lstrip("v")
        assets = self._selected_release.get("assets", [])
        has_exe = any(a.get("name") == GAME_EXE_NAME for a in assets)
        has_jars = bool(
            _find_jar_asset(assets, "ninja-server") and _find_jar_asset(assets, "ninja-client")
        )

        # Nothing downloadable in this release
        if not has_exe and not has_jars:
            self._download_btn.configure(state="disabled", text="v  No downloadable assets")
            return

        installed = self._game_exe_installed()
        jars_installed = _get_server_jar().exists() and _get_client_jar().exists()

        if has_exe:
            # Exe-based release (may also include JARs)
            if not installed:
                label = f"v  Install {tag}"
            elif ver == self._local_version and (not has_jars or jars_installed):
                label = f"v  Reinstall {tag}"
            elif has_jars and not jars_installed:
                label = f"v  Install JARs for {tag}"
            elif _is_newer(ver, self._local_version):
                label = f"^  Update to {tag}"
            else:
                label = f"v  Downgrade to {tag}"
        else:
            # JAR-only release
            if not jars_installed:
                label = f"v  Install JARs {tag}"
            elif _is_newer(ver, self._local_version):
                label = f"^  Update JARs to {tag}"
            elif ver == self._local_version:
                label = f"v  Reinstall JARs {tag}"
            else:
                label = f"v  Downgrade JARs to {tag}"

        self._download_btn.configure(state="normal", text=label)
        # Play button enabled when client JAR is available
        play_ready = _get_client_jar().exists() and self._java_ok
        play_state = "normal" if play_ready else "disabled"
        play_fg = ACCENT if play_ready else TEXT_DIM
        self._play_btn.configure(state=play_state, fg=play_fg)

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self) -> None:
        if self._downloading or not self._selected_release:
            return

        assets = self._selected_release.get("assets", [])
        exe_asset = next((a for a in assets if a.get("name") == GAME_EXE_NAME), None)
        server_jar_asset = _find_jar_asset(assets, "ninja-server")
        client_jar_asset = _find_jar_asset(assets, "ninja-client")

        if not exe_asset and not server_jar_asset and not client_jar_asset:
            messagebox.showwarning(
                "No Asset",
                "The selected release has no downloadable assets (exe or JARs).\n"
                "Check the GitHub releases page manually.",
                parent=self.root,
            )
            return

        # JAR-only release: skip exe download, go straight to JAR download
        if not exe_asset:
            self._downloading = True
            self._download_cancel.clear()
            self._download_btn.configure(state="disabled", text="Downloading…")
            self._cancel_btn.pack(side="left", padx=(8, 0))
            self._status_var.set("Connecting…")
            threading.Thread(
                target=self._download_jars_only_worker,
                args=(self._selected_release, server_jar_asset, client_jar_asset),
                daemon=True,
            ).start()
            return

        sha_asset = next((a for a in assets if a.get("name") == f"{GAME_EXE_NAME}.sha256"), None)
        expected_sha = None
        if sha_asset:
            try:
                with urllib.request.urlopen(sha_asset["browser_download_url"], timeout=10) as r:
                    expected_sha = r.read().decode().strip().split()[0]
            except Exception:
                pass

        self._downloading = True
        self._download_cancel.clear()
        self._download_btn.configure(state="disabled", text="Downloading…")
        self._cancel_btn.pack(side="left", padx=(8, 0))
        self._status_var.set("Connecting…")

        threading.Thread(
            target=self._download_worker,
            args=(
                exe_asset["browser_download_url"],
                exe_asset.get("size", 0),
                expected_sha,
                self._selected_release,
                server_jar_asset,
                client_jar_asset,
            ),
            daemon=True,
        ).start()

    def _cancel_download(self) -> None:
        self._download_cancel.set()
        self._status_var.set("Cancelling…")

    def _sync_player_expectations(self, tag: str) -> tuple[bool, str]:
        """
        Download docs/PLAYER_EXPECTATIONS.md for the selected release tag
        and replace the local live copy.

        Returns:
            (True, "ok") on success, otherwise (False, reason)
        """
        clean_tag = (tag or "").strip()
        if not clean_tag:
            return False, "missing release tag"

        url = (
            f"https://raw.githubusercontent.com/{GAME_REPO}/"
            f"{clean_tag}/docs/PLAYER_EXPECTATIONS.md"
        )
        dest = _get_base_dir() / PLAYER_EXPECTATIONS_REL_PATH
        tmp = dest.with_suffix(".md.new")

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"indie-ninja-launcher/{LAUNCHER_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                text = resp.read().decode("utf-8")
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(dest)
            return True, "ok"
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            return False, str(exc)

    def _download_worker(
        self,
        url: str,
        total_size: int,
        expected_sha: str | None,
        release: dict,
        server_jar_asset: dict | None = None,
        client_jar_asset: dict | None = None,
    ) -> None:
        dest = _get_base_dir() / f"{GAME_EXE_NAME}.new"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"indie-ninja-launcher/{LAUNCHER_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if total_size <= 0:
                    total_size = int(resp.headers.get("Content-Length", 0))

                downloaded = 0
                speed_samples: list[tuple[float, int]] = []
                last_t = time.monotonic()

                with open(dest, "wb") as f:
                    while True:
                        if self._download_cancel.is_set():
                            raise OSError("Download cancelled.")
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.monotonic()
                        dt = now - last_t
                        last_t = now
                        speed_samples.append((dt, len(chunk)))
                        if len(speed_samples) > 6:
                            speed_samples.pop(0)

                        total_dt = sum(s[0] for s in speed_samples)
                        total_b = sum(s[1] for s in speed_samples)
                        speed = total_b / total_dt if total_dt > 0 else 0

                        if total_size > 0:
                            pct = min(100.0, downloaded / total_size * 100)
                            remaining = total_size - downloaded
                            eta_s = int(remaining / speed) if speed > 0 else 0
                            eta_str = f"{eta_s}s" if eta_s < 60 else f"{eta_s // 60}m {eta_s % 60}s"
                            status = (
                                f"Downloading…  "
                                f"{_format_bytes(downloaded)} / {_format_bytes(total_size)}"
                                f"  {_format_bytes(int(speed))}/s  ETA: {eta_str}"
                            )
                            self.root.after(0, self._progress_var.set, pct)
                            self.root.after(0, self._status_var.set, status)

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

            # Always install to the fixed exe name — never use _get_game_exe() here
            # because that fallback returns demo_game.py when ninja_dash.exe is absent.
            final_exe = _get_base_dir() / GAME_EXE_NAME
            if final_exe.exists():
                bak = final_exe.with_suffix(".bak")
                bak.unlink(missing_ok=True)
                final_exe.rename(bak)
            dest.rename(final_exe)

            tag = release.get("tag_name", "")
            ver = tag.lstrip("v")
            if ver:
                vpath = _get_version_path()
                try:
                    try:
                        data = json.loads(vpath.read_text(encoding="utf-8"))
                    except Exception:
                        data = {}
                    data["version"] = ver
                    vpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception:
                    pass

            # ── Download JARs if present in this release ──────────────────────
            for jar_asset, jar_dest_name, label in [
                (server_jar_asset, SERVER_JAR_NAME, "server JAR"),
                (client_jar_asset, CLIENT_JAR_NAME, "client JAR"),
            ]:
                if not jar_asset or self._download_cancel.is_set():
                    continue
                jar_url = jar_asset["browser_download_url"]
                jar_size = jar_asset.get("size", 0)
                jar_dest = _get_base_dir() / f"{jar_dest_name}.new"
                self.root.after(0, self._status_var.set, f"Downloading {label}…")
                try:
                    req = urllib.request.Request(
                        jar_url,
                        headers={"User-Agent": f"indie-ninja-launcher/{LAUNCHER_VERSION}"},
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        if jar_size <= 0:
                            jar_size = int(resp.headers.get("Content-Length", 0))
                        downloaded = 0
                        with open(jar_dest, "wb") as f:
                            while True:
                                if self._download_cancel.is_set():
                                    raise OSError("Download cancelled.")
                                chunk = resp.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                if jar_size > 0:
                                    pct = min(100.0, downloaded / jar_size * 100)
                                    self.root.after(0, self._progress_var.set, pct)
                    final_jar = _get_base_dir() / jar_dest_name
                    final_jar.unlink(missing_ok=True)
                    jar_dest.rename(final_jar)
                except Exception:
                    jar_dest.unlink(missing_ok=True)
                    # Non-fatal — JAR download failure doesn't break the exe install

            docs_ok, docs_reason = self._sync_player_expectations(tag)
            docs_note = "PLAYER_EXPECTATIONS synced" if docs_ok else f"PLAYER_EXPECTATIONS sync failed ({docs_reason})"
            self.root.after(0, self._on_download_done, tag, docs_note)

        except Exception as exc:
            dest.unlink(missing_ok=True)
            self.root.after(0, self._on_download_error, str(exc))

    def _download_jars_only_worker(
        self,
        release: dict,
        server_jar_asset: dict | None,
        client_jar_asset: dict | None,
    ) -> None:
        """Download ninja-server-all.jar and ninja-client-all.jar with no exe involved."""
        tag = release.get("tag_name", "")
        try:
            for jar_asset, jar_dest_name, label in [
                (server_jar_asset, SERVER_JAR_NAME, "server JAR"),
                (client_jar_asset, CLIENT_JAR_NAME, "client JAR"),
            ]:
                if not jar_asset or self._download_cancel.is_set():
                    continue
                jar_url = jar_asset["browser_download_url"]
                jar_size = jar_asset.get("size", 0)
                jar_dest = _get_base_dir() / f"{jar_dest_name}.new"
                self.root.after(0, self._status_var.set, f"Downloading {label}…")
                self.root.after(0, self._progress_var.set, 0.0)
                try:
                    req = urllib.request.Request(
                        jar_url,
                        headers={"User-Agent": f"indie-ninja-launcher/{LAUNCHER_VERSION}"},
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        if jar_size <= 0:
                            jar_size = int(resp.headers.get("Content-Length", 0))
                        downloaded = 0
                        with open(jar_dest, "wb") as f:
                            while True:
                                if self._download_cancel.is_set():
                                    raise OSError("Download cancelled.")
                                chunk = resp.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                if jar_size > 0:
                                    pct = min(100.0, downloaded / jar_size * 100)
                                    self.root.after(0, self._progress_var.set, pct)
                    final_jar = _get_base_dir() / jar_dest_name
                    final_jar.unlink(missing_ok=True)
                    jar_dest.rename(final_jar)
                except Exception as exc:
                    jar_dest.unlink(missing_ok=True)
                    self.root.after(0, self._on_download_error, f"{label} failed: {exc}")
                    return

            # Update local version from release tag
            ver = tag.lstrip("v")
            if ver:
                vpath = _get_version_path()
                try:
                    try:
                        data = json.loads(vpath.read_text(encoding="utf-8"))
                    except Exception:
                        data = {}
                    data["version"] = ver
                    vpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception:
                    pass

            docs_ok, docs_reason = self._sync_player_expectations(tag)
            docs_note = "PLAYER_EXPECTATIONS synced" if docs_ok else f"PLAYER_EXPECTATIONS sync failed ({docs_reason})"
            self.root.after(0, self._on_download_done, tag, docs_note)

        except Exception as exc:
            self.root.after(0, self._on_download_error, str(exc))

    def _on_download_done(self, tag: str, docs_note: str = "") -> None:
        self._downloading = False
        self._cancel_btn.pack_forget()
        self._local_version = tag.lstrip("v")
        self._progress_var.set(100.0)
        status = f"OK  {tag} installed. Ready to play."
        if docs_note:
            status = f"{status}  [{docs_note}]"
        self._status_var.set(status)
        self._play_btn.configure(state="normal", fg=ACCENT)
        self._installed_label_var.set(f"Installed:  v{self._local_version}")

        labels = [
            _version_label(r["tag_name"], self._local_version, i == 0)
            for i, r in enumerate(self._all_releases)
        ]
        self._version_combo.configure(values=labels)
        self._refresh_download_btn()
        self._refresh_java_section()

    def _on_download_error(self, message: str) -> None:
        self._downloading = False
        self._cancel_btn.pack_forget()
        self._progress_var.set(0.0)
        self._status_var.set(f"X  {message}")
        self._refresh_download_btn()

    # ── Launch helpers ────────────────────────────────────────────────────────

    def _launch_with_args(self, *extra_args: str) -> None:
        """Build command for the game exe + extra_args, Popen it, then minimise launcher."""
        game_path = _get_game_exe()
        if not game_path.exists():
            messagebox.showerror(
                "Game Not Found",
                f"Could not find the game at:\n{game_path}\n\nPlease download a version first.",
                parent=self.root,
            )
            return
        cmd = [sys.executable, str(game_path)] if game_path.suffix == ".py" else [str(game_path)]
        # Inject --record if the Replays tab checkbox is set (skip for replay playback)
        if self._record_var.get() and "--replay" not in extra_args:
            rec_name = self._record_name_var.get().strip()
            if not rec_name:
                rec_name = f"session_{int(time.time())}"
            if not rec_name.endswith(".json"):
                rec_name += ".json"
            cmd += ["--record", rec_name]
            self._record_var.set(0)

        cmd.extend(extra_args)
        try:
            proc = subprocess.Popen(cmd)
            self._status_var.set("Game Running…  (launcher minimised)")
            self.root.iconify()
            threading.Thread(target=self._watch_game_process, args=(proc,), daemon=True).start()
        except Exception as exc:
            messagebox.showerror("Launch Error", str(exc), parent=self.root)

    # ── JAR info helpers ─────────────────────────────────────────────────────

    def _refresh_jar_info(self) -> None:
        lines = []
        _, java_str = _detect_java()
        lines.append(f"Java:    {java_str}")
        for label, path in [
            ("Client JAR", _get_client_jar()),
            ("Server JAR", _get_server_jar()),
        ]:
            if path.exists():
                try:
                    size = _format_bytes(path.stat().st_size)
                except OSError:
                    size = "?"
                lines.append(f"{label}:  {path.name}  ({size})")
            else:
                lines.append(f"{label}:  NOT FOUND")
        self._jar_info_var.set("\n".join(lines))

    def _verify_jar_sha256(self) -> None:
        results = []
        for label, path in [
            ("Client JAR", _get_client_jar()),
            ("Server JAR", _get_server_jar()),
        ]:
            if not path.exists():
                results.append(f"{label}: not found")
                continue
            self._jar_info_var.set(f"Hashing {label}…")
            self.root.update_idletasks()
            sha = _sha256_file(path)
            results.append(f"{label}: {sha}")
        self._jar_info_var.set("\n".join(results))

    def _reveal_game_dir(self) -> None:
        d = _get_base_dir()
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(d))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(d)])

    # ── Server ping ───────────────────────────────────────────────────────────

    def _ping_server_addr(self) -> None:
        """TCP-connect to the join address and report latency."""
        addr = self._java_addr_var.get().strip()
        if not addr or addr == self._JAVA_ADDR_PLACEHOLDER:
            self._ping_result_var.set("no address")
            return
        if ":" in addr:
            host, _, port_str = addr.rpartition(":")
            try:
                port = int(port_str)
            except ValueError:
                self._ping_result_var.set("bad address")
                return
        else:
            host = addr
            port = 7777
        self._ping_result_var.set("pinging…")
        threading.Thread(target=self._do_ping, args=(host, port), daemon=True).start()

    def _do_ping(self, host: str, port: int) -> None:
        try:
            t0 = time.perf_counter()
            with socket.create_connection((host, port), timeout=3):
                pass
            ms = (time.perf_counter() - t0) * 1000
        except OSError:
            self.root.after(0, self._on_ping_done, None)
            return
        self.root.after(0, self._on_ping_done, ms)

    def _on_ping_done(self, ms: float | None) -> None:
        if ms is None:
            self._ping_result_var.set("unreachable")
            self._ping_result_label_widget.configure(fg="#e53935")
            return
        label = f"{ms:.0f}ms"
        if ms < 100:
            color = "#4caf50"
        elif ms < 250:
            color = "#ffd700"
        else:
            color = "#e53935"
        self._ping_result_var.set(label)
        self._ping_result_label_widget.configure(fg=color)

    # ── Java section helpers ──────────────────────────────────────────────────

    _JAVA_ADDR_PLACEHOLDER = "host:7777"

    def _on_java_addr_focus_in(self, _event=None) -> None:
        if self._java_addr_var.get() == self._JAVA_ADDR_PLACEHOLDER:
            self._java_addr_entry.delete(0, "end")
            self._java_addr_entry.config(fg=TEXT_PRIMARY)

    def _on_java_addr_focus_out(self, _event=None) -> None:
        if not self._java_addr_var.get().strip():
            self._java_addr_entry.insert(0, self._JAVA_ADDR_PLACEHOLDER)
            self._java_addr_entry.config(fg=TEXT_DIM)

    def _refresh_java_section(self) -> None:
        """Update JAR status label and button states based on current disk state."""
        client_ok = _get_client_jar().exists()
        server_ok = _get_server_jar().exists()

        if client_ok and server_ok:
            self._java_jar_var.set("JARs installed")
            self._java_jar_label.configure(fg="#4caf50")
        elif client_ok or server_ok:
            missing = "server" if not server_ok else "client"
            self._java_jar_var.set(f"{missing} JAR missing — reinstall")
            self._java_jar_label.configure(fg="#ffd700")
        else:
            self._java_jar_var.set("JARs not installed — click Install")
            self._java_jar_label.configure(fg=TEXT_DIM)

        ready = self._java_ok and client_ok
        server_ready = self._java_ok and server_ok
        btn_state = "normal" if ready else "disabled"
        srv_state = "normal" if server_ready else "disabled"
        btn_fg = ACCENT if ready else TEXT_DIM
        self._play_btn.configure(state=btn_state, fg=btn_fg)
        self._java_join_btn.configure(state=btn_state)
        self._java_host_play_btn.configure(
            state="normal" if (ready and server_ready) else "disabled"
        )
        self._java_server_btn.configure(state=srv_state)

    def _launch_java_solo(self) -> None:
        """Launch client connecting to localhost (mode selection handled in-game)."""
        port_str = self._host_port_var.get().strip()
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            port = 7777
        self._launch_java_client("127.0.0.1", port)

    def _launch_java_host_play(self) -> None:
        """Start the server then connect the client to localhost."""
        self._launch_java_server()
        if self._java_server_proc is not None:
            port_str = self._host_port_var.get().strip()
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError
            except ValueError:
                port = 7777
            self._launch_java_client("127.0.0.1", port)

    def _launch_java_join(self) -> None:
        addr = self._java_addr_var.get().strip()
        if not addr or addr == self._JAVA_ADDR_PLACEHOLDER:
            messagebox.showerror(
                "No Server Address",
                "Enter the server address as  host:port  (e.g. 192.168.1.5:7777).",
                parent=self.root,
            )
            return
        if ":" not in addr:
            addr = f"{addr}:7777"
        host, _, port_str = addr.rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror(
                "Bad Address", f"Port must be a number, got: {port_str}", parent=self.root
            )
            return
        self._launch_java_client(host, port)

    def _launch_java_client(self, host: str, port: int) -> None:
        java = _find_java_exe()
        if not java:
            messagebox.showerror(
                "Java Not Found",
                f"Java {JAVA_MIN_VERSION}+ is required to run the Java client.\n"
                "Download it from adoptium.net",
                parent=self.root,
            )
            return
        jar = _get_client_jar()
        if not jar.exists():
            messagebox.showerror(
                "Client JAR Not Found",
                f"Could not find:\n{jar}\n\nPlease install the latest version first.",
                parent=self.root,
            )
            return
        cfg = _read_launcher_config()
        xms = cfg.get("jvm_client_xms", 128)
        xmx = cfg.get("jvm_client_xmx", 512)
        extra = cfg.get("jvm_extra_args", "").split()
        profile_name = (
            self._profile_var.get().strip() if hasattr(self, "_profile_var") else "Player1"
        ) or "Player1"
        player_id = self._ensure_profile_player_id(profile_name)
        # Inject -Dninja.record=true for solo replay recording when checkbox is set.
        record_flags = ["-Dninja.record=true"] if self._record_var.get() else []
        cmd = [
            java,
            "-XX:+UseZGC",
            f"-Xms{xms}m",
            f"-Xmx{xmx}m",
            f"-Dninja.playerId={player_id}",
            f"-Dninja.profileName={profile_name}",
            *record_flags,
            *extra,
            "-jar",
            str(jar),
            host,
            str(port),
        ]
        try:
            proc = subprocess.Popen(cmd, cwd=str(_get_base_dir()))
            self._status_var.set(f"Java Client Running…  ({host}:{port})")
            self.root.iconify()
            threading.Thread(
                target=self._watch_java_process,
                args=(proc, "Java Client"),
                daemon=True,
            ).start()
        except Exception as exc:
            messagebox.showerror("Launch Error", str(exc), parent=self.root)

    def _launch_java_server(self) -> None:
        java = _find_java_exe()
        if not java:
            messagebox.showerror(
                "Java Not Found",
                f"Java {JAVA_MIN_VERSION}+ is required to run the Java server.\n"
                "Download it from adoptium.net",
                parent=self.root,
            )
            return
        jar = _get_server_jar()
        if not jar.exists():
            messagebox.showerror(
                "Server JAR Not Found",
                f"Could not find:\n{jar}\n\nPlease install the latest version first.",
                parent=self.root,
            )
            return
        port_str = self._host_port_var.get().strip()
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be 1–65535.", parent=self.root)
            return
        if _is_port_in_use(port):
            kill = messagebox.askyesno(
                "Port In Use",
                f"Port {port} is already in use — a server from a previous session "
                f"may still be running.\n\nStop the existing process and start fresh?",
                parent=self.root,
            )
            if not kill:
                return
            if not _kill_process_on_port(port):
                messagebox.showerror(
                    "Could Not Stop",
                    f"Failed to free port {port}. Try stopping the process manually "
                    "in Task Manager.",
                    parent=self.root,
                )
                return
        cfg = _read_launcher_config()
        xms = cfg.get("jvm_server_xms", 256)
        xmx = cfg.get("jvm_server_xmx", 1024)
        extra = cfg.get("jvm_extra_args", "").split()
        # Inject -Dninja.record=true when the Replays tab "Record" checkbox is set.
        record_flags = ["-Dninja.record=true"] if self._record_var.get() else []
        cmd = [
            java,
            "-XX:+UseZGC",
            f"-Xms{xms}m",
            f"-Xmx{xmx}m",
            *record_flags,
            *extra,
            "-jar",
            str(jar),
            str(port),
        ]
        try:
            self._java_server_proc = subprocess.Popen(cmd, cwd=str(_get_base_dir()))
            self._status_var.set(f"Java Server running on port {port}")
            self._java_server_btn.configure(
                text="[S]  Stop Server",
                bg="#5a1a1a",
                command=self._stop_java_server,
            )
            threading.Thread(
                target=self._watch_java_server,
                args=(self._java_server_proc,),
                daemon=True,
            ).start()
        except Exception as exc:
            messagebox.showerror("Launch Error", str(exc), parent=self.root)

    def _stop_java_server(self) -> None:
        proc = self._java_server_proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._on_java_server_stopped()

    def _watch_java_server(self, proc: subprocess.Popen) -> None:
        proc.wait()
        self.root.after(0, self._on_java_server_stopped)

    def _on_java_server_stopped(self) -> None:
        self._java_server_proc = None
        self._java_server_btn.configure(
            text="[S]  Start Server",
            bg=BTN_HOST_BG,
            command=self._launch_java_server,
        )
        self._status_var.set("Server stopped.")

    # ── Game process watcher + crash detection (P1-F6) ───────────────────────

    _EXIT_CODE_NAMES: dict[int, str] = {
        -1073741819: "ACCESS_VIOLATION",
        -1073741571: "STACK_OVERFLOW",
        -1073741676: "ILLEGAL_INSTRUCTION",
        -1073741510: "CTRL_C_EXIT",
        0xC0000005: "ACCESS_VIOLATION",
        0xC00000FD: "STACK_OVERFLOW",
        0xC000001D: "ILLEGAL_INSTRUCTION",
        0xC0000409: "STACK_BUFFER_OVERRUN",
        0xC0000094: "INTEGER_DIVIDE_BY_ZERO",
    }

    def _watch_game_process(self, proc: subprocess.Popen) -> None:
        proc.wait()
        self.root.after(0, self._on_game_exited, proc.returncode)

    def _watch_java_process(self, proc: subprocess.Popen, label: str) -> None:
        """Watch a Java process — restore window on exit, no crash dialog."""
        proc.wait()
        code = proc.returncode
        if code == 0:
            msg = f"{label} exited."
        else:
            msg = f"{label} exited (code {code}). Check the terminal for details."
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self._status_var.set, msg)

    def _decode_exit_code(self, code: int) -> str:
        name = self._EXIT_CODE_NAMES.get(code) or self._EXIT_CODE_NAMES.get(code & 0xFFFFFFFF)
        hex_str = f"0x{code & 0xFFFFFFFF:08X}"
        return f"{hex_str} ({name})" if name else hex_str

    def _on_game_exited(self, returncode: int) -> None:
        self.root.deiconify()
        if returncode == 0:
            self._status_var.set("OK  Game exited normally.")
            return
        log_tail = ""
        log_files = _list_log_files()
        if log_files:
            log_tail = _read_tail(log_files[0], 30)
        self._build_crash_dialog(returncode, log_tail)

    def _build_crash_dialog(self, returncode: int, log_tail: str) -> None:
        import urllib.parse

        code_str = self._decode_exit_code(returncode)

        win = tk.Toplevel(self.root)
        win.title("Game Crashed")
        win.configure(bg=BG_DARK)
        win.geometry("620x440")
        win.grab_set()

        pad = tk.Frame(win, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(
            pad,
            text="  Game Crashed",
            font=("Consolas", 11, "bold"),
            fg="#e05252",
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")
        tk.Frame(pad, height=1, bg="#e05252").pack(fill="x", pady=(4, 6))
        tk.Label(
            pad,
            text=f"Exit code:  {code_str}",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x")

        if log_tail:
            tk.Label(
                pad,
                text="Last 30 log lines:",
                font=("Consolas", 9),
                fg=TEXT_DIM,
                bg=BG_DARK,
                anchor="w",
            ).pack(fill="x", pady=(8, 2))
            log_frame = tk.Frame(pad, bg=BG_CARD)
            log_frame.pack(fill="both", expand=True)
            log_txt = tk.Text(
                log_frame,
                font=("Consolas", 7),
                bg=BG_CARD,
                fg=TEXT_PRIMARY,
                relief="flat",
                height=10,
                wrap="none",
                state="disabled",
            )
            log_ys = tk.Scrollbar(log_frame, orient="vertical", command=log_txt.yview)
            log_txt.configure(yscrollcommand=log_ys.set)
            log_ys.pack(side="right", fill="y")
            log_txt.pack(fill="both", expand=True, padx=4, pady=2)
            log_txt.configure(state="normal")
            log_txt.insert("1.0", log_tail)
            log_txt.see("end")
            log_txt.configure(state="disabled")

        btn_row = tk.Frame(pad, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(10, 0))

        def _open_report() -> None:
            body_lines = [
                f"**Exit code:** {code_str}",
                f"**Version:** v{self._local_version}",
                f"**OS:** {platform.platform()}",
                "",
                "---",
                "",
                "*(describe what you were doing when the crash happened)*",
            ]
            if log_tail:
                body_lines += ["", "---", "**Log tail:**", "```", log_tail, "```"]
            params = urllib.parse.urlencode(
                {
                    "title": f"[Crash] Exit {code_str}",
                    "labels": "crash,bug",
                    "body": "\n".join(body_lines),
                }
            )
            webbrowser.open(f"{ISSUES_URL}?{params}")

        def _copy_to_clipboard() -> None:
            text = f"Exit code: {code_str}\n\n{log_tail}"
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "Crash info copied to clipboard.", parent=win)

        tk.Button(
            btn_row,
            text="Open Crash Report",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=_open_report,
        ).pack(side="left")
        tk.Button(
            btn_row,
            text="Copy to Clipboard",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=_copy_to_clipboard,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Dismiss",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=win.destroy,
        ).pack(side="right")

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
