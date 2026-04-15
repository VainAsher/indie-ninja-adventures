---
doc_type: plan
status: completed
owner: core-team
last_updated: 2026-04-15
version_anchor: v0.11.45
---
<!-- markdownlint-disable MD031 MD032 MD040 MD060 -->
# Launcher Enhancement Plan

**Version:** 2.2
**Date:** 2026-03-31
**Launcher current version:** v1.1.0
**Game current version:** v0.9.5

> **Note â€” stale `version.json`:** The repository `version.json` still reads `"version": "0.8.4"` because the hotfix branches (v0.8.5 â†’ v0.9.5) did not bump the file. The canonical version is v0.9.5 per git history and `CHANGELOG.md`. `version.json` should be updated to `"0.9.5"` before the next release build.

---

## 1. Executive Summary

### Current State

The launcher (`launcher/launcher.py`, 1,526 lines) is a stdlib-only tkinter application built for Windows. It ships as a standalone `ninja_dash_launcher.exe` via PyInstaller with zero pip dependencies. The launcher has not changed since v1.1.0 (released with game v0.8.0); all game-side changes since then are in the game executable only.

**Current tabs and capabilities:**

| Tab | Features |
| --- | --- |
| **Play** | Version display, auto-update (GitHub Releases API, SHA256 verify), Solo launch, Host (port + max players), Join (host:port) |
| **Report** | Pre-filled GitHub issue URLs (Bug, Feedback, Performance, Crash) with auto-filled version/OS/Python, optional log tail |
| **Dev Tools** | Profiler (10s headless benchmark, CSV parse, per-section timing), Log viewer (20 most recent), Replay launcher (20 most recent) |

**Game changes since the plan was first written (v0.8.4 â†’ v0.9.5):**

| Version | Change | Launcher relevance |
| --- | --- | --- |
| v0.8.5 | Cross-machine world desync fix (hub seed sync) | None |
| v0.8.6 | TCP_NODELAY + non-blocking send loop (lag fix) | None |
| v0.8.7 | Encode-once broadcast, smart INPUT rate limiter | None |
| v0.8.8 | JSON â†’ msgpack wire protocol (PROTOCOL_VERSION 2) | **Version parity now critical** â€” mismatched builds disconnect immediately |
| v0.8.9 | WORLD_STATE delta encoding (~60% bandwidth reduction) | Profiler CSV may have new bandwidth columns |
| v0.9.0 | **Instanced zones** â€” per-hub simulation, portal travel, ZONE_PRESENCE | Multiplayer UI should surface zone/hub state |
| v0.9.1 | Fix visibility regression (ConnectedPlayer.hub_id not set on join) | None |
| v0.9.2 | Fix seed mismatch (derive_region_seed not called for initial zone) | None |
| v0.9.3 | **Phase 3b** server-authoritative combat + 84 new regression tests | Crash reports now carry server-side HP state |
| v0.9.4 | Hotfix: decouple simulation (60 Hz) from broadcast (20 Hz) | Profiler headless benchmark now reflects 20 Hz broadcast |
| v0.9.5 | Hotfix: lerp + hard-snap rubber-band (replaces dead-zone) | None |

### Existing Systems Available for Surfacing

The following game systems produce data the launcher can read without importing any game code â€” pure JSON/CSV on disk:

| System | File Location | Key Data |
| --- | --- | --- |
| **Saves** | `user_data/saves/savegame.json` | PlayerProgress, GameStatistics, CampaignSaveData, HMAC integrity |
| **Replays** | `user_data/replays/<name>.json` | Per-frame input commands + metadata (seed, hub, mission, frames) |
| **Mod manifests** | `user_data/mods/<id>/mod.json` | mod_id, name, version, author, description, dependencies |
| **Settings** | `user_data/settings/settings.json` | Volume, display, gameplay, key bindings, debug flags |
| **Profiler** | `docs/perf_baseline.csv` | 20+ columns: frame, fps, frame_total, update, render, collision, ... |

### Architecture Constraints

- **Stdlib only** â€” no pip dependencies in launcher (urllib, json, hmac, hashlib, zipfile, socket, shutil, threading â€” all stdlib)
- **tkinter** â€” Python 3.11 bundled tk 8.6
- **PyInstaller onefile** â€” spec at `build/ninja_dash_launcher.spec`
- **No game imports** â€” launcher reads files directly; never imports `systems`, `core`, or `game` modules

---

## 2. Architecture Decisions

### A1. Single-File vs. Module Split

Keep everything in `launcher/launcher.py` through Phase 2. The split trigger: if any single tab's `_build_<tab>_tab()` method exceeds ~400 lines, extract it to a sibling module. When that point arrives:

```text
launcher/
    launcher.py           # LauncherApp shell, constants, shared helpers (~600 lines)
    tabs/
        play.py
        report.py
        saves.py
        mods.py
        settings_tab.py
        replays.py
        devtools.py
```

### A2. Window Size Progression

The current fixed geometry is `640x540` (`WINDOW_W = 640`, `WINDOW_H = 540`). New tabs with Treeview layouts require more space.

| After Phase | WINDOW_W | WINDOW_H | Change |
| --- | --- | --- | --- |
| Current | 640 | 540 | Fixed |
| Phase 1 | 640 | 560 | +20px for profile row |
| Phase 2+ | 760 | 640 | `resizable(True, True)`, `minsize(640, 540)` |

Update `WINDOW_W` and `WINDOW_H` constants and any hard-coded canvas widths in the splash frame.

### A3. Shared Data Helpers

Add a block of pure-function helpers in `launcher.py` alongside the existing helpers (currently around lines 90â€“240). These are called from multiple new tabs:

```python
def _get_user_data_dir() -> Path:
    """Returns the user_data/ directory, respecting NINJADASH_USER_DATA env var."""

def _get_saves_dir() -> Path: ...
def _get_mods_dir() -> Path: ...
def _get_settings_path() -> Path: ...
def _get_profiles_path() -> Path: ...    # user_data/profiles/profiles.json (new)
def _read_save_file() -> dict | None:    # strips HMAC wrapper, returns inner data dict
def _read_mod_manifests() -> list[dict]: # scans user_data/mods/*/mod.json
def _read_settings() -> dict:            # merged with DEFAULT_SETTINGS fallbacks
def _write_settings_safe(data: dict):    # atomic write via .tmp + rename
```

### A4. Profile Storage (New File)

User profiles are a launcher-level concept not yet in the game's save system. Store them at `user_data/profiles/profiles.json`:

```json
{
  "active_profile": "Player1",
  "profiles": {
    "Player1": {
      "created": "2026-03-30",
      "save_slot": "savegame.json",
      "avatar_color": "#ffd700"
    }
  }
}
```

Created automatically on first launcher start if absent. The launcher passes `--profile <name>` to the game executable (silently ignored until native support is added).

### A5. Mod Enable/Disable Sidecar (New File)

The mod manager writes a sidecar file that the game's `ModLoader` will read at `user_data/mods/enabled_mods.json`:

```json
{
  "enabled": ["example_mod", "another_mod"],
  "disabled": ["broken_mod"]
}
```

Until `core/mod_system.py` is updated to read this file, the toggle is displayed with a "pending restart" note.

### A6. Backup Protocol

Any launcher operation that writes or deletes a save file must:

1. Create a timestamped copy in `user_data/saves/backups/` **before** the operation
2. Write new content to a `.tmp` file then atomically rename (avoids partial-write corruption)
3. Display a confirmation dialog before destructive operations

---

## 3. Phase 1 â€” Quick Wins

**Scope:** No new tabs. Enhancements to existing Play tab and Dev Tools tab.
**Effort:** 2â€“4 days
**Risk:** Low â€” no file mutations except profile JSON creation

---

### P1-F1: Profile Switcher (Play Tab)

**What:** A profile dropdown and "New Profile" button inserted in the Play tab between the version row and the progress bar. Selecting a profile sets it as active for all subsequent launches.

**UI Addition (Play tab):**

```text
  Profile: [ Player1 â–¼ ]   [ + New Profile ]
```

**Behaviour:**

- On startup: `_read_profiles()` loads `profiles.json`, creates default `"Player1"` if absent
- `ttk.Combobox` bound to `self._profile_var = tk.StringVar()`
- Selecting a profile calls `_on_profile_selected()` â†’ updates `active_profile` â†’ writes `profiles.json`
- "New Profile" opens `tk.simpledialog.askstring("New Profile", "Profile name:")` â†’ validates (non-empty, unique) â†’ writes `profiles.json` â†’ refreshes combobox
- All `_launch_with_args()` calls append `["--profile", self._profile_var.get()]` automatically

**New methods:** `_read_profiles()`, `_write_profiles(data)`, `_build_profile_row(parent)`, `_on_profile_selected()`, `_on_new_profile()`

**Game-side note:** `--profile` arg is silently ignored by `demo_game.py` until native profile support is added. No breakage.

---

### P1-F2: Replay Metadata Display (Dev Tools Tab)

**What:** The current replays section shows only a filename combobox. Add a metadata panel below it.

**UI Addition (Dev Tools, replays section):**

```text
  [ perf_run4.json â–¼ ]  [Launch]  [Delete]  [Refresh]
  Mode: playtest  |  Hub: central_hub  |  Frames: 4,241
  World seed: 2008173233  |  Date: 2026-03-29
```

**Behaviour:**

- On `<<ComboboxSelected>>`: read the replay JSON (`json.loads(path.read_text())`), extract `metadata` dict
- Populate a two-line `tk.Label` (using `self._replay_meta_var = tk.StringVar()`)
- "Delete": `messagebox.askyesno` confirmation â†’ `path.unlink()` â†’ refresh list
- If `metadata` key is absent (old format): show "No metadata"

**New methods:** `_read_replay_metadata(path: Path) -> dict`, `_on_replay_selected()`, `_delete_selected_replay_devtools()`

---

### P1-F3: Profiler Full Column Display + Baseline Comparison

**What:** The current profiler display shows 5 hard-coded columns. The actual CSV has 20+ timing sections. Display all of them in a scrollable text area. Add a baseline selector for comparison.

**UI Enhancement (Dev Tools, profiler section):**

```text
  [Run 10s Benchmark]  [Save as Baseline]  Baseline: [ perf_baseline_20260329.csv â–¼ ]  [Compare]

  Frames: 600  |  FPS avg=79.4  p5=68.1  min=42.0

  Section              avg     p95     max     vs baseline
  frame_total         12.6ms  15.2ms  44.7ms  +0.4ms
  update               3.4ms   5.1ms  28.2ms  -0.1ms
  render               7.2ms   9.8ms  16.0ms  +0.8ms (+12%)
  render_tiles         5.3ms   6.4ms  12.1ms  ...
  render_particles     0.0ms   0.1ms   0.2ms
  render_hud           1.1ms   2.1ms   3.2ms
  collision            0.4ms   0.8ms   4.3ms
  physics              0.1ms   0.2ms   0.9ms
  enemy_manager        0.0ms   0.1ms   0.4ms
  ...all other columns...
```

**Behaviour:**

- Replace the current `tk.Label` results display with a `tk.Text` widget (DISABLED after population, NORMAL to write)
- `_refresh_profiler_display()` iterates all keys from the parsed CSV except `frame_count`/`fps_*`
- Baseline dropdown: scan `docs/perf_baseline*.csv` files, populate `ttk.Combobox`
- "Compare": parse both CSVs, compute delta and percentage, add `vs baseline` column
- "Save as Baseline" already works; refresh baseline list after saving

**v0.9.4 note:** The server now runs physics at 60 Hz but only broadcasts at 20 Hz. The headless benchmark still measures the full 60 Hz client loop; the profiler CSV may gain a `broadcast_overhead` column once the game exposes it.

**New methods:** Rewrite `_refresh_profiler_display()`, add `_refresh_baseline_list()`, `_compare_to_baseline()`

---

### P1-F4: Log Viewer Filter and Search

**What:** The existing log viewer popup (`_view_log()` Toplevel) shows raw content. Add a log-level filter and a search bar.

**UI Addition (inside the log popup Toplevel):**

```text
  Filter: [ ALL â–¼ ]   Search: [____________________]  [Find Next]
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  ...log content with WARNING lines in yellow, ERROR lines in red...
```

**Behaviour:**

- `ttk.Combobox` with values `["ALL", "DEBUG", "INFO", "WARNING", "ERROR"]`; filters content by line prefix
- `tk.Text` with `tag_config("WARNING", foreground="#ffd700")`, `tag_config("ERROR", foreground="#e05252")`
- Search: `text.search(pattern, "1.0", nocase=True)` loop; highlight matches with `"found"` tag (blue background)
- "Find Next" cycles through matches

**New methods:** Rewrite `_view_log()` to accept a richer Toplevel builder; add `_apply_log_filter()`, `_find_in_log()`

---

### P1-F5: Download Manager Polish

**What:** The current update download shows only a progress bar and percentage. Add download speed, ETA, downloaded/total bytes, and a Cancel button.

**UI Enhancement (Play tab, during download):**

```text
  Downloading ninja_dash_v0.8.4.exe...
  [â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘]  62%   3.2 MB / 5.1 MB   1.1 MB/s   ETA: 2s
  [Cancel Download]
```

**Behaviour:**

- Wrap `urllib.request.urlretrieve` with a custom `reporthook(block_num, block_size, total_size)`
- Track `time.monotonic()` samples across blocks to compute rolling download speed (average over last 5 blocks)
- ETA = `(total_size - downloaded) / speed_bytes_per_sec`
- "Cancel Download": set a `threading.Event` flag; the reporthook raises `CancelledError` when it sees the flag set; clean up the partial file
- Bytes display: format as MB if > 1 MB, else KB

**New methods:** `_build_download_reporthook()`, `_cancel_download()`, `_format_bytes(n) -> str`

---

### P1-F6: Crash Detection and Auto-Report

**What:** When the launcher launches the game via `subprocess.Popen`, watch the process in a background thread. If it exits with a non-zero code, surface a "Game Crashed" dialog offering to auto-file a crash report.

**UI Flow:**

```text
  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
  â•‘  Game exited with code -1073740791       â•‘
  â•‘  (EXCEPTION_STACK_OVERFLOW)              â•‘
  â•‘                                          â•‘
  â•‘  Last 20 lines of log:                   â•‘
  â•‘  [ERROR] physics: stack overflow in...   â•‘
  â•‘                                          â•‘
  â•‘  [Open Crash Report]  [Copy to Clipboard]â•‘
  â•‘  [Ignore]                                â•‘
  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

**Behaviour:**

- Background watcher thread: `proc.wait()` â†’ check `proc.returncode`
- Non-zero exit: read last 30 lines of most recent log, format a GitHub issue URL (same pattern as Report tab) with crash context pre-filled: version, OS, exit code, log tail, world seed from most recent replay metadata
- "Open Crash Report" opens the pre-filled URL in browser
- "Copy to Clipboard": `root.clipboard_clear(); root.clipboard_append(crash_text)`
- Exit code mapping: common Windows NTSTATUS codes decoded to human-readable names (e.g., `0xC0000005` â†’ `ACCESS_VIOLATION`)
- On clean exit (code 0): restore launcher window silently

**New methods:** `_watch_game_process(proc)`, `_on_game_exited(returncode)`, `_build_crash_dialog(returncode, log_tail)`, `_decode_exit_code(code) -> str`

**Note:** This also enables the "stay alive after launch" pattern needed for P3-F4 multi-slot saves. The process watcher thread is the shared foundation.

**v0.9.3 note:** Since Phase 3b, player HP is server-authoritative. Crash reports in multiplayer sessions should also capture the last known `WorldSnapshot` health values from the most recent log line â€” these are now the ground-truth HP values, not the local client's.

---

## 4. Phase 2 â€” Core Features

**Scope:** Four new tabs â€” Saves, Mods, Settings, Replays
**Effort:** 1â€“2 weeks
**Window change:** Resize to 760Ã—640, `resizable(True, True)`

---

### P2-F1: Save Data Tab

**New tab:** "Saves" (inserted as index 2, shifting Report and Dev Tools right)

**UI Layout:**

```text
TAB: Saves
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  SAVE SLOT                                   [Backup Now]

  savegame.json (active)                     Status: â˜… Verified
  Version: 0.7.0  |  Saved: 2026-03-30 00:20

  CAMPAIGN           STATISTICS
  Hub: central_hub   Deaths: 0    Jumps: 0    Dashes: 0
  Currency: 0        Coins: 0     Perf Runs: 0
  Missions: 0/30     Abilities: 2  Bosses: 0
  Playtime: 0h 0m    Fastest time: --

  [Backup Now]   [Restore Backup]   [Delete Save]

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  BACKUPS                                     [Refresh]

  savegame_20260330_001902.json    2026-03-30 00:19   [Restore]
  savegame_20260330_001943.json    2026-03-30 00:19   [Restore]
  savegame_20260330_002014.json    2026-03-30 00:20   [Restore]
```

**Data Flow:**

1. `_read_save_file()` reads `user_data/saves/savegame.json`, strips `"signature"` and `"version"` outer keys, returns inner `"data"` dict
2. `_verify_save_signature(data_str, signature)` â€” inline HMAC check using `hmac.new(SAVE_KEY, data_bytes, "sha256").hexdigest()`. `SAVE_KEY = b"ninja_dash_v0_3_save_integrity_key_2025"` (duplicated from `systems/save_system.py` â€” see risks)
3. Display all fields read-only in two columns using `ttk.Frame` grid layout
4. **Backup Now**: `shutil.copy2(saves_dir/"savegame.json", backups_dir/f"savegame_{timestamp}.json")`
5. **Restore Backup**: `messagebox.askyesno` â†’ backup current â†’ atomic copy backup â†’ refresh display
6. **Delete Save**: `messagebox.askyesno` ("Also delete backups? [Yes/No/Cancel]") â†’ `path.unlink()`
7. Backup list: `ttk.Treeview` with columns (filename, date); `sorted(backups_dir.glob("*.json"), key=mtime, reverse=True)`

**New methods:** `_build_saves_tab(parent)`, `_refresh_saves_display()`, `_verify_save_signature(data_str, sig) -> bool`, `_backup_save_now()`, `_restore_backup(path)`, `_delete_save()`, `_refresh_backups_list()`

**Risk â€” HMAC key duplication:** The integrity key is defined in `systems/save_system.py`. The launcher must duplicate it or display "unverifiable" without it. Preferred fix: extract the key to a shared location (e.g., `config/integrity_key.txt` or `version.json`) that both the game and launcher read. Until then, duplicate the constant with a comment pointing to the source. If the keys diverge, the launcher will show "TAMPERED" on valid saves â€” a cosmetic issue, not a data risk.

---

### P2-F2: Mod Manager Tab

**New tab:** "Mods"

**UI Layout:**

```text
TAB: Mods
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  INSTALLED MODS                              [Open Mods Folder]  [Refresh]

  â”Œâ”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ EN â”‚ Name              â”‚ Version â”‚ Author   â”‚ Status         â”‚
  â”œâ”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
  â”‚ â˜‘  â”‚ Example Mod       â”‚ 1.0.0   â”‚ Dev      â”‚ OK             â”‚
  â”‚ â˜  â”‚ Another Mod       â”‚ 0.2.1   â”‚ Someone  â”‚ Missing: xyz   â”‚
  â””â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

  Selected mod: Example Mod
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚  ID: example_mod                                           â”‚
  â”‚  Description: Demonstrates the mod API                    â”‚
  â”‚  Entry: main.py  |  Dependencies: none                     â”‚
  â”‚  Path: user_data/mods/example_mod/                         â”‚
  â”‚                                                            â”‚
  â”‚  [Reveal in Explorer]        [Delete Mod]                  â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  INSTALL MOD
  From ZIP:  [Browse...]                    [Install from ZIP]
  From URL:  [________________________________]  [Download & Install]
```

**Data Flow:**

1. `_read_mod_manifests()` â€” `list(mods_dir.glob("*/mod.json"))`, parse each, return list of dicts
2. `_read_enabled_mods()` â€” load `user_data/mods/enabled_mods.json`, return `set[str]` of enabled mod IDs. Create file with all discovered mods enabled if absent
3. `ttk.Treeview` columns: `("en", "name", "version", "author", "status")` â€” `en` column shows `"â˜‘"` or `"â˜"`
4. **Toggle enable/disable:** Bind `<ButtonRelease-1>` on treeview; if click x-coord is within column 0 bounds, call `_toggle_mod_enabled(mod_id)` â†’ update `enabled_mods.json` â†’ refresh list
5. **Dependency check (display-only):** For each mod, check if its `dependencies` list items are present in the discovered mod IDs. Show "Missing: X" in Status column if not
6. **Install from ZIP:** `filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])` â†’ `_install_mod_zip(path)` â†’ extract to `mods/<mod_id>/` (reads `mod.json` from ZIP to determine `mod_id`) â†’ verify `mod.json` exists â†’ refresh list
7. **Install from URL:** Validate URL is a `.zip` link â†’ `urllib.request.urlretrieve` in thread â†’ same extraction
8. **Delete:** `messagebox.askyesno` â†’ `shutil.rmtree(mod_dir)` â†’ update `enabled_mods.json` â†’ refresh list
9. **Reveal:** `os.startfile(mod_dir)` (Windows)

**New methods:** `_build_mods_tab(parent)`, `_read_mod_manifests() -> list[dict]`, `_read_enabled_mods() -> set[str]`, `_write_enabled_mods(enabled: set[str])`, `_refresh_mods_list()`, `_on_mod_tree_click(event)`, `_toggle_mod_enabled(mod_id: str)`, `_on_mod_selected(event)`, `_install_mod_zip(zip_path: Path)`, `_install_mod_url(url: str)`, `_delete_mod(mod_id: str)`, `_reveal_mod_folder(mod_id: str)`

**Game-side change required:** `core/mod_system.py`'s `ModLoader.load_all_mods()` must be updated to read `user_data/mods/enabled_mods.json` and skip mods not in the enabled set. Until then, the toggle shows "(pending game restart to apply)".

**Security warning:** Installing a mod executes untrusted Python code. Display a prominent warning dialog before any ZIP install: "Mods execute code on your machine. Only install mods from sources you trust." Future: mod signature verification.

---

### P2-F3: Settings Editor Tab

**New tab:** "Settings" (scrollable content)

**UI Layout:**

```text
TAB: Settings
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  AUDIO
    Master Volume   [==========|--]  1.0
    Music  Volume   [=======|-----]  0.7
    SFX    Volume   [=============]  0.8

  DISPLAY
    Fullscreen [ ]     VSync [âœ“]     Show FPS [ ]
    Resolution [1280x720 â–¼]          (requires restart)

  GAMEPLAY
    Screen Shake [âœ“]    Particles [âœ“]
    Camera Smoothing  [======|------]  0.1

  CONTROLS (key bindings â€” read-only; use P3-F2 to enable rebinding)
    Left: left    Right: right    Jump: space
    Dash: shift   Crouch: down

  DEVELOPER
    Show Hitboxes [ ]    Log Level [INFO â–¼]

  [Save Settings]    [Reset to Defaults]    [Open Settings File]
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
```

**Data Flow:**

1. `_read_settings()` loads `user_data/settings/settings.json` merged with `DEFAULT_SETTINGS` from `config/settings.py` (copy the dict literal into launcher constants)
2. Each setting bound to a `tk.Variable` subclass: `tk.DoubleVar` (float), `tk.BooleanVar` (bool), `tk.StringVar` (string/enum)
3. Volume sliders: `ttk.Scale(from_=0.0, to=1.0, orient="horizontal")` with live label showing current value
4. Resolution options: `["1280x720", "1920x1080", "2560x1440", "800x600"]`; split on `"x"` when writing
5. **Save Settings:** `_write_settings_safe(data)` â€” atomic temp+rename write to `settings.json`. The game's `HotReloadWatcher` in `dev_tools/hot_reload.py` detects the change and reloads if the game is running
6. **Reset to Defaults:** `messagebox.askyesno` â†’ write DEFAULT_SETTINGS â†’ reload UI
7. **Open Settings File:** `os.startfile(settings_path)` (Windows)
8. Scroll container: `tk.Canvas` + `tk.Scrollbar` with an inner `tk.Frame` â€” the standard tkinter scrollable frame pattern

**Settings that require game restart:** Fullscreen, resolution. Label these `"(requires restart)"`.

**New methods:** `_build_settings_tab(parent)`, `_build_scrollable_frame(parent) -> tk.Frame`, `_load_settings_into_ui()`, `_save_settings_from_ui()`, `_reset_settings_to_defaults()`

---

### P2-F4: Replays Tab

**New tab:** "Replays" (split out of Dev Tools â€” Dev Tools retains Profiler and Logs)

**UI Layout:**

```text
TAB: Replays
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  REPLAY LIBRARY                                       [Refresh]

  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ Name             â”‚ Mode      â”‚ Hub          â”‚ Frames â”‚ Date  â”‚
  â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”¤
  â”‚ perf_run4        â”‚ playtest  â”‚ central_hub  â”‚ 4,241  â”‚ 03-29 â”‚
  â”‚ session_01       â”‚ campaign  â”‚ forest_hub   â”‚ 18,420 â”‚ 03-28 â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”˜

  Selected: perf_run4.json
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚  Mode: playtest  |  World seed: 2008173233                   â”‚
  â”‚  Hub: central_hub  |  Mission: None                          â”‚
  â”‚  Total frames: 4241  |  Game-start frame: 424                â”‚
  â”‚  File: user_data/replays/perf_run4.json                      â”‚
  â”‚                                                              â”‚
  â”‚  [â–¶ Launch Replay]   [Delete]   [Rename]   [Reveal]          â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  RECORD NEW REPLAY
  Name: [____________________]   [Record on Next Launch]
  (Launches with --record <name>; replay is saved when session ends)
```

**Data Flow:**

1. `ttk.Treeview` with columns `("name", "mode", "hub", "frames", "date")`; populated by scanning `user_data/replays/`
2. Metadata loaded from each replay JSON's `"metadata"` key; `frames` = `len(commands)` if no `terminated_frame`
3. **Launch Replay:** `self._launch_with_args("--replay", stem, "--show-replay")`
4. **Delete:** `messagebox.askyesno` â†’ `path.unlink()` â†’ refresh
5. **Rename:** `tk.simpledialog.askstring` â†’ validate new name not empty/not taken â†’ `path.rename(new_path)` â†’ refresh
6. **Reveal:** `os.startfile(replays_dir)`
7. **Record on Next Launch:** Sets `self._pending_record = name_entry.get().strip()`. `_launch_with_args()` appends `["--record", self._pending_record]` then clears `self._pending_record` after launch

**New methods:** `_build_replays_tab(parent)`, `_refresh_replays_tree()`, `_read_replay_metadata(path: Path) -> dict`, `_on_replay_tree_select(event)`, `_launch_selected_replay()`, `_delete_selected_replay()`, `_rename_selected_replay()`, `_record_on_next_launch()`

---

## 5. Phase 3 â€” Advanced Features

**Effort:** 2â€“4 weeks (individual features are independent; pick any order)

---

### P3-F1: Statistics and Achievement Viewer

**Location:** Sub-panel within the Saves tab, below the save slot detail.

**UI Addition:**

```text
  LIFETIME STATISTICS
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ Deaths   â”‚  Jumps   â”‚  Dashes  â”‚ Playtime â”‚
  â”‚    42    â”‚  1,337   â”‚   892    â”‚  4h 12m  â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚  Coins   â”‚ Missions â”‚  Bosses  â”‚ Perf Runsâ”‚
  â”‚   420    â”‚  7 / 30  â”‚    2     â”‚    1     â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

Purely reads `statistics` and `campaign` sections from the save JSON. No game-side changes.

---

### P3-F2: Keyboard Shortcut Configurator

**Location:** Settings tab, extends the read-only "CONTROLS" section to an interactive rebinder.

**UI Enhancement:**

```text
  CONTROLS
  Action        Bound Key            [Reset Controls]
  Move Left     [ left        ] â† click to rebind, then press any key
  Move Right    [ right       ]
  Jump          [ space       ]
  Dash          [ lshift      ]
  Crouch        [ down        ]
```

**Behaviour:**

- Clicking a binding entry puts it into listening mode (border color changes, text shows "Press any key...")
- A `<KeyPress>` binding on the root window captures the next event, converts `event.keysym` to the settings key name string
- Writes back via `_write_settings_safe()`
- "Reset Controls" restores default key mapping after confirmation

**Risk:** A badly bound key (e.g., binding `jump` to `escape`) can make the game awkward. Warn if a key is already used, and always show "Reset Controls" prominently.

---

### P3-F3: News Feed and Changelog Panel

**Location:** Play tab, below the version row.

**UI Addition:**

```text
  LATEST â€” v0.8.4  (2026-03-31)
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚  What's new:                                         â”‚
  â”‚  â€¢ Fixed hub transition crash                        â”‚
  â”‚  â€¢ Improved enemy AI in forest zone                  â”‚
  â”‚  â€¢ New mission: The Bamboo Gauntlet                  â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Behaviour:**

- Data is already available: `_fetch_releases()` returns `releases[0]["body"]` (GitHub Markdown)
- In `_on_fetch_done()`, strip basic Markdown (`**`, `##`, leading `-` bullets) and populate a `tk.Text(state=DISABLED)` widget
- No additional network calls; reuses the existing releases fetch

---

### P3-F4: Multi-Slot Save Management

**Location:** Saves tab (extends P2-F1) + profile system (extends P1-F1)

**Concept:** Each profile owns its own save directory at `user_data/profiles/<name>/saves/`. The launcher swaps the active profile's save to the canonical `user_data/saves/savegame.json` before launch and copies it back after the game exits.

**Launch Wrapper:**

```text
_pre_launch_save_swap()
    â†’ backup current savegame.json
    â†’ copy profiles/<active>/saves/savegame.json â†’ saves/savegame.json

subprocess.Popen([game_exe, ...])  # non-blocking
_watch_game_process(proc)  # background thread
    â†’ proc.wait()
    â†’ _post_launch_save_restore()
        â†’ copy saves/savegame.json â†’ profiles/<active>/saves/savegame.json
        â†’ restore launcher window
```

**Risk:** If the game crashes during a save write, `savegame.json` may be partial. The pre-swap backup is the recovery path. The `_post_launch_save_restore()` must run even on non-zero exit. **Implement this last** when the profile system is stable.

**Note on launcher staying alive:** Currently the launcher calls `self.root.after(200, self.root.destroy)` after launch. For post-launch file watching, change this to `self.root.iconify()` (minimize) and show a "Game Running..." status. Restore and do post-launch work when the watcher thread completes.

---

### P3-F5: Server Ping Monitor

**Location:** Play tab, multiplayer section, next to the Join button.

**UI Addition:**

```text
  [Join Game]  [ Ping ]  â†’  42ms  (or "Unreachable")
  Active zones: 2  (reported by server on connect handshake â€” future)
```

**Implementation:**

```python
import socket, time

def _ping_server(host: str, port: int, timeout: float = 2.0) -> float | None:
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.monotonic() - t0) * 1000  # ms
    except OSError:
        return None
```

Run in a thread; display result in a `tk.Label` next to the Join button. Green if < 100ms, yellow if < 250ms, red if higher or unreachable.

**v0.9.0 note:** The server now manages multiple instanced zones (`_ZoneInstance` registry). A future server diagnostic endpoint could return active zone count and player distribution; the ping monitor is the natural place to surface this once the server exposes it.

---

### P3-F6: Profiler Chart View

**Location:** Dev Tools tab (Profiler section), toggle between table and chart views.

**UI Addition:**

```text
  [Table View]  [Chart View]    â† toggle buttons

  render      â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ  7.2ms avg
  update      â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ         3.4ms avg
  frame_total â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ  12.6ms avg
  collision   â–ˆâ–ˆâ–ˆâ–ˆ                 0.4ms avg
  physics     â–ˆ                    0.1ms avg
```

**Implementation:** Pure `tk.Canvas` drawing with `canvas.create_rectangle()` and `canvas.create_text()`. Bar width = `(avg_ms / max_avg_ms) * canvas_width`. Color: green < 8ms, yellow < 16ms, red >= 16ms. No matplotlib needed.

---

## 6. Phase 4 â€” Professional Polish

**Scope:** Industry-standard launcher features found in Steam, GOG Galaxy, and Battle.net. All stdlib-only.
**Effort:** 4â€“8 weeks (features are independent; prioritise based on player demand)

---

### P4-F1: Game File Integrity Verifier

**What:** Verifies the installed `ninja_dash.exe` has not been corrupted or tampered with, by comparing its SHA256 against the hash published with the GitHub release. Equivalent to Steam's "Verify integrity of game files".

**UI (Play tab addition):**

```text
  [Verify Game Files]
  â†’ Checking ninja_dash.exe...        âœ“ File OK  (SHA256 matches v0.8.4)
  â†’ Checking ninja_dash_launcher.exe... âœ— MISMATCH â€” [Reinstall]
```

**Behaviour:**

- Fetch the release asset list from GitHub API (already cached from `_fetch_releases()`)
- Extract the SHA256 field from the release body (convention: add a `## Checksums` section to release notes with `SHA256: <hex>  ninja_dash.exe`)
- `hashlib.sha256(path.read_bytes()).hexdigest()` for each local exe
- Display per-file pass/fail; offer "Reinstall" (triggers the existing download flow) on mismatch
- Run in background thread; show a progress spinner label

**New methods:** `_verify_game_files()`, `_extract_release_checksums(release_body: str) -> dict[str, str]`, `_hash_file(path: Path) -> str`

---

### P4-F2: Quick Launch Presets

**What:** Save named launch configurations â€” a combination of game mode, multiplayer settings, mods enabled, and custom CLI args â€” as one-click presets. Useful for developers and streamers with fixed setups.

**UI (Play tab sub-panel):**

```text
  LAUNCH PRESETS                    [+ New Preset]  [Edit]  [Delete]
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ â–¶ Solo Campaign (default)    â€” solo, no mods                  â”‚
  â”‚ â–¶ 4P Host - LAN              â€” host:7777, 4 players           â”‚
  â”‚ â–¶ Dev: Headless Bench        â€” --headless --profile dev       â”‚
  â”‚ â–¶ Streamer Mode              â€” solo, mod: hud_overlay enabled  â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Preset Format** (stored in `user_data/presets.json`):

```json
{
  "presets": [
    {
      "name": "4P Host - LAN",
      "mode": "host",
      "port": 7777,
      "max_players": 4,
      "profile": "Player1",
      "extra_args": [],
      "enabled_mods": ["hud_overlay"]
    }
  ]
}
```

**Behaviour:**

- Each preset row has a single "â–¶ Launch" button
- "New Preset" opens a `tk.Toplevel` form with fields for each setting
- Preset mods override the global enabled mods for that launch (passed via `--mod-override <id,...>` arg, or applied by the file-swap approach)
- Presets are profile-independent by default; optionally bind to a specific profile

**New methods:** `_build_presets_panel(parent)`, `_read_presets() -> list[dict]`, `_write_presets(data)`, `_launch_preset(preset: dict)`, `_open_preset_editor(preset: dict | None)`

---

### P4-F3: System Requirements Checker

**What:** On first launch (or via a "Check System" button), verify the host machine meets the game's minimum requirements. Surfaces actionable errors rather than cryptic crashes.

**UI (Play tab, shown once on first launch then dismissible):**

```text
  SYSTEM CHECK
  âœ“ Python 3.11.x detected
  âœ“ pygame 2.6.1 installed
  âœ“ Disk space: 142 MB free of 10 MB required
  âœ— RAM: 1.8 GB free â€” game recommends 2 GB
  âœ“ Display: 1920x1080 @ 60Hz (minimum 1280x720)
  âœ“ Windows 10/11 detected

  [Dismiss]   [Don't show again]
```

**Checks (all stdlib):**

- Python version: `sys.version_info >= (3, 11)`
- Disk space: `shutil.disk_usage(game_dir).free`
- RAM: `ctypes.windll.kernel32.GlobalMemoryStatusEx` (Windows-specific struct)
- Display resolution: `tk.Winfo_screenwidth()` / `tk.Winfo_screenheight()`
- OS version: `platform.version()`
- pygame installation: `importlib.util.find_spec("pygame")` (checks without importing)

**Storage:** `user_data/launcher_state.json` with `"syscheck_dismissed": true` to suppress on subsequent launches.

**New methods:** `_run_system_check() -> list[tuple[bool, str]]`, `_show_syscheck_dialog(results)`, `_build_check_row(parent, ok, msg)`

---

### P4-F4: Playtime Tracker

**What:** Track wall-clock playtime per profile and per session. Displayed on the Play tab and the Saves tab. Independent of the in-game save system's playtime counter (which only counts in-game frames, not menu/loading time).

**UI (Play tab profile row extension):**

```text
  Profile: [ Player1 â–¼ ]   [ + New ]   Total: 14h 32m  |  Last session: 47m
```

**Storage** (appended to `profiles.json`):

```json
{
  "profiles": {
    "Player1": {
      "playtime_seconds": 52320,
      "sessions": [
        { "start": "2026-03-30T20:14:00", "duration_seconds": 2820 }
      ]
    }
  }
}
```

**Behaviour:**

- Record `session_start = time.time()` before `subprocess.Popen`
- In the process watcher thread: on game exit, compute `duration = time.time() - session_start`
- Append session record to `profiles[active]["sessions"]`; update `playtime_seconds` total
- Keep last 30 session records; summarise older ones into the total
- Display "Last session: Xm" and "Total: Xh Ym" in profile row

**New methods:** `_on_session_start()`, `_on_session_end(duration_seconds: float)`, `_format_playtime(seconds: int) -> str`

---

### P4-F5: Update Channel Selector

**What:** Let users opt into beta or development builds by selecting a release channel. Maps to GitHub's `prerelease` flag on releases.

**UI (Play tab, version row addition):**

```text
  Channel: [ Stable â–¼ ]    â† options: Stable, Beta, Dev
  Version:  v0.9.5  [latest]   Protocol: v2 (msgpack)
```

**Behaviour:**

- "Stable": only non-prerelease GitHub releases (`"prerelease": false`)
- "Beta": include prereleases (`"prerelease": true`)
- "Dev": also show draft releases (requires a PAT â€” show warning if not configured)
- Channel stored in `user_data/launcher_state.json` as `"update_channel": "stable"`
- `_fetch_releases()` filters the release list based on selected channel before version comparison
- Warn when switching from Stable to Beta: "Beta builds may contain bugs and incomplete features."

**v0.8.8 note â€” protocol version parity is now critical.** Since v0.8.8 the game uses msgpack binary frames (`PROTOCOL_VERSION = "2"`). A client running v0.8.7 or earlier connecting to a v0.8.8+ server will immediately disconnect with a decode error â€” there is no graceful fallback. The launcher should display the installed protocol version alongside the game version and warn the user if the host address they are joining is known to be running a different protocol version. The update channel selector is the natural enforcement point: switching channels should warn "Multiplayer requires all players to run the same version."

**New methods:** `_build_channel_selector(parent)`, `_on_channel_changed()`, `_filter_releases_by_channel(releases, channel) -> list`

---

### P4-F6: Screenshot Gallery

**What:** Browse screenshots captured during gameplay. The game would need to write PNG files to `user_data/screenshots/` on a screenshot key press. The launcher displays them as thumbnails.

**UI (new "Media" panel within Replays tab):**

```text
  SCREENSHOTS                              [Open Folder]  [Refresh]
  â”Œâ”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”
  â”‚      â”‚ â”‚      â”‚ â”‚      â”‚ â”‚      â”‚
  â”‚ img  â”‚ â”‚ img  â”‚ â”‚ img  â”‚ â”‚ img  â”‚
  â”‚      â”‚ â”‚      â”‚ â”‚      â”‚ â”‚      â”‚
  â””â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”˜
  2026-03-30  2026-03-30  2026-03-29  ...

  Click to open full-size in default viewer
```

**Implementation:**

- `tk.PhotoImage` can load PNG natively (tkinter 8.6+) â€” no Pillow needed for thumbnails
- Scale thumbnails to ~120Ã—68px using `PhotoImage.subsample(n)` (integer downscale only; accept nearest power-of-2 subsample)
- Layout: `tk.Canvas` with dynamically placed image items in a wrapping grid pattern (recalculate on window resize via `<Configure>` event)
- Click thumbnail: `os.startfile(path)` opens in Windows Photos
- "Open Folder": `os.startfile(screenshots_dir)`

**Game-side change required:** Add `F12` screenshot capture to `demo_game.py` writing `user_data/screenshots/screenshot_<timestamp>.png` via `pygame.image.save()`.

**New methods:** `_build_screenshots_panel(parent)`, `_refresh_screenshots_grid()`, `_load_thumbnail(path: Path) -> tk.PhotoImage`, `_on_thumbnail_click(path: Path)`

---

### P4-F7: System Info Collector for Bug Reports

**What:** Enhance the Report tab with an "Attach System Info" checkbox that auto-collects hardware/software context and embeds it in the GitHub issue URL.

**UI Enhancement (Report tab):**

```text
  [âœ“] Attach system info:
      OS: Windows 11 Home 10.0.26200
      CPU: AMD Ryzen 7 5800X   RAM: 16 GB
      GPU: NVIDIA RTX 3070 (via registry)
      Python: 3.11.8   pygame: 2.6.1
      Game version: v0.8.4   Launcher: v2.1
      Display: 1920x1080 @ 144Hz
```

**Collection (stdlib):**

- OS: `platform.platform()`
- CPU: `platform.processor()`
- RAM: `ctypes.windll.kernel32.GlobalMemoryStatusEx`
- GPU: `winreg` read from `HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968...}` (display adapter key)
- Python/pygame versions: `sys.version`, `importlib.metadata.version("pygame")`
- Display: `root.winfo_screenwidth()` / `root.winfo_screenheight()`

Embed as a collapsible `<details>` HTML block in the GitHub issue body (GitHub issues render HTML in body text).

**New methods:** `_collect_system_info() -> dict`, `_format_system_info_for_issue(info: dict) -> str`, `_get_gpu_name() -> str`

---

### P4-F8: Accessibility Options

**What:** Make the launcher itself more accessible â€” font size scaling, high-contrast mode, and reduced-motion mode for animated elements.

**UI (Settings tab, new LAUNCHER section):**

```text
  LAUNCHER APPEARANCE
    Theme:      [ Dark â–¼ ]  (Dark / High Contrast / Light)
    Font Size:  [ Normal â–¼ ]  (Small / Normal / Large / Extra Large)
    Animations: [âœ“]  (uncheck to disable splash animation, progress pulse)
```

**Behaviour:**

- Theme: redefine the `COLORS` dict (currently hardcoded) as a theme dict; `"high_contrast"` uses white on black with yellow accents; `"light"` inverts the palette
- `ttk.Style.configure()` propagated to all widgets on theme change via `_apply_theme()`
- Font size: scale all `FONTS` dict entries by a multiplier (`small=0.85`, `normal=1.0`, `large=1.2`, `xl=1.5`)
- Animations: `self._animations_enabled` flag; skip `after()` animation loops in splash canvas when False
- Persisted in `user_data/launcher_state.json` as `"theme": "dark"`, `"font_scale": 1.0`, `"animations": true`

**New methods:** `_build_launcher_appearance_section(parent)`, `_apply_theme(theme_name: str)`, `_apply_font_scale(scale: float)`

---

### P4-F9: Community Hub Panel

**What:** A dedicated panel with quick links to the game's community spaces, social accounts, and external resources. Doubles as a lightweight "About" screen.

**UI (new "Community" tab or Play tab sidebar):**

```text
  COMMUNITY
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚  Indie Ninja Adventures                 â”‚
  â”‚  by Vain Asher Gaming                   â”‚
  â”‚                                         â”‚
  â”‚  [Discord]  [GitHub]  [itch.io]         â”‚
  â”‚  [Bug Reports]  [Feature Requests]      â”‚
  â”‚                                         â”‚
  â”‚  Latest community post:                 â”‚
  â”‚  "v0.8.4 balance patch notes"  03-31    â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Behaviour:**

- All links open via `webbrowser.open(url)` (stdlib)
- "Latest community post": fetch the most recent open issue title from `VainAsher/indie-ninja-feedback` via GitHub API (`/repos/owner/repo/issues?state=open&per_page=1`) â€” same auth-free approach as the existing releases fetch
- Cache result in `user_data/launcher_state.json` with a 1-hour TTL to avoid hammering the API
- Links are configurable via a `COMMUNITY_LINKS` dict constant in the launcher for easy maintenance

**New methods:** `_build_community_tab(parent)`, `_fetch_latest_feedback() -> dict | None`, `_build_link_button(parent, label, url)`

---

### P4-F10: Custom Launch Arguments Editor

**What:** Power-user feature. A collapsible "Advanced" panel on the Play tab that exposes raw CLI argument editing for the game executable. Useful for testers and modders.

**UI (Play tab, collapsed by default):**

```text
  â–¶ Advanced Launch Options
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Extra args: [--debug-zones --skip-intro --max-enemies 10  ]
  [âœ“] Record replay as:  [session_20260331                  ]
  [ ] Force world seed:  [_________________________         ]
  [ ] Skip hub intro cutscene
  [ ] Enable debug overlay
  [Reset to defaults]
```

**Behaviour:**

- `ttk.Frame` with a toggle button that shows/hides the panel (`frame.pack_forget()` / `frame.pack()`)
- Free-text args entry appended verbatim to the launch command â€” with a warning: "Invalid args may crash the game"
- Checkboxes for the most common power-user flags: `--skip-intro`, `--debug-overlay`, `--force-seed <n>`
- Force world seed: pass `--seed <n>` to the game (requires game-side support of `--seed` arg; document as future)
- Persisted as `user_data/launcher_state.json` key `"last_extra_args"` so they survive launcher restarts

**New methods:** `_build_advanced_panel(parent)`, `_toggle_advanced_panel()`, `_collect_advanced_args() -> list[str]`

---

### P4-F11: Export and Import Save Archives

**What:** Export a complete save snapshot (save file + backups + settings) as a ZIP archive for external backup or sharing between machines. Import reverses the process.

**UI (Saves tab addition):**

```text
  IMPORT / EXPORT
  [Export Save Archive...]   â†’ Creates saves_Player1_20260331.zip
  [Import Save Archive...]   â†’ Validates and restores from ZIP
```

**Export ZIP contents:**

```text
saves_Player1_20260331.zip
  savegame.json
  backups/
    savegame_20260330_001902.json
    ...
  settings/settings.json
  profiles/profiles.json
  export_manifest.json        â† version, profile, export_date, file hashes
```

**Behaviour:**

- `zipfile.ZipFile` (stdlib) for both create and extract
- Export: `filedialog.asksaveasfilename(defaultextension=".zip")` â†’ write all files â†’ write `export_manifest.json` with SHA256 of each included file
- Import: `filedialog.askopenfilename` â†’ read `export_manifest.json` â†’ verify hashes â†’ confirm "This will replace your current save" â†’ backup current â†’ extract
- Version compatibility check: warn if `export_manifest["game_version"]` differs from current

**New methods:** `_export_save_archive()`, `_import_save_archive()`, `_write_export_manifest(zf, files: list[Path])`, `_verify_import_manifest(zf) -> bool`

---

## 7. Risks and Mitigations

| Risk | Severity | Mitigation |
| --- | --- | --- |
| **Protocol version mismatch causes silent disconnect** (v0.8.8+) | **High** | Launcher must display installed protocol version; warn before joining if mismatched. `PROTOCOL_VERSION = "2"` (msgpack) is incompatible with any v0.8.7 or earlier build â€” no graceful fallback. |
| HMAC key duplicated in launcher | Medium | Extract key to a shared constants file (e.g., `config/integrity.py`); both game and launcher import from it. Until then, duplicate with a comment. |
| `version.json` is stale (currently reads 0.8.4, code is 0.9.5) | Medium | Update `version.json` to `"0.9.5"` before the next release build; add a CI check that `version.json` matches the latest git tag. |
| Save file corruption during restore | High | Atomic write (`.tmp` + `rename`); pre-operation timestamped backup; confirm before restore |
| Multi-slot save swap loses data on game crash | High | Pre-swap backup; `_post_launch_save_restore` runs on any exit code; keep backups for 7 days |
| Mod ZIP install executes untrusted code | High | Prominent unsigned-mod warning dialog before every install; future: signature verification |
| `enabled_mods.json` not respected by game | Medium | Show "pending restart" badge; document the contract in `core/mod_system.py` |
| Launcher window grows too large | Medium | Extract to `launcher/tabs/` when any tab build method exceeds ~400 lines |
| tkinter Treeview has no native checkbox | Low | Unicode â˜‘/â˜ text in column 0, toggled on click â€” functionally equivalent |
| Settings write races with game's hot-reload | Low | Atomic temp+rename; watcher only fires after rename completes |
| Key rebinder captures modifier keys | Low | Filter out pure modifier keysyms (Shift_L, Control_L, etc.) in capture handler |
| `filedialog.askopenfilename` unavailable headless | Low | Only called from button click; never in headless/benchmark mode |
| Screenshot thumbnails exhaust memory | Low | Keep a `dict[path, PhotoImage]` cache; evict LRU entries when cache > 50 items |
| GPU registry key missing on some systems | Low | Wrap `winreg` read in try/except; fall back to "GPU: Unknown" |

---

## 8. Implementation Order (Recommended)

Ordered by value/risk ratio â€” highest value, lowest risk first:

| # | Feature | Phase | Why This Order |
| --- | --- | --- | --- |
| 1 | P1-F3 Profiler full columns | 1 | Pure display fix, zero risk, immediate usefulness |
| 2 | P1-F2 Replay metadata display | 1 | Low code, high UX improvement |
| 3 | P1-F4 Log viewer filter/search | 1 | Self-contained Toplevel enhancement |
| 4 | P1-F5 Download manager polish | 1 | Improves existing download UX; no new data |
| 5 | P1-F1 Profile switcher | 1 | Foundation for multi-profile; game ignores `--profile` safely |
| 6 | P1-F6 Crash detection | 1 | Enables process watcher; foundation for P3-F4 and P4-F4 |
| 7 | P4-F3 System requirements checker | 4 | First-launch feature; self-contained; high player value |
| 8 | P2-F3 Settings Editor tab | 2 | No game-side changes needed; hot-reload already works |
| 9 | P2-F4 Replays tab | 2 | Splits cramped Dev Tools; no mutation risk |
| 10 | P2-F1 Save Data tab | 2 | Core requested feature; careful backup protocol |
| 11 | P4-F11 Export/Import save archives | 4 | Extends Save tab naturally; pure zipfile, no new patterns |
| 12 | P2-F2 Mod Manager tab | 2 | Most complex; needs `enabled_mods.json` game-side contract |
| 13 | P4-F9 Community hub panel | 4 | Low complexity; no mutations |
| 14 | P3-F3 News feed | 3 | Trivial; data already fetched |
| 15 | P3-F5 Server ping | 3 | One function, minimal UI |
| 16 | P4-F5 Update channel selector | 4 | Extends releases fetch already in place |
| 17 | P4-F2 Quick launch presets | 4 | High developer value; medium complexity |
| 18 | P4-F10 Custom launch arguments | 4 | Low risk, power-user feature |
| 19 | P3-F6 Profiler chart | 3 | Visual polish |
| 20 | P4-F1 File integrity verifier | 4 | Needs checksum convention in release notes |
| 21 | P3-F1 Stats/achievement viewer | 3 | Extends Saves tab |
| 22 | P4-F7 System info for bug reports | 4 | Extends Report tab |
| 23 | P4-F8 Accessibility options | 4 | Theme/font refactor touches all widgets |
| 24 | P4-F4 Playtime tracker | 4 | Depends on process watcher (P1-F6) being stable |
| 25 | P4-F6 Screenshot gallery | 4 | Needs game-side F12 capture first |
| 26 | P3-F2 Key rebinder | 3 | Requires careful UX + testing |
| 27 | P3-F4 Multi-slot saves | 3 | Highest risk; implement last |

---

## 9. Complexity and Effort Summary

| Feature | Phase | Complexity | Lines Est. | Game-side change? |
| --- | --- | --- | --- | --- |
| Profiler full columns | 1 | Low | ~40 | No |
| Replay metadata display | 1 | Low | ~60 | No |
| Log viewer filter/search | 1 | Medium | ~80 | No |
| Download manager polish | 1 | Low | ~70 | No |
| Profile switcher (Play tab) | 1 | Low | ~100 | Optional `--profile` arg |
| Crash detection + auto-report | 1 | Medium | ~120 | No |
| Settings Editor tab | 2 | Medium | ~250 | No (hot-reload exists) |
| Replays tab | 2 | Medium | ~200 | No |
| Save Data tab | 2 | Medium | ~300 | No |
| Mod Manager tab | 2 | High | ~450 | `enabled_mods.json` contract |
| News feed panel | 3 | Low | ~50 | No |
| Server ping | 3 | Low | ~30 | No |
| Profiler chart view | 3 | Medium | ~150 | No |
| Stats/achievement viewer | 3 | Low | ~100 | No |
| Key rebinder | 3 | Medium | ~120 | No |
| Multi-slot save management | 3 | High | ~200 | No (file-swap approach) |
| Game file integrity verifier | 4 | Medium | ~100 | Checksum convention in release notes |
| Quick launch presets | 4 | Medium | ~200 | No |
| System requirements checker | 4 | Low | ~120 | No |
| Playtime tracker | 4 | Low | ~80 | No |
| Update channel selector | 4 | Low | ~60 | No |
| Screenshot gallery | 4 | Medium | ~150 | `pygame.image.save()` on F12 |
| System info for bug reports | 4 | Low | ~80 | No |
| Accessibility options | 4 | High | ~200 | No |
| Community hub panel | 4 | Low | ~80 | No |
| Custom launch arguments | 4 | Low | ~90 | Optional `--seed`, `--skip-intro` args |
| Export/Import save archives | 4 | Medium | ~150 | No |

---

## 10. New Files Required

| File | Created By | Purpose |
| --- | --- | --- |
| `user_data/profiles/profiles.json` | Launcher on first start | Per-profile metadata and playtime |
| `user_data/mods/enabled_mods.json` | Launcher Mod Manager | Mod enable/disable state |
| `user_data/presets.json` | Launcher Quick Launch | Named launch configurations |
| `user_data/launcher_state.json` | Launcher on first start | Channel, syscheck dismissed flag, theme, last args, API cache |

No pip dependencies are introduced at any phase. All features use stdlib modules already available in Python 3.11: `json`, `hashlib`, `hmac`, `shutil`, `zipfile`, `socket`, `threading`, `ctypes`, `winreg`, `platform`, `webbrowser`, `importlib.util`, `importlib.metadata`, `urllib.request`, `tkinter`, `tkinter.ttk`, `tkinter.messagebox`, `tkinter.simpledialog`, `tkinter.filedialog`.

---

## 11. Critical Files

| File | Role |
| --- | --- |
| `launcher/launcher.py` | Primary implementation target |
| `version.json` | Version source of truth â€” **currently stale at 0.8.4; update to 0.9.5** |
| `systems/save_system.py` | HMAC key constant, save data schema |
| `core/mod_system.py` | ModLoader â€” needs `enabled_mods.json` support (P2-F2) |
| `config/settings.py` | DEFAULT_SETTINGS dict â€” copy into launcher constants |
| `network/input_pipeline.py` | Replay JSON format and metadata schema |
| `network/protocol.py` | `PROTOCOL_VERSION`, `CLIENT_VERSION`, `SERVER_VERSION` â€” surface in launcher for version parity check |
| `network/server.py` | Instanced zone architecture (v0.9.0+); `_ZoneInstance` registry for future zone status display |
| `network/client.py` | `_EntityCache`, `current_hub_id`, `poll_transition()` â€” zone-aware state for multiplayer UI |
| `game/game_simulator.py` | Phase 3b combat mechanics (v0.9.3+) â€” server-authoritative HP relevant to crash reports |
| `dev_tools/hot_reload.py` | Settings hot-reload (confirms settings write is compatible) |
| `build/ninja_dash_launcher.spec` | PyInstaller spec â€” verify no new data files need adding |
| `docs/CHANGELOG.md` | Authoritative version history â€” launcher news feed should pull from GitHub releases body |
| `demo_game.py` | Add `--profile`, `--seed`, `--skip-intro` args; F12 screenshot capture |

