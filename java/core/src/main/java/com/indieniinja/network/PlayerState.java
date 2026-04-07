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
    public int     facing;             // 1 = right, -1 = left
    public boolean isDead;
    public String  animState;          // "" = use inference
    public float   wallSlideStamina;   // 0.0–3.0; for HUD stamina bar
    public boolean isWallSliding;
    public boolean teleportPhaseMode;  // cursor is active (hold-to-phase mode)
    public float   teleportCursorX;    // ghost cursor world X (only valid when phaseMode)
    public float   teleportCursorY;    // ghost cursor world Y
    public float   stamina;            // 0–30; drains while running, regens otherwise
    public float   mana;               // 0–30; regens passively, spent on ninjutsu
    public boolean ninjutsuCasting;    // brief casting anim active
    /** Player inventory — always sent (not delta-encoded). */
    public InventoryState inventory = new InventoryState();

    // ── Progression ───────────────────────────────────────────────────────────
    public int experience = 0;
    public int level      = 1;
    /** Unlocked ability wire strings (e.g. "double_jump", "dash"). */
    public java.util.List<String> abilities = new java.util.ArrayList<>();

    public PlayerState() {}

    public Map<String, Object> toMap() {
        java.util.LinkedHashMap<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("player_id",          playerId);
        m.put("slot",               slot);
        m.put("pos",                List.of(posX, posY));
        m.put("vel",                List.of(velX, velY));
        m.put("health",             health);
        m.put("facing",             facing);
        m.put("is_dead",            isDead);
        m.put("anim_state",         animState != null ? animState : "");
        m.put("wall_slide_stamina",   wallSlideStamina);
        m.put("is_wall_sliding",      isWallSliding);
        m.put("teleport_phase_mode",  teleportPhaseMode);
        m.put("teleport_cursor_x",    teleportCursorX);
        m.put("teleport_cursor_y",    teleportCursorY);
        m.put("stamina",              stamina);
        m.put("mana",                 mana);
        m.put("ninjutsu_casting",     ninjutsuCasting);
        m.put("inventory",            inventory != null ? inventory.toMap() : new InventoryState().toMap());
        m.put("experience",           experience);
        m.put("level",                level);
        m.put("abilities",            abilities != null ? abilities : java.util.List.of());
        return m;
    }

    @SuppressWarnings("unchecked")
    public static PlayerState fromMap(Map<String, Object> m) {
        PlayerState s = new PlayerState();
        s.playerId          = str(m, "player_id", "");
        s.slot              = num(m, "slot", 0);
        List<Object> pos = (List<Object>) m.getOrDefault("pos", List.of(0, 0));
        List<Object> vel = (List<Object>) m.getOrDefault("vel", List.of(0, 0));
        s.posX              = flt(pos.get(0));
        s.posY              = flt(pos.get(1));
        s.velX              = flt(vel.get(0));
        s.velY              = flt(vel.get(1));
        s.health            = num(m, "health", 5);
        s.facing            = num(m, "facing", 1);
        s.isDead            = bool(m, "is_dead");
        s.animState         = str(m, "anim_state", "");
        s.wallSlideStamina    = flt2(m, "wall_slide_stamina", 3.0f);
        s.isWallSliding       = bool(m, "is_wall_sliding");
        s.teleportPhaseMode   = bool(m, "teleport_phase_mode");
        s.teleportCursorX     = flt2(m, "teleport_cursor_x", 0f);
        s.teleportCursorY     = flt2(m, "teleport_cursor_y", 0f);
        s.stamina             = flt2(m, "stamina",   30f);
        s.mana                = flt2(m, "mana",      30f);
        s.ninjutsuCasting     = bool(m, "ninjutsu_casting");
        Object inv = m.get("inventory");
        s.inventory = (inv instanceof java.util.Map<?,?> im)
            ? InventoryState.fromMap((java.util.Map<String,Object>) im)
            : new InventoryState();
        s.experience = num(m, "experience", 0);
        s.level      = num(m, "level",      1);
        Object abilRaw = m.get("abilities");
        if (abilRaw instanceof java.util.List<?> al)
            for (Object a : al) s.abilities.add(a.toString());
        return s;
    }

    private static String  str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
    private static int     num(Map<String,Object> m, String k, int    d) { Object v=m.get(k); return v instanceof Number n?n.intValue():d; }
    private static boolean bool(Map<String,Object> m, String k)          { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static float   flt(Object v)                                  { return v instanceof Number n ? n.floatValue() : 0f; }
    private static float   flt2(Map<String,Object> m, String k, float d) { Object v=m.get(k); return v instanceof Number n ? n.floatValue() : d; }
}
