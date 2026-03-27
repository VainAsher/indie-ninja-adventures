# Sprite Sheet Specification
Version: 1.0 — Indie Ninja Adventures

This document is the contract between artists and the animation engine.
All sprite assets **must** conform to this spec to load correctly.

---

## Format Rules

| Rule | Value |
|------|-------|
| File format | PNG with transparency (RGBA) |
| Layout | Horizontal strip — all frames left to right, single row |
| Frame size | Consistent within a sheet (all frames same width × height) |
| Background | Transparent |
| Colour profile | sRGB |

---

## Frame Sizes by Character

| Character | Hitbox (w × h) | Sprite canvas (w × h) | Notes |
|-----------|---------------|----------------------|-------|
| Player | 28 × 56 | 64 × 80 | Extra canvas for weapon swing / cape |
| Player (crouch) | 28 × 28 | 64 × 40 | Separate `crouch_spritesheet.png` |
| Goblin | 32 × 48 | 48 × 56 | |
| Bat | 24 × 24 | 40 × 32 | Wings extend beyond hitbox |
| Slime | 40 × 32 | 48 × 40 | |
| Skeleton | 32 × 56 | 48 × 64 | |
| Wolf | 48 × 32 | 64 × 40 | |
| NPC (all types) | 32 × 48 | 48 × 56 | Same canvas as Goblin |

Sprite canvas may be larger than the hitbox to accommodate visual effects.
The engine centres the sprite canvas on the hitbox centre point.

---

## Animations per Character

### Player — `assets/sprites/player/`

| State | Filename | Frames | FPS | Loop |
|-------|----------|--------|-----|------|
| idle | `idle_spritesheet.png` | 2 | 8 | yes |
| walk | `walk_spritesheet.png` | 4 | 10 | yes |
| run | `run_spritesheet.png` | 6 | 12 | yes |
| slow_walk | `walk_spritesheet.png` | 4 | 8 | yes |
| jump | `jumpfall_spritesheet.png` | 1 (frame 0) | — | no |
| fall | `jumpfall_spritesheet.png` | 1 (frame 1) | — | no |
| crouch | `idle_spritesheet.png` | 2 | 6 | yes |
| dash | `run_spritesheet.png` | 6 | 20 | yes |
| wall_slide | `jumpfall_spritesheet.png` | 2 | 8 | yes |
| wall_hang | `jumpfall_spritesheet.png` | 2 | 6 | yes |
| air_spin | `jumpfall_spritesheet.png` | 2 | 10 | yes |
| hurt | `hurt_spritesheet.png` | 3 | 12 | no |
| death | `death_spritesheet.png` | 5 | 12 | no |
| attack / slash1–3 | `attack-sword_spritesheet.png` | 6 | 15 | no |
| throw_ground | `attack-sword_spritesheet.png` | 4 | 12 | no |
| teleport | `attack-sword_spritesheet.png` | 4 | 12 | no |
| ninjutsu_summon | `attack-sword_spritesheet.png` | 4 | 10 | no |

### Enemies — `assets/sprites/characters/{type}/`

Supported types: `goblin`, `bat`, `slime`, `skeleton`, `wolf`

| State | Filename | Frames | FPS | Loop |
|-------|----------|--------|-----|------|
| idle | `idle_spritesheet.png` | 2 | 8 | yes |
| walk | `walk_spritesheet.png` | 4 | 10 | yes |
| run | `run_spritesheet.png` | 4–6 | 12 | yes |
| attack | `attack_spritesheet.png` | 4 | 12 | no |
| hurt | `hurt_spritesheet.png` | 2 | 10 | no |
| death | `death_spritesheet.png` | 4 | 10 | no |
| stunned | `hurt_spritesheet.png` | 2 | 6 | yes |

**Bat exception:** uses `idle_spritesheet.png` for all movement states (flying — no walk cycle).

### NPCs — `assets/sprites/characters/npc/`

All NPC types share one sprite set. Visual differentiation via accessories (drawn on top) is not supported with sprites — each NPC type needs its own folder if visual variation is required.

| Type folder | State | Filename | Frames | FPS | Loop |
|-------------|-------|----------|--------|-----|------|
| `npc_mission_giver/` | idle | `idle_spritesheet.png` | 2 | 6 | yes |
| `npc_mission_giver/` | walk | `walk_spritesheet.png` | 4 | 8 | yes |
| `npc_shop/` | idle | `idle_spritesheet.png` | 2 | 6 | yes |
| `npc_shop/` | walk | `walk_spritesheet.png` | 4 | 8 | yes |
| `npc_tutorial/` | idle | `idle_spritesheet.png` | 2 | 6 | yes |
| `npc_lore/` | idle | `idle_spritesheet.png` | 2 | 6 | yes |

---

## Directory Layout

```
assets/
  sprites/
    player/
      idle_spritesheet.png
      walk_spritesheet.png
      run_spritesheet.png
      jumpfall_spritesheet.png
      attack-sword_spritesheet.png
      hurt_spritesheet.png
      death_spritesheet.png
    characters/
      goblin/
        idle_spritesheet.png
        walk_spritesheet.png
        run_spritesheet.png
        attack_spritesheet.png
        hurt_spritesheet.png
        death_spritesheet.png
      bat/
        idle_spritesheet.png
        attack_spritesheet.png
        hurt_spritesheet.png
        death_spritesheet.png
      slime/
        idle_spritesheet.png
        walk_spritesheet.png
        attack_spritesheet.png
        hurt_spritesheet.png
        death_spritesheet.png
      skeleton/
        idle_spritesheet.png
        walk_spritesheet.png
        attack_spritesheet.png
        hurt_spritesheet.png
        death_spritesheet.png
      wolf/
        idle_spritesheet.png
        walk_spritesheet.png
        run_spritesheet.png
        attack_spritesheet.png
        hurt_spritesheet.png
        death_spritesheet.png
      npc_mission_giver/
        idle_spritesheet.png
        walk_spritesheet.png
      npc_shop/
        idle_spritesheet.png
        walk_spritesheet.png
      npc_tutorial/
        idle_spritesheet.png
        walk_spritesheet.png
      npc_lore/
        idle_spritesheet.png
    projectiles/
      shuriken.png
```

---

## Naming Convention

- All filenames lowercase with underscores
- Always suffix `_spritesheet.png`
- Sheet contains **all frames in one row**, left to right
- Frame count must match what is registered in `rendering/animation_system.py`

---

## Facing Direction

- All sprites drawn **facing right**
- The engine caches a horizontally-flipped copy at load time
- Do NOT supply separate left-facing sheets

---

## Fallback Behaviour

If a sprite sheet file is missing:
- The engine generates a coloured placeholder rectangle (no crash)
- For enemies/NPCs, procedural rendering is used instead
- Missing files are logged to console: `[AnimationRegistry] Missing: path/to/file.png`

---

## Pixel Art Guidelines (recommended)

- Work at 1× pixel density (no scaling artefacts)
- Keep transparent padding consistent across frames (helps centering)
- Test at hitbox size (see table above) to verify readability
