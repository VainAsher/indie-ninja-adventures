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
