# Performance Optimizations

**Indie Ninja Adventures** | v0.7.1 | 2026-03-28

---

## Context

The game targets stable 60 FPS at 1280×720. Several critical performance regressions were identified and fixed during development. This document records the root causes, fixes, and measured results.

---

## O1 — Raycast spatial hash (2025-12-23)

**File**: `systems/collision_system.py`

**Problem**: Enemy AI calls `raycast()` every frame for line-of-sight and obstacle detection. The original DDA raycast iterated over all tiles in the level (~44,000) for every step along the ray (~50 steps). With 10 enemies:

```
44,000 tiles × 50 steps × 10 enemies × 60 Hz = ~1.3 billion checks/second
```

Result: **6–7 FPS** with any enemies present.

**Fix**: Use the existing spatial hash (`tile_lookup`, chunk size 320 px) to only check the ~10–20 tiles near each ray step. Also increased step size from 1 px to 8 px.

**Result**:

| Metric | Before | After |
| --- | --- | --- |
| Tile checks per raycast | ~2,200,000 | 60–120 |
| Speedup | — | ~20,000× |
| Frame time (10 enemies) | ~150 ms | ~16 ms |
| FPS | 6–7 | 60 |

**Trade-off**: 8 px steps may miss obstacles narrower than 8 px. Acceptable for the game's tile grid (32 px tiles).

---

## O2 — Enemy physics sync removal (2025-12-23)

**File**: `entities/enemy_manager.py`

**Problem**: After the AI movement component wrote velocity to `enemy.physics.vx`, a `sync_to_physics()` call immediately overwrote it with `enemy.velocity_x` (which was 0). Enemies could not move.

**Fix**: Removed the redundant `sync_to_physics()` call. The movement component writes directly to physics; `sync_from_physics()` at the end of the update copies back to scalars for rendering.

**Result**: Enemy patrol, chase, and knockback all became functional.

---

## O3 — Tile render culling (2025-12-13)

**File**: `rendering/tile_loader.py` (or demo_game.py render loop)

**Problem**: The render loop iterated over all tiles in the megamap (40,000+ tiles for a 10-room world) every frame, even tiles 5 rooms away from the camera.

**Fix**: Culling pass — only render tiles whose world rect intersects the camera viewport.

**Result**: Tile render time dropped from single-digit FPS to 60 FPS in multi-room worlds.

---

## O4 — Conditional room boundaries (2025-12-13)

**File**: `systems/room_generation.py`

**Problem**: Every room was generated with solid walls on all 4 edges, physically blocking movement between adjacent rooms even when the world graph had them connected.

**Fix**: `_add_room_boundaries()` checks `room.neighbor_dirs` and only adds walls on edges that have no neighbor connection.

**Result**: Room traversal restored; no longer requires workarounds in the camera/collision systems.

---

## O5 — Hazard overlay caching

**File**: `rendering/hazard_renderer.py`

**Problem**: Hazard overlays (lava glow, poison mist, void darkness) were redrawn per-frame as filled surfaces with alpha blending. On rooms with many hazard tiles this was ~12 ms/frame.

**Fix**: Pre-render hazard overlay surfaces once on room load; composite cached surface each frame.

**Result**: Hazard render time 12.36 ms → 0.23 ms.

---

## O6–O10 — Miscellaneous surface and allocation optimizations

A batch of smaller optimizations made during the same period:

| ID | Area | Change | Benefit |
| --- | --- | --- | --- |
| O6 | Particle system | Pre-allocate particle pool; reuse slots | Reduced GC pressure during heavy combat |
| O7 | Sprite manager | Build flip-cache at load time for all player frames | No per-frame `pygame.transform.flip` calls |
| O8 | Collision system | Reuse single `pygame.Rect` point in raycast instead of creating new each step | Reduced allocation in hot path |
| O9 | HUD minimap | Cache minimap surface; only redraw on room change | Eliminated per-frame minimap full redraw |
| O10 | Autotiling | Cache tile variant selection per-tile on load; skip re-evaluation at runtime | Autotile lookup is O(1) per tile per frame |

---

## Cumulative result

| Metric | Before optimizations | After O1–O10 |
| --- | --- | --- |
| FPS (idle) | ~60 | ~129 |
| FPS (10 enemies) | 6–7 | ~60 |
| Hazard render | 12.36 ms | 0.23 ms |
| Raycast (per call) | ~36 ms | <1 ms |

Numbers from archive profiling session (`docs/archive/BUGFIX_PERFORMANCE_AND_MOVEMENT.md`, `docs/archive/TRAVERSAL_AND_PERFORMANCE_FIXES.md`).

---

## Frame profiler

A lightweight frame profiler is available in `utils/` (see `utils/__init__.py`). It is not wired to a UI display — results go to the logger. To enable, set `PROFILER_ENABLED = True` in the profiler config and check `user_data/logs/`.

---

## Guidelines for future work

- **Always query the spatial hash** (`tile_lookup`) rather than iterating `self.tiles` in any hot path
- **Cache surfaces** for anything that does not change every frame (overlays, minimaps, static HUD elements)
- **Pool objects** for frequently-spawned entities (particles, projectiles, pickups)
- **Profile before optimizing** — the raycast bug was only obvious because it crashed FPS to 6
- **Never add `sync_to_physics()` calls** unless there is a specific reason — physics writes should be direct
