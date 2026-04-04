package com.indieniinja.network;

import java.util.Map;

/** Authoritative enemy state — mirrors Python network/snapshots.py EnemyState. */
public final class EnemyState {

    public String  enemyId;
    public float   x, y, vx, vy;
    public int     hp;
    public String  aiState;       // "idle"|"patrol"|"chase"|"attack"|"dead"
    public boolean facingRight;

    public EnemyState() {}

    public Map<String, Object> toMap() {
        return Map.of(
            "enemy_id",    enemyId,
            "x",           x,
            "y",           y,
            "vx",          vx,
            "vy",          vy,
            "hp",          hp,
            "ai_state",    aiState,
            "facing_right",facingRight
        );
    }

    public static EnemyState fromMap(Map<String, Object> m) {
        EnemyState e = new EnemyState();
        e.enemyId    = str(m, "enemy_id", "");
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
