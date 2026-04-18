package com.indieniinja.physics;

import com.indieniinja.core.Entity;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.TickEvent;

import java.util.List;

import static com.indieniinja.physics.PhysicsConstants.*;

/**
 * Physics system — applies gravity and integrates velocity.
 *
 * Java equivalent of Python's systems/physics_system.py PhysicsSystem.
 * Subscribed to TickEvent at priority 60 (runs before collision at 45).
 *
 * Hot path: zero allocations per tick. All work is direct float field access
 * on PhysicsState objects — JIT-compiled to register operations after warm-up.
 */
public final class PhysicsSystem {

    /** Live entities managed externally (e.g., by EntityManager). */
    private final List<Entity> entities;

    public PhysicsSystem(EventBus bus, List<Entity> entities) {
        this.entities = entities;
        // Priority 60 — runs before CollisionSystem (priority 45)
        bus.subscribe(TickEvent.class, this::onTick, 60);
    }

    // ── Tick handler ─────────────────────────────────────────────────────────

    private void onTick(TickEvent event) {
        for (Entity entity : entities) {
            PhysicsState p = entity.physics;
            if (p == null) continue;
            applyGravity(p);
            // Integrate velocity → position
            p.x += p.vx;
            p.y += p.vy;
        }
    }

    // ── Gravity ───────────────────────────────────────────────────────────────

    /**
     * Apply gravity with state-based multipliers.
     * Mirrors Python physics_system.py _apply_gravity() exactly.
     */
    private static void applyGravity(PhysicsState p) {
        if (p.onGround) return;      // collision system zeroes vy on landing
        if (p.gravityFrozen) return; // traversal override (climb/ledge hang) holds position

        // Base gravity
        p.vy += GRAVITY;

        // Falling faster than rising (more responsive feel)
        if (p.vy > 0) {
            p.vy += GRAVITY * (FALL_GRAVITY_MULT - 1.0f);
        }

        // Jump cut: player released jump mid-air
        if (p.jumpCutActive && p.vy < 0) {
            p.vy += GRAVITY * (JUMP_CUT_MULT - 1.0f);
        }

        // Fast fall: down held while airborne
        if (p.fastFallActive && p.vy > 0) {
            p.vy += GRAVITY * (FAST_FALL_MULT - 1.0f);
        }

        // Terminal velocity cap
        if (p.vy > MAX_FALL_SPEED) {
            p.vy = MAX_FALL_SPEED;
        }
    }
}
