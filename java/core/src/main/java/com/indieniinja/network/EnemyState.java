package com.indieniinja.network;

import java.util.Map;

/** Authoritative enemy state — mirrors Python network/snapshots.py EnemyState. */
public final class EnemyState {

    public String  enemyId;
    public String  enemyType;     // "goblin"|"bat"|"slime"|"skeleton"|"wolf"
    public float   x, y, vx, vy;
    public int     hp;
    public String  aiState;       // "idle"|"patrol"|"chase"|"attack"|"dead"
    public boolean facingRight;

    public EnemyState() {}

    public Map<String, Object> toMap() {
        java.util.LinkedHashMap<String,Object> m = new java.util.LinkedHashMap<>();
        m.put("enemy_id",     enemyId);
        m.put("enemy_type",   enemyType != null ? enemyType : "goblin");
        m.put("x",            x);
        m.put("y",            y);
        m.put("vx",           vx);
        m.put("vy",           vy);
        m.put("hp",           hp);
        m.put("ai_state",     aiState);
        m.put("facing_right", facingRight);
        return m;
    }

    public static EnemyState fromMap(Map<String, Object> m) {
        EnemyState e = new EnemyState();
        e.enemyId    = str(m, "enemy_id", "");
        e.enemyType  = str(m, "enemy_type", "goblin");
        e.x          = flt(m, "x");
        e.y          = flt(m, "y");
        e.vx         = flt(m, "vx");
        e.vy         = flt(m, "vy");
        e.hp         = num(m, "hp", 0);
        e.aiState    = str(m, "ai_state", "idle");
        e.facingRight = bool(m, "facing_right");
        return e;
    }

    private static String  str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static int     num(Map<String,Object> m, String k, int    d) { Object v=m.get(k); return v instanceof Number n?n.intValue():d; }
    private static boolean bool(Map<String,Object> m, String k)          { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static float   flt(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Number n?n.floatValue():0f; }
}
