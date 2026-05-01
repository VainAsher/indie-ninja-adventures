package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Verifies that Act I mission prerequisites are enforced at runtime.
 * mission_1 → mission_2 → mission_3 → summit_shrine must be played in order.
 */
class MissionSequencingTest {

    private static MissionDefinition mission(String id, List<String> requires) {
        return new MissionDefinition(
            id, id, "", "lantern", 1, 6, "blob",
            List.of(new MissionObjective(ObjectiveType.KILL_ALL_ENEMIES, "Clear dungeon",
                1, null, 0, null, null, 0f)),
            List.of(), List.of(), 0, List.of(), 0f, 1,
            id, requires, false
        );
    }

    private static MissionManager act1Manager() {
        MissionDefinition m1 = mission("act1_mission_1", List.of());
        MissionDefinition m2 = mission("act1_mission_2", List.of("act1_mission_1"));
        MissionDefinition m3 = mission("act1_mission_3", List.of("act1_mission_2"));
        MissionDefinition boss = new MissionDefinition(
            "summit_shrine", "The Summit Shrine", "", "lantern", 3, 8, "snake",
            List.of(new MissionObjective(ObjectiveType.DEFEAT_BOSS, "Defeat Siren",
                1, null, 0, null, "siren", 0f)),
            List.of(), List.of(), 0, List.of(), 0f, 1,
            "summit_shrine", List.of("act1_mission_3"), true
        );
        return new MissionManager(Map.of(
            m1.missionId, m1,
            m2.missionId, m2,
            m3.missionId, m3,
            boss.missionId, boss
        ));
    }

    @Test
    void mission1IsUnlockedFromStart() {
        MissionManager mgr = act1Manager();
        assertTrue(mgr.isUnlocked("act1_mission_1"));
    }

    @Test
    void mission2LockedUntilMission1Complete() {
        MissionManager mgr = act1Manager();
        assertFalse(mgr.isUnlocked("act1_mission_2"));
    }

    @Test
    void mission2UnlocksAfterMission1Completed() {
        MissionManager mgr = act1Manager();
        mgr.startMission("act1_mission_1");
        mgr.onEnemyKilled(1);
        mgr.completeMission();

        assertTrue(mgr.isUnlocked("act1_mission_2"));
        assertFalse(mgr.isUnlocked("act1_mission_3"));
        assertFalse(mgr.isUnlocked("summit_shrine"));
    }

    @Test
    void fullSequenceUnlocksInOrder() {
        MissionManager mgr = act1Manager();

        // Complete m1
        mgr.startMission("act1_mission_1");
        mgr.onEnemyKilled(1);
        mgr.completeMission();

        // Complete m2
        mgr.startMission("act1_mission_2");
        mgr.onEnemyKilled(1);
        mgr.completeMission();

        // Complete m3
        mgr.startMission("act1_mission_3");
        mgr.onEnemyKilled(1);
        mgr.completeMission();

        assertTrue(mgr.isUnlocked("summit_shrine"),
            "summit_shrine must be unlocked after all 3 missions complete");
    }

    @Test
    void availableMissionsFiltersLockedOnes() {
        MissionManager mgr = act1Manager();
        List<String> ids = mgr.availableMissions(1).stream()
            .map(d -> d.missionId).collect(Collectors.toList());

        assertTrue(ids.contains("act1_mission_1"), "mission_1 should be available at start");
        assertFalse(ids.contains("act1_mission_2"), "mission_2 locked until mission_1 done");
        assertFalse(ids.contains("act1_mission_3"), "mission_3 locked until mission_2 done");
        assertFalse(ids.contains("summit_shrine"),  "summit_shrine locked until mission_3 done");
    }

    @Test
    void summitShrineHasGuaranteedBossExitFlag() {
        MissionManager mgr = act1Manager();
        MissionDefinition def = mgr.getDefinition("summit_shrine");
        assertTrue(def.guaranteedBossExit);
    }
}
