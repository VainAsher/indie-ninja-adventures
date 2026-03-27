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

**Findings:** TileLoader already performant (PIL LANCZOS at load, cached by biome/type/variant, culled per frame). No code changes required.
**Output:** Summary added to this plan.

---

## PHASE 6 — RENDER PIPELINE INTEGRATION ✅

**Goal:** Single clean render pipeline with documented draw order.
**Output:** Summary added to this plan.

---

## PHASE 7 — PERFORMANCE VALIDATION

**Goal:** Confirm no regressions introduced by animation system.
**Output:** Profiling run results added to this plan.

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-27 | Branch: feature/animation-pipeline | Isolated from perf branch |
| 2026-03-27 | Keep procedural renderer as fallback | Backward compatible — sprites optional |
| 2026-03-27 | Pre-scale enemy frames at registration | Avoids per-frame `transform.scale` calls |
| 2026-03-27 | SpriteManager registers into AnimationRegistry | Zero reload — reuse existing player data |
| 2026-03-27 | Enemy AI state mapped to anim state via constant dict | Decouples AI logic from rendering |
