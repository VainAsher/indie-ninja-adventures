package com.indieniinja.network;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InputCommandTest {

    @Test
    void toMapFromMapRoundTripKeepsWeaponSelectFlags() {
        InputCommand src = new InputCommand(9);
        src.stanceSwitch = true;
        src.selectWeapon1 = true;
        src.selectWeapon2 = false;

        InputCommand restored = InputCommand.fromMap(src.toMap());
        assertTrue(restored.stanceSwitch);
        assertTrue(restored.selectWeapon1);
        assertFalse(restored.selectWeapon2);
    }

    @Test
    void fromMapDefaultsWeaponSelectFlagsToFalseWhenMissing() {
        Map<String, Object> legacy = new LinkedHashMap<>();
        legacy.put("frame", 1);
        legacy.put("jump", true);
        legacy.put("stance_switch", false);

        InputCommand restored = InputCommand.fromMap(legacy);
        assertFalse(restored.selectWeapon1);
        assertFalse(restored.selectWeapon2);
    }
}
