# Settings System

## Purpose

The settings system provides persistent user configuration for Indie Ninja Adventures. Settings are stored as JSON on disk and survive game restarts. All default values are defined in one place so new installs start with a sensible baseline, and unknown keys added by future versions are handled gracefully through a merge-with-defaults strategy at load time.

The primary API is the `GameSettings` class in `config/settings.py`. At runtime the game loop in `demo_game.py` holds a `GameSettings` instance named `runtime_settings` and passes it directly to the `SettingsMenu`. Changes made in the menu are written to disk immediately and applied to live systems through a single callback.

---

## Settings Reference

The table below lists every key in `GameSettings.DEFAULT_SETTINGS` (`config/settings.py`, lines 27–51), its default value, the type that is expected, and its wiring status.

### Audio

| Key | Default | Type | Controls | Status |
|-----|---------|------|----------|--------|
| `volume_master` | `1.0` | float 0–1 | Intended global volume multiplier | Not wired — no code reads this key at runtime |
| `volume_music` | `0.7` | float 0–1 | Background music volume | Not wired — music is not implemented |
| `volume_sfx` | `0.8` | float 0–1 | SFX playback volume via `AudioManager.set_volume()` | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |

### Display

| Key | Default | Type | Controls | Status |
|-----|---------|------|----------|--------|
| `fullscreen` | `False` | bool | Calls `pygame.display.toggle_fullscreen()` when changed | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |
| `vsync` | `True` | bool | Intended VSync flag | Not wired — `pygame.display.set_mode()` does not currently use this key |
| `window_width` | `1280` | int | Intended window width | Not wired — window size is calculated from screen resolution at startup |
| `window_height` | `720` | int | Intended window height | Not wired — same as above |

### Gameplay

| Key | Default | Type | Controls | Status |
|-----|---------|------|----------|--------|
| `screenshake` | `True` | bool | Enables / disables `camera.config.enable_shake` | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |
| `particles` | `True` | bool | Enables / disables `ParticleSystem.enabled` | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |
| `camera_smoothing` | `0.1` | float | Sets `camera.config.follow_speed` (clamped 0.02–0.2) | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |

### Controls

| Key | Default | Type | Controls | Status |
|-----|---------|------|----------|--------|
| `key_left` | `"left"` | string name | Left movement key | Live — mapped through `_build_key_bindings()` → `Player.set_key_bindings()` |
| `key_right` | `"right"` | string name | Right movement key | Live — same path |
| `key_jump` | `"space"` | string name | Jump key | Live — same path |
| `key_dash` | `"shift"` | string name | Dash ability key | Live — same path |
| `key_crouch` | `"down"` | string name | Crouch key | Live — same path |

### Developer

| Key | Default | Type | Controls | Status |
|-----|---------|------|----------|--------|
| `show_fps` | `False` | bool | Displays FPS counter overlay | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |
| `show_hitboxes` | `False` | bool | Renders collision hitboxes (`show_debug_overlay`) | Live — wired through `apply_runtime_settings()` and `SettingsMenu` |
| `log_level` | `"INFO"` | string | Intended logger level | Not wired — `GameLogger` does not read this key at startup |

---

## How Settings Flow at Runtime

```
User presses Enter on a SettingsMenu item
    -> SettingsMenu callback (e.g. _toggle_shake, _cycle_sfx_vol, _toggle_fullscreen)
        -> self._set(key, new_value)
            -> settings.set(key, value)    [in-memory update, config/settings.py line 117]
            -> settings.save()             [writes to disk, config/settings.py line 96]
        -> self._refresh_labels()          [updates on-screen text]
        -> self._apply_changes()           [ui/menu_system.py line 502]
            -> self.on_change()            [the callback passed at SettingsMenu construction]
                -> apply_runtime_settings()  [demo_game.py line 1204]
```

`apply_runtime_settings()` reads every live-wired key from `runtime_settings` and pushes the values into the appropriate system objects. It is also called once at startup (demo_game.py line 1230) to apply the loaded settings before the first frame.

`SettingsMenu` is constructed with both the `GameSettings` instance and `apply_runtime_settings` as the `on_change` callback (`demo_game.py`, lines 1858–1859):

```python
SettingsMenu(GAME_WIDTH, GAME_HEIGHT, runtime_settings, apply_runtime_settings)
```

---

## Key Binding System

### String names to pygame constants

Key bindings are stored in settings as human-readable strings (`"left"`, `"space"`, `"shift"`, `"a"`, etc.). Before being handed to the player they are translated to `pygame` integer constants by `_build_key_bindings()` (`demo_game.py`, lines 1185–1202).

The translation map `_KEY_NAME_MAP` (lines 1187–1194) covers:

- Arrow keys: `"left"`, `"right"`, `"up"`, `"down"`
- Common keys: `"space"`, `"return"`, `"shift"` / `"lshift"` / `"rshift"`, `"ctrl"`, `"alt"`
- All lowercase letters `"a"` through `"z"` — generated dynamically via `pygame.K_<letter>`

Any string not in the map is silently dropped. The action will then fall back to the hardcoded default inside the relevant mechanic.

### Recognised action names

`_build_key_bindings()` processes exactly five actions: `left`, `right`, `jump`, `dash`, `crouch`. The settings keys that feed them are `key_left`, `key_right`, `key_jump`, `key_dash`, `key_crouch`.

### Player.set_key_bindings()

`Player.set_key_bindings(bindings)` (`entities/player.py`, lines 207–215) accepts a `dict[str, int]` mapping action name to pygame key constant and stores it as `self._key_bindings`. During `on_tick`, each mechanic calls `self._key_pressed(action)` which looks up the action in `_key_bindings` (line 359); if the action is absent the mechanic falls back to its own hardcoded default constant.

Key bindings are applied:

1. At startup, after the player is created (`demo_game.py`, line 1259).
2. Whenever `apply_runtime_settings()` is called and `player is not None` (line 1214–1215).

---

## GameSettings API

All methods are defined in `config/settings.py`.

### `get(key, default=None)`

Lines 104–115. Returns the current value for `key`. If the key is not present in either the loaded settings or `DEFAULT_SETTINGS`, returns `default`. Never raises.

```python
vol = runtime_settings.get("volume_sfx", 0.8)
fs  = runtime_settings.get("fullscreen", False)
```

### `set(key, value)`

Lines 117–125. Updates the in-memory settings dict. Does **not** persist to disk. Call `save()` explicitly to persist.

```python
runtime_settings.set("fullscreen", True)
```

### `save()`

Lines 96–102. Writes the current in-memory settings to `user_data/settings/settings.json` as formatted JSON. Prints an error and continues if the write fails.

### `load()`

Lines 79–94. Called automatically by `__init__`. Reads the settings file and merges it over `DEFAULT_SETTINGS` so that keys added in a newer version of the game are present even in an existing save file. If the file cannot be read, defaults are used and an error is printed.

### `reset_to_defaults()`

Lines 127–130. Replaces in-memory settings with a fresh copy of `DEFAULT_SETTINGS` and saves immediately.

### `get_all()`

Lines 132–134. Returns a shallow copy of the full settings dict.

### `update(new_settings)`

Lines 136–143. Bulk-updates multiple keys at once from a dict. Does not save automatically.

---

## Storage Location

Settings are stored at:

```
user_data/settings/settings.json
```

The base `user_data` directory is resolved in `GameSettings._get_user_data_dir()` (`config/settings.py`, lines 69–77):

1. If the environment variable `NINJADASH_USER_DATA` is set, that path is used.
2. Otherwise, `user_data/` relative to the project root (the parent of the `config/` directory) is used.

This means the path is `<project_root>/user_data/settings/settings.json` by default. The directory is created on first run if it does not exist.

---

## How to Add a New Setting

1. Add the key and its default value to `GameSettings.DEFAULT_SETTINGS` in `config/settings.py` (lines 27–51). Put it in the appropriate category block and choose a descriptive snake_case name.

2. Decide whether the setting should be surfaced in the `SettingsMenu`. If yes, add a label method, a toggle/cycle method, and an entry in `_build_items()` inside `SettingsMenu` (`ui/menu_system.py`, lines 423–445). Follow the pattern of `_toggle_shake` / `_label_shake` for booleans, or `_cycle_sfx_vol` / `_label_sfx_vol` for stepped values.

3. Add the runtime application logic to `apply_runtime_settings()` in `demo_game.py` (lines 1204–1228). Read the value with `runtime_settings.get("your_key", default)` and push it into the relevant system.

4. If the new setting is a key binding, add the action name to the `for action in (...)` loop inside `_build_key_bindings()` (line 1196) and ensure the corresponding `key_<action>` default is in `DEFAULT_SETTINGS`.

No migration is needed for existing save files: `load()` merges new keys over defaults automatically.

---

## File References

| File | Relevant lines | Purpose |
|------|---------------|---------|
| `config/settings.py` | 13–146 | `GameSettings` class (complete file) |
| `config/settings.py` | 27–51 | `DEFAULT_SETTINGS` — all keys and defaults |
| `demo_game.py` | 462–464 | `runtime_settings` passed to `initialize_audio()` at startup |
| `demo_game.py` | 1178 | `_last_fullscreen` sentinel for toggling fullscreen |
| `demo_game.py` | 1185–1202 | `_build_key_bindings()` — string name to pygame constant mapping |
| `demo_game.py` | 1204–1229 | `apply_runtime_settings()` — all live-wired settings applied here |
| `demo_game.py` | 1230 | Initial call to `apply_runtime_settings()` at startup |
| `demo_game.py` | 1259 | Initial call to `player.set_key_bindings()` after player creation |
| `demo_game.py` | 1856–1859 | `SettingsMenu` construction with `runtime_settings` and callback |
| `ui/menu_system.py` | 388–545 | `SettingsMenu` class — UI layer for all exposed settings |
| `entities/player.py` | 193–215 | `_key_bindings` field and `set_key_bindings()` method |
| `entities/player.py` | 359 | Key lookup inside mechanic tick using `_key_bindings` |
