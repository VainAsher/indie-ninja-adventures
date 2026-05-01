package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SaveDataParityTest {

    @Test
    void restoreRestoresStorySnapshotAndActiveMission() {
        MissionDefinition active = mission(
            "active_mission",
            List.of(
                new MissionObjective(ObjectiveType.ACTIVATE_SWITCHES, "Switches", 0, null, 2, null, null, 0f),
                new MissionObjective(ObjectiveType.REACH_LOCATION, "Reach", 0, null, 0, "checkpoint", null, 0f)
            )
        );
        MissionDefinition done = mission(
            "done_mission",
            List.of(new MissionObjective(ObjectiveType.REACH_LOCATION, "Reach", 0, null, 0, "done", null, 0f))
        );

        StoryManager story = new StoryManager();
        MissionManager missions = new MissionManager(Map.of(
            active.missionId, active,
            done.missionId, done
        ));

        SaveData save = new SaveData();
        save.storyAct = Act.ACT_VI_ASCENT.wire();
        save.hubState = "RECOVERING";
        save.hubDegradationLevel = 7;
        save.lanternsMetCount = 3;
        save.veilMaidenEncountered = true;
        save.veilMaidenDefeatedAct1 = true;
        save.veilMaidenDefeatedFinal = false;
        save.yinYangPresent = false;
        save.storyFlags = Map.of("custom_flag", "custom_value");

        save.missionStates = Map.of(
            "active_mission", MissionState.IN_PROGRESS,
            "done_mission", MissionState.COMPLETED
        );
        save.missionBestTimes = Map.of("done_mission", 12.5f);
        save.missionAttempts = Map.of("active_mission", 4);
        save.activeMissionId = "active_mission";
        save.missionTimer = 42.0f;
        save.activeMissionObjectiveProgress = Map.of(
            "reach_location_checkpoint", 1,
            "activate_switches_", 1
        );

        save.restore(story, missions);

        Map<String, String> ctx = story.toConditionContext();
        assertEquals(String.valueOf(Act.ACT_VI_ASCENT.wire()), ctx.get("act"));
        assertEquals("RECOVERING", ctx.get("hub_state"));
        assertEquals("7", ctx.get("hub_degradation_level"));
        assertEquals("3", ctx.get("lanterns_met"));
        assertEquals("true", ctx.get("veil_maiden_encountered"));
        assertEquals("true", ctx.get("veil_maiden_defeated_act1"));
        assertEquals("false", ctx.get("yin_yang_present"));
        assertEquals("custom_value", ctx.get("custom_flag"));

        assertEquals(MissionState.COMPLETED, missions.getState("done_mission"));
        assertEquals("active_mission", missions.getActiveMissionId());
        assertEquals(42.0f, missions.getMissionTimer(), 0.001f);
        assertTrue(missions.isExitLocked()); // only 1/2 switches done in saved progress
    }

    @Test
    void restoreCanReopenMissionExitWhenSavedObjectivesAreComplete() {
        MissionDefinition mission = mission(
            "reach_only",
            List.of(new MissionObjective(
                ObjectiveType.REACH_LOCATION, "Reach", 0, null, 0, "goal", null, 0f))
        );
        StoryManager story = new StoryManager();
        MissionManager missions = new MissionManager(Map.of(mission.missionId, mission));

        SaveData save = new SaveData();
        save.activeMissionId = "reach_only";
        save.activeMissionObjectiveProgress = Map.of("reach_location_goal", 1);
        save.missionStates = Map.of("reach_only", MissionState.IN_PROGRESS);

        save.restore(story, missions);

        assertEquals("reach_only", missions.getActiveMissionId());
        assertFalse(missions.isExitLocked());
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
            0,
            null, List.of(), false
        );
    }
}
