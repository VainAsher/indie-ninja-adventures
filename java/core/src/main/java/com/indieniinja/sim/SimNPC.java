package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsState;

/**
 * Server-side NPC entity.
 *
 * Simulates the patrol movement and player-facing logic from Python's
 * entities/npc.py NPC._update_patrol() and NPC.update().
 *
 * NPCs now carry a full PhysicsState so they are processed by PhysicsSystem
 * and CollisionSystem (gravity, tile collision) just like ground enemies.
 * Edge detection prevents them from walking off ledges.
 */
public final class SimNPC {

    // ── Python parity constants ───────────────────────────────────────────────
    /** Patrol speed in px/tick (Python: patrol_speed=30 px/s ÷ 60 Hz). */
    public static final float PATROL_SPEED       = 30f / 60f;
    /** Proximity for the "interactable" flag (Python: interaction_radius=48). */
    public static final float INTERACTION_RADIUS = 48f;
    /** Wait time at each patrol waypoint in seconds (Python: patrol_wait_time=2.0). */
    private static final float PATROL_WAIT       = 2.0f;
    private static final float TICKS_PER_SEC     = 60f;

    // ── Fixed identity ────────────────────────────────────────────────────────
    public final String id;
    public final String type;   // e.g. "lore", "shop", "mission_giver", "tutorial", "siren"

    /**
     * Physics state — position, velocity, collision flags.
     * Gravity and tile collision are applied by PhysicsSystem/CollisionSystem
     * each tick via EntityManager, exactly like ground enemies.
     */
    public final PhysicsState physics;

    // ── Convenience aliases (read physics.x/y; kept for existing callers) ─────
    /** @deprecated Use {@link #physics}.x directly. */
    public float x() { return physics.x; }
    /** @deprecated Use {@link #physics}.y directly. */
    public float y() { return physics.y; }

    // ── Mutable state ─────────────────────────────────────────────────────────
    public int     facing        = 1;   // 1 = right, -1 = left
    public String  animState     = "idle";
    public boolean isInteractable;

    // ── Patrol ────────────────────────────────────────────────────────────────
    public final float patrolMinX;
    public final float patrolMaxX;
    private float patrolWaitTimer = 0f;

    public SimNPC(String id, String type, float x, float y,
                  int width, int height,
                  float patrolMinX, float patrolMaxX) {
        this.id         = id;
        this.type       = type;
        this.physics    = new PhysicsState(x, y, width, height);
        this.patrolMinX = patrolMinX;
        this.patrolMaxX = patrolMaxX;
    }

    /**
     * Advance patrol/facing logic one 60 Hz tick.
     * Physics (gravity + collision) are handled externally by EntityManager
     * before this is called; {@link #physics}.onGround is already updated.
     *
     * @param nearestPlayerX world-X of the nearest player centre,
     *                       or {@code Float.NaN} if no players present
     * @param edgeAhead      true if there is no solid floor tile one step
     *                       ahead in the current facing direction — caller
     *                       computes this from the SpatialHash
     */
    public void step(float nearestPlayerX, boolean edgeAhead) {
        float npcCx = physics.x + physics.width * 0.5f;

        // Face the nearest player when they're close (Python: NPC.update)
        isInteractable = false;
        if (!Float.isNaN(nearestPlayerX)) {
            float dist = Math.abs(nearestPlayerX - npcCx);
            if (dist < INTERACTION_RADIUS * 2f) {
                facing = (nearestPlayerX < npcCx) ? -1 : 1;
            }
            isInteractable = dist < INTERACTION_RADIUS;
        }

        // Patrol movement (Python: NPC._update_patrol)
        if (patrolMinX >= patrolMaxX) {
            animState = "idle";
            return;
        }
        if (patrolWaitTimer > 0f) {
            patrolWaitTimer -= 1f / TICKS_PER_SEC;
            animState = "idle";
            return;
        }

        // Turn around at patrol bounds, walls, or ledge edges
        boolean atRightBound = npcCx >= patrolMaxX;
        boolean atLeftBound  = npcCx <= patrolMinX;
        boolean wallBlocked  = physics.onWall && physics.wallDir == facing;

        if (facing == 1 && (atRightBound || edgeAhead || wallBlocked)) {
            facing = -1;
            patrolWaitTimer = PATROL_WAIT;
        } else if (facing == -1 && (atLeftBound || edgeAhead || wallBlocked)) {
            facing = 1;
            patrolWaitTimer = PATROL_WAIT;
        }

        // Apply horizontal velocity (CollisionSystem will handle wall resolution)
        physics.vx = facing * PATROL_SPEED;
        physics.x += physics.vx;
        animState = "walk";
    }
}
