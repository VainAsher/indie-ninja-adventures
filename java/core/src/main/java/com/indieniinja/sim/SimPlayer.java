package com.indieniinja.sim;

import com.indieniinja.network.InputCommand;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.physics.PhysicsState;

/**
 * Server-side player simulation state.
 *
 * Mirrors the subset of Python's Player/PlayerState that the server needs
 * for authoritative simulation: physics, health, facing, and animation.
 * The server does NOT run the full mechanics pipeline (jump, dash, etc.) in
 * Phase B — movement remains client-authoritative (positions from INPUT).
 * This struct records them so the snapshot builder can read them.
 *
 * Phase C will drive these from the full Java mechanics pipeline.
 */
public final class SimPlayer {

    public final String playerId;
    public final int    slot;

    // Physics — updated from INPUT messages (client-authoritative in Phase B)
    public final PhysicsState physics;

    // State
    public int     health;
    public int     maxHealth = 5;
    public int     facing    = 1;   // 1=right, -1=left
    public boolean isDead    = false;
    public String  animState = "";

    // Invincibility frames after taking damage (ticks)
    public int invincibilityTicks = 0;

    // ── Advanced movement mechanics state ────────────────────────────────────
    // Dash
    public float   dashTimer    = 0f;    // seconds remaining while dash is active
    public float   dashCooldown = 0f;    // seconds until next dash is allowed
    public boolean isDashing    = false;

    // Jump
    public int     jumpCount    = 0;     // jumps consumed (0=grounded, 1=first, 2=double)
    public float   coyoteTimer  = 0f;    // seconds remaining to jump after walking off edge
    public float   jumpBuffer   = 0f;    // seconds remaining from a buffered jump press

    // Previous-tick input state for rising-edge detection
    public boolean prevJump     = false;
    public boolean prevDash     = false;

    // Ground state from previous tick (for coyote-time detection)
    public boolean wasOnGround  = false;

    // ── Wall slide mechanic state ────────────────────────────────────────────
    // Mirrors Python mechanics/wall_slide.py WallSlideMechanic
    public float   wallSlideStamina        = WALL_SLIDE_MAX_STAMINA;
    public boolean isWallSliding           = false;
    public boolean awaitGroundAfterExhaust = false;
    public int     exhaustDetachFrames     = 0;   // nudge off wall for N ticks after exhaust

    // Wall slide constants (match Python WallSlideMechanic)
    public static final float WALL_SLIDE_SPEED        = 3.0f;
    public static final float WALL_SLIDE_MAX_STAMINA  = 3.0f;
    public static final float WALL_SLIDE_REGEN_RATE   = 3.0f / 2.0f;  // full in 2s
    public static final float WALL_SLIDE_MIN_STAMINA  = 0.3f;
    public static final float WALL_SLIDE_EXHAUST_THRESH  = 0.5f;
    public static final float WALL_SLIDE_EXHAUST_PENALTY = 0.25f;
    public static final float WALL_SLIDE_DRAIN_MULT      = 1.6f;
    public static final float WALL_FRICTION_SPEED        = 6.0f;

    // Input — written by Netty I/O thread, read by sim thread via AtomicRef in PlayerRecord
    public InputCommand latestInput = InputCommand.neutral(0);

    public SimPlayer(String playerId, int slot, float spawnX, float spawnY) {
        this.playerId = playerId;
        this.slot     = slot;
        this.physics  = new PhysicsState(
            spawnX, spawnY,
            PhysicsConstants.PLAYER_WIDTH,
            PhysicsConstants.PLAYER_HEIGHT
        );
        this.health = maxHealth;
    }

    public boolean isAlive() {
        return health > 0 && !isDead;
    }

    /** Apply damage; set isDead flag if health reaches 0. */
    public void takeDamage(int dmg) {
        if (invincibilityTicks > 0) return;
        health = Math.max(0, health - dmg);
        if (health <= 0) isDead = true;
        invincibilityTicks = 60;  // 1 second invincibility at 60 Hz
    }

    /** Called each tick; decrements invincibility timer. */
    public void tickInvincibility() {
        if (invincibilityTicks > 0) invincibilityTicks--;
    }
}
