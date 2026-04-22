package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsConstants;

/**
 * Server-side pickup simulation entity.
 *
 * Pickups are static (no physics movement); authoritative collection is checked
 * by the GameSimulator each tick — a player AABB overlapping the pickup
 * marks it alive=false, included in the WorldSnapshot, then removed from the list.
 *
 * Room pickups (spawned from layout) use a PickupSlot and have a short randomised
 * lifetime (30–60 s) before respawning at the same position.
 * Loot drops from enemies use the default 45-second lifetime with slotIdx = -1.
 */
public final class SimPickup {

    public final String  pickupId;
    public final String  pickupType;
    public final float   x, y;
    public final int     width  = PhysicsConstants.TILE_SIZE;
    public final int     height = PhysicsConstants.TILE_SIZE;
    public       boolean alive  = true;

    /**
     * Index into GameSimulator.pickupSlots, or -1 for loot drops that do not respawn.
     * When this pickup expires or is collected, the simulator starts the slot's cooldown.
     */
    public final int slotIdx;
    /** Mission/objective pickups are persistent and never expire on a lifetime timer. */
    public final boolean persistent;
    /**
     * Player slot allowed to collect this pickup.
     * -1 means unscoped (collectible by any player).
     */
    public final int missionOwnerSlot;

    // Lifetime counter — ticks at 60 Hz. Default 2700 (~45 s) for loot drops.
    public int ticksRemaining;

    /** Loot-drop constructor — no respawn slot, default 45-second lifetime. */
    public SimPickup(String pickupId, String pickupType, float x, float y) {
        this(pickupId, pickupType, x, y, -1, 2700, false, -1);
    }

    /** Full constructor used by the room-pickup factory. */
    public SimPickup(String pickupId, String pickupType, float x, float y,
                     int slotIdx, int ticksRemaining) {
        this(pickupId, pickupType, x, y, slotIdx, ticksRemaining, false, -1);
    }

    /** Full constructor with explicit persistence control. */
    public SimPickup(String pickupId, String pickupType, float x, float y,
                     int slotIdx, int ticksRemaining, boolean persistent) {
        this(pickupId, pickupType, x, y, slotIdx, ticksRemaining, persistent, -1);
    }

    /** Full constructor with explicit persistence and mission-owner scoping. */
    public SimPickup(String pickupId, String pickupType, float x, float y,
                     int slotIdx, int ticksRemaining, boolean persistent, int missionOwnerSlot) {
        this.pickupId        = pickupId;
        this.pickupType      = pickupType;
        this.x               = x;
        this.y               = y;
        this.slotIdx         = slotIdx;
        this.ticksRemaining  = ticksRemaining;
        this.persistent      = persistent;
        this.missionOwnerSlot = missionOwnerSlot;
    }

    /** AABB overlap test — used for authoritative collection check. */
    public boolean overlaps(float px, float py, int pw, int ph) {
        return px < x + width  && px + pw > x
            && py < y + height && py + ph > y;
    }

    /**
     * True when this pickup is collectible by the provided player slot.
     * Mission-scoped pickups are reserved for one slot; all others are global.
     */
    public boolean canBeCollectedBy(int playerSlot) {
        return missionOwnerSlot < 0 || missionOwnerSlot == playerSlot;
    }

    /** Advance lifetime; marks dead if expired. */
    public void tick() {
        if (!alive) return;
        if (persistent) return;
        if (--ticksRemaining <= 0) alive = false;
    }
}
