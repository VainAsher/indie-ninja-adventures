package com.indieniinja.client;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class KeyBindingsTest {

    @Test
    void defaultsFollowGddKeyboardPreset() {
        KeyBindings keys = KeyBindings.defaults();
        assertEquals("LEFT", keys.describe("left"));
        assertEquals("RIGHT", keys.describe("right"));
        assertEquals("Z", keys.describe("jump"));
        assertEquals("X", keys.describe("attack"));
        assertEquals("A", keys.describe("stance_switch"));
        assertEquals("1", keys.describe("select_weapon_1"));
        assertEquals("2", keys.describe("select_weapon_2"));
        assertEquals("S", keys.describe("block"));
        assertEquals("D", keys.describe("teleport"));
        assertEquals("F", keys.describe("throw"));
        assertEquals("R", keys.describe("ninjutsu"));
        assertEquals("E", keys.describe("interact"));
        assertTrue(keys.sharesAnyKey("minimap", "fullmap"));
    }

    @Test
    void keybindingsBlockOverridesDefaults() {
        String json = """
            {
              "keybindings": {
                "attack": ["U"],
                "mission_menu": ["M"],
                "select_weapon_2": ["Y"],
                "minimap": ["Q"],
                "fullmap": ["N"]
              }
            }
            """;
        KeyBindings keys = KeyBindings.fromJsonString(json);
        assertEquals("U", keys.describe("attack"));
        assertEquals("M", keys.describe("mission_menu"));
        assertEquals("Y", keys.describe("select_weapon_2"));
        assertEquals("Q", keys.describe("minimap"));
        assertEquals("N", keys.describe("fullmap"));
        assertFalse(keys.sharesAnyKey("minimap", "fullmap"));
    }

    @Test
    void legacyKeyFieldsStillParse() {
        String json = """
            {
              "key_left": "a",
              "key_jump": "space",
              "key_dash": "shift",
              "key_crouch": "down"
            }
            """;
        KeyBindings keys = KeyBindings.fromJsonString(json);
        assertEquals("A", keys.describe("left"));
        assertEquals("SPACE", keys.describe("jump"));
        assertEquals("SHIFT", keys.describe("dash"));
        assertEquals("DOWN", keys.describe("crouch"));
    }
}
