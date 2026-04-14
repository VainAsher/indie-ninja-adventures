package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SaveManagerMigrationTest {

    @Test
    void clampStoryActOrdinalSupportsAllSevenActs() {
        assertEquals(0, SaveManager.clampStoryActOrdinal(-3));
        assertEquals(0, SaveManager.clampStoryActOrdinal(0));
        assertEquals(6, SaveManager.clampStoryActOrdinal(6));
        assertEquals(6, SaveManager.clampStoryActOrdinal(99));
    }

    @Test
    void invalidSavedHubStateIsSanitizedToFull() {
        StoryManager story = new StoryManager();
        MissionManager missions = new MissionManager(Map.of());
        SaveManager manager = new SaveManager(story, missions);

        SaveData loaded = new SaveData();
        loaded.hubState = "not_a_real_hub_state";

        manager.applyLoadedData(loaded);
        SaveData out = manager.buildSaveSnapshotForWrite();

        assertEquals("FULL", out.hubState);
    }
}
