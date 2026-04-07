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
    public boolean prevTeleport = false;

    // Ground state from previous tick (for coyote-time detection)
    public boolean wasOnGround  = false;

    // ── Combat state ─────────────────────────────────────────────────────────
    // Melee attack (J key / left mouse)
    public boolean isAttacking      = false;
    public int     attackActiveTicks = 0;    // ticks remaining in active hitbox window
    public float   attackCooldown   = 0f;    // seconds until next attack allowed
    public boolean prevAttack       = false; // rising-edge detection
    public boolean pendingShuriken  = false; // set by applyPlayerInput; consumed by GameSimulator

    // Shuriken (K key)
    public int     shurikenAmmo     = 5;     // matches Python default ammo count
    public float   throwCooldown    = 0f;    // seconds until next throw allowed
    public boolean isThrowing       = false; // for "throw" anim state
    public boolean prevThrow        = false; // rising-edge detection

    // Combat constants (match Python combat_mechanic.py / shuriken.py)
    public static final int   MELEE_DAMAGE         = 1;
    public static final int   MELEE_ACTIVE_TICKS   = 8;    // frames hitbox is live
    public static final float MELEE_COOLDOWN       = 0.4f; // seconds
    public static final float MELEE_REACH          = 48f;  // px forward from player center
    public static final float MELEE_HEIGHT         = 40f;  // hitbox height
    public static final float SHURIKEN_SPEED       = 10f;  // px/tick (600px/s ÷ 60)
    public static final float SHURIKEN_COOLDOWN    = 0.35f;
    public static final int   SHURIKEN_DAMAGE      = 1;
    public static final float SHURIKEN_STUN        = 0.4f;
    public static final int   SHURIKEN_MAX_AMMO    = 5;

    // ── Teleport state ───────────────────────────────────────────────────────
    public float   teleportCooldown  = 0f;    // seconds until next teleport
    public boolean isTeleporting     = false; // brief invuln window after teleport
    public float   teleportInvulnTimer = 0f;

    public static final float TELEPORT_RANGE    = 256f; // px — 8 tiles, matches Python
    public static final float TELEPORT_COOLDOWN = 3.0f; // seconds
    public static final float TELEPORT_INVULN   = 0.25f;// seconds of invulnerability after

    // ── Wall jump state ──────────────────────────────────────────────────────
    public float   wallCoyoteTimer = 0f;  // brief window to wall-jump after leaving wall
    public int     lastWallDir     = 0;   // last wall direction (for wall-jump when onWall=false)

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
