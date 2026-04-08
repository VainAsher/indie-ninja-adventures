package com.indieniinja.network;

import java.util.Map;

/**
 * Wire state for a horizontal oscillating moving platform.
 * Always sent on wire (not delta-encoded) — positional accuracy is critical.
 */
public final class MovingPlatformState {

    public String platformId;  // "mplat_{originX}_{originY}"
    public float  x;
    public float  y;
    public float  width;
    public float  height;

    public MovingPlatformState() {}

    public Map<String, Object> toMap() {
        return Map.of(
            "platform_id", platformId,
            "x",           x,
            "y",           y,
            "width",       width,
            "height",      height
        );
    }

    public static MovingPlatformState fromMap(Map<String, Object> m) {
        MovingPlatformState s = new MovingPlatformState();
        s.platformId = str(m, "platform_id", "");
        s.x          = flt(m, "x");
        s.y          = flt(m, "y");
        s.width      = flt(m, "width");
        s.height     = flt(m, "height");
        return s;
    }

    private static String str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static float  flt(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Number n?n.floatValue():0f; }
}
