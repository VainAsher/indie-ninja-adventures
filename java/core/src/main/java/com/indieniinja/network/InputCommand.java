package com.indieniinja.network;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Input command — Java equivalent of Python network/commands.py InputCommand.
 *
 * Key ordering in toMap() must match Python's to_dict() exactly for protocol parity.
 * All boolean fields default to false (neutral / no input).
 */
public final class InputCommand {

    public int     frame;
    public boolean up, down, left, right;
    public boolean jump, dash, crouch;
    public boolean toggleProc, cycleCamera;
    public boolean attack, throwShuriken, teleport, ninjutsu;
    public boolean interact, inventory, consumable;
    public boolean minimap, fullmap, controlsOverlay, debugOverlay;
    public boolean slowWalk, menuConfirm, menuBack;
    /** Toggle Yin/Yang stance (client just-pressed key). */
    public boolean stanceSwitch;

    public InputCommand() {}

    public InputCommand(int frame) {
        this.frame = frame;
    }

    /** Neutral (no input) command for a given frame. */
    public static InputCommand neutral(int frame) {
        return new InputCommand(frame);
    }

    /**
     * Serialize to Map with exactly the same key order as Python's to_dict().
     * Used when building WORLD_STATE player entries.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(32);
        m.put("frame",            frame);
        m.put("up",               up);
        m.put("down",             down);
        m.put("left",             left);
        m.put("right",            right);
        m.put("jump",             jump);
        m.put("dash",             dash);
        m.put("crouch",           crouch);
        m.put("toggle_proc",      toggleProc);
        m.put("cycle_camera",     cycleCamera);
        m.put("attack",           attack);
        m.put("throw",            throwShuriken);
        m.put("teleport",         teleport);
        m.put("ninjutsu",         ninjutsu);
        m.put("interact",         interact);
        m.put("inventory",        inventory);
        m.put("consumable",       consumable);
        m.put("minimap",          minimap);
        m.put("fullmap",          fullmap);
        m.put("controls_overlay", controlsOverlay);
        m.put("debug_overlay",    debugOverlay);
        m.put("slow_walk",        slowWalk);
        m.put("menu_confirm",     menuConfirm);
        m.put("menu_back",        menuBack);
        m.put("stance_switch",    stanceSwitch);
        return m;
    }

    /** Deserialize from a payload map received over the wire. */
    public static InputCommand fromMap(Map<String, Object> m) {
        InputCommand c = new InputCommand();
        c.frame           = num(m, "frame", 0);
        c.up              = bool(m, "up");
        c.down            = bool(m, "down");
        c.left            = bool(m, "left");
        c.right           = bool(m, "right");
        c.jump            = bool(m, "jump");
        c.dash            = bool(m, "dash");
        c.crouch          = bool(m, "crouch");
        c.toggleProc      = bool(m, "toggle_proc");
        c.cycleCamera     = bool(m, "cycle_camera");
        c.attack          = bool(m, "attack");
        c.throwShuriken   = bool(m, "throw");
        c.teleport        = bool(m, "teleport");
        c.ninjutsu        = bool(m, "ninjutsu");
        c.interact        = bool(m, "interact");
        c.inventory       = bool(m, "inventory");
        c.consumable      = bool(m, "consumable");
        c.minimap         = bool(m, "minimap");
        c.fullmap         = bool(m, "fullmap");
        c.controlsOverlay = bool(m, "controls_overlay");
        c.debugOverlay    = bool(m, "debug_overlay");
        c.slowWalk        = bool(m, "slow_walk");
        c.menuConfirm     = bool(m, "menu_confirm");
        c.menuBack        = bool(m, "menu_back");
        c.stanceSwitch    = bool(m, "stance_switch");
        return c;
    }

    private static boolean bool(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v instanceof Boolean b ? b : Boolean.parseBoolean(String.valueOf(v));
    }

    private static int num(Map<String, Object> m, String key, int def) {
        Object v = m.get(key);
        return v instanceof Number n ? n.intValue() : def;
    }
}
