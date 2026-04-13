package com.indieniinja.sim;

/**
 * Server-side shuriken projectile.
 * Java equivalent of Python mechanics/shuriken.py ShurikenProjectile.
 *
 * Spawned by GameSimulator for both player throws and enemy ranged attacks.
 * Moved each tick by GameSimulator.stepShurikens():
 *   1. Advance position by (vx, vy)
 *   2. Check tile collision via SpatialHash → stuck=true, stuckTimer=2s
 *   3. Check target AABB (enemy or player) → damage, stuck=true, stuckTimer=0.1s
 *   4. Decrement ttl each tick; remove when ttl<=0 or stuckTimer<=0
 */
public final class SimShuriken {

    public static final float W  = 12f;
    public static final float H  = 12f;

    public final String shurikenId;
    public final int    ownerSlot;      // player slot for player-thrown projectiles; negative for enemy projectiles
    public final boolean damagesPlayers;
    public final int     damage;

    public float x, y;
    public float vx, vy;

    public boolean alive       = true;
    public boolean stuck       = false;
    public float   stuckTimer  = 0f;
    public float   ttl         = 2.0f;   // seconds before despawn if not hitting anything

    public SimShuriken(String shurikenId, int ownerSlot,
                       float x, float y, float vx, float vy) {
        this(shurikenId, ownerSlot, x, y, vx, vy, false, 1);
    }

    public SimShuriken(String shurikenId, int ownerSlot,
                       float x, float y, float vx, float vy,
                       boolean damagesPlayers, int damage) {
        this.shurikenId = shurikenId;
        this.ownerSlot  = ownerSlot;
        this.x          = x;
        this.y          = y;
        this.vx         = vx;
        this.vy         = vy;
        this.damagesPlayers = damagesPlayers;
        this.damage         = Math.max(1, damage);
    }
}
