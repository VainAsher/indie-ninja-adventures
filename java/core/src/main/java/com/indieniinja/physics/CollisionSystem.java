package com.indieniinja.physics;

import com.indieniinja.core.Entity;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.TickEvent;

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
    private final SpatialHash  spatialHash;

    public CollisionSystem(EventBus bus, List<Entity> entities, SpatialHash spatialHash) {
        this.entities    = entities;
        this.spatialHash = spatialHash;
        // Priority 45 — after physics (60), before mechanics (40)
        bus.subscribe(TickEvent.class, this::onTick, 45);
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
        for (TileRect tile : candidates) {
            if (tile.isPlatform()) continue;  // platforms: vertical only
            if (!tile.overlaps(p.x, p.y, p.width, p.height)) continue;

            // Skip tiles the entity is only grazing from above — this happens every
            // tick now that gravity is always applied (+0.4px before correction).
            // A penetration < 2px from the top means it's a floor contact, not a wall.
            float topPenetration = (p.y + p.height) - tile.y();
            if (topPenetration >= 0 && topPenetration < 2f && p.y + p.height <= tile.y() + tile.h()) continue;

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
        for (TileRect tile : candidates) {
            if (!tile.overlaps(p.x, p.y, p.width, p.height)) continue;

            float entityBottom = p.y + p.height;
            float entityTop    = p.y;

            float overlapTop    = entityBottom - tile.y();
            float overlapBottom = (tile.y() + tile.h()) - entityTop;

            if (tile.isPlatform()) {
                // One-way: only collide from above, only when moving downward
                if (p.vy >= 0 && overlapTop >= 0 && overlapTop <= PLATFORM_GRACE_PIXELS + p.vy + 1) {
                    p.y      = tile.y() - p.height;
                    p.vy     = 0;
                    p.onGround = true;
                }
            } else {
                if (p.vy >= 0 && overlapTop > 0 && overlapTop < overlapBottom) {
                    // Landing on top of solid tile
                    p.y        = tile.y() - p.height;
                    p.vy       = 0;
                    p.onGround = true;

                    // Corner smoothing: if player clips a corner horizontally,
                    // nudge them past the corner instead of stopping them.
                    applyCornerSmoothing(p, tile);

                } else if (p.vy < 0 && overlapBottom < overlapTop) {
                    // Hitting ceiling
                    p.y  = tile.y() + tile.h();
                    p.vy = 0;
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
