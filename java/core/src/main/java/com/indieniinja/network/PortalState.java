package com.indieniinja.network;

import java.util.Map;
import java.util.LinkedHashMap;

/**
 * Wire representation of a portal entity.
 * Portals are always sent on the full snapshot (not delta-encoded) as part of WorldSnapshot.
 * Client uses this to render pulsing portals and send PORTAL_TRAVEL on E-key interaction.
 */
public final class PortalState {

    public String  portalId;
    public String  portalType;       // "hub" | "mission"
    public String  destinationId;    // hub id or mission id
    public float   x;
    public float   y;
    public int     width  = 64;
    public int     height = 96;
    public boolean isActive;
    public boolean isLocked;
    public String  requiredAbility;  // ability name needed to enter, or "" for open portals
    public float   pulseTimer;       // server-side for determinism; client re-derives

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("portal_id",        portalId);
        m.put("portal_type",      portalType);
        m.put("destination_id",   destinationId);
        m.put("x",                x);
        m.put("y",                y);
        m.put("width",            width);
        m.put("height",           height);
        m.put("is_active",        isActive);
        m.put("is_locked",        isLocked);
        m.put("required_ability", requiredAbility != null ? requiredAbility : "");
        return m;
    }

    @SuppressWarnings("unchecked")
    public static PortalState fromMap(Object raw) {
        if (!(raw instanceof Map<?,?> m)) return null;
        Map<String, Object> map = (Map<String, Object>) m;
        PortalState p = new PortalState();
        p.portalId        = str(map, "portal_id",      "");
        p.portalType      = str(map, "portal_type",    "hub");
        p.destinationId   = str(map, "destination_id", "");
        p.x               = num(map, "x", 0f);
        p.y               = num(map, "y", 0f);
        p.width           = (int) num(map, "width",  64f);
        p.height          = (int) num(map, "height", 96f);
        p.isActive        = bool(map, "is_active");
        p.isLocked        = bool(map, "is_locked");
        p.requiredAbility = str(map, "required_ability", "");
        return p;
    }

    private static String  str(Map<String, Object> m, String k, String d)  { Object v = m.get(k); return v != null ? v.toString() : d; }
    private static float   num(Map<String, Object> m, String k, float  d)  { Object v = m.get(k); return v instanceof Number n ? n.floatValue() : d; }
    private static boolean bool(Map<String, Object> m, String k)            { Object v = m.get(k); return v instanceof Boolean b && b; }
}
