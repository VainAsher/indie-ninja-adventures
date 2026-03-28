"""
Generate placeholder SFX WAV files for assets/audio/sfx/.

Uses only stdlib (wave, struct, math) — no pygame or third-party deps required.
Each sound is a short sine-wave with a distinct frequency profile so you can
tell them apart during testing.

Run from the project root:
    python tools/gen_placeholder_sfx.py
"""

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
OUT_DIR = Path(__file__).parent.parent / "assets" / "audio" / "sfx"


def _write_wav(path: Path, frames: bytes) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames)


def _sine_sweep(
    freq_start: float,
    freq_end: float,
    duration: float,
    amplitude: float = 0.35,
    attack: float = 0.01,
    decay: float = 0.05,
) -> bytes:
    """Generate a frequency-swept sine wave with a simple envelope."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        progress = i / n
        freq = freq_start + (freq_end - freq_start) * progress

        # Simple envelope: linear attack / linear decay at tail
        env = 1.0
        if t < attack:
            env = t / attack
        elif t > duration - decay:
            env = (duration - t) / decay

        val = amplitude * env * math.sin(2 * math.pi * freq * t)
        samples.append(max(-1.0, min(1.0, val)))

    return struct.pack(f"<{n}h", *[int(s * 32767) for s in samples])


def _tone_sequence(
    freqs: list[float],
    seg_dur: float,
    amplitude: float = 0.35,
) -> bytes:
    """Play a sequence of fixed tones, one after another."""
    chunks = []
    for f in freqs:
        chunks.append(_sine_sweep(f, f, seg_dur, amplitude))
    return b"".join(chunks)


# ------------------------------------------------------------------
# Sound definitions — (name, generator call)
# ------------------------------------------------------------------

def _gen_swing():
    """Short descending whoosh — sword cutting air."""
    return _sine_sweep(900, 300, 0.14, amplitude=0.30, decay=0.06)

def _gen_hit_enemy():
    """Punchy low thud — impact on enemy."""
    return _sine_sweep(220, 110, 0.10, amplitude=0.45, decay=0.07)

def _gen_player_hurt():
    """Mid-range grunt / descending sting."""
    return _sine_sweep(520, 220, 0.20, amplitude=0.38, decay=0.10)

def _gen_player_death():
    """Long descending tone — defeat."""
    return _sine_sweep(440, 80, 0.55, amplitude=0.40, decay=0.20)

def _gen_jump():
    """Short ascending chirp."""
    return _sine_sweep(280, 560, 0.14, amplitude=0.30, attack=0.01, decay=0.05)

def _gen_land():
    """Very short low thud."""
    return _sine_sweep(160, 80, 0.08, amplitude=0.45, attack=0.005, decay=0.05)

def _gen_dash():
    """Quick high-pitched whoosh."""
    return _sine_sweep(700, 1000, 0.10, amplitude=0.28, decay=0.04)

def _gen_pickup_coin():
    """Bright ascending ding-ding."""
    return _tone_sequence([880, 1047], seg_dur=0.07, amplitude=0.30)

def _gen_pickup_item():
    """Warmer two-note chime."""
    return _tone_sequence([523, 659], seg_dur=0.10, amplitude=0.32)

def _gen_menu_select():
    """Very short soft click."""
    return _sine_sweep(440, 440, 0.05, amplitude=0.25, attack=0.005, decay=0.03)

def _gen_menu_confirm():
    """Two quick ascending tones."""
    return _tone_sequence([523, 784], seg_dur=0.07, amplitude=0.30)

def _gen_inventory_open():
    """Gentle ascending sweep — page/panel open."""
    return _sine_sweep(300, 600, 0.15, amplitude=0.28, attack=0.02, decay=0.06)


SOUNDS = {
    "swing":          _gen_swing,
    "hit_enemy":      _gen_hit_enemy,
    "player_hurt":    _gen_player_hurt,
    "player_death":   _gen_player_death,
    "jump":           _gen_jump,
    "land":           _gen_land,
    "dash":           _gen_dash,
    "pickup_coin":    _gen_pickup_coin,
    "pickup_item":    _gen_pickup_item,
    "menu_select":    _gen_menu_select,
    "menu_confirm":   _gen_menu_confirm,
    "inventory_open": _gen_inventory_open,
}


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, gen_fn in SOUNDS.items():
        path = OUT_DIR / f"{name}.wav"
        _write_wav(path, gen_fn())
        print(f"  wrote {path.name}")
    print(f"\nDone — {len(SOUNDS)} placeholder SFX written to {OUT_DIR}")
