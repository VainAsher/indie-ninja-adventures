"""
AudioManager — SFX playback with silent fallback.

Wraps pygame.mixer.Sound. If a sound file is missing, playback for that
name is silently skipped. The game never crashes due to missing audio assets.

Usage:
    manager = AudioManager(sfx_volume=0.8)
    manager.load_sounds(Path("assets/audio/sfx"))
    manager.play("swing")
    manager.set_volume(0.5)
"""

from __future__ import annotations

from pathlib import Path

import pygame


class AudioManager:
    """Manages SFX playback with silent fallback when assets are missing."""

    # All expected SFX names. Add new names here to extend the system.
    _SFX_NAMES = (
        "swing",           # sword attack swing
        "hit_enemy",       # sword connects with enemy / boss
        "player_hurt",     # player takes non-lethal damage
        "player_death",    # player dies
        "jump",            # player jumps
        "land",            # player lands after being airborne
        "dash",            # dash ability activates
        "pickup_coin",     # coin collected
        "pickup_item",     # collectible or health pickup
        "menu_select",     # menu cursor moves
        "menu_confirm",    # menu item activated
        "inventory_open",  # inventory opened or closed
    )

    def __init__(self, sfx_volume: float = 0.8) -> None:
        self._volume: float = max(0.0, min(1.0, sfx_volume))
        self._sounds: dict[str, pygame.mixer.Sound] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_sounds(self, sfx_dir: Path) -> None:
        """Load SFX files from *sfx_dir*. Silently skips missing files."""
        for name in self._SFX_NAMES:
            for ext in ("wav", "ogg", "mp3"):
                path = sfx_dir / f"{name}.{ext}"
                if path.exists():
                    try:
                        sound = pygame.mixer.Sound(str(path))
                        sound.set_volume(self._volume)
                        self._sounds[name] = sound
                    except Exception as exc:
                        print(f"[AUDIO] Failed to load {path}: {exc}")
                    break  # try next name once first matching ext is attempted

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play(self, name: str) -> None:
        """Play a named SFX. No-op if the sound was not loaded."""
        sound = self._sounds.get(name)
        if sound:
            sound.play()

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    def set_volume(self, vol: float) -> None:
        """Set SFX volume (0.0–1.0) and update all already-loaded sounds."""
        self._volume = max(0.0, min(1.0, vol))
        for sound in self._sounds.values():
            sound.set_volume(self._volume)

    @property
    def volume(self) -> float:
        return self._volume

    def __repr__(self) -> str:
        return f"AudioManager(sounds={list(self._sounds)}, volume={self._volume:.2f})"
