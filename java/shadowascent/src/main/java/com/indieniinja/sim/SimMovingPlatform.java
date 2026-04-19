package com.indieniinja.sim;

/**
 * Horizontal oscillating platform.
 *
 * Moves left↔right between [originX, originX + rangeX] at a fixed speed.
 * Players standing on top ride the platform (their vx is nudged each tick by
 * the platform's velocity via GameSimulator.applyPlatformRiding()).
 *
 * Python parity: entities/moving_platform.py MovingPlatform.
 */
public final class SimMovingPlatform {

    public final String id;
    /** World-pixel position of top-left corner. */
    public float x;
    public float y;
    /** Platform dimensions in pixels. */
    public final float width;
    public final float height;
    /** Left boundary (world-px, inclusive). */
    public final float leftBound;
    /** Right boundary (world-px) — x+width reaches at most this. */
    public final float rightBound;
    /** Speed in pixels per tick (positive = moving right). */
    public float vx;

    public SimMovingPlatform(String id, float x, float y,
                              float width, float height,
                              float leftBound, float rightBound,
                              float speed) {
        this.id         = id;
        this.x          = x;
        this.y          = y;
        this.width      = width;
        this.height     = height;
        this.leftBound  = leftBound;
        this.rightBound = rightBound;
        this.vx         = speed;
    }

    /** Advance one physics tick; bounce off bounds. */
    public void step() {
        x += vx;
        if (x <= leftBound) {
            x  = leftBound;
            vx = Math.abs(vx);
        } else if (x + width >= rightBound) {
            x  = rightBound - width;
            vx = -Math.abs(vx);
        }
    }

    /** True if world-pixel point (px, py) is standing on top of this platform. */
    public boolean isStandingOn(float px, float py, float pw, float ph) {
        // Player bottom must be at or just above platform top
        float playerBottom = py + ph;
        float platTop      = y;
        if (playerBottom < platTop - 4f || playerBottom > platTop + 6f) return false;
        // Horizontal overlap
        return px + pw > x + 2f && px < x + width - 2f;
    }
}
