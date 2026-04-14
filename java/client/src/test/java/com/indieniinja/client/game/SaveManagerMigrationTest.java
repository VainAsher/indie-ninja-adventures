package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SaveManagerMigrationTest {

    @Test
    void clampStoryActOrdinalSupportsAllSevenActs() {
        assertEquals(0, SaveManager.clampStoryActOrdinal(-3));
        assertEquals(0, SaveManager.clampStoryActOrdinal(0));
        assertEquals(6, SaveManager.clampStoryActOrdinal(6));
        assertEquals(6, SaveManager.clampStoryActOrdinal(99));
    }
}
