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
    }
}
