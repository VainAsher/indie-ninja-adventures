package com.indieniinja.physics;

import com.indieniinja.core.Entity;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.TickEvent;
import com.indieniinja.world.WorldGenerator;

import java.util.List;

import static com.indieniinja.physics.PhysicsConstants.*;

/**
 * AABB collision detection and resolution with spatial hashing.
 *
 * Java equivalent of Python's systems/collision_system.py CollisionSystem.
 * Subscribed to TickEvent at priority 45 (after PhysicsSystem at 60,
 * before mechanics at 40).
 *
 * Key behaviours preserved from Python:
 *  - Swept (sub-step) collision for speeds above SWEPT_COLLISION_THRESHOLD (8.0)
 *  - One-way platform collision (only from above)
 *  - Corner smoothing for tall-player edge catches
 *  - Per-frame collision flag reset before resolution
 *
 * Zero allocation hot path: no new objects created during collision resolution.
 */
public final class CollisionSystem {

    private final List<Entity> entities;
    private SpatialHash spatialHash;

    /**
     * Dynamic tile rects for moving/falling platforms.
     * GameSimulator repopulates this list before each tick.
     * Kept as a simple ArrayList — platforms are few (~5-20 per room).
     */
    private final java.util.ArrayList<TileRect> dynamicTiles = new java.util.ArrayList<>(32);

    public CollisionSystem(EventBus bus, List<Entity> entities, SpatialHash spatialHash) {
        this.entities    = entities;
        this.spatialHash = spatialHash;
        // Priority 45 — after physics (60), before mechanics (40)
        bus.subscribe(TickEvent.class, this::onTick, 45);
    }

    /** Hot-swap the spatial hash when the player crosses a room boundary. */
    public void setSpatialHash(SpatialHash hash) { this.spatialHash = hash; }

    /**
     * Replace the dynamic tile list with current platform positions.
     * Called by GameSimulator.stepPlatforms() before clock.stepOne() fires.
     */
    public void setDynamicTiles(java.util.List<TileRect> tiles) {
        dynamicTiles.clear();
        dynamicTiles.addAll(tiles);
    }

    // ── Tick handler ─────────────────────────────────────────────────────────

    private void onTick(TickEvent event) {
        for (Entity entity : entities) {
            PhysicsState p = entity.physics;
            if (p == null) continue;
            p.resetCollisionFlags();
            resolveEntity(p);
        }
    }

    // ── Per-entity resolution ─────────────────────────────────────────────────

    private void resolveEntity(PhysicsState p) {
        float speed = (float) Math.sqrt(p.vx * p.vx + p.vy * p.vy);

        if (speed > SWEPT_COLLISION_THRESHOLD) {
            // Sub-step sweep to prevent tunnelling (e.g. during dash at 16 px/tick)
            int steps = (int) Math.ceil(speed / SWEPT_STEP_SIZE);
            float sx = p.vx / steps;
            float sy = p.vy / steps;
            // Undo the velocity integration done by PhysicsSystem so we can
            // re-apply it incrementally. (Physics ran first at priority 60.)
            p.x -= p.vx;
            p.y -= p.vy;
            for (int i = 0; i < steps; i++) {
                p.x += sx;
                resolveHorizontal(p);
                p.y += sy;
                resolveVertical(p);
            }
        } else {
            // Single-step (most common case — no new objects allocated)
            resolveHorizontal(p);
            resolveVertical(p);
        }
    }

    // ── Horizontal resolution ─────────────────────────────────────────────────

    private void resolveHorizontal(PhysicsState p) {
        List<TileRect> candidates = spatialHash.candidates(p.x, p.y, p.width, p.height);
        resolveHorizontalList(p, candidates);
        resolveHorizontalList(p, dynamicTiles);
    }

    private void resolveHorizontalList(PhysicsState p, List<TileRect> candidates) {
        for (TileRect tile : candidates) {
            if (tile.isPlatform()) continue;  // platforms: vertical only
            if (tile.tileType() == WorldGenerator.WATER) continue;  // water: passable
            if (!tile.overlaps(p.x, p.y, p.width, p.height)) continue;

            // Determine collision axis by comparing intersection depths on X and Y.
            // If horizontal overlap < vertical overlap → wall hit; otherwise floor/ceiling.
            // Mirrors Python collision_system.py _check_horizontal_collisions:
            //   overlap_x = min(right,tile.right) - max(left,tile.left)
            //   overlap_y = min(bottom,tile.bottom) - max(top,tile.top)
            //   is_horizontal = overlap_x < overlap_y
            float overlapX = Math.min(p.x + p.width,  tile.x() + tile.w()) - Math.max(p.x, tile.x());
            float overlapY = Math.min(p.y + p.height, tile.y() + tile.h()) - Math.max(p.y, tile.y());
            if (overlapY <= overlapX) continue;  // floor/ceiling contact — not a wall hit

            float overlapLeft  = (p.x + p.width) - tile.x();
            float overlapRight = (tile.x() + tile.w()) - p.x;

            if (p.vx > 0 && overlapLeft < overlapRight) {
                // Moving right — push left
                p.x = tile.x() - p.width;
                p.vx = 0;
                p.onWall  = true;
                p.wallDir = 1;
            } else if (p.vx < 0 && overlapRight < overlapLeft) {
                // Moving left — push right
                p.x = tile.x() + tile.w();
                p.vx = 0;
                p.onWall  = true;
                p.wallDir = -1;
            }
        }
    }

    // ── Vertical resolution ───────────────────────────────────────────────────

    private void resolveVertical(PhysicsState p) {
        List<TileRect> candidates = spatialHash.candidates(p.x, p.y, p.width, p.height);
        resolveVerticalList(p, candidates);
        resolveVerticalList(p, dynamicTiles);
    }

    private void resolveVerticalList(PhysicsState p, List<TileRect> candidates) {
        for (TileRect tile : candidates) {
            if (!tile.overlaps(p.x, p.y, p.width, p.height)) continue;

            // ── Hazard zone detection (WATER is passable; mark flag and skip solid resolve) ──
            if (tile.tileType() == WorldGenerator.WATER) {
                p.inWater = true;
                // Water: dampen velocity and slow fall, but do not block movement
                p.vx *= 0.82f;
                p.vy  = Math.min(p.vy, 2.0f);  // cap fall speed in water
                continue;
            }

            float entityBottom = p.y + p.height;
            float entityTop    = p.y;
            float overlapTop    = entityBottom - tile.y();
            float overlapBottom = (tile.y() + tile.h()) - entityTop;

            if (tile.isPlatform()) {
                // One-way: only collide from above, only when moving downward
                if (p.vy >= 0 && overlapTop >= 0 && overlapTop <= PLATFORM_GRACE_PIXELS + p.vy + 1) {
                    p.y        = tile.y() - p.height;
                    p.vy       = 0;
                    p.onGround = true;
                }
            } else {
                if (p.vy >= 0 && overlapTop >= 0 && overlapTop < overlapBottom) {
                    // Landing on top of solid tile
                    p.y        = tile.y() - p.height;
                    p.vy       = 0;
                    p.onGround = true;

                    // Hazard surface flags
                    if (tile.tileType() == WorldGenerator.ICE)  p.onIce  = true;
                    if (tile.tileType() == WorldGenerator.LAVA) p.onLava = true;

                    if (overlapTop > 0.5f) applyCornerSmoothing(p, tile);

                } else if (p.vy < 0 && overlapBottom < overlapTop) {
                    // Hitting ceiling (including lava ceiling = damage)
                    p.y  = tile.y() + tile.h();
                    p.vy = 0;
                    if (tile.tileType() == WorldGenerator.LAVA) p.onLava = true;
                }
            }
        }
    }

    // ── Corner smoothing ──────────────────────────────────────────────────────

    /**
     * If the player lands on a tile corner with a small horizontal overlap,
     * nudge them horizontally past the edge so they don't get stuck.
     * Mirrors Python collision_system.py corner smoothing logic.
     */
    private static void applyCornerSmoothing(PhysicsState p, TileRect tile) {
        float leftOverlap  = (p.x + p.width) - tile.x();
        float rightOverlap = (tile.x() + tile.w()) - p.x;

        if (leftOverlap > 0 && leftOverlap >= CORNER_MIN_OVERLAP && leftOverlap <= CORNER_MAX_OVERLAP) {
            p.x -= leftOverlap;
        } else if (rightOverlap > 0 && rightOverlap >= CORNER_MIN_OVERLAP && rightOverlap <= CORNER_MAX_OVERLAP) {
            p.x += rightOverlap;
        }
    }
}
