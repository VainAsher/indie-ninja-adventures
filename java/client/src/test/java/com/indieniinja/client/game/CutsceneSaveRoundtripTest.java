package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Verifies that completed cutscene ids survive a SaveData capture/restore cycle.
 * Lives in the game package to access SaveManager package-private helpers.
 */
class CutsceneSaveRoundtripTest {

    @Test
    void completedCutscenesRoundtripThroughSaveData() {
        StoryManager   story   = new StoryManager();
        MissionManager missions = new MissionManager();
        SaveManager    saveMgr = new SaveManager(story, missions);

        saveMgr.completedCutscenes().add("act1_linzi_first_appearance");
        saveMgr.completedCutscenes().add("act1_first_thinning");

        SaveData snapshot = saveMgr.buildSaveSnapshotForWrite();
        assertTrue(snapshot.completedCutscenes.contains("act1_linzi_first_appearance"),
                "completed cutscene must appear in save snapshot");
        assertTrue(snapshot.completedCutscenes.contains("act1_first_thinning"));

        StoryManager   story2   = new StoryManager();
        MissionManager missions2 = new MissionManager();
        SaveManager    saveMgr2 = new SaveManager(story2, missions2);
        saveMgr2.applyLoadedData(snapshot);

        assertTrue(saveMgr2.completedCutscenes().contains("act1_linzi_first_appearance"),
                "completed cutscenes must survive save/load round-trip");
        assertTrue(saveMgr2.completedCutscenes().contains("act1_first_thinning"));
    }

    @Test
    void emptyCompletedCutscenesRoundtripsCleanly() {
        StoryManager   story   = new StoryManager();
        MissionManager missions = new MissionManager();
        SaveManager    saveMgr = new SaveManager(story, missions);

        SaveData snapshot = saveMgr.buildSaveSnapshotForWrite();
        assertNotNull(snapshot.completedCutscenes,
                "completedCutscenes must never be null in snapshot");

        saveMgr.applyLoadedData(snapshot);
        assertTrue(saveMgr.completedCutscenes().isEmpty(),
                "empty set must round-trip as empty set");
    }

    @Test
    void missingSaveFieldDefaultsToEmptyOnLoad() {
        // Simulate an old save that has no completedCutscenes field (null after JSON load)
        StoryManager   story   = new StoryManager();
        MissionManager missions = new MissionManager();
        SaveManager    saveMgr = new SaveManager(story, missions);

        SaveData old = new SaveData();
        old.completedCutscenes = null; // as if field was absent in old JSON

        saveMgr.applyLoadedData(old);
        assertNotNull(saveMgr.completedCutscenes(), "set must not be null after loading old save");
        assertTrue(saveMgr.completedCutscenes().isEmpty(), "missing field must default to empty");
    }
}
