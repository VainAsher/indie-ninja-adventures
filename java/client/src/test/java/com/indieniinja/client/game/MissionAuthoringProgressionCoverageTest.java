package com.indieniinja.client.game;

import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MissionAuthoringProgressionCoverageTest {

    private static final EnumSet<ObjectiveType> EXPECTED_TYPES = EnumSet.of(
        ObjectiveType.COLLECT_ITEMS,
        ObjectiveType.ACTIVATE_SWITCHES,
        ObjectiveType.REACH_LOCATION,
        ObjectiveType.TIME_CHALLENGE,
        ObjectiveType.DEFEAT_BOSS,
        ObjectiveType.KILL_ALL_ENEMIES
    );

    @Test
    void allAuthoredMissionsProgressThroughObjectiveAdaptersAndUnlockExit() throws Exception {
        Map<String, MissionDefinition> definitions = loadDefinitionsFromAuthoredMissions();
        assertEquals(30, definitions.size(), "Expected authored campaign mission count to remain 30");

        int progressed = 0;
        EnumSet<ObjectiveType> seenTypes = EnumSet.noneOf(ObjectiveType.class);

        for (MissionDefinition def : definitions.values()) {
            MissionManager mgr = new MissionManager(Map.of(def.missionId, def));
            mgr.startMission(def.missionId);
            assertTrue(mgr.isExitLocked(), "Exit must start locked for mission " + def.missionId);

            for (MissionObjective obj : def.objectives) {
                seenTypes.add(obj.type);
                satisfyObjectiveViaRuntimeAdapter(mgr, def, obj);
            }

            assertFalse(mgr.isExitLocked(),
                "Mission objectives should unlock exit in authored mission " + def.missionId);
            mgr.completeMission();
            assertEquals(MissionState.COMPLETED, mgr.getState(def.missionId));
            progressed++;
        }

        assertEquals(definitions.size(), progressed, "All authored missions must be progressable");
        assertEquals(EXPECTED_TYPES, seenTypes, "Objective type coverage drifted in authored missions");
    }

    private static void satisfyObjectiveViaRuntimeAdapter(
        MissionManager mgr,
        MissionDefinition def,
        MissionObjective obj
    ) {
        switch (obj.type) {
            case COLLECT_ITEMS -> {
                String item = requireNonBlank(obj.item, def.missionId, "collect_items");
                int needed = Math.max(1, obj.count);
                mgr.onItemCollected(item, needed);
            }
            case ACTIVATE_SWITCHES -> {
                int needed = Math.max(1, obj.count > 0 ? obj.count : obj.target);
                for (int i = 0; i < needed; i++) {
                    mgr.onSwitchActivated(def.missionId + ":switch_" + i);
                }
            }
            case REACH_LOCATION -> {
                String location = requireNonBlank(obj.location, def.missionId, "reach_location");
                mgr.onReachLocation(location);
            }
            case TIME_CHALLENGE -> {
                float limit = obj.timeLimit > 0f ? obj.timeLimit : (def.timeLimit > 0f ? def.timeLimit : 30f);
                mgr.tick(limit * 0.5f);
            }
            case DEFEAT_BOSS -> {
                String boss = (obj.boss == null || obj.boss.isBlank()) ? "siren" : obj.boss;
                mgr.onBossDefeated(boss);
            }
            case KILL_ALL_ENEMIES -> mgr.onEnemyKilled(Math.max(1, obj.target));
        }
    }

    private static Map<String, MissionDefinition> loadDefinitionsFromAuthoredMissions() throws Exception {
        Path missionsPath = findMissionsJson();
        String jsonText = Files.readString(missionsPath);
        JsonValue root = new JsonReader().parse(jsonText);
        JsonValue missions = root.get("missions");
        assertNotNull(missions, "missions array missing in missions.json");

        Method parse = MissionDefinition.class.getDeclaredMethod("parse", JsonValue.class);
        parse.setAccessible(true);

        Map<String, MissionDefinition> out = new LinkedHashMap<>();
        for (JsonValue mission : missions) {
            MissionDefinition def = (MissionDefinition) parse.invoke(null, mission);
            out.put(def.missionId, def);
        }
        return out;
    }

    private static Path findMissionsJson() {
        Path dir = Paths.get("").toAbsolutePath();
        while (dir != null) {
            Path candidate = dir.resolve("data").resolve("missions.json");
            if (Files.isRegularFile(candidate)) return candidate;
            dir = dir.getParent();
        }
        throw new AssertionError("Could not locate data/missions.json from test working directory");
    }

    private static String requireNonBlank(String value, String missionId, String objectiveType) {
        if (value == null || value.isBlank()) {
            throw new AssertionError(
                "Mission " + missionId + " has blank qualifier for objective type " + objectiveType);
        }
        return value;
    }
}

