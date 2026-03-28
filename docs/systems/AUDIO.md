# Audio System

## Purpose and Rationale

The audio system provides sound effect playback for Indie Ninja Adventures. It is intentionally minimal and resilient: the game must never crash due to a missing audio asset or an unavailable audio device. Both conditions are handled with silent fallback — callers can call `play()` freely without checking whether a sound was actually loaded.

This design means audio assets can be added, removed, or left absent without touching any game logic. Developers working on a machine without audio hardware (CI runners, headless test environments) get the same behaviour as players who have accidentally deleted a sound file.

Music playback is not implemented in the current version. The system handles SFX only.

---

## Architecture

### Module layout

```
audio/
    __init__.py          # re-exports AudioManager
    audio_manager.py     # AudioManager class
```

`audio/__init__.py` (line 1–4) simply imports and re-exports `AudioManager` so callers can write `from audio import AudioManager`.

### AudioManager class (`audio/audio_manager.py`)

`AudioManager` wraps `pygame.mixer.Sound`. It holds a fixed catalogue of 12 expected SFX names (`_SFX_NAMES`, lines 25–38). At load time it scans the asset directory for matching files; names that have no file are omitted silently from the internal dict. At playback time, a lookup against that dict either plays the sound or does nothing.

Key attributes:

- `_sounds: dict[str, pygame.mixer.Sound]` — populated by `load_sounds()`; absent names are simply not present in the dict.
- `_volume: float` — the current master SFX volume, clamped to `[0.0, 1.0]` on every write.

### pygame.mixer integration

`pygame.mixer` is initialised outside `AudioManager`, in `initialize_audio()` (`game/game_initialization.py`, lines 508–534). The mixer is configured at:

```
frequency = 44100 Hz
size      = -16 (signed 16-bit)
channels  = 2 (stereo)
buffer    = 512 samples
```

If `pygame.mixer.init()` raises an exception, `initialize_audio()` returns an `AudioManager` that was never given any sounds — all `play()` calls become no-ops. The rest of the game is unaffected.

---

## The 12 SFX Slots

These are the canonical names defined in `AudioManager._SFX_NAMES` (`audio/audio_manager.py`, lines 25–38). Any name not in this tuple will never be loaded.

| Name              | Trigger                                               |
|-------------------|-------------------------------------------------------|
| `swing`           | Player executes a sword attack (demo_game.py line 1719) |
| `hit_enemy`       | Sword attack connects with an enemy or boss (lines 1731, 1741) |
| `player_hurt`     | Player takes non-lethal damage (lines 2231, 2266, 2525) |
| `player_death`    | Player health reaches zero (lines 2222, 2257, 2516)  |
| `jump`            | Player jumps (line 2434)                              |
| `land`            | Player lands after being airborne (line 2428)         |
| `dash`            | Dash ability activates (line 2436)                    |
| `pickup_coin`     | Coin is collected (line 2623)                         |
| `pickup_item`     | Collectible or health pickup is collected (lines 2609, 2620) |
| `menu_select`     | Menu cursor moves to a new item (line 1836)           |
| `menu_confirm`    | Menu item is activated / confirmed (line 1840)        |
| `inventory_open`  | Inventory panel is opened or closed (line 1766)       |

---

## How to Play a Sound

`AudioManager.play(name)` (`audio/audio_manager.py`, lines 66–70) looks up the name in `_sounds` and calls `pygame.mixer.Sound.play()`. If the name is absent — either because the file was never found or because the name is not in `_SFX_NAMES` — the method is a no-op.

```python
# Anywhere that has a reference to the audio_manager instance:
audio_manager.play("swing")
audio_manager.play("jump")
audio_manager.play("pickup_coin")
```

The instance lives as a local variable in the main game loop in `demo_game.py` (created at line 462) and is passed into the loop body as a closure variable.

---

## How to Add a New SFX

1. Add the new canonical name as a string to `AudioManager._SFX_NAMES` in `audio/audio_manager.py` (lines 25–38). Follow the existing snake_case convention and add a comment describing what triggers it.

2. Place the audio file in `assets/audio/sfx/`. The file must be named exactly `<name>.wav`, `<name>.ogg`, or `<name>.mp3` — the loader tries extensions in that order and takes the first match (lines 51–60 of `audio_manager.py`).

3. Call `audio_manager.play("<name>")` at the appropriate point in game logic (typically inside `demo_game.py`'s main loop).

No other changes are required. The next time the game starts, `load_sounds()` will find the file and add it to `_sounds`.

---

## Volume Wiring

Volume changes flow through three layers:

```
SettingsMenu._cycle_sfx_vol()
    -> settings.set("volume_sfx", value)
    -> settings.save()
    -> on_change()   [the callback passed at construction]
        -> apply_runtime_settings()   [demo_game.py line 1204]
            -> audio_manager.set_volume(float(runtime_settings.get("volume_sfx", 0.8)))
                -> AudioManager.set_volume(vol)   [audio_manager.py lines 76–80]
                    -> sound.set_volume(vol)  for each loaded Sound
```

`SettingsMenu` cycles through five fixed steps: `0.0, 0.25, 0.5, 0.75, 1.0`, labelled `Off, 25%, 50%, 75%, 100%` (`ui/menu_system.py`, lines 420–421). Changes take effect immediately because `_apply_changes()` (line 502–504) calls the `on_change` callback, which is `apply_runtime_settings`.

`AudioManager.set_volume()` updates `_volume` and then iterates over every already-loaded `pygame.mixer.Sound` object, calling `set_volume()` on each (lines 78–80). This means volume changes apply to all sounds at once, including any that are currently playing.

---

## initialize_audio() Function

`initialize_audio()` lives in `game/game_initialization.py` (lines 508–534). It is called once at startup from `demo_game.py` (line 462–464):

```python
audio_manager = initialize_audio(
    sfx_volume=float(runtime_settings.get("volume_sfx", 0.8))
)
```

The function:

1. Calls `pygame.mixer.init()` with the parameters described above.
2. On failure, prints a warning and returns an empty `AudioManager` (silent fallback).
3. On success, constructs an `AudioManager` with the requested initial volume.
4. Resolves the SFX asset directory via `get_resource_path("assets", "audio", "sfx")` (compatible with PyInstaller packaging).
5. If the directory exists, calls `manager.load_sounds(sfx_dir)` and prints how many sounds were loaded.
6. If the directory does not exist, prints a warning and returns the manager (silent fallback — all `play()` calls will be no-ops).

---

## Asset Location

SFX files live under:

```
assets/audio/sfx/
```

Supported formats, tried in priority order: `.wav`, `.ogg`, `.mp3`.

File names must match the canonical names in `_SFX_NAMES` exactly (lowercase, underscores). Example:

```
assets/audio/sfx/swing.wav
assets/audio/sfx/jump.ogg
assets/audio/sfx/player_death.wav
```

---

## Known Limitations

- **Music is not implemented.** `GameSettings` defines `volume_music` and `volume_master` keys (`config/settings.py`, lines 29–31), but no music player exists. `apply_runtime_settings()` does not read `volume_music` or `volume_master`.
- **No spatial audio.** All sounds play at the same volume regardless of where the event occurred in the game world.
- **Single channel per sound.** `pygame.mixer.Sound.play()` is called with default arguments; rapid re-triggering of the same sound (e.g. many coins at once) may cut off the previous instance depending on the mixer channel pool.
- **No audio bus or categories.** There is only one volume control. Master volume and per-category volumes (music, ambient) are placeholders in settings only.

---

## File References

| File | Relevant lines | Purpose |
|------|---------------|---------|
| `audio/audio_manager.py` | 1–88 | AudioManager class (complete file) |
| `audio/__init__.py` | 1–4 | Package re-export |
| `game/game_initialization.py` | 508–534 | `initialize_audio()` function |
| `demo_game.py` | 462–464 | AudioManager construction at startup |
| `demo_game.py` | 1204–1229 | `apply_runtime_settings()` — volume wiring |
| `demo_game.py` | 1719, 1731, 1741, 1766, 1836, 1840 | SFX call sites (combat, UI) |
| `demo_game.py` | 2222, 2231, 2257, 2266, 2428, 2434, 2436, 2516, 2525, 2609, 2620, 2623 | SFX call sites (player state, pickups) |
| `ui/menu_system.py` | 388–534 | `SettingsMenu` class |
| `config/settings.py` | 27–51 | `DEFAULT_SETTINGS` including audio keys |
