# Rendering System

## Pipeline Overview

All game content is drawn to a virtual surface at a fixed internal resolution
of 1280 x 720 pixels. At the end of each frame this surface is scaled to the
actual window size with aspect-ratio-preserving letterboxing.

```
game_surface (1280x720) <- all blit/draw calls target this surface
       |
       v
camera.present(screen)  <- pygame.transform.scale into a subsurface
                           bounded by letterbox_left/letterbox_top
```

The virtual surface is obtained from `camera.get_game_surface()` each frame.
No temporary surface is allocated during scaling; `pygame.transform.scale`
writes directly into the window's subsurface.

---

## CameraSystem

File: `systems/camera_system.py`

### Modes

| Mode | Behaviour |
|---|---|
| `WORLD_CLAMP` | Follows player; clamps to world boundary |
| `ROOM_CLAMP` | Follows player; clamps to current room boundary. Rooms smaller than the viewport are centered. |
| `FREE` | No following; responds to `move_free_camera(dx, dy)` |
| `LOCKED` | Camera position is fixed; effects still update |

Default mode at startup: `WORLD_CLAMP`.

### Smooth Follow

The camera uses a configurable deadzone and lerp factor:

- `deadzone_width`: 200 px, `deadzone_height`: 150 px (area where the camera
  does not move when the player stays inside it).
- `follow_speed`: 0.1 (lerp factor per tick; lower = smoother).
- Optional spring mode (`enable_spring = False` by default): adds velocity-based
  overshoot with damping.

The integer offset `(_offset_x, _offset_y)` is cached once per `update()` call
and reused by every `apply(rect)` call that frame, avoiding repeated float
arithmetic.

### Screen Shake and Pan

`add_screen_shake(intensity, duration)` overlays a random offset that decays
over `duration` seconds. The global multiplier `shake_multiplier` (default 0.3)
scales the requested intensity. `add_damage_shake` uses a separate
`damage_shake_multiplier` (0.45).

`add_camera_pan(offset_x, offset_y)` lerps the camera toward an offset over
time (smooth pan speed 0.1). Both effects are composited into `_offset_x` /
`_offset_y` on each `update()`.

### Resize Handling

`handle_resize(window_width, window_height)` must be called after any fullscreen
toggle or window resize event. It recalculates:

- `render_width` and `render_height` — the scaled dimensions that preserve the
  16:9 virtual aspect ratio.
- `letterbox_left` and `letterbox_top` — pixel offsets for centering the scaled
  image.
- `_scaled_rect` — a cached `pygame.Rect` used in `present()`.

If the window is wider than 16:9 the image is pillarboxed (black bars on left
and right). If taller it is letterboxed (black bars on top and bottom).

---

## AnimationStateMachine and AnimationRegistry

File: `rendering/animation_system.py`

### Architecture

`AnimationRegistry` is a global class-level store. It is loaded once at startup
by calling `register_all_characters(assets_root)`. All entity instances of the
same character type share identical list references — no frame data is
duplicated.

`AnimationStateMachine` is a lightweight per-entity controller. It holds only:
- `_state`: current state name string
- `_entry_ms`: `pygame.time.get_ticks()` at the moment of the last transition

Frame data and animation metadata are references into the registry. No
`Surface` copies are made during construction or `get_frame()`.

`get_frame(facing)` is O(1): a dict lookup into `_flip_cache`, followed by
integer arithmetic to derive the frame index from elapsed milliseconds.

### State Priority Order

The function `get_player_render_state(player)` in `demo_game.py` implements
the priority ladder used to select the animation state each frame:

1. `death` — `current_hp <= 0`
2. `hurt` — `invincibility_frames > 0` (player is in i-frames)
3. `teleport` — `is_teleporting_phase` or `is_teleporting_invuln`
4. `ninjutsu_summon` — `ninjutsu_casting`
5. `ninjutsu_hand` — `ninjutsu_active`
6. `throw_air` / `throw_crouch` / `throw_ground` — `is_throwing`
7. `slash_air` — `is_air_attacking` or (`not on_ground and attack_stage > 0`)
8. `slash1` / `slash2` / `slash3` — `attack_stage` 1, 2, or 3
9. `dash` — `is_dashing`
10. `wall_hang` — `is_wall_hanging`
11. `ceiling_hang` — `is_ceiling_hanging`
12. `wall_slide` — `on_wall and not on_ground`
13. `air_spin` — in air with `jumps_left < max_jumps` (double-jumped)
14. `jump` — `vy < 0`
15. `fall` — `vy >= 0`
16. `crouch` — `crouching`
17. `run` — `is_running and abs(vx) > 0.5`
18. `slow_walk` — `abs(vx) > 0.1`
19. `idle` — all else

### Sprite Facing Lock During Attack

When the current animation state is in the attack set
(`slash1`, `slash2`, `slash3`, `slash_air`, `jump_slash`,
`throw_ground`, `throw_crouch`, `throw_air`) the wall-facing inversion is
suppressed. Normally, when the player is touching a wall while airborne the
facing used for sprite selection is inverted so the character appears to face
away from the wall. This inversion is skipped mid-combo to prevent the sprite
flipping direction during a sword swing.

### Non-Looping Animation Restart

`transition(new_state)` records the entry time on every state change. Because
`get_frame` computes the frame index from `elapsed_ms = current_ms - entry_ms`,
non-looping animations such as attack and hurt always restart from frame 0
whenever the state changes to them.

---

## SpriteManager

File: `rendering/sprite_manager.py`

`SpriteManager` handles player sprite loading. It is distinct from
`AnimationRegistry` but registers its loaded data into the registry after
loading, so the player can use `AnimationStateMachine` without re-loading any
assets.

### Frame Extraction

`SpriteSheet(filepath, frame_count)` loads a horizontal strip PNG and divides
it into `frame_count` equal-width frames. An optional `boundaries` list of
x-positions allows variable-width frame cuts for sheets like
`attack-sword_spritesheet.png` (whose frames vary from 68 px to 172 px wide).

Variable-width boundary sets used:

| Name | Boundaries | Used for |
|---|---|---|
| `_ATKSWORD_6` | `[0, 68, 144, 303, 416, 575, 688]` | 6-frame sword attacks |
| `_ATKSWORD_4` | `[0, 68, 144, 303, 416]` | 4-frame throws and ninjutsu |

### Flip Cache

After loading, both facing directions are pre-computed:
- `cache[(state, 1)]` — right-facing frames (original)
- `cache[(state, -1)]` — left-facing frames (`pygame.transform.flip(surf, True, False)`)

No `pygame.transform` calls occur after startup.

### Jump/Fall Frame Split

`jumpfall_spritesheet.png` contains two frames: index 0 is the falling pose
and index 1 is the ascending pose. `SpriteManager._load_animations` slices
the raw frame list to assign the correct frame to each state:

- `jump` state: uses `raw_frames[1]` (ascending)
- `fall` state: uses `raw_frames[0]` (falling)

### Scale

`get_scaled_frame(state, facing, time_ms, target_size)` returns a
`pygame.transform.scale` copy at the requested size. This is used when
target size is not known at load time (player sprite). For enemies, scaling
is done once at registration time and stored in the cache.

For attack frames, the render loop scales by hitbox height only (preserving
aspect ratio) to avoid distortion of the wide sword-swing frames. The scaled
frame is then anchored so the player-body portion aligns with the hitbox.

---

## TileLoader

File: `rendering/tile_loader.py`

### Loading and Scaling

Tile assets are PNG files stored in `assets/biomes/` at 70 x 70 pixels.
`TileLoader._load_and_scale_tile(tile_path)` uses PIL (`Image.open`,
`resize(..., Image.LANCZOS)`) to scale each tile to the target game size
(default 32 x 32 px). LANCZOS was chosen for its quality when downscaling.

The scaled result is converted to a `pygame.Surface` via
`pygame.image.fromstring(data, size, mode)` and returned as
`convert_alpha()`.

All loaded tiles are cached by `(biome, tile_type, index)` key. Autotiled
tiles add `(biome, tile_type, shape, variant_idx, "autotile")` as the key.

### Biome-Specific Tile Sets

| Biome | Tile types |
|---|---|
| `dungeon` | solid, platform, decorative, lava, water, platform_falling, platform_moving |
| `cave` | solid, platform, liquid, lava, water, platform_falling, platform_moving |
| `building` | solid, platform, decorative, lava, water, platform_falling, platform_moving |
| `forest` | solid, platform, lava, water, platform_falling, platform_moving |
| `town` | solid, platform, lava, water, platform_falling, platform_moving |
| `sewer` | solid, platform, lava, water (murky green), platform_falling, platform_moving |
| `hollow` | solid, platform, lava (corrupted magenta), water, platform_falling, platform_moving |

When an asset file is missing, a colored fallback tile is generated with a
`+30` brightness border. Fallback tiles are cached separately in
`self.fallback_tiles`.

### Autotile Support

`get_autotiled_tile(biome, tile_type, tilemap, x, y, tile_id, seed)`:

1. Calls `autotile_key(tilemap, x, y, tile_id)` to derive a 3x3 neighbor
   shape identifier.
2. Uses `deterministic_variant_index(x, y, seed, num_variants)` to select a
   variant without random variation between frames.
3. Loads the variant-specific PNG and caches it.

`preload_biome(biome)` pre-warms the cache for all registered tile types in a
biome, useful at level load time.

---

## ParticleSystem

File: `rendering/particles.py`

`ParticleSystem` maintains a flat list of `Particle` dataclasses. In-place
swap-and-pop removal avoids list rebuilds during iteration.

### Emitter Types

| Method | Particle color | Count | Use |
|---|---|---|---|
| `emit_dust(x, y, count)` | `(200, 200, 200)` gray | 8 default | Landing impact, footsteps |
| `emit_dash(x, y, direction)` | `(255, 120, 255)` magenta | 12 | Dash activation |
| `emit_attack_warning(x, y, count)` | `(255, 80, 80)` red | 6 default | Enemy attack windup |
| `emit_attack_impact(x, y, count)` | `(255, 255, 120)` yellow | 12 default | Enemy attack active phase |

### Update and Lifetime

`update(dt)` ticks each particle:
- Decrements `life` by `dt`.
- Advances `x += vx * dt`, `y += vy * dt`.
- Applies gravity: `vy += 300 * dt`.
- Removes particles when `life <= 0`.

Particle positions in `emit_*` methods for enemy effects use screen
coordinates (world position minus camera offset). Dust and dash positions
come in world coordinates and are transformed by `camera.apply(rect)` inside
`draw()`.

`draw(surface, camera, color_override)` iterates all live particles and calls
`pygame.draw.rect` for each, applying `camera.apply` to convert the world rect
to screen space.

---

## Rendering Order

Each frame, content is drawn to `game_surface` in the following order. Items
drawn later appear on top.

1. Background fill: `game_surface.fill(COLOR_BG)` — solid color `(10, 10, 20)`
2. Solid tiles — autotiled or fallback, camera-culled to viewport plus a 10-tile
   margin
3. Liquid tiles — lava and water, same culling
4. Static platforms — autotiled
5. Dynamic platforms — moving and falling platforms with a pulsing overlay when
   triggered
6. Particles — dust and dash effects (world-space)
7. Hazards — `render_hazards(game_surface, hazards, camera)`
8. Pickups — `render_pickups(game_surface, pickups, camera)`
9. Portals — `draw_portal` for each portal in `portal_manager`
10. Enemies — sprites via `draw_enemy`; attack telegraph overlays (glow,
    exclamation, flash); health bars; goblin dagger hitbox outlines (debug);
    skeleton arrows; boss entity and boss projectiles
11. NPCs — sprites via `draw_npc_char`
12. Player — sprite frame scaled to hitbox; shadow ellipse; teleport phase
    ghost cursor; invincibility flash overlay; shuriken projectiles
13. Companion orbs — Yin and Yang story companions (v0.7.0)
14. Exit marker — pulsing gold portal outline
15. Objective compass arrow
16. HUD — hearts (top-left), stamina bar, mana bar, dash CD bar, teleport CD
    bar, ninjutsu CD bar, shuriken ammo count; compass indicators (top-right);
    debug HUD overlay (only when `show_debug_overlay` is True)
17. Inventory UI overlay
18. Minimap (small corner overlay) or full-map overlay when `show_full_map`
19. NPC indicators and interaction prompts
20. Dialogue UI (modal)
21. Mission menu UI (modal)
22. Shop UI (modal)
23. Victory screen
24. Landing / main menu background (covers gameplay when in menu state)
25. Menu overlays — `menu_manager.render(game_surface)`
26. Tutorial and controls hints
27. Hub brightness overlay (story-driven brightness effect)
28. Cutscene overlay (full-screen dimmed text box)
29. Moral choice UI (ending choice)

After all draw calls, `camera.present(screen)` scales the virtual surface into
the window.

---

## HUD Elements

File: `rendering/hud.py` — `HUDRenderer`

### Hearts

`draw_hearts(surface, current_hp, max_hp, x, y, low_health_time)` renders
Zelda-style heart containers. Full hearts are crimson (`(220, 20, 60)`); empty
hearts are dark gray. When `current_hp <= 1`, the last heart pulses using a
sine wave keyed to `low_health_time`.

The main render loop in `demo_game.py` draws hearts inline at the top-left
rather than always delegating to `HUDRenderer.draw_hearts`. Both paths produce
the same visual result.

### Bars

`draw_bar(surface, label, value, max_value, x, y, width, height, color)` draws
a filled progress bar with a label above it. Used for:

- Stamina (blue)
- Mana (blue, only when `mana_max > 0`)
- Dash CD (magenta)
- Teleport CD (cyan)
- Ninjutsu CD (gold)

### Objectives

`rendering/objective_hud.py` provides `ObjectiveHUDRenderer`. It is only shown
in campaign and playtest modes when there are active objectives.

### Compass Indicators

`draw_compass_indicators` renders a navigation panel in the top-right corner
showing directional arrows and tile-distance to the nearest coin, the exit,
and hub portals. Distance is expressed in tiles (px / 32).

### Minimap

File: `rendering/minimap.py`

The minimap shows the procedural world as a grid of color-coded room squares.

| Room type | Color |
|---|---|
| Start | `(80, 220, 80)` green |
| Exit | `(220, 80, 80)` red |
| Shop | `(220, 180, 80)` gold |
| Combat | `(180, 80, 80)` dark red |
| Platform | `(120, 120, 160)` blue-gray |
| Treasure | `(220, 220, 80)` yellow |
| Boss | `(180, 80, 180)` purple |

The current room is highlighted with a white outline. A white dot marks the
player position within the room. Connection lines between adjacent rooms are
drawn in gray.

`show_minimap` (M key by default) toggles the corner minimap. `show_full_map`
(Tab by default) scales the minimap to approximately 85% of the screen with a
semi-transparent overlay behind it.

---

## Debug Overlays

### F3 — Debug HUD

`pygame.K_F3` toggles `show_debug_overlay`. When active, `hud.draw_hud` renders
a full data panel in the top-left:

- Mode and seed labels
- FPS counter
- Camera mode name
- Player world position and velocity
- Coin and collectible counts
- Full set of resource bars (health, stamina, mana, dash CD, teleport CD,
  ninjutsu CD, shuriken ammo)
- Ground / wall contact flags and facing direction

The setting is also persisted via `runtime_settings` as `show_hitboxes`.

### Hitbox Visualization

When `show_debug_overlay` is True, the active sword attack rect
`attack_fx_rect` is outlined in an orange pulse. The attack flash surfaces
(`_atk_glow_surf`, `_atk_flash_surf`) are always drawn during enemy attack
sub-states regardless of the debug flag — they are considered gameplay
telegraphs, not debug tools.

---

## Known Limitations

- No screen-shake implementation for player-damage events. The `CameraSystem`
  has full `add_screen_shake` / `add_damage_shake` support, but at the time of
  writing the game loop does not call these on player damage. It is wired up
  only for some enemy and portal events via `camera_effects`.
- No hit-flash on the player sprite when contact damage is received. The
  invincibility flash (white overlay every 6 frames) fires only for i-frame
  duration, not as a one-frame impact indicator.
- Particle positions for enemy attack events are passed as screen-space
  coordinates (world minus camera offset) while dust and dash particles are
  passed in world-space. Both are handled correctly by the respective callers
  but the inconsistency is a known footgun.

---

## File References

| File | Role |
|---|---|
| `systems/camera_system.py` | Virtual surface, letterboxing, follow modes, shake/pan |
| `rendering/animation_system.py` | AnimationRegistry, AnimationStateMachine, per-character defs |
| `rendering/sprite_manager.py` | SpriteSheet extraction, flip cache, SpriteManager for player |
| `rendering/tile_loader.py` | PNG loading, PIL LANCZOS scaling, biome tile sets, autotile |
| `rendering/particles.py` | Dust, dash, and enemy attack particles |
| `rendering/hud.py` | Hearts, resource bars, compass, HUDRenderer |
| `rendering/minimap.py` | Room-type minimap and full-map overlay |
| `rendering/objective_hud.py` | Objective progress display (campaign/playtest only) |
| `rendering/enemy_renderer.py` | `draw_enemy`, `draw_npc` using AnimationStateMachine |
| `rendering/hazard_renderer.py` | `render_hazards` |
| `rendering/pickup_renderer.py` | `render_pickups` |
| `demo_game.py` | Main render loop; `get_player_render_state`; rendering order |
