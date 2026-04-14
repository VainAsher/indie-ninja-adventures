package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CampaignCriticalFlowTest {

    @Test
    void missionProgressAndSaveLoadRoundtripPreserveCriticalCampaignState() {
        MissionDefinition mission = mission(
            "critical_flow_mission",
            List.of(
                new MissionObjective(ObjectiveType.ACTIVATE_SWITCHES, "Switch", 0, null, 1, null, null, 0f),
                new MissionObjective(ObjectiveType.REACH_LOCATION, "Reach checkpoint", 0, null, 0, "checkpoint", null, 0f),
                new MissionObjective(ObjectiveType.COLLECT_ITEMS, "Collect relics", 0, "relic", 2, null, null, 0f),
                new MissionObjective(ObjectiveType.KILL_ALL_ENEMIES, "Clear enemies", 2, null, 0, null, null, 0f),
                new MissionObjective(ObjectiveType.DEFEAT_BOSS, "Defeat Siren", 0, null, 0, null, "siren", 0f),
                new MissionObjective(ObjectiveType.TIME_CHALLENGE, "Beat timer", 0, null, 0, null, null, 30f)
            ),
            30f
        );

        StoryManager story = new StoryManager();
        story.setAct(Act.ACT_III_LABYRINTH);
        story.setFlag("tutorial_completed", "true");
        MissionManager missions = new MissionManager(Map.of(mission.missionId, mission));
        SaveManager saveManager = new SaveManager(story, missions);

        missions.startMission(mission.missionId);
        missions.onSwitchActivated("critical_flow_mission:lever_1");
        missions.onReachLocation("checkpoint");
        missions.onItemCollected("relic", 1);
        missions.tick(5f);

        SaveData inProgress = saveManager.buildSaveSnapshotForWrite();

        StoryManager restoredStory = new StoryManager();
        MissionManager restoredMissions = new MissionManager(Map.of(mission.missionId, mission));
        SaveManager restoredSaveManager = new SaveManager(restoredStory, restoredMissions);
        restoredSaveManager.applyLoadedData(inProgress);

        assertEquals("critical_flow_mission", restoredMissions.getActiveMissionId());
        assertTrue(restoredMissions.isExitLocked());
        assertEquals(1, restoredMissions.getObjectiveProgressSnapshot().get("activate_switches_"));
        assertEquals(1, restoredMissions.getObjectiveProgressSnapshot().get("reach_location_checkpoint"));
        assertEquals(1, restoredMissions.getObjectiveProgressSnapshot().get("collect_items_relic"));
        assertEquals(String.valueOf(Act.ACT_III_LABYRINTH.wire()),
            restoredStory.toConditionContext().get("act"));

        restoredMissions.onItemCollected("relic", 1);
        restoredMissions.onEnemyKilled(2);
        restoredMissions.onBossDefeated("siren");
        assertFalse(restoredMissions.isExitLocked());

        restoredMissions.completeMission();
        assertNull(restoredMissions.getActiveMissionId());
        assertEquals(MissionState.COMPLETED, restoredMissions.getState("critical_flow_mission"));
    }

    @Test
    void timeChallengeMissionFailsWhenTimeLimitIsExceeded() {
        MissionDefinition mission = mission(
            "time_trial",
            List.of(new MissionObjective(
                ObjectiveType.TIME_CHALLENGE, "Beat the timer", 0, null, 0, null, null, 1f)),
            1f
        );
        MissionManager missions = new MissionManager(Map.of(mission.missionId, mission));

        missions.startMission(mission.missionId);
        missions.tick(1.2f);

        assertFalse(missions.isActive());
        assertEquals(MissionState.FAILED, missions.getState(mission.missionId));
    }

    private static MissionDefinition mission(
        String missionId,
        List<MissionObjective> objectives,
        float timeLimit
    ) {
        return new MissionDefinition(
            missionId,
            "Critical Flow Mission",
            "Mission used for campaign critical-path integration coverage",
            "forest",
            2,
            2,
            "linear",
            objectives,
            List.of(),
            List.of(),
            0,
            List.of(),
            timeLimit,
            0
        );
    }
}
