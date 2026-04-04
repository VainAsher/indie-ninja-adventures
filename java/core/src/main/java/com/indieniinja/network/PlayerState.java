package com.indieniinja.network;

import java.util.List;
import java.util.Map;

/**
 * Per-player state in a multiplayer frame.
 * Java equivalent of Python network/snapshots.py PlayerState.
 * Key order matches Python's to_dict() exactly.
 */
public final class PlayerState {

    public String  playerId;
    public int     slot;
    public float   posX, posY;
    public float   velX, velY;
    public int     health;
    public int     facing;       // 1 = right, -1 = left
    public boolean isDead;
    public String  animState;    // "" = use inference

    public PlayerState() {}

    public Map<String, Object> toMap() {
        return Map.of(
            "player_id", playerId,
            "slot",      slot,
            "pos",       List.of(posX, posY),
            "vel",       List.of(velX, velY),
            "health",    health,
            "facing",    facing,
            "is_dead",   isDead,
            "anim_state",animState != null ? animState : ""
        );
    }

    @SuppressWarnings("unchecked")
    public static PlayerState fromMap(Map<String, Object> m) {
        PlayerState s = new PlayerState();
        s.playerId  = str(m, "player_id", "");
        s.slot      = num(m, "slot", 0);
        List<Object> pos = (List<Object>) m.getOrDefault("pos", List.of(0, 0));
        List<Object> vel = (List<Object>) m.getOrDefault("vel", List.of(0, 0));
        s.posX      = flt(pos.get(0));
        s.posY      = flt(pos.get(1));
        s.velX      = flt(vel.get(0));
        s.velY      = flt(vel.get(1));
        s.health    = num(m, "health", 5);
        s.facing    = num(m, "facing", 1);
        s.isDead    = bool(m, "is_dead");
        s.animState = str(m, "anim_state", "");
        return s;
    }

    private static String  str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static int     num(Map<String,Object> m, String k, int    d) { Object v=m.get(k); return v instanceof Number n?n.intValue():d; }
    private static boolean bool(Map<String,Object> m, String k)          { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static float   flt(Object v) { return v instanceof Number n ? n.floatValue() : 0f; }
}
