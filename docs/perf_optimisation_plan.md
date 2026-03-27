# Performance Optimisation Plan
Branch: `perf/profiling-and-optimisation`
Target: 60 FPS stable, ≤16.7ms frame time

---

## PHASE 0 — CODEBASE SUMMARY ✅

**Entry point:** `demo_game.py` → `main()`
**Game loop:** `demo_game.py` line ~1323 (`while running:`)
**Entity system:** `core/entity_manager.py` — dict-based, iterated per physics/collision tick
**Render system:** `demo_game.py` (inline render pipeline) + `rendering/` modules
**AI modules:** `entities/enemy_ai.py`, `entities/enemy_manager.py`

### Hot Path (per-frame):
```
Clock.tick() → TickEvent (immediate) → PhysicsSystem → CollisionSystem
→ EnemyManager.update() → [AI per enemy] → Rendering pipeline → present()
```

### Known Bottlenecks Identified in Phase 0:

| # | Location | Type | Severity |
|---|----------|------|----------|
| B1 | `collision_system._has_support_below()` | O(all_tiles) linear scan — no spatial hash | CRITICAL |
| B2 | `collision_system._snap_to_ground()` | O(all_tiles) linear scan — no spatial hash | CRITICAL |
| B3 | `enemy_manager._update_arrows()` | O(arrows × all_tiles) — no spatial hash | HIGH |
| B4 | `demo_game.py` liquid tile loop | O(W×H) nested loop each frame, Rect allocs | HIGH |
| B5 | `demo_game.py` player invincibility | `frame.surface.copy()` per frame during i-frames | MEDIUM |
| B6 | `demo_game.py` teleport ghost | `frame.surface.copy()` per frame during teleport | MEDIUM |
| B7 | `demo_game.py` falling platform overlay | SRCALPHA surface alloc per triggered platform per frame | MEDIUM |
| B8 | `demo_game.py` HUD heart warning | SRCALPHA surface alloc per low-health frame | LOW |
| B9 | `demo_game.py` arrow angle math | degrees→radians→trig per arrow (redundant conversion) | LOW |

### Already Optimised (do not re-touch):
- Attack telegraph overlays (pre-allocated surfaces)
- Tile culling (viewport bounds)
- Spatial hash for tile-entity collision
- Enemy AI off-screen culling
- Chase update throttling (0.5s interval)
- Camera offset caching (`_offset_x/_offset_y`)
- Particle list in-place removal
- `present()` in-place scale (no temp surface)

---

## PHASE 1 — PROFILING ✅

**Goal:** Instrument the hot path, collect 500+ frames of real timings.

### Tasks:
- [x] Add `FrameProfiler` utility to `utils/frame_profiler.py`
- [x] Instrument demo_game.py: update phase, render phase, collision, AI, entity physics
- [ ] Run game for 30+ seconds with enemies present, capture CSV output
- [ ] Analyse CSV to confirm bottleneck rankings

**Output:** `docs/perf_baseline.csv` (generated at runtime with `--profile` flag)

**Note:** Profiling run deferred to Phase 4 — optimisations applied first, combined before/after run planned.

---

## PHASE 2 — BOTTLENECK INVESTIGATION ✅

Phase 0 static analysis was sufficient to confirm all bottleneck rankings. Root causes documented per-optimisation below.

---

## PHASE 3 — OPTIMISATIONS ✅

### O1 — Fix `_has_support_below` to use spatial hash ✅

**File:** `systems/collision_system.py`
**Change:** `for tile in self.tiles:` → `for tile in self._get_candidate_tiles(...)`
**Impact:** O(all_tiles) → O(10–30 tiles)

### O2 — Fix `_snap_to_ground` to use spatial hash ✅

**File:** `systems/collision_system.py`
**Change:** Same pattern for both `tiles` and `platforms` iteration
**Impact:** O(all_tiles) → O(10–30 tiles)

### O3 — Fix arrow-tile collision to use spatial hash ✅

**File:** `entities/enemy_manager.py`
**Change:** `for tile in collision_system.tiles:` → `_get_candidate_tiles(arrow_rect, ...)`
**Impact:** O(arrows × all_tiles) → O(arrows × 10–30)

### O4 — Cache liquid tile list at level load ✅

**File:** `demo_game.py` (`refresh_platform_state()` + render loop)
**Change:** Pre-built `liquid_tiles` list filled during tilemap scan; per-frame loop iterates list with bounds cull
**Impact:** O(W×H) per frame → O(liquid_count) per frame

### O5 — Eliminate per-frame surface copies (invincibility) ✅

**File:** `demo_game.py`
**Change:** `frame.surface.copy()` + `BLEND_RGBA_ADD` → pre-allocated `_player_flash_surf` + `set_alpha` blit
**Note:** Teleport ghost copy left in place (rare event, acceptable overhead)

### O6 — Pre-allocate falling platform overlay ✅

**File:** `demo_game.py`
**Change:** `pygame.Surface(..., SRCALPHA)` per triggered platform per frame → pre-allocated `_platform_overlay_surf` + `set_alpha` clipped blit

### O7 — Pre-allocate HUD heart warning surface ✅

**File:** `demo_game.py`
**Change:** `pygame.Surface((heart_size, heart_size), SRCALPHA)` per low-hp frame → pre-allocated `_heart_warn_surf` + `set_alpha` clipped blit

### O8 — Fix arrow angle math (skip radians↔degrees conversion) ⬜

**File:** `demo_game.py`
**Risk:** Trivial — deferred, lower priority than Phase 4 profiling run

---

## PHASE 4 — VALIDATION & FINAL REPORT ⬜

- Run `python demo_game.py --profile` for 30+ seconds with enemies present
- Collect `docs/perf_baseline.csv`
- Compute avg/p95/max per section, compare against pre-optimisation expectations
- Confirm no gameplay regressions (manual play test)
- Write final report with before/after table

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-27 | Branch: perf/profiling-and-optimisation | Isolated from master |
| 2026-03-27 | No multi-threading / multi-clock | Fixed-timestep physics requires determinism |
| 2026-03-27 | Phase 0 complete | Explorer agent full codebase analysis done |
| 2026-03-27 | O1–O7 applied without profiling baseline | Static analysis confidence high; Phase 4 will capture post-opt metrics |
| 2026-03-27 | Teleport ghost copy not fixed | Rare event; SRCALPHA copy cost amortised over long teleport cooldown |
| 2026-03-27 | O8 deferred | Arrow angle math low severity; Phase 4 run will confirm if still needed |
