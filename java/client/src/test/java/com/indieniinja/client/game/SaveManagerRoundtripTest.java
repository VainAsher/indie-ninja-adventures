package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SaveManagerRoundtripTest {

    @Test
    void loadThenBuildWriteSnapshotPreservesLiveDataAndManagerState() {
        MissionDefinition mission = mission(
            "roundtrip_mission",
            List.of(
                new MissionObjective(ObjectiveType.ACTIVATE_SWITCHES, "Switches", 0, null, 2, null, null, 0f),
                new MissionObjective(ObjectiveType.REACH_LOCATION, "Reach", 0, null, 0, "goal", null, 0f)
            )
        );
        StoryManager story = new StoryManager();
        MissionManager missions = new MissionManager(Map.of(mission.missionId, mission));
        SaveManager saveManager = new SaveManager(story, missions);

        SaveData loaded = new SaveData();
        loaded.worldSeed = 987654321L;
        loaded.currentHubId = "solo_hub";
        loaded.currentHubX = 345.5f;
        loaded.currentHubY = 678.25f;
        loaded.currency = 77;
        loaded.playerInventory = Map.of("health_potion", 3, "iron_sword", 1);
        loaded.equippedWeapon = "iron_sword";
        loaded.unlockedAbilities = List.of("dash", "teleport");
        loaded.visitedRoomKeys = List.of("0,0", "1,0");
        loaded.totalEnemiesKilled = 13;
        loaded.achievements = List.of("first_steps");

        loaded.storyAct = Act.ACT_V_HEARTH.wire();
        loaded.hubState = "EMPTY";
        loaded.hubDegradationLevel = 6;
        loaded.lanternsMetCount = 2;
        loaded.veilMaidenEncountered = true;
        loaded.veilMaidenDefeatedAct1 = true;
        loaded.veilMaidenDefeatedFinal = false;
        loaded.yinYangPresent = false;
        loaded.storyFlags = Map.of("custom_story_flag", "ok");

        loaded.missionStates = Map.of("roundtrip_mission", MissionState.IN_PROGRESS);
        loaded.activeMissionId = "roundtrip_mission";
        loaded.missionTimer = 21.5f;
        loaded.activeMissionObjectiveProgress = Map.of(
            "activate_switches_", 1,
            "reach_location_goal", 1
        );
        loaded.missionAttempts = Map.of("roundtrip_mission", 4);
        loaded.missionBestTimes = Map.of("roundtrip_mission", 12.75f);

        saveManager.applyLoadedData(loaded);
        SaveData out = saveManager.buildSaveSnapshotForWrite();

        assertEquals(loaded.worldSeed, out.worldSeed);
        assertEquals(loaded.currentHubId, out.currentHubId);
        assertEquals(loaded.currentHubX, out.currentHubX, 0.0001f);
        assertEquals(loaded.currentHubY, out.currentHubY, 0.0001f);
        assertEquals(loaded.currency, out.currency);
        assertEquals(loaded.playerInventory, out.playerInventory);
        assertEquals(loaded.equippedWeapon, out.equippedWeapon);
        assertEquals(loaded.unlockedAbilities, out.unlockedAbilities);
        assertEquals(loaded.visitedRoomKeys, out.visitedRoomKeys);
        assertEquals(loaded.totalEnemiesKilled, out.totalEnemiesKilled);
        assertEquals(loaded.achievements, out.achievements);

        assertEquals(loaded.storyAct, out.storyAct);
        assertEquals(loaded.hubState, out.hubState);
        assertEquals(loaded.hubDegradationLevel, out.hubDegradationLevel);
        assertEquals(loaded.lanternsMetCount, out.lanternsMetCount);
        assertEquals(loaded.veilMaidenEncountered, out.veilMaidenEncountered);
        assertEquals(loaded.veilMaidenDefeatedAct1, out.veilMaidenDefeatedAct1);
        assertEquals(loaded.veilMaidenDefeatedFinal, out.veilMaidenDefeatedFinal);
        assertEquals(loaded.yinYangPresent, out.yinYangPresent);
        assertTrue(out.storyFlags.containsKey("custom_story_flag"));
        assertEquals("ok", out.storyFlags.get("custom_story_flag"));

        assertEquals("roundtrip_mission", out.activeMissionId);
        assertEquals(21.5f, out.missionTimer, 0.0001f);
        assertEquals(loaded.activeMissionObjectiveProgress, out.activeMissionObjectiveProgress);
        assertEquals(MissionState.IN_PROGRESS, out.missionStates.get("roundtrip_mission"));
        assertEquals(4, out.missionAttempts.get("roundtrip_mission"));
        assertEquals(12.75f, out.missionBestTimes.get("roundtrip_mission"), 0.0001f);
    }

    @Test
    void buildWriteSnapshotOverlaysCurrentManagerStateOverLiveData() {
        MissionDefinition mission = mission(
            "overlay_mission",
            List.of(new MissionObjective(
                ObjectiveType.REACH_LOCATION, "Reach", 0, null, 0, "goal", null, 0f))
        );
        StoryManager story = new StoryManager();
        MissionManager missions = new MissionManager(Map.of(mission.missionId, mission));
        SaveManager saveManager = new SaveManager(story, missions);

        SaveData loaded = new SaveData();
        loaded.currency = 15;
        loaded.storyAct = Act.ACT_II_FALL.wire();
        loaded.missionStates = Map.of("overlay_mission", MissionState.NOT_STARTED);
        saveManager.applyLoadedData(loaded);

        // Mutate runtime manager state after load.
        story.setAct(Act.ACT_VI_ASCENT);
        missions.startMission("overlay_mission");
        missions.onReachLocation("goal");

        SaveData out = saveManager.buildSaveSnapshotForWrite();

        // liveData-origin fields stay as loaded unless changed through runtime sync hooks.
        assertEquals(15, out.currency);
        // manager-origin fields reflect current runtime state.
        assertEquals(Act.ACT_VI_ASCENT.wire(), out.storyAct);
        assertEquals("overlay_mission", out.activeMissionId);
        assertEquals(1, out.activeMissionObjectiveProgress.get("reach_location_goal"));
        assertEquals(MissionState.IN_PROGRESS, out.missionStates.get("overlay_mission"));
    }

    private static MissionDefinition mission(String missionId, List<MissionObjective> objectives) {
        return new MissionDefinition(
            missionId,
            "Mission",
            "desc",
            "forest",
            1,
            1,
            "linear",
            objectives,
            List.of(),
            List.of(),
            0,
            List.of(),
            0f,
            0
        );
    }
}
