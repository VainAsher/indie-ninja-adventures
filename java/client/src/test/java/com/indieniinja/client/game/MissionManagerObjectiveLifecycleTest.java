package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MissionManagerObjectiveLifecycleTest {

    @Test
    void switchAndReachObjectivesUnlockExitThenRequireExplicitComplete() {
        MissionDefinition def = missionWithObjectives(
            "test_mission",
            List.of(
                new MissionObjective(
                    ObjectiveType.ACTIVATE_SWITCHES, "Activate switches",
                    0, null, 2, null, null, 0f),
                new MissionObjective(
                    ObjectiveType.REACH_LOCATION, "Reach objective location",
                    0, null, 0, "checkpoint", null, 0f)
            )
        );
        MissionManager mgr = new MissionManager(Map.of(def.missionId, def));

        mgr.startMission(def.missionId);
        assertTrue(mgr.isActive());
        assertTrue(mgr.isExitLocked());

        // Wrong mission tag must not count.
        mgr.onSwitchActivated("other_mission:switch_01");
        assertTrue(mgr.isExitLocked());

        // Current mission tag counts.
        mgr.onSwitchActivated("test_mission:switch_01");
        assertTrue(mgr.isExitLocked());

        // Reach location alone is insufficient until all switches are done.
        mgr.onReachLocation("checkpoint");
        assertTrue(mgr.isExitLocked());

        // Second tagged switch unlocks mission exit.
        mgr.onSwitchActivated("test_mission:switch_02");
        assertFalse(mgr.isExitLocked());
        assertTrue(mgr.isActive());
        assertEquals(MissionState.IN_PROGRESS, mgr.getState(def.missionId));

        // Mission only completes on explicit completion call (exit-contact equivalent).
        mgr.completeMission();
        assertFalse(mgr.isActive());
        assertEquals(MissionState.COMPLETED, mgr.getState(def.missionId));
    }

    @Test
    void activateSwitchesObjectiveUsesCountField() {
        MissionDefinition def = missionWithObjectives(
            "switch_count_mission",
            List.of(new MissionObjective(
                ObjectiveType.ACTIVATE_SWITCHES, "Use count field",
                99, null, 2, null, null, 0f))
        );
        MissionManager mgr = new MissionManager(Map.of(def.missionId, def));

        mgr.startMission(def.missionId);
        mgr.onSwitchActivated("switch_count_mission:a");
        assertTrue(mgr.isExitLocked());

        mgr.onSwitchActivated("switch_count_mission:b");
        assertFalse(mgr.isExitLocked());
    }

    private static MissionDefinition missionWithObjectives(
        String missionId, List<MissionObjective> objectives
    ) {
        return new MissionDefinition(
            missionId,
            "Test Mission",
            "Lifecycle test mission",
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
