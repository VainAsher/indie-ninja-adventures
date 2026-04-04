package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsConstants;

/**
 * Server-side pickup simulation entity.
 * Java equivalent of the runtime fields read by Python's GameSimulator.get_snapshot().
 *
 * Pickups are static (no physics movement); authoritative collection is checked
 * by the GameSimulator each tick — a player AABB overlapping the pickup
 * marks it alive=false, included in the WorldSnapshot, then removed from the list.
 */
public final class SimPickup {

    public final String  pickupId;
    public final String  pickupType;   // "health_potion", "coin", "item"
    public final float   x, y;
    public final int     width  = PhysicsConstants.TILE_SIZE;
    public final int     height = PhysicsConstants.TILE_SIZE;
    public       boolean alive  = true;

    // Lifetime counter — pickups despawn after 30 seconds (1800 ticks at 60 Hz)
    public int  ticksRemaining = 1800;

    public SimPickup(String pickupId, String pickupType, float x, float y) {
        this.pickupId   = pickupId;
        this.pickupType = pickupType;
        this.x          = x;
        this.y          = y;
    }

    /** AABB overlap test — used for authoritative collection check. */
    public boolean overlaps(float px, float py, int pw, int ph) {
        return px < x + width  && px + pw > x
            && py < y + height && py + ph > y;
    }

    /** Advance lifetime; marks dead if expired. */
    public void tick() {
        if (!alive) return;
        if (--ticksRemaining <= 0) alive = false;
    }
}
