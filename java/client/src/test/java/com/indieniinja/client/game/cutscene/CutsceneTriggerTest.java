package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneTriggerTest {

    @Test
    void definitionLoadsOptionalTriggers() {
        CutsceneDefinition def = CutsceneLoader.loadString("""
                {
                  "id": "triggered_scene",
                  "triggers": [
                    { "event": "npc_interact", "id": "linzi" },
                    { "event": "mission_complete", "id": "act1_first_patrol" },
                    { "event": "flag_change", "id": "linzi_arrived" }
                  ],
                  "steps": []
                }
                """);

        assertEquals(3, def.triggers.size());
        assertTrue(def.hasTrigger(CutsceneTriggerType.NPC_INTERACT, "linzi"));
        assertTrue(def.hasTrigger(CutsceneTriggerType.MISSION_COMPLETE, "act1_first_patrol"));
        assertTrue(def.hasTrigger(CutsceneTriggerType.FLAG_CHANGE, "linzi_arrived"));
    }

    @Test
    void triggerRouterStartsFirstMatchingUncompletedScene() {
        CutsceneDefinition linzi = new CutsceneDefinition.Builder("linzi_scene")
                .triggers(List.of(new CutsceneTrigger(CutsceneTriggerType.NPC_INTERACT, "linzi")))
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.SET_FLAG)
                        .flag("linzi_scene_started")
                        .build()))
                .build();
        CutsceneManager manager = managerWith(linzi);
        CutsceneTriggerRouter router = new CutsceneTriggerRouter(manager);

        assertTrue(router.onNpcInteract("linzi"));
        assertTrue(manager.completedIds().contains("linzi_scene"));
    }

    @Test
    void triggerRouterIgnoresMissingTrigger() {
        CutsceneDefinition linzi = new CutsceneDefinition.Builder("linzi_scene")
                .triggers(List.of(new CutsceneTrigger(CutsceneTriggerType.NPC_INTERACT, "linzi")))
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(1f).build()))
                .build();
        CutsceneTriggerRouter router = new CutsceneTriggerRouter(managerWith(linzi));

        assertFalse(router.onNpcInteract("samson"));
    }

    private static CutsceneManager managerWith(CutsceneDefinition... defs) {
        Map<String, CutsceneDefinition> map = new HashMap<>();
        for (CutsceneDefinition def : defs) {
            map.put(def.id, def);
        }
        return new CutsceneManager(
                map,
                new StoryManager(),
                new DialogueManager(),
                locked -> {},
                new HashSet<>());
    }
}
