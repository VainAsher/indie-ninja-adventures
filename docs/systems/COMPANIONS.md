# Companion Orbs — Yin & Yang

**Indie Ninja Adventures** | v0.7.1 | 2026-03-28

---

## Rationale

Yin & Yang are twin spirit-orbs that orbit the player. They are purely cosmetic — no gameplay effect — but carry the emotional core of the story. They represent the player character's lost family (children), and their presence or absence across story acts is the primary visual signal of narrative progress.

---

## Architecture

**File**: `entities/companions.py` — `CompanionOrbs` class

The class is self-contained. It takes player position each tick and computes orb positions, glow animations, and particle trails. It renders directly to the game surface.

---

## Visual design

| Orb | Side | Color | Animation | Meaning |
| --- | --- | --- | --- | --- |
| Yin | Left | Soft white-blue `(220, 220, 255)` | Steady pulse (2.0 rad/s) | Calm, reflection |
| Yang | Right | Warm gold `(255, 220, 150)` | Fast flicker (6.0 rad/s) | Energy, joy |

**Orbit parameters**:
- Radius: 35 px from player center
- Rotation speed: 0.8 rad/s (slow, gentle orbit)
- Orbs are π apart (180°) — always on opposite sides

**Glow**: Each orb has a 16 px soft glow sphere behind the 8 px core disc.

**Particles**: Optional particle trail emitted from each orb position (enabled by default, `enable_particles: True`).

---

## Story presence

| Act | Orbs present | Reason |
| --- | --- | --- |
| Act 0 (prologue) | Both | Before the journey begins |
| Act 1 | Neither | Consumed by the Veil Maiden |
| Act 2 | Neither | Still lost |
| Act 3 | Both | Recovered / memory restored |
| Act 4 (epilogue) | Constellation only | Returned as stars post-ending |

Both endings (`SAVE` and `DESTROY`) set `constellation_visible: True` — the orbs are never physically present again in post-game, but are visible as distant stars in the hub sky.

---

## API

```python
orbs = CompanionOrbs()

# Control visibility (driven by StoryManager / act transitions)
orbs.yin_active = False   # hide Yin
orbs.yang_active = False  # hide Yang

# Each physics tick
orbs.update(dt, player_x, player_y, player_width, player_height)

# Each render frame
orbs.render(surface, camera_offset_x, camera_offset_y)
```

`update()` advances orbit angle, pulse/flicker animation timers, and particle state.
`render()` draws glow, core disc, and particles for each active orb.

---

## Audio

`enable_audio: False` — a gentle hum/chime placeholder exists in the design but no audio file is wired. If audio is added, it should be a quiet ambient loop tied to the SFX volume setting.

---

## Current status

`CompanionOrbs` is **fully implemented** visually. Story-driven visibility toggling (act transitions) is wired through `StoryManager`. Audio is not implemented.
