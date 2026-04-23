package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HeadlessManagerConstructorGuardTest {

    @Test
    void dialogueManagerDefaultConstructorIsHeadlessSafe() {
        DialogueManager manager = assertDoesNotThrow(DialogueManager::new);
        assertFalse(manager.isActive());
        assertFalse(manager.startDialogue("missing"));
    }

    @Test
    void missionManagerDefaultConstructorIsHeadlessSafe() {
        MissionManager manager = assertDoesNotThrow(() -> new MissionManager());
        assertTrue(manager.availableMissions(1).isEmpty());
        assertFalse(manager.isActive());
    }

    @Test
    void saveManagerListSlotsIsHeadlessSafe() {
        SaveManager.SlotInfo[] slots = assertDoesNotThrow(SaveManager::listSlots);
        assertEquals(SaveManager.MAX_SLOTS, slots.length);
        for (int i = 0; i < slots.length; i++) {
            assertEquals(i + 1, slots[i].slot());
            assertTrue(slots[i].isEmpty());
        }
    }
}
