package com.indieniinja.sim;

import com.indieniinja.network.PortalState;

/**
 * Server-side portal entity.
 * Portals are placed in the world by LevelLayout and included in every full snapshot.
 * The server checks proximity + ability gate; the client sends PORTAL_TRAVEL on E-key press.
 */
public final class SimPortal {

    public final String  portalId;
    public final String  portalType;       // "hub" | "mission"
    public final String  destinationId;
    public final float   x;
    public final float   y;
    public final int     width  = 64;
    public final int     height = 96;
    public boolean isActive = true;
    public float   pulseTimer = 0f;

    /** Ability required to enter this portal. Empty string = open to all. */
    public final String requiredAbility;

    public SimPortal(String id, String type, String destId, float x, float y, String requiredAbility) {
        this.portalId        = id;
        this.portalType      = type;
        this.destinationId   = destId;
        this.x               = x;
        this.y               = y;
        this.requiredAbility = requiredAbility != null ? requiredAbility : "";
    }

    /** Step animation timer. */
    public void step(float dt) {
        if (isActive) pulseTimer += dt * 2f;  // 2 oscillations/sec (matches Python)
    }

    /**
     * Returns true if the player is close enough to interact.
     * Interaction radius: 56px from portal centre.
     */
    public boolean canInteract(float px, float py) {
        float cx = x + width  * 0.5f;
        float cy = y + height * 0.5f;
        float dx = px - cx;
        float dy = py - cy;
        return (dx * dx + dy * dy) <= 56f * 56f;
    }

    /**
     * Returns true if the player has the required ability to travel through this portal.
     * An empty requiredAbility means the portal is always open.
     */
    public boolean canPlayerEnter(SimPlayer player) {
        if (requiredAbility.isEmpty()) return true;
        return player.unlockedAbilities.contains(requiredAbility);
    }

    public PortalState toState() {
        PortalState s = new PortalState();
        s.portalId        = portalId;
        s.portalType      = portalType;
        s.destinationId   = destinationId;
        s.x               = x;
        s.y               = y;
        s.width           = width;
        s.height          = height;
        s.isActive        = isActive;
        s.isLocked        = false;  // client derives from required_ability vs own abilities
        s.requiredAbility = requiredAbility;
        return s;
    }
}
