package com.indieniinja.sim;

/**
 * Falling platform state machine.
 * Java equivalent of Python game_simulator.py _update_falling_platform().
 *
 * State transitions (mirror Python exactly):
 *   idle      → triggered (player steps on)
 *   triggered → idle      (player steps off before delay)
 *   triggered → falling   (after TRIGGER_DELAY seconds)
 *   falling   → respawn   (after DROP_DISTANCE pixels fallen)
 *   respawn   → idle      (after RESPAWN_DELAY seconds)
 */
public final class FallingPlatform {

    // Constants — mirror Python game_simulator.py literals exactly
    public static final float TRIGGER_DELAY  = 0.35f;
    public static final float RESPAWN_DELAY  = 2.5f;
    public static final float DROP_DISTANCE  = 32 * 12;     // 384 px
    public static final float GRAVITY        = 1800.0f;     // px/s²
    public static final float MAX_SPEED      = 800.0f;      // px/s terminal
    public static final int   CARRY_TOLERANCE = 2;          // px

    public enum State { IDLE, TRIGGERED, FALLING, RESPAWN }

    public final String platformId;   // "plat_{ox}_{oy}"
    public final float  originX;
    public final float  originY;
    public final int    width;
    public final int    height;

    // Mutable sim state
    public State state   = State.IDLE;
    public float posY;      // current Y (starts at originY)
    public float vy       = 0f;
    public float timer    = 0f;
    public boolean active  = true;   // collision active when idle/triggered
    public boolean visible = true;

    public FallingPlatform(String platformId, float originX, float originY, int width, int height) {
        this.platformId = platformId;
        this.originX    = originX;
        this.originY    = originY;
        this.posY       = originY;
        this.width      = width;
        this.height     = height;
    }

    /**
     * Advance state machine by one fixed tick.
     * @param dt        fixed timestep (1/60 s)
     * @param supported true if a player is currently resting on this platform
     */
    public void step(float dt, boolean supported) {
        switch (state) {
            case IDLE -> {
                active  = true;
                visible = true;
                if (supported) {
                    state = State.TRIGGERED;
                    timer = 0f;
                }
            }
            case TRIGGERED -> {
                active  = true;
                visible = true;
                if (!supported) {
                    state = State.IDLE;
                    timer = 0f;
                } else {
                    timer += dt;
                    if (timer >= TRIGGER_DELAY) {
                        state  = State.FALLING;
                        timer  = 0f;
                        vy     = 0f;
                        active = false;
                    }
                }
            }
            case FALLING -> {
                active  = false;
                visible = true;
                vy   = Math.min(vy + GRAVITY * dt, MAX_SPEED);
                posY += vy * dt;
                if (posY - originY >= DROP_DISTANCE) {
                    state   = State.RESPAWN;
                    timer   = 0f;
                    visible = false;
                    posY    = originY;   // reset for snapshot
                }
            }
            case RESPAWN -> {
                active  = false;
                visible = false;
                timer  += dt;
                if (timer >= RESPAWN_DELAY) {
                    state   = State.IDLE;
                    timer   = 0f;
                    vy      = 0f;
                    active  = true;
                    visible = true;
                }
            }
        }
    }

    /** Returns the wire state string matching Python's platform["state"]. */
    public String wireState() {
        return state.name().toLowerCase();
    }

    /**
     * True if the given entity AABB is resting on this platform.
     * Mirrors Python GameSimulator._entity_on_platform().
     */
    public boolean entityOnPlatform(float ex, float ey, int ew, int eh, boolean onGround) {
        if (!onGround) return false;
        float eRight = ex + ew, platLeft = originX, platRight = originX + width;
        if (eRight <= platLeft || ex >= platRight) return false;
        float gap = posY - (ey + eh);
        return gap >= -1 && gap <= CARRY_TOLERANCE;
    }
}
