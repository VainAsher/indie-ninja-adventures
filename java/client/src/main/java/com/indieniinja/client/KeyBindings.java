package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Runtime keybinding table for launcher-distributed settings.
 *
 * Supports:
 * - defaults aligned to GDD 10.3.13 keyboard preset
 * - optional settings override via user_data/settings/settings.json
 * - legacy fallback fields (key_left, key_right, key_jump, key_dash, key_crouch)
 */
public final class KeyBindings {

    private static final Logger log = LoggerFactory.getLogger(KeyBindings.class);

    private static final String ACTION_LEFT = "left";
    private static final String ACTION_RIGHT = "right";
    private static final String ACTION_UP = "up";
    private static final String ACTION_DOWN = "down";
    private static final String ACTION_JUMP = "jump";
    private static final String ACTION_DASH = "dash";
    private static final String ACTION_CROUCH = "crouch";
    private static final String ACTION_SLOW_WALK = "slow_walk";
    private static final String ACTION_ATTACK = "attack";
    private static final String ACTION_BLOCK = "block";
    private static final String ACTION_THROW = "throw";
    private static final String ACTION_TRAVERSAL = "teleport";
    private static final String ACTION_ECHO = "ninjutsu";
    private static final String ACTION_STANCE = "stance_switch";
    private static final String ACTION_INTERACT = "interact";
    private static final String ACTION_INVENTORY = "inventory";
    private static final String ACTION_CONSUMABLE = "consumable";
    private static final String ACTION_MINIMAP = "minimap";
    private static final String ACTION_FULLMAP = "fullmap";
    private static final String ACTION_CONTROLS_OVERLAY = "controls_overlay";
    private static final String ACTION_DEBUG_OVERLAY = "debug_overlay";
    private static final String ACTION_CYCLE_CAMERA = "cycle_camera";
    private static final String ACTION_TOGGLE_PROC = "toggle_proc";
    private static final String ACTION_MENU_CONFIRM = "menu_confirm";
    private static final String ACTION_MENU_BACK = "menu_back";
    private static final String ACTION_MISSION_MENU = "mission_menu";
    private static final String ACTION_TOGGLE_HITBOXES = "toggle_hitboxes";

    private final Map<String, int[]> bindings = new LinkedHashMap<>();

    private KeyBindings() {
        applyDefaults();
    }

    public static KeyBindings defaults() {
        return new KeyBindings();
    }

    public static KeyBindings fromJsonString(String jsonText) {
        KeyBindings kb = new KeyBindings();
        kb.applySettingsJson(jsonText);
        return kb;
    }

    public static KeyBindings load(FileHandle settingsFile) {
        KeyBindings kb = new KeyBindings();
        if (settingsFile == null || !settingsFile.exists()) return kb;
        try {
            String json = settingsFile.readString("UTF-8");
            kb.applySettingsJson(json);
        } catch (Exception ex) {
            log.warn("[Controls] failed to load settings from {} (using defaults): {}",
                settingsFile.path(), ex.toString());
        }
        return kb;
    }

    public boolean isHeld(String action) {
        if (Gdx.input == null) return false;
        int[] codes = bindings.get(action);
        if (codes == null) return false;
        for (int code : codes) if (Gdx.input.isKeyPressed(code)) return true;
        return false;
    }

    public boolean isJustPressed(String action) {
        if (Gdx.input == null) return false;
        int[] codes = bindings.get(action);
        if (codes == null) return false;
        for (int code : codes) if (Gdx.input.isKeyJustPressed(code)) return true;
        return false;
    }

    public boolean sharesAnyKey(String actionA, String actionB) {
        int[] a = bindings.get(actionA);
        int[] b = bindings.get(actionB);
        if (a == null || b == null) return false;
        for (int x : a) {
            for (int y : b) {
                if (x == y) return true;
            }
        }
        return false;
    }

    public String[] getNames(String action) {
        int[] codes = bindings.get(action);
        if (codes == null || codes.length == 0) return new String[0];
        String[] out = new String[codes.length];
        for (int i = 0; i < codes.length; i++) {
            String raw = Input.Keys.toString(codes[i]);
            out[i] = prettify(raw);
        }
        return out;
    }

    public String describe(String action) {
        String[] names = getNames(action);
        if (names.length == 0) return "UNBOUND";
        return String.join("/", dedupe(names));
    }

    public String controlPresetSummary() {
        return "move=" + describe(ACTION_LEFT) + "/" + describe(ACTION_RIGHT)
            + " jump=" + describe(ACTION_JUMP)
            + " attack=" + describe(ACTION_ATTACK)
            + " dash=" + describe(ACTION_DASH)
            + " stance=" + describe(ACTION_STANCE)
            + " guard=" + describe(ACTION_BLOCK)
            + " traversal=" + describe(ACTION_TRAVERSAL)
            + " throw=" + describe(ACTION_THROW)
            + " echo=" + describe(ACTION_ECHO)
            + " interact=" + describe(ACTION_INTERACT)
            + " map=" + describe(ACTION_MINIMAP) + "(tap-quick/hold-full)";
    }

    private void applyDefaults() {
        bind(ACTION_LEFT, "LEFT");
        bind(ACTION_RIGHT, "RIGHT");
        bind(ACTION_UP, "UP");
        bind(ACTION_DOWN, "DOWN");
        bind(ACTION_JUMP, "Z");
        bind(ACTION_DASH, "C");
        bind(ACTION_CROUCH, "DOWN");
        bind(ACTION_SLOW_WALK, "SHIFT_LEFT", "SHIFT_RIGHT");
        bind(ACTION_ATTACK, "X");
        bind(ACTION_BLOCK, "S");
        bind(ACTION_THROW, "F");
        bind(ACTION_TRAVERSAL, "D");
        bind(ACTION_ECHO, "R");
        bind(ACTION_STANCE, "A");
        bind(ACTION_INTERACT, "E");
        bind(ACTION_INVENTORY, "I");
        bind(ACTION_CONSUMABLE, "Q");
        bind(ACTION_MINIMAP, "TAB");
        bind(ACTION_FULLMAP, "TAB");
        bind(ACTION_CONTROLS_OVERLAY, "F1");
        bind(ACTION_DEBUG_OVERLAY, "F3");
        bind(ACTION_CYCLE_CAMERA, "V");
        bind(ACTION_TOGGLE_PROC, "P");
        bind(ACTION_MENU_CONFIRM, "ENTER");
        bind(ACTION_MENU_BACK, "ESCAPE");
        bind(ACTION_MISSION_MENU, "O");
        bind(ACTION_TOGGLE_HITBOXES, "H");
    }

    private void applySettingsJson(String jsonText) {
        if (jsonText == null || jsonText.isBlank()) return;
        JsonValue root;
        try {
            root = new JsonReader().parse(jsonText);
        } catch (Exception ex) {
            log.warn("[Controls] malformed settings json, keeping defaults: {}", ex.toString());
            return;
        }

        JsonValue kbObj = root.get("keybindings");
        if (kbObj != null && kbObj.isObject()) {
            for (JsonValue child = kbObj.child; child != null; child = child.next) {
                List<String> names = readNames(child);
                if (!names.isEmpty()) bindFromSettings(child.name, names);
            }
        }

        applyLegacyFallback(root);
    }

    private void applyLegacyFallback(JsonValue root) {
        Map<String, String> legacy = Map.of(
            "key_left", ACTION_LEFT,
            "key_right", ACTION_RIGHT,
            "key_jump", ACTION_JUMP,
            "key_dash", ACTION_DASH,
            "key_crouch", ACTION_CROUCH
        );
        for (Map.Entry<String, String> e : legacy.entrySet()) {
            JsonValue v = root.get(e.getKey());
            if (v == null || v.isNull()) continue;
            String raw = v.isString() ? v.asString() : String.valueOf(v);
            if (raw == null || raw.isBlank()) continue;
            bindFromSettings(e.getValue(), List.of(raw));
        }
    }

    private static List<String> readNames(JsonValue value) {
        List<String> out = new ArrayList<>();
        if (value == null || value.isNull()) return out;
        if (value.isString()) {
            out.add(value.asString());
            return out;
        }
        if (!value.isArray()) return out;
        for (JsonValue item = value.child; item != null; item = item.next) {
            if (item != null && item.isString()) out.add(item.asString());
        }
        return out;
    }

    private void bind(String action, String... names) {
        bindFromSettings(action, Arrays.asList(names));
    }

    private void bindFromSettings(String action, List<String> names) {
        if (action == null || action.isBlank() || names == null || names.isEmpty()) return;
        List<Integer> resolved = new ArrayList<>();
        for (String rawName : names) {
            int code = resolveCode(rawName);
            if (code < 0) {
                log.warn("[Controls] unknown key '{}' for action '{}'", rawName, action);
                continue;
            }
            resolved.add(code);
        }
        if (resolved.isEmpty()) return;
        int[] arr = resolved.stream().mapToInt(Integer::intValue).toArray();
        bindings.put(action, arr);
    }

    private static int resolveCode(String raw) {
        if (raw == null) return -1;
        String n = raw.trim().toUpperCase(Locale.ROOT)
            .replace('-', '_')
            .replace(' ', '_');
        if (n.isEmpty()) return -1;
        n = normalizeAlias(n);
        try {
            java.lang.reflect.Field f = Input.Keys.class.getField(n);
            return f.getInt(null);
        } catch (Exception ignored) {
            // fall through to secondary lookup
        }
        try {
            int code = Input.Keys.valueOf(n);
            if (code != -1) return code;
        } catch (Exception ignored) {
            // invalid key
        }
        return -1;
    }

    private static String normalizeAlias(String n) {
        if (n.length() == 1) {
            char c = n.charAt(0);
            if (c >= '0' && c <= '9') return "NUM_" + c;
            if (c >= 'A' && c <= 'Z') return String.valueOf(c);
        }
        if (n.startsWith("DIGIT_") && n.length() == 7) {
            char c = n.charAt(6);
            if (c >= '0' && c <= '9') return "NUM_" + c;
        }
        return switch (n) {
            case "ESC" -> "ESCAPE";
            case "RETURN" -> "ENTER";
            case "SPACEBAR" -> "SPACE";
            case "CTRL" -> "CONTROL_LEFT";
            case "CONTROL" -> "CONTROL_LEFT";
            case "SHIFT" -> "SHIFT_LEFT";
            case "ALT" -> "ALT_LEFT";
            default -> n;
        };
    }

    private static String prettify(String raw) {
        if (raw == null || raw.isBlank()) return "UNBOUND";
        String upper = raw.toUpperCase(Locale.ROOT);
        return switch (upper) {
            case "ESCAPE" -> "ESC";
            case "LEFT SHIFT", "RIGHT SHIFT", "L-SHIFT", "R-SHIFT" -> "SHIFT";
            case "LEFT CONTROL", "RIGHT CONTROL", "L-CONTROL", "R-CONTROL" -> "CTRL";
            case "LEFT ALT", "RIGHT ALT", "L-ALT", "R-ALT" -> "ALT";
            case "PAGE UP" -> "PGUP";
            case "PAGE DOWN" -> "PGDN";
            case "UP", "DOWN", "LEFT", "RIGHT", "SPACE", "TAB", "ENTER" -> upper;
            default -> upper;
        };
    }

    private static String[] dedupe(String[] names) {
        Set<String> set = new LinkedHashSet<>(Arrays.asList(names));
        return set.toArray(new String[0]);
    }
}
