package com.indieniinja.network;

import java.util.Map;

/** Authoritative platform state — mirrors Python network/snapshots.py PlatformState. */
public final class PlatformState {

    public String platformId;    // "plat_{origin_x}_{origin_y}"
    public String state;         // "idle"|"triggered"|"falling"|"respawn"
    public float  posY;
    public float  timer;
    public float  vy;

    public PlatformState() {}

    public Map<String, Object> toMap() {
        return Map.of(
            "platform_id", platformId,
            "state",       state,
            "pos_y",       posY,
            "timer",       timer,
            "vy",          vy
        );
    }

    public static PlatformState fromMap(Map<String, Object> m) {
        PlatformState p = new PlatformState();
        p.platformId = str(m, "platform_id", "");
        p.state      = str(m, "state", "idle");
        p.posY       = flt(m, "pos_y");
        p.timer      = flt(m, "timer");
        p.vy         = flt(m, "vy");
        return p;
    }

    private static String str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static float  flt(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Number n?n.floatValue():0f; }
}
