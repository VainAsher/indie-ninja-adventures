package com.indieniinja.network;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Wire state for a single NPC entity.
 *
 * Sent in WorldSnapshot.npcs — always full list (not delta-encoded), because
 * NPCs are few, slow-changing, and the extra bytes are negligible.
 *
 * Java equivalent of Python entities/npc.py NPC dataclass fields that are
 * relevant to rendering and client-side interaction detection.
 */
public final class NPCState {

    public String  npcId;
    public String  npcType;        // e.g. "lore", "shop", "mission_giver", "tutorial", "siren"
    public float   x;
    public float   y;
    public int     facing;         // -1 = left, 1 = right
    public String  animState;      // "idle", "walk"
    public boolean isInteractable; // true when a player is within INTERACTION_RADIUS

    public NPCState() {}

    public static NPCState fromMap(Map<String, Object> m) {
        NPCState n = new NPCState();
        n.npcId          = str(m, "npc_id",         "");
        n.npcType        = str(m, "npc_type",        "lore");
        n.x              = num(m, "x",               0f);
        n.y              = num(m, "y",               0f);
        n.facing         = (int) num(m, "facing",    1f);
        n.animState      = str(m, "anim_state",      "idle");
        n.isInteractable = bool(m, "is_interactable");
        return n;
    }

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(7);
        m.put("npc_id",          npcId);
        m.put("npc_type",        npcType);
        m.put("x",               x);
        m.put("y",               y);
        m.put("facing",          facing);
        m.put("anim_state",      animState);
        m.put("is_interactable", isInteractable);
        return m;
    }

    private static float   num(Map<String,Object> m, String k, float  d) { Object v=m.get(k); return v instanceof Number n?n.floatValue():d; }
    private static boolean bool(Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static String  str(Map<String,Object> m, String k, String d)  { Object v=m.get(k); return v!=null?v.toString():d; }
}
