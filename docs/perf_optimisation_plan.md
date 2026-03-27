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

## PHASE 1 — PROFILING ⬜

**Goal:** Instrument the hot path, collect 500+ frames of real timings.

### Tasks:
- [ ] Add `FrameProfiler` utility to `utils/frame_profiler.py`
- [ ] Instrument demo_game.py: update phase, render phase, collision, AI, entity physics
- [ ] Run game for 30+ seconds with enemies present, capture CSV output
- [ ] Analyse CSV to confirm bottleneck rankings

**Output:** `docs/perf_baseline.csv` + profiling results table

---

## PHASE 2 — BOTTLENECK INVESTIGATION ⬜

For each bottleneck confirmed by profiling: document location, evidence, cause, impact.

---

## PHASE 3 — OPTIMISATIONS ⬜ (apply one at a time)

### O1 — Fix `_has_support_below` to use spatial hash
**File:** `systems/collision_system.py`
**Risk:** Low — internal helper, no API change

### O2 — Fix `_snap_to_ground` to use spatial hash
**File:** `systems/collision_system.py`
**Risk:** Low

### O3 — Fix arrow-tile collision to use spatial hash
**File:** `entities/enemy_manager.py`
**Risk:** Low

### O4 — Cache liquid tile list at level load
**File:** `demo_game.py` + `game/world_builder.py` or `game/level_factory.py`
**Risk:** Low — rendering-only change

### O5 — Eliminate per-frame surface copies (invincibility + teleport)
**File:** `demo_game.py`
**Risk:** Medium — visual change, verify correctness

### O6 — Pre-allocate falling platform overlay
**File:** `demo_game.py`
**Risk:** Low

### O7 — Pre-allocate HUD heart warning surface
**File:** `demo_game.py`
**Risk:** Low

### O8 — Fix arrow angle math (skip radians↔degrees conversion)
**File:** `demo_game.py`
**Risk:** Trivial

---

## PHASE 4 — VALIDATION & FINAL REPORT ⬜

- Run full profiling pass post-optimisations
- Compare before/after metrics
- Confirm no gameplay regressions

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-27 | Branch: perf/profiling-and-optimisation | Isolated from master |
| 2026-03-27 | No multi-threading / multi-clock | Fixed-timestep physics requires determinism |
| 2026-03-27 | Phase 0 complete | Explorer agent full codebase analysis done |
