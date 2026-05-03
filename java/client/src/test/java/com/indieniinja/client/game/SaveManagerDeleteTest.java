package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SaveManagerDeleteTest {

    @Test
    void deleteSlot_invalidIndex_throwsIllegalArgument() {
        assertThrows(IllegalArgumentException.class, () -> SaveManager.deleteSlot(0));
        assertThrows(IllegalArgumentException.class, () -> SaveManager.deleteSlot(SaveManager.MAX_SLOTS + 1));
        assertThrows(IllegalArgumentException.class, () -> SaveManager.deleteSlot(-1));
    }

    @Test
    void deleteSlot_noGdx_returnsFalse() {
        // Gdx.files is null in the test JVM — deleteSlot must return false cleanly,
        // never throw, and never attempt filesystem operations.
        assertFalse(SaveManager.deleteSlot(1));
        assertFalse(SaveManager.deleteSlot(2));
        assertFalse(SaveManager.deleteSlot(3));
    }
}
