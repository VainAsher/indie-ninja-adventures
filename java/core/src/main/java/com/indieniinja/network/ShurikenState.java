package com.indieniinja.network;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Per-shuriken state broadcast in WorldSnapshot.
 * Java equivalent of Python mechanics/shuriken.py ShurikenProjectile wire fields.
 */
public final class ShurikenState {

    public String  shurikenId;
    public int     ownerSlot;
    public float   x, y;
    public float   vx;
    public boolean stuck;
    public boolean alive;

    public ShurikenState() {}

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("shuriken_id", shurikenId);
        m.put("owner_slot",  ownerSlot);
        m.put("x",           x);
        m.put("y",           y);
        m.put("vx",          vx);
        m.put("stuck",       stuck);
        m.put("alive",       alive);
        return m;
    }

    public static ShurikenState fromMap(Map<String, Object> m) {
        ShurikenState s = new ShurikenState();
        s.shurikenId = str(m, "shuriken_id", "");
        s.ownerSlot  = num(m, "owner_slot",  0);
        s.x          = flt(m, "x",           0f);
        s.y          = flt(m, "y",           0f);
        s.vx         = flt(m, "vx",          0f);
        s.stuck      = bool(m, "stuck");
        s.alive      = bool(m, "alive");
        return s;
    }

    private static String  str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static int     num(Map<String,Object> m, String k, int    d) { Object v=m.get(k); return v instanceof Number n?n.intValue():d; }
    private static boolean bool(Map<String,Object> m, String k)          { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static float   flt(Map<String,Object> m, String k, float  d) { Object v=m.get(k); return v instanceof Number n?n.floatValue():d; }
}
