package com.indieniinja.network;

import java.util.Map;

/** Authoritative pickup state — mirrors Python network/snapshots.py PickupState. */
public final class PickupState {

    public String  pickupId;
    public float   x, y;
    public String  pickupType;
    public boolean alive;

    public PickupState() {}

    public Map<String, Object> toMap() {
        return Map.of(
            "pickup_id",   pickupId,
            "x",           x,
            "y",           y,
            "pickup_type", pickupType,
            "alive",       alive
        );
    }

    public static PickupState fromMap(Map<String, Object> m) {
        PickupState p = new PickupState();
        p.pickupId   = str(m, "pickup_id", "");
        p.x          = flt(m, "x");
        p.y          = flt(m, "y");
        p.pickupType = str(m, "pickup_type", "");
        p.alive      = bool(m, "alive");
        return p;
    }

    private static String  str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static boolean bool(Map<String,Object> m, String k)          { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static float   flt(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Number n?n.floatValue():0f; }
}
