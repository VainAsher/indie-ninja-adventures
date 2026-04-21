---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Audio System (Java)

## Scope

Canonical audio runtime for the Java client.

## Primary Java owners

- `java/client/src/main/java/com/indieniinja/client/audio/AudioManager.java`
- `java/client/src/main/java/com/indieniinja/client/audio/MusicManager.java`
- `java/client/src/main/java/com/indieniinja/client/GameScreen.java`

## Runtime flow

1. `GameScreen` creates `AudioManager` and `MusicManager` during screen startup.
2. SFX assets are loaded from `assets/audio/sfx`.
3. Music assets are loaded from `assets/audio/music`.
4. `MusicManager.update(delta)` is called each frame for cross-fades.
5. `GameScreen` triggers SFX by gameplay state transitions (jump, land, dash, swing, hurt, death).
6. `MusicManager.playZone(hubId, act)` selects zone/act tracks on snapshot updates.

## Method-level call graphs

- Boot/load graph:
  - `GameScreen` startup -> `new AudioManager(0.8f)` -> `AudioManager.loadSounds(Gdx.files.internal("assets/audio/sfx"))`
  - `GameScreen` startup -> `new MusicManager()` -> `MusicManager.loadTracks(Gdx.files.internal("assets/audio/music"))`
- Per-frame graph:
  - `GameScreen.render(delta)` -> `musicManager.update(delta)` -> `MusicManager.update(delta)`
- Zone/act BGM graph:
  - `GameScreen.render(...)` (snapshot hub/act update) -> `musicManager.playZone(snapHub, snapAct)` -> `MusicManager.startCrossFadeTo(...)`
- SFX trigger graph:
  - `GameScreen` movement/combat transitions -> `audioManager.play("jump"|"land"|"dash"|"swing"|"player_hurt"|"player_death")`

## Contracts

- Missing SFX/BGM assets are non-fatal (silent fallback).
- SFX names are fixed by `AudioManager.SFX_NAMES`.
- BGM prefers `{zone}_act{N}` before `{zone}`.

## Current gaps

- No dedicated in-game audio settings menu in the Java client yet.
- Volume defaults are currently code-defined at startup.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/AUDIO.md`
