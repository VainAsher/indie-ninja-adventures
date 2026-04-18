package com.indieniinja.physics;

/**
 * Mutable physics state for one entity.
 * Direct Java equivalent of Python's core/state.py PhysicsState.
 *
 * Uses plain float fields — no boxing — for zero-allocation hot-path access.
 */
public final class PhysicsState {

    // Position (pixels)
    public float x, y;

    // Velocity (pixels per tick at 60 Hz)
    public float vx, vy;

    // Collision flags — reset each tick before collision resolution
    public boolean onGround;
    public boolean onWall;
    public int     wallDir;     // -1 = left wall, +1 = right wall, 0 = none

    // Gravity modifier flags (set by mechanics, read by physics system)
    public boolean jumpCutActive;   // jump released mid-air → extra gravity
    public boolean fastFallActive;  // down held while airborne
    public boolean gravityFrozen;   // traversal override (climb/ledge) → skip gravity this tick

    // Hazard tile contact flags — reset each tick by CollisionSystem before resolution
    public boolean inWater;         // inside a WATER tile — reduced speed, no dash
    public boolean onIce;           // standing on an ICE tile — near-zero friction
    public boolean onLava;          // contact with LAVA tile — 1 HP/tick damage event
    public boolean inGas;           // inside a GAS tile — mild drag, no solid block

    /**
     * Ability bitmask — gates medium effects in CollisionSystem.
     * Bit constants are defined in {@link PhysicsConstants}: ABILITY_WATER_WALK,
     * ABILITY_ICE_GRIP, ABILITY_GAS_RESIST.
     * Set once at spawn (or when abilities are granted/revoked).
     */
    public int abilityFlags;

    // Entity dimensions (set once at spawn)
    public int width;
    public int height;

    public PhysicsState(float x, float y, int width, int height) {
        this.x = x;
        this.y = y;
        this.width  = width;
        this.height = height;
    }

    /** Reset per-frame collision flags before the collision pass. */
    public void resetCollisionFlags() {
        onGround = false;
        onWall   = false;
        wallDir  = 0;
        inWater  = false;
        onIce    = false;
        onLava   = false;
        inGas    = false;
    }
}
