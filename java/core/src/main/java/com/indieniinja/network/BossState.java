package com.indieniinja.network;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Per-boss wire state broadcast inside WorldSnapshot.
 * Java equivalent of Python entities/boss.py Boss.to_dict().
 */
public final class BossState {

    public String  bossId;
    public String  bossType;
    public float   x, y;
    public int     hp;
    public int     maxHp;
    public String  aiState;
    public int     phase;
    public boolean facingRight;
    public boolean alive;

    public BossState() {}

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("boss_id",      bossId);
        m.put("boss_type",    bossType);
        m.put("x",            x);
        m.put("y",            y);
        m.put("hp",           hp);
        m.put("max_hp",       maxHp);
        m.put("ai_state",     aiState);
        m.put("phase",        phase);
        m.put("facing_right", facingRight);
        m.put("alive",        alive);
        return m;
    }

    @SuppressWarnings("unchecked")
    public static BossState fromMap(Map<?, ?> raw) {
        Map<String, Object> m = (Map<String, Object>) raw;
        BossState s = new BossState();
        s.bossId     = str(m, "boss_id",   "");
        s.bossType   = str(m, "boss_type", "forest_guardian");
        s.x          = flt(m, "x");
        s.y          = flt(m, "y");
        s.hp         = (int) num(m, "hp",      0L);
        s.maxHp      = (int) num(m, "max_hp",  1L);
        s.aiState    = str(m, "ai_state",  "idle");
        s.phase      = (int) num(m, "phase",   1L);
        s.facingRight = bool(m, "facing_right");
        s.alive       = bool(m, "alive");
        return s;
    }

    private static String  str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static long    num(Map<String,Object> m, String k, long   d) { Object v=m.get(k); return v instanceof Number n?n.longValue():d; }
    private static boolean bool(Map<String,Object> m, String k)          { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static float   flt(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Number n?n.floatValue():0f; }
}
