package com.indieniinja.network;

import java.util.Map;

/** Authoritative platform state — mirrors Python network/snapshots.py PlatformState. */
public final class PlatformState {

    public String platformId;    // "plat_{origin_x}_{origin_y}"
    public String state;         // "idle"|"triggered"|"falling"|"respawn"
    public float  posY;
    public float  timer;
    public float  vy;
    /** World-space X of the platform's left edge (= originX, constant). */
    public float  originX;
    /** Platform dimensions in pixels. */
    public int    width;
    public int    height;
    /** False while in "respawn" state — client should skip rendering. */
    public boolean visible = true;

    public PlatformState() {}

    public Map<String, Object> toMap() {
        java.util.Map<String,Object> m = new java.util.LinkedHashMap<>();
        m.put("platform_id", platformId);
        m.put("state",       state);
        m.put("pos_y",       posY);
        m.put("timer",       timer);
        m.put("vy",          vy);
        m.put("origin_x",    originX);
        m.put("width",       width);
        m.put("height",      height);
        m.put("visible",     visible);
        return m;
    }

    public static PlatformState fromMap(Map<String, Object> m) {
        PlatformState p = new PlatformState();
        p.platformId = str(m, "platform_id", "");
        p.state      = str(m, "state", "idle");
        p.posY       = flt(m, "pos_y");
        p.timer      = flt(m, "timer");
        p.vy         = flt(m, "vy");
        p.originX    = flt(m, "origin_x");
        Object w = m.get("width");  p.width  = w instanceof Number n ? n.intValue() : 96;
        Object h = m.get("height"); p.height = h instanceof Number n ? n.intValue() : 32;
        Object v = m.get("visible"); p.visible = !(v instanceof Boolean b) || b;
        return p;
    }

    private static String str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static float  flt(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Number n?n.floatValue():0f; }
}
