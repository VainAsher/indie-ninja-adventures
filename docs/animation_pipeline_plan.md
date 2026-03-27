# Animation Pipeline Plan
Branch: `feature/animation-pipeline`
Goal: Unified, scalable, performant rendering and animation pipeline

---

## Global Rules

- DO NOT break gameplay logic
- DO NOT introduce per-frame heavy operations
- DO NOT load or transform images inside the render loop
- DO NOT duplicate animation data per entity
- ALL assets loaded and processed at startup
- Rendering must remain performant at scale

---

## PHASE 0 — CODEBASE DISCOVERY ✅

**Player:** `entities/player.py` — 8 mechanics, state read via `get_player_render_state()` in `demo_game.py`
**Enemy:** `entities/enemy.py` + `entities/enemy_manager.py` — procedural rendering via `enemy_renderer.py`
**NPC:** `entities/npc.py` + `entities/npc_manager.py` — procedural rendering
**Render loop:** `demo_game.py` lines 2539–3247
**Asset loading:** `rendering/sprite_manager.py` (player-only), `rendering/tile_loader.py`, `rendering/enemy_renderer.py`

### Known issues
| # | Issue |
|---|---|
| A1 | `SpriteManager` is player-only — no shared system |
| A2 | No `AnimationStateMachine` — non-looping anims (attack/hurt) never reset on transition |
| A3 | `get_scaled_frame()` calls `pygame.transform.scale()` every render frame |
| A4 | Enemy/NPC animation is a 0–3 integer counter, no state awareness |
| A5 | No shared frame data — naïve sprite addition would duplicate per entity |

---

## PHASE 1 — SPRITE SHEET SPECIFICATION ✅

**Output:** `docs/sprite_sheet_spec.md`

---

## PHASE 2 — ANIMATION SYSTEM CORE ✅

**Output:** `rendering/animation_system.py`
- `AnimationStateMachine` — per entity, owns current state + elapsed timer only
- `AnimationRegistry` — global, load-once, zero duplication
- `register_all_characters(assets_root)` — startup registration call
- Enemy AI state → animation state mapping helper

---

## PHASE 3 — PLAYER INTEGRATION ✅

**Files changed:**
- `rendering/sprite_manager.py` — registers with `AnimationRegistry` after loading
- `demo_game.py` — create `player.anim_sm`, update + use in render loop

---

## PHASE 4 — ENEMY + NPC INTEGRATION ✅

**Files changed:**
- `entities/enemy.py` — add `anim_sm` field
- `entities/npc.py` — add `anim_sm` field
- `entities/enemy_manager.py` — create state machines on spawn, update each tick
- `entities/npc_manager.py` — create state machines on spawn, update each tick
- `rendering/enemy_renderer.py` — sprite path with procedural fallback

---

## PHASE 5 — TILE SYSTEM REVIEW ✅

**Findings — no code changes needed:**

- `TileLoader._load_and_scale_tile()`: PIL LANCZOS 70×70→32×32 **at load time only**
- `TileLoader.cache`: `dict[(biome, tile_type, index)] → Surface` — O(1) per frame
- Autotile cache: `dict[(biome, tile_type, shape, variant_idx, "autotile")] → Surface`
- `preload_biome()` available for explicit warm-up before level entry
- Headless mode guard: falls back to colored rectangles — no disk I/O in tests
- Render loop culls tiles via camera rect before blit — no off-screen work

---

## PHASE 6 — RENDER PIPELINE INTEGRATION ✅

**Draw order (demo_game.py lines ~2544–3447):**

| # | Layer | Notes |
| --- | --- | --- |
| 1 | Solid tiles | Camera-culled, autotiled |
| 2 | Liquid tiles (lava/water) | Pre-built at level load |
| 3 | Static platforms | Camera-culled |
| 4 | Dynamic platforms (moving/falling) | With overlay surf |
| 5 | Particles (behind player) | |
| 6 | Hazards | |
| 7 | Pickups | |
| 8 | Portals | |
| 9 | Enemies | `draw_enemy()` — sprite path first, procedural fallback; health bars; debug hitboxes |
| 10 | NPCs | `draw_npc()` — same pattern |
| 11 | Player | `anim_sm.get_frame()` → scaled blit; fallback to SpriteManager |
| 12 | Companion orbs | |
| 13 | Shuriken projectiles | |
| 14 | Exit marker | |
| 15 | HUD | Health, FPS, objectives, compass, full-map overlay |
| 16 | Menu overlay | |
| 17 | Tutorial overlay | |
| 18 | Hub brightness overlay | |
| 19 | Cutscene overlay | On top of everything |
| 20 | Moral choice UI | Final battle only |

**Integration status:** AnimationStateMachine frames blit correctly at layer 9/10/11. No architectural changes needed — pipeline was already layer-sorted.

---

## PHASE 7 — PERFORMANCE VALIDATION ✅

**Micro-benchmarks (headless, Python 3.11, 100k iterations):**

| Operation | Cost |
| --- | --- |
| `AnimationStateMachine.transition()` | 0.211 µs / call |
| `AnimationStateMachine.get_frame()` | 0.338 µs / call |
| 20 enemies `get_frame()` per frame | 0.006 ms total |

**Replay profiling (34,862 frames, `perf_run.json` recording):**

| Section | avg | median | p95 |
| --- | --- | --- | --- |
| frame_total | 6.01 ms | 4.04 ms | 14.5 ms |
| render | 4.97 ms | 2.92 ms | 12.5 ms |
| render_enemies | 0.011 ms | 0.003 ms | 0.045 ms |
| enemy_manager | 0.085 ms | 0.007 ms | 0.378 ms |
| collision | 0.136 ms | 0.074 ms | 0.430 ms |
| physics | 0.003 ms | 0.003 ms | 0.004 ms |

**Verdict:** No regressions. `render_enemies` avg 0.011 ms is negligible. The state machine overhead
(transition + get_frame per entity per frame) is sub-microsecond. All global rules satisfied — no
per-frame loads, no per-frame transforms, zero frame data duplication across entity instances.

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-27 | Branch: feature/animation-pipeline | Isolated from perf branch |
| 2026-03-27 | Keep procedural renderer as fallback | Backward compatible — sprites optional |
| 2026-03-27 | Pre-scale enemy frames at registration | Avoids per-frame `transform.scale` calls |
| 2026-03-27 | SpriteManager registers into AnimationRegistry | Zero reload — reuse existing player data |
| 2026-03-27 | Enemy AI state mapped to anim state via constant dict | Decouples AI logic from rendering |
