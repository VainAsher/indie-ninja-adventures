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
import hmac
import json
import os
import platform
import re
import shutil
import socket
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
SERVER_JAR_NAME = "ninja-server-all.jar"
CLIENT_JAR_NAME = "ninja-client-all.jar"
VERSION_FILE = "version.json"
LAUNCHER_VERSION = "1.7.0"
JAVA_MIN_VERSION = 21
WINDOW_TITLE = "Indie Ninja Adventures"
WINDOW_W = 760
WINDOW_H = 640
SPLASH_W = 640  # splash image/text stays fixed at 640; window can be wider
SPLASH_H = 200  # canvas height — crops the 640×320 scaled image to top portion

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

# Benchmark: run for this many seconds then terminate
_BENCHMARK_SECONDS = 10

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


def _get_profiler_csv() -> Path:
    return _get_user_data_dir() / "perf_baseline.csv"


def _get_saves_dir() -> Path:
    return _get_user_data_dir() / "saves"


def _get_settings_path() -> Path:
    return _get_user_data_dir() / "settings" / "settings.json"


# Default settings — duplicated from config/settings.py (launcher cannot import game modules)
_DEFAULT_SETTINGS: dict = {
    "volume_master": 1.0,
    "volume_music": 0.7,
    "volume_sfx": 0.8,
    "fullscreen": False,
    "vsync": True,
    "show_fps": False,
    "window_width": 1280,
    "window_height": 720,
    "screenshake": True,
    "particles": True,
    "camera_smoothing": 0.1,
    "key_left": "left",
    "key_right": "right",
    "key_jump": "space",
    "key_dash": "shift",
    "key_crouch": "down",
    "show_hitboxes": False,
    "log_level": "INFO",
}

# HMAC key — duplicated from systems/save_system.py; must stay in sync
_SAVE_HMAC_KEY = b"ninja_dash_v0_3_save_integrity_key_2025"


def _read_settings() -> dict:
    try:
        loaded = json.loads(_get_settings_path().read_text(encoding="utf-8"))
        return {**_DEFAULT_SETTINGS, **loaded}
    except Exception:
        return _DEFAULT_SETTINGS.copy()


def _write_settings_safe(data: dict) -> None:
    path = _get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def _format_playtime(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def _verify_save_hmac(data_dict: dict, signature: str) -> bool:
    """Verify a save file's HMAC-SHA256 integrity signature."""
    data_str = json.dumps(data_dict, sort_keys=True)
    expected = hmac.new(_SAVE_HMAC_KEY, data_str.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _get_mods_dir() -> Path:
    return _get_user_data_dir() / "mods"


def _get_enabled_mods_path() -> Path:
    return _get_mods_dir() / "enabled_mods.json"


def _read_mod_manifests() -> list[dict]:
    """Return list of mod manifest dicts (each has an extra '_path' key)."""
    mods_dir = _get_mods_dir()
    results = []
    if not mods_dir.exists():
        return results
    for subdir in sorted(mods_dir.iterdir()):
        if not subdir.is_dir():
            continue
        manifest_path = subdir / "mod.json"
        if not manifest_path.exists():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["_path"] = str(subdir)
            results.append(data)
        except Exception:
            pass
    return results


def _read_enabled_mods() -> "set | None":
    """Return set of enabled mod IDs, or None if no config exists (treat all as enabled)."""
    path = _get_enabled_mods_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("enabled", []))
    except Exception:
        return None


def _write_enabled_mods(enabled: set) -> None:
    """Write enabled_mods.json listing enabled and disabled mod IDs."""
    all_ids = {m["mod_id"] for m in _read_mod_manifests()}
    disabled = sorted(all_ids - enabled)
    data = {"enabled": sorted(enabled), "disabled": disabled}
    path = _get_enabled_mods_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


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


def _read_replay_meta(path: Path) -> dict:
    """Read a replay JSON and return its metadata keys (omits 'commands' list)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
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
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", parts[-1]],
                            capture_output=True)
                        break
        else:
            subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
    except Exception:
        pass
    time.sleep(0.3)
    return not _is_port_in_use(port)


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
        self.root.resizable(True, True)
        self.root.minsize(640, 540)
        self.root.configure(bg=BG_DARK)

        self._local_version = _read_local_version()
        self._all_releases: list[dict] = []
        self._selected_release: dict | None = None
        self._downloading = False
        self._download_cancel = threading.Event()
        self._splash_photo: tk.PhotoImage | None = None
        self._benchmark_proc: subprocess.Popen | None = None
        self._java_server_proc: subprocess.Popen | None = None
        self._benchmark_timer: threading.Timer | None = None
        self._record_var = tk.IntVar(value=0)
        self._record_name_var = tk.StringVar(value="")
        self._settings_vars: dict[str, tk.Variable] = {}
        self._ctrl_key_labels: dict[str, tk.Label] = {}
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
            text="INDIE NINJA ADVENTURES",
            font=("Impact", 18),
            fill="#050510",
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx,
            ty,
            text="INDIE NINJA ADVENTURES",
            font=("Impact", 18),
            fill=ACCENT,
            anchor="sw",
        )
        self._splash_canvas.create_text(
            tx,
            ty - 22,
            text="Vain Asher Gaming",
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
        mods_frame = tk.Frame(self._notebook, bg=BG_DARK)

        self._notebook.add(play_frame, text="  Play  ")
        self._notebook.add(report_frame, text="  Report  ")
        self._notebook.add(devtools_frame, text="  Dev Tools  ")
        self._notebook.add(replays_frame, text="  Replays  ")
        self._notebook.add(saves_frame, text="  Saves  ")
        self._notebook.add(settings_frame, text="  Settings  ")
        self._notebook.add(mods_frame, text="  Mods  ")

        self._build_play_tab(play_frame)
        self._build_report_tab(report_frame)
        self._build_devtools_tab(devtools_frame)
        self._build_replays_tab(replays_frame)
        self._build_saves_tab(saves_frame)
        self._build_settings_tab(settings_frame)
        self._build_mods_tab(mods_frame)

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

        # Ping button + result label
        tk.Frame(mp_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=12)
        ping_frame = tk.Frame(mp_row, bg=BG_DARK)
        ping_frame.pack(side="left")
        tk.Button(
            ping_frame,
            text="Ping",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=5,
            command=self._ping_server_addr,
        ).pack(side="left")
        self._ping_result_var = tk.StringVar(value="")
        self._ping_result_label_widget = tk.Label(
            ping_frame,
            textvariable=self._ping_result_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        )
        self._ping_result_label_widget.pack(side="left", padx=(4, 0))

        # ── Java Client section ───────────────────────────────────────────────
        tk.Frame(ctrl, height=1, bg=ACCENT).pack(fill="x", pady=(10, 0))

        java_header = tk.Frame(ctrl, bg=BG_DARK)
        java_header.pack(fill="x", pady=(4, 0))
        tk.Label(
            java_header,
            text="JAVA CLIENT",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
        ).pack(side="left")
        tk.Label(
            java_header,
            text="beta",
            font=("Consolas", 7),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left", padx=(6, 0))

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

        # Launch row
        java_btn_row = tk.Frame(ctrl, bg=BG_DARK)
        java_btn_row.pack(fill="x", pady=(6, 0))

        self._java_solo_btn = tk.Button(
            java_btn_row,
            text="[J]  Connect to localhost",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=5,
            command=self._launch_java_solo,
        )
        self._java_solo_btn.pack(side="left")

        tk.Frame(java_btn_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=12)

        # Java server controls (host port + start server button)
        java_server_frame = tk.Frame(java_btn_row, bg=BG_DARK)
        java_server_frame.pack(side="left")

        tk.Label(
            java_server_frame,
            text="Connect:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        self._java_addr_var = tk.StringVar(value="")
        self._java_addr_entry = tk.Entry(
            java_server_frame,
            textvariable=self._java_addr_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_DIM,
            insertbackground=ACCENT,
            relief="flat",
            width=14,
        )
        self._java_addr_entry.pack(side="left", padx=(4, 6))
        self._java_addr_entry.insert(0, "host:7777")
        self._java_addr_entry.bind("<FocusIn>", self._on_java_addr_focus_in)
        self._java_addr_entry.bind("<FocusOut>", self._on_java_addr_focus_out)

        self._java_join_btn = tk.Button(
            java_server_frame,
            text="->  Join",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BTN_JOIN_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=5,
            command=self._launch_java_join,
        )
        self._java_join_btn.pack(side="left")

        tk.Frame(java_btn_row, width=1, bg=BG_MID).pack(side="left", fill="y", padx=12)

        self._java_server_btn = tk.Button(
            java_btn_row,
            text="[S]  Start Server",
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BTN_HOST_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=5,
            command=self._launch_java_server,
        )
        self._java_server_btn.pack(side="left")

        self._refresh_java_section()

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

        # Baseline compare row
        prof_btn_row2 = tk.Frame(pad, bg=BG_DARK)
        prof_btn_row2.pack(fill="x", pady=(4, 0))
        tk.Label(
            prof_btn_row2,
            text="Baseline:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")
        self._baseline_var = tk.StringVar()
        self._baseline_combo = ttk.Combobox(
            prof_btn_row2,
            textvariable=self._baseline_var,
            state="readonly",
            style="Launcher.TCombobox",
            width=22,
            font=("Consolas", 8),
        )
        self._baseline_combo.pack(side="left", padx=(4, 6))
        tk.Button(
            prof_btn_row2,
            text="Compare",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._compare_to_baseline,
        ).pack(side="left")

        # Table / Chart toggle
        self._prof_view_mode = "table"
        toggle_row = tk.Frame(pad, bg=BG_DARK)
        toggle_row.pack(fill="x", pady=(4, 0))
        self._prof_table_btn = tk.Button(
            toggle_row,
            text="[Table]",
            font=("Consolas", 8, "bold"),
            fg=TEXT_SELECTED,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=2,
            command=lambda: self._set_prof_view("table"),
        )
        self._prof_table_btn.pack(side="left")
        self._prof_chart_btn = tk.Button(
            toggle_row,
            text="Chart",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=2,
            command=lambda: self._set_prof_view("chart"),
        )
        self._prof_chart_btn.pack(side="left", padx=(4, 0))

        # Results display: text table (read-only, scrollable)
        prof_text_frame = tk.Frame(pad, bg=BG_CARD)
        prof_text_frame.pack(fill="x", pady=(6, 0))
        self._prof_txt = tk.Text(
            prof_text_frame,
            font=("Consolas", 8),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            wrap="none",
            relief="flat",
            height=8,
            state="disabled",
        )
        _prof_ys = ttk.Scrollbar(prof_text_frame, orient="vertical", command=self._prof_txt.yview)
        _prof_xs = ttk.Scrollbar(prof_text_frame, orient="horizontal", command=self._prof_txt.xview)
        self._prof_txt.configure(yscrollcommand=_prof_ys.set, xscrollcommand=_prof_xs.set)
        _prof_xs.pack(side="bottom", fill="x")
        _prof_ys.pack(side="right", fill="y")
        self._prof_txt.pack(fill="both", expand=True)
        self._prof_text_frame = prof_text_frame

        # Chart canvas (hidden until chart mode selected)
        self._prof_canvas = tk.Canvas(
            pad,
            bg=BG_CARD,
            height=120,
            highlightthickness=0,
        )
        # Not packed yet — shown on demand

        self._refresh_baseline_list()
        # Load existing CSV on open
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

        sig = wrapper.get("signature", "")
        inner = wrapper.get("data", {})
        if sig and inner:
            ok = _verify_save_hmac(inner, sig)
            status = "★ Verified" if ok else "✗ Signature mismatch"
        elif inner:
            status = "? No signature (old format)"
        else:
            status = "? Unknown format"
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
            text="Save Settings",
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            command=self._save_settings_from_ui,
            **_b,
        ).pack(side="left")
        tk.Button(
            btn_frame,
            text="Reset to Defaults",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._reset_settings_to_defaults,
            **_b,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_frame,
            text="Open File",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._open_settings_file,
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

        def _sldr(key: str, label: str, lo: float = 0.0, hi: float = 1.0) -> None:
            var = tk.DoubleVar()
            self._settings_vars[key] = var
            row = tk.Frame(pad, bg=BG_DARK)
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=label,
                font=("Consolas", 9),
                fg=TEXT_DIM,
                bg=BG_DARK,
                width=20,
                anchor="w",
            ).pack(side="left")
            val_lbl = tk.Label(
                row,
                text="0.00",
                font=("Consolas", 9),
                fg=TEXT_PRIMARY,
                bg=BG_DARK,
                width=5,
                anchor="e",
            )
            val_lbl.pack(side="right")

            def _upd(*_):
                val_lbl.config(text=f"{var.get():.2f}")

            var.trace_add("write", _upd)
            tk.Scale(
                row,
                variable=var,
                from_=lo,
                to=hi,
                orient="horizontal",
                length=200,
                bg=BG_DARK,
                fg=TEXT_DIM,
                troughcolor=BG_MID,
                highlightbackground=BG_DARK,
                activebackground=ACCENT,
                sliderrelief="flat",
                showvalue=0,
                resolution=0.01,
                bd=0,
            ).pack(side="right", padx=(0, 4))

        def _chk(key: str, label: str) -> None:
            var = tk.BooleanVar()
            self._settings_vars[key] = var
            tk.Checkbutton(
                pad,
                text=label,
                variable=var,
                font=("Consolas", 9),
                fg=TEXT_PRIMARY,
                bg=BG_DARK,
                activebackground=BG_DARK,
                activeforeground=TEXT_SELECTED,
                selectcolor=BG_MID,
                relief="flat",
                bd=0,
            ).pack(anchor="w", pady=2)

        # PATHS
        _sec("PATHS")
        tk.Label(
            pad,
            text=(
                "Game Directory — the folder containing ninja_dash.exe,\n"
                "user_data/, mods/, and version.json.\n"
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

        # AUDIO
        _sec("AUDIO")
        _sldr("volume_master", "Master Volume")
        _sldr("volume_music", "Music Volume")
        _sldr("volume_sfx", "SFX Volume")

        # DISPLAY
        _sec("DISPLAY")
        disp_row = tk.Frame(pad, bg=BG_DARK)
        disp_row.pack(fill="x", pady=2)
        for key, label in [
            ("fullscreen", "Fullscreen"),
            ("vsync", "VSync"),
            ("show_fps", "Show FPS"),
        ]:
            var = tk.BooleanVar()
            self._settings_vars[key] = var
            tk.Checkbutton(
                disp_row,
                text=label,
                variable=var,
                font=("Consolas", 9),
                fg=TEXT_PRIMARY,
                bg=BG_DARK,
                activebackground=BG_DARK,
                activeforeground=TEXT_SELECTED,
                selectcolor=BG_MID,
                relief="flat",
                bd=0,
            ).pack(side="left", padx=(0, 16))

        res_row = tk.Frame(pad, bg=BG_DARK)
        res_row.pack(fill="x", pady=2)
        tk.Label(
            res_row,
            text="Resolution:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            width=14,
            anchor="w",
        ).pack(side="left")
        res_var = tk.StringVar()
        self._settings_vars["resolution"] = res_var
        ttk.Combobox(
            res_row,
            textvariable=res_var,
            values=["800x600", "1280x720", "1920x1080", "2560x1440"],
            state="readonly",
            style="Launcher.TCombobox",
            width=13,
            font=("Consolas", 9),
        ).pack(side="left", padx=(4, 8))
        tk.Label(
            res_row,
            text="(requires restart)",
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(side="left")

        # GAMEPLAY
        _sec("GAMEPLAY")
        _chk("screenshake", "Screen Shake")
        _chk("particles", "Particles")
        _sldr("camera_smoothing", "Camera Smoothing")

        # CONTROLS (read-only display)
        _sec("CONTROLS")
        ctrl_grid = tk.Frame(pad, bg=BG_DARK)
        ctrl_grid.pack(fill="x", pady=(0, 4))
        for i, (key, label) in enumerate(
            [
                ("key_left", "Left"),
                ("key_right", "Right"),
                ("key_jump", "Jump"),
                ("key_dash", "Dash"),
                ("key_crouch", "Crouch"),
            ]
        ):
            col_f = tk.Frame(ctrl_grid, bg=BG_DARK)
            col_f.pack(side="left", padx=(0, 20))
            tk.Label(
                col_f,
                text=f"{label}:",
                font=("Consolas", 8),
                fg=TEXT_DIM,
                bg=BG_DARK,
                anchor="w",
            ).pack(fill="x")
            klbl = tk.Label(
                col_f,
                text="—",
                font=("Consolas", 9, "bold"),
                fg=TEXT_PRIMARY,
                bg=BG_DARK,
                anchor="w",
            )
            klbl.pack(fill="x")
            self._ctrl_key_labels[key] = klbl

        # DEVELOPER
        _sec("DEVELOPER")
        _chk("show_hitboxes", "Show Hitboxes")
        dev_row = tk.Frame(pad, bg=BG_DARK)
        dev_row.pack(fill="x", pady=2)
        tk.Label(
            dev_row,
            text="Log Level:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            width=14,
            anchor="w",
        ).pack(side="left")
        log_var = tk.StringVar()
        self._settings_vars["log_level"] = log_var
        ttk.Combobox(
            dev_row,
            textvariable=log_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            style="Launcher.TCombobox",
            width=10,
            font=("Consolas", 9),
        ).pack(side="left", padx=(4, 0))

        self._load_settings_into_ui()

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

    def _load_settings_into_ui(self) -> None:
        settings = _read_settings()
        for key, var in self._settings_vars.items():
            if key == "resolution":
                w = settings.get("window_width", 1280)
                h = settings.get("window_height", 720)
                var.set(f"{w}x{h}")
            else:
                val = settings.get(key, _DEFAULT_SETTINGS.get(key))
                if val is not None:
                    var.set(val)
        for key, lbl in self._ctrl_key_labels.items():
            lbl.config(text=str(settings.get(key, _DEFAULT_SETTINGS.get(key, "—"))))

    def _save_settings_from_ui(self) -> None:
        settings = _read_settings()
        for key, var in self._settings_vars.items():
            if key == "resolution":
                try:
                    w, h = var.get().split("x")
                    settings["window_width"] = int(w)
                    settings["window_height"] = int(h)
                except ValueError:
                    pass
            else:
                settings[key] = var.get()
        try:
            _write_settings_safe(settings)
            messagebox.showinfo("Saved", "Settings saved.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc), parent=self.root)

    def _reset_settings_to_defaults(self) -> None:
        if not messagebox.askyesno(
            "Reset Settings", "Reset all settings to defaults?", parent=self.root
        ):
            return
        try:
            _write_settings_safe(_DEFAULT_SETTINGS.copy())
            self._load_settings_into_ui()
            messagebox.showinfo("Reset", "Settings reset to defaults.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Reset Failed", str(exc), parent=self.root)

    def _open_settings_file(self) -> None:
        path = _get_settings_path()
        if not path.exists():
            try:
                _write_settings_safe(_DEFAULT_SETTINGS.copy())
            except Exception:
                pass
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
        self._refresh_mods_list()
        self._refresh_baseline_list()
        # Also re-read the local game version from the new directory
        self._local_version = _read_local_version()

    # ── Tab 7: Mods ───────────────────────────────────────────────────────────

    def _build_mods_tab(self, parent: tk.Frame) -> None:
        pad = tk.Frame(parent, bg=BG_DARK)
        pad.pack(fill="both", expand=True, padx=16, pady=(8, 6))

        # Header
        hdr_row = tk.Frame(pad, bg=BG_DARK)
        hdr_row.pack(fill="x")
        tk.Label(
            hdr_row,
            text="INSTALLED MODS",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")
        _b = dict(font=("Consolas", 9), relief="flat", cursor="hand2", padx=8, pady=3)
        tk.Button(
            hdr_row,
            text="Open Folder",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._reveal_mods_folder,
            **_b,
        ).pack(side="right")
        tk.Button(
            hdr_row,
            text="Refresh",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._refresh_mods_list,
            **_b,
        ).pack(side="right", padx=(0, 4))
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(3, 6))

        # Mods Treeview
        tree_frame = tk.Frame(pad, bg=BG_CARD)
        tree_frame.pack(fill="x")

        cols = ("en", "name", "version", "author", "status")
        self._mods_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            style="Replay.Treeview",
            height=6,
            selectmode="browse",
        )
        for col, width, label in [
            ("en", 30, ""),
            ("name", 160, "Name"),
            ("version", 70, "Version"),
            ("author", 90, "Author"),
            ("status", 90, "Status"),
        ]:
            self._mods_tree.heading(col, text=label, anchor="w")
            self._mods_tree.column(col, width=width, minwidth=20, stretch=(col == "name"))

        mods_ys = tk.Scrollbar(tree_frame, orient="vertical", command=self._mods_tree.yview)
        self._mods_tree.configure(yscrollcommand=mods_ys.set)
        mods_ys.pack(side="right", fill="y")
        self._mods_tree.pack(fill="x")
        self._mods_tree.bind("<<TreeviewSelect>>", self._on_mod_selected)
        self._mods_tree.bind("<ButtonRelease-1>", self._on_mods_tree_click)

        # Pending-restart note
        self._mods_note_var = tk.StringVar(value="")
        tk.Label(
            pad,
            textvariable=self._mods_note_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_DARK,
            anchor="w",
        ).pack(fill="x", pady=(3, 0))

        # Detail panel
        detail_frame = tk.Frame(pad, bg=BG_CARD)
        detail_frame.pack(fill="x", pady=(6, 0))
        self._mod_detail_var = tk.StringVar(value="Select a mod above to see details.")
        tk.Label(
            detail_frame,
            textvariable=self._mod_detail_var,
            font=("Consolas", 8),
            fg=TEXT_DIM,
            bg=BG_CARD,
            anchor="w",
            justify="left",
            padx=6,
            pady=4,
        ).pack(fill="x")

        # Action buttons
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(8, 0))
        btn_row = tk.Frame(pad, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(6, 0))

        _b2 = dict(font=("Consolas", 9), relief="flat", cursor="hand2", padx=10, pady=4)
        tk.Button(
            btn_row,
            text="Toggle Enable",
            fg=TEXT_PRIMARY,
            bg=BG_MID,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            command=self._toggle_selected_mod,
            **_b2,
        ).pack(side="left")
        tk.Button(
            btn_row,
            text="Reveal Folder",
            fg=TEXT_DIM,
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground=TEXT_PRIMARY,
            command=self._reveal_selected_mod_folder,
            **_b2,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            btn_row,
            text="Delete Mod",
            fg="#e05252",
            bg=BG_DARK,
            activebackground=BG_MID,
            activeforeground="#e05252",
            command=self._delete_selected_mod,
            **_b2,
        ).pack(side="left", padx=(6, 0))

        # Install section
        tk.Frame(pad, height=1, bg=BG_MID).pack(fill="x", pady=(10, 0))
        inst_hdr = tk.Frame(pad, bg=BG_DARK)
        inst_hdr.pack(fill="x", pady=(4, 4))
        tk.Label(
            inst_hdr,
            text="INSTALL MOD",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BG_DARK,
            anchor="w",
        ).pack(side="left")

        inst_row = tk.Frame(pad, bg=BG_DARK)
        inst_row.pack(fill="x")
        tk.Label(
            inst_row,
            text="From ZIP:",
            font=("Consolas", 9),
            fg=TEXT_DIM,
            bg=BG_DARK,
            width=10,
            anchor="w",
        ).pack(side="left")
        self._mod_zip_var = tk.StringVar()
        tk.Entry(
            inst_row,
            textvariable=self._mod_zip_var,
            font=("Consolas", 9),
            bg=BG_MID,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            width=28,
        ).pack(side="left", padx=(4, 6))
        tk.Button(
            inst_row,
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
            command=self._browse_mod_zip,
        ).pack(side="left")
        tk.Button(
            inst_row,
            text="Install",
            font=("Consolas", 9, "bold"),
            fg=ACCENT,
            bg=BTN_PLAY_BG,
            activebackground=BG_CARD,
            activeforeground=TEXT_SELECTED,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=3,
            command=self._install_mod_zip,
        ).pack(side="left", padx=(6, 0))

        self._refresh_mods_list()

    # ── Mods tab actions ──────────────────────────────────────────────────────

    def _refresh_mods_list(self) -> None:
        for row in self._mods_tree.get_children():
            self._mods_tree.delete(row)
        manifests = _read_mod_manifests()
        if not manifests:
            self._mods_note_var.set("No mods found in user_data/mods/")
            self._mod_detail_var.set("No mods installed.")
            return

        enabled_set = _read_enabled_mods()
        all_ids = {m["mod_id"] for m in manifests}

        for m in manifests:
            mod_id = m.get("mod_id", "?")
            # enabled_set is None means all enabled (no config written yet)
            is_enabled = enabled_set is None or mod_id in enabled_set
            en_str = "☑" if is_enabled else "☐"

            deps = m.get("dependencies", [])
            missing = [d for d in deps if d not in all_ids]
            if missing:
                status = f"Missing: {', '.join(missing)}"
            else:
                status = "OK"

            self._mods_tree.insert(
                "",
                "end",
                iid=mod_id,
                values=(
                    en_str,
                    m.get("name", mod_id),
                    m.get("version", "?"),
                    m.get("author", "?"),
                    status,
                ),
            )

        note = "(enable/disable takes effect after game restart)" if manifests else ""
        self._mods_note_var.set(note)

        first = self._mods_tree.get_children()
        if first:
            self._mods_tree.selection_set(first[0])
            self._on_mod_selected()

    def _on_mod_selected(self, _event=None) -> None:
        sel = self._mods_tree.selection()
        if not sel:
            return
        mod_id = sel[0]
        manifests = _read_mod_manifests()
        m = next((x for x in manifests if x.get("mod_id") == mod_id), None)
        if not m:
            return
        deps = m.get("dependencies", []) or []
        dep_str = ", ".join(deps) if deps else "none"
        self._mod_detail_var.set(
            f"ID: {mod_id}   Version: {m.get('version', '?')}   Entry: {m.get('entry_point', '?')}\n"
            f"Description: {m.get('description', '—')}\n"
            f"Dependencies: {dep_str}\n"
            f"Path: {m.get('_path', '?')}"
        )

    def _on_mods_tree_click(self, event) -> None:
        region = self._mods_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self._mods_tree.identify_column(event.x)
        if col != "#1":  # "en" column
            return
        iid = self._mods_tree.identify_row(event.y)
        if iid:
            self._toggle_mod_enabled(iid)

    def _toggle_selected_mod(self) -> None:
        sel = self._mods_tree.selection()
        if not sel:
            messagebox.showwarning("No Mod Selected", "Select a mod first.", parent=self.root)
            return
        self._toggle_mod_enabled(sel[0])

    def _toggle_mod_enabled(self, mod_id: str) -> None:
        enabled_set = _read_enabled_mods()
        if enabled_set is None:
            # First write: start with all enabled, then toggle
            all_ids = {m["mod_id"] for m in _read_mod_manifests()}
            enabled_set = all_ids.copy()
        if mod_id in enabled_set:
            enabled_set.discard(mod_id)
        else:
            enabled_set.add(mod_id)
        _write_enabled_mods(enabled_set)
        self._refresh_mods_list()
        # Re-select the toggled mod
        if self._mods_tree.exists(mod_id):
            self._mods_tree.selection_set(mod_id)

    def _reveal_selected_mod_folder(self) -> None:
        sel = self._mods_tree.selection()
        if not sel:
            return
        mod_id = sel[0]
        mod_dir = _get_mods_dir() / mod_id
        if not mod_dir.exists():
            return
        try:
            os.startfile(str(mod_dir))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(mod_dir)])

    def _reveal_mods_folder(self) -> None:
        mods_dir = _get_mods_dir()
        mods_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(mods_dir))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(mods_dir)])

    def _delete_selected_mod(self) -> None:
        sel = self._mods_tree.selection()
        if not sel:
            messagebox.showwarning("No Mod Selected", "Select a mod first.", parent=self.root)
            return
        mod_id = sel[0]
        mod_dir = _get_mods_dir() / mod_id
        if not messagebox.askyesno(
            "Delete Mod",
            f"Delete mod '{mod_id}' and all its files?\n\nThis cannot be undone.",
            parent=self.root,
        ):
            return
        try:
            shutil.rmtree(mod_dir)
        except OSError as exc:
            messagebox.showerror("Delete Failed", str(exc), parent=self.root)
            return
        # Remove from enabled list if present
        enabled_set = _read_enabled_mods()
        if enabled_set is not None:
            enabled_set.discard(mod_id)
            _write_enabled_mods(enabled_set)
        self._refresh_mods_list()

    def _browse_mod_zip(self) -> None:
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Select Mod ZIP",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            parent=self.root,
        )
        if path:
            self._mod_zip_var.set(path)

    def _install_mod_zip(self) -> None:
        import zipfile

        zip_path_str = self._mod_zip_var.get().strip()
        if not zip_path_str:
            messagebox.showwarning(
                "No File Selected", "Browse to a ZIP file first.", parent=self.root
            )
            return
        zip_path = Path(zip_path_str)
        if not zip_path.exists():
            messagebox.showerror("Not Found", f"File not found:\n{zip_path}", parent=self.root)
            return

        if not messagebox.askyesno(
            "Security Warning",
            "Mods execute Python code on your machine.\n\n"
            "Only install mods from sources you trust.\n\n"
            "Continue with installation?",
            parent=self.root,
            icon="warning",
        ):
            return

        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                candidates = [n for n in names if n.rstrip("/").endswith("mod.json")]
                if not candidates:
                    messagebox.showerror(
                        "Invalid Mod ZIP", "No mod.json found in the ZIP file.", parent=self.root
                    )
                    return
                # Pick the shallowest mod.json
                manifest_name = min(candidates, key=lambda n: n.count("/"))
                manifest_data = json.loads(zf.read(manifest_name).decode("utf-8"))
                mod_id = manifest_data.get("mod_id", "").strip()
                if not mod_id:
                    messagebox.showerror(
                        "Invalid mod.json",
                        "mod.json is missing the 'mod_id' field.",
                        parent=self.root,
                    )
                    return

                dest_dir = _get_mods_dir() / mod_id
                if dest_dir.exists():
                    if not messagebox.askyesno(
                        "Overwrite?",
                        f"Mod '{mod_id}' is already installed. Overwrite?",
                        parent=self.root,
                    ):
                        return
                    shutil.rmtree(dest_dir)
                dest_dir.mkdir(parents=True, exist_ok=True)

                # Strip common prefix (supports both flat and subfolder layout)
                prefix = manifest_name[: manifest_name.rfind("/") + 1]
                for member in zf.infolist():
                    fname = member.filename
                    if not fname.startswith(prefix) or fname == prefix:
                        continue
                    rel = fname[len(prefix) :]
                    out = dest_dir / rel
                    if fname.endswith("/"):
                        out.mkdir(parents=True, exist_ok=True)
                    else:
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(zf.read(fname))
        except Exception as exc:
            messagebox.showerror("Install Failed", str(exc), parent=self.root)
            return

        # Auto-enable the newly installed mod
        enabled_set = _read_enabled_mods()
        if enabled_set is None:
            enabled_set = {m["mod_id"] for m in _read_mod_manifests()}
        else:
            enabled_set.add(mod_id)
        _write_enabled_mods(enabled_set)

        self._mod_zip_var.set("")
        self._refresh_mods_list()
        messagebox.showinfo(
            "Installed",
            f"Mod '{mod_id}' installed and enabled.\n\nRestart the game to apply.",
            parent=self.root,
        )

    # ── Profiler actions ──────────────────────────────────────────────────────

    def _refresh_profiler_display(self, baseline_stats: dict | None = None) -> None:
        """Read the existing profiler CSV (if any) and show a summary in the Text widget."""
        csv_path = _get_profiler_csv()
        stats = _parse_profiler_csv(csv_path)

        self._prof_txt.configure(state="normal")
        self._prof_txt.delete("1.0", "end")

        if not stats:
            self._prof_txt.insert("1.0", "No profiler data — run a benchmark first.")
            self._prof_txt.configure(state="disabled")
            return

        has_baseline = baseline_stats is not None
        if has_baseline:
            header = f"{'Section':<20s}  {'avg':>7s}  {'p95':>7s}  {'max':>7s}  {'Δavg':>8s}"
        else:
            header = f"{'Section':<20s}  {'avg':>7s}  {'p95':>7s}  {'max':>7s}"
        sep = "─" * len(header)

        fps_line = (
            f"Frames: {stats['frame_count']}    "
            f"FPS  avg={stats['fps_avg']:.1f}  p5={stats['fps_p5']:.1f}  min={stats['fps_min']:.1f}"
        )
        lines = [fps_line, sep, header, sep]

        sections = [k for k in stats if k not in ("frame_count", "fps_avg", "fps_p5", "fps_min")]
        for sec in sections:
            d = stats[sec]
            if has_baseline and sec in baseline_stats:
                bd = baseline_stats[sec]
                delta = d["avg"] - bd["avg"]
                sign = "+" if delta >= 0 else ""
                lines.append(
                    f"  {sec:<18s}  {d['avg']:6.2f}ms  {d['p95']:6.2f}ms  {d['max']:6.2f}ms  "
                    f"{sign}{delta:+.2f}ms"
                )
            else:
                lines.append(
                    f"  {sec:<18s}  {d['avg']:6.2f}ms  {d['p95']:6.2f}ms  {d['max']:6.2f}ms"
                )

        self._prof_txt.insert("1.0", "\n".join(lines))
        self._prof_txt.configure(state="disabled")

        if self._prof_view_mode == "chart":
            self._draw_profiler_chart(stats)

    def _refresh_baseline_list(self) -> None:
        """Populate the baseline combobox with perf_baseline*.csv files."""
        base_dir = _get_user_data_dir()
        files = (
            sorted(base_dir.glob("perf_baseline*.csv"), reverse=True) if base_dir.exists() else []
        )
        names = [f.name for f in files]
        self._baseline_combo.configure(values=names)
        if names:
            self._baseline_combo.current(0)

    def _compare_to_baseline(self) -> None:
        """Parse selected baseline CSV and re-render profiler display with delta column."""
        name = self._baseline_var.get()
        if not name:
            messagebox.showinfo("No Baseline", "No baseline file selected.", parent=self.root)
            return
        baseline_path = _get_user_data_dir() / name
        baseline_stats = _parse_profiler_csv(baseline_path)
        if not baseline_stats:
            messagebox.showerror(
                "Parse Error", f"Could not read baseline:\n{baseline_path}", parent=self.root
            )
            return
        self._refresh_profiler_display(baseline_stats=baseline_stats)
        self._bench_status_var.set(f"Comparing vs {name}")

    def _set_prof_view(self, mode: str) -> None:
        """Toggle between 'table' and 'chart' view for profiler results."""
        self._prof_view_mode = mode
        if mode == "table":
            self._prof_table_btn.configure(
                fg=TEXT_SELECTED, bg=BG_MID, font=("Consolas", 8, "bold")
            )
            self._prof_chart_btn.configure(fg=TEXT_DIM, bg=BG_DARK, font=("Consolas", 8))
            self._prof_canvas.pack_forget()
            self._prof_text_frame.pack(fill="x", pady=(6, 0))
        else:
            self._prof_chart_btn.configure(
                fg=TEXT_SELECTED, bg=BG_MID, font=("Consolas", 8, "bold")
            )
            self._prof_table_btn.configure(fg=TEXT_DIM, bg=BG_DARK, font=("Consolas", 8))
            self._prof_text_frame.pack_forget()
            self._prof_canvas.pack(fill="x", pady=(6, 0))
            csv_path = _get_profiler_csv()
            stats = _parse_profiler_csv(csv_path)
            if stats:
                self._draw_profiler_chart(stats)
            else:
                self._prof_canvas.delete("all")
                self._prof_canvas.create_text(
                    4, 60, text="No data", fill=TEXT_DIM, anchor="w", font=("Consolas", 8)
                )

    def _draw_profiler_chart(self, stats: dict) -> None:
        """Draw a horizontal bar chart of per-section avg timings on the Canvas."""
        canvas = self._prof_canvas
        canvas.update_idletasks()
        canvas.delete("all")

        sections = [k for k in stats if k not in ("frame_count", "fps_avg", "fps_p5", "fps_min")]
        if not sections:
            return

        W = canvas.winfo_width() or 400
        label_w = 130
        bar_area = W - label_w - 60
        max_val = max(stats[s]["avg"] for s in sections) or 1.0
        bar_h = 14
        gap = 6
        y0 = 8

        for i, sec in enumerate(sections):
            avg = stats[sec]["avg"]
            y = y0 + i * (bar_h + gap)
            bar_len = int(bar_area * avg / max_val)
            # Color thresholds (ms)
            if avg < 8:
                color = "#4caf50"  # green
            elif avg < 16:
                color = "#ffd700"  # yellow (ACCENT)
            else:
                color = "#e53935"  # red
            canvas.create_text(
                label_w - 4,
                y + bar_h // 2,
                text=sec[:20],
                fill=TEXT_DIM,
                anchor="e",
                font=("Consolas", 7),
            )
            canvas.create_rectangle(
                label_w, y, label_w + bar_len, y + bar_h, fill=color, outline=""
            )
            canvas.create_text(
                label_w + bar_len + 4,
                y + bar_h // 2,
                text=f"{avg:.2f}ms",
                fill=TEXT_PRIMARY,
                anchor="w",
                font=("Consolas", 7),
            )

    def _run_benchmark(self) -> None:
        """Launch the game headless with --profile, kill after N seconds, refresh display."""
        if self._benchmark_proc is not None:
            return  # already running

        game_path = _get_game_exe()
        if not game_path.exists():
            messagebox.showerror(
                "Game Not Found", f"Could not find:\n{game_path}", parent=self.root
            )
            return

        cmd = [sys.executable, str(game_path)] if game_path.suffix == ".py" else [str(game_path)]
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
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc), parent=self.root)

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

        if not has_exe:
            self._download_btn.configure(state="disabled", text="v  No exe asset")
            return

        installed = self._game_exe_installed()
        has_jars = _find_jar_asset(assets, "ninja-server") and _find_jar_asset(
            assets, "ninja-client"
        )
        jars_installed = _get_server_jar().exists() and _get_client_jar().exists()

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

        self._download_btn.configure(state="normal", text=label)
        play_state = "normal" if installed else "disabled"
        play_fg = ACCENT if installed else TEXT_DIM
        self._play_btn.configure(state=play_state, fg=play_fg)

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

        sha_asset = next((a for a in assets if a.get("name") == f"{GAME_EXE_NAME}.sha256"), None)
        expected_sha = None
        if sha_asset:
            try:
                with urllib.request.urlopen(sha_asset["browser_download_url"], timeout=10) as r:
                    expected_sha = r.read().decode().strip().split()[0]
            except Exception:
                pass

        server_jar_asset = _find_jar_asset(assets, "ninja-server")
        client_jar_asset = _find_jar_asset(assets, "ninja-client")

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

            self.root.after(0, self._on_download_done, tag)

        except Exception as exc:
            dest.unlink(missing_ok=True)
            self.root.after(0, self._on_download_error, str(exc))

    def _on_download_done(self, tag: str) -> None:
        self._downloading = False
        self._cancel_btn.pack_forget()
        self._local_version = tag.lstrip("v")
        self._progress_var.set(100.0)
        self._status_var.set(f"OK  {tag} installed. Ready to play.")
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

    # ── Server ping (P3-F5) ───────────────────────────────────────────────────

    def _ping_server_addr(self) -> None:
        """TCP-connect to the join address and report latency."""
        addr = self._join_addr_var.get().strip()
        if not addr or addr == self._JOIN_PLACEHOLDER:
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
        self._java_solo_btn.configure(state=btn_state, fg=btn_fg)
        self._java_join_btn.configure(state=btn_state)
        self._java_server_btn.configure(state=srv_state)

    def _launch_java_solo(self) -> None:
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
        cmd = [java, "-XX:+UseZGC", "-Xms128m", "-Xmx512m", "-jar", str(jar), host, str(port)]
        try:
            proc = subprocess.Popen(cmd)
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
        cmd = [java, "-XX:+UseZGC", "-Xms128m", "-Xmx512m", "-jar", str(jar), str(port)]
        try:
            self._java_server_proc = subprocess.Popen(cmd)
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
