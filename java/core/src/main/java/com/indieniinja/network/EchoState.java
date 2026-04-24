package com.indieniinja.network;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Wire-format state for a server-side echo replay entity (M6 Echo system).
 *
 * An echo is a ghost of a player's last 10 seconds of input, replayed as a
 * transparent phantom sprite. It is spawned from an echo_trigger NPC interaction
 * and advances to unlock echo_door puzzle gates.
 */
public final class EchoState {

    /** Unique echo ID — format: "<hubId>_echo_<seq>". */
    public String  echoId      = "";
    /** Slot of the player whose input buffer sourced this echo. */
    public int     ownerSlot   = 0;
    /** World-space position (left edge of AABB, same coordinate space as PlayerState). */
    public float   x           = 0f;
    public float   y           = 0f;
    /** Facing direction: 1 = right, -1 = left. */
    public int     facing      = 1;
    /** Current animation state string — used to pick the correct sprite frame. */
    public String  animState   = "idle";
    /** Weapon state string: "unarmed" | "sword" | "pistol". */
    public String  weaponState = "unarmed";
    /** False once the echo replay is complete or has been recalled. */
    public boolean active      = true;
    /** Stance variant at spawn: "silent" (Yin) | "riot" (Yang) | "resonant" (Flow). */
    public String  echoType    = "silent";

    public EchoState() {}

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(9);
        m.put("echo_id",      echoId);
        m.put("owner_slot",   ownerSlot);
        m.put("x",            x);
        m.put("y",            y);
        m.put("facing",       facing);
        m.put("anim_state",   animState);
        m.put("weapon_state", weaponState);
        m.put("active",       active);
        m.put("echo_type",    echoType != null ? echoType : "silent");
        return m;
    }

    public static EchoState fromMap(Object raw) {
        if (!(raw instanceof Map<?, ?> map)) return null;
        EchoState s = new EchoState();
        s.echoId      = str(map, "echo_id",      "");
        s.ownerSlot   = (int) num(map, "owner_slot",   0);
        s.x           = flt(map, "x",             0f);
        s.y           = flt(map, "y",             0f);
        s.facing      = (int) num(map, "facing",        1);
        s.animState   = str(map, "anim_state",   "idle");
        s.weaponState = str(map, "weapon_state", "unarmed");
        s.active      = bool(map, "active",       true);
        s.echoType    = str(map, "echo_type",    "silent");
        return s;
    }

    private static String  str(Map<?,?> m, String k, String d)  { Object v=m.get(k); return v!=null?v.toString():d; }
    private static long    num(Map<?,?> m, String k, long d)     { Object v=m.get(k); return v instanceof Number n?n.longValue():d; }
    private static float   flt(Map<?,?> m, String k, float d)   { Object v=m.get(k); return v instanceof Number n?n.floatValue():d; }
    private static boolean bool(Map<?,?> m, String k, boolean d) { Object v=m.get(k); return v instanceof Boolean b?b:d; }
}
