package com.indieniinja.client.game.cutscene;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneLoaderTest {

    // ── Valid load ─────────────────────────────────────────────────────────────

    @Test
    void validMinimalJsonLoadsCleanly() {
        String json = """
                {
                  "id": "test_scene",
                  "version": 1,
                  "act": 1,
                  "blocking": true,
                  "skip_policy": "never",
                  "start_conditions": [],
                  "completion_flags": ["test_done"],
                  "steps": [
                    { "type": "lock_player" },
                    { "type": "wait", "duration": 1.5 },
                    { "type": "unlock_player" }
                  ]
                }
                """;

        CutsceneDefinition def = CutsceneLoader.loadString(json);

        assertEquals("test_scene", def.id);
        assertEquals(1, def.version);
        assertEquals(1, def.act);
        assertTrue(def.blocking);
        assertEquals(SkipPolicy.NEVER, def.skipPolicy);
        assertEquals(1, def.completionFlags.size());
        assertEquals("test_done", def.completionFlags.get(0));
        assertEquals(3, def.steps.size());
        assertEquals(CutsceneStepType.LOCK_PLAYER,   def.steps.get(0).type);
        assertEquals(CutsceneStepType.WAIT,          def.steps.get(1).type);
        assertEquals(1.5f,                           def.steps.get(1).duration, 0.001f);
        assertEquals(CutsceneStepType.UNLOCK_PLAYER, def.steps.get(2).type);
    }

    @Test
    void dialogueStepFieldsLoad() {
        String json = """
                {
                  "id": "dialogue_scene",
                  "steps": [
                    { "type": "dialogue", "speaker": "Linzi", "text_key": "linzi.hello" }
                  ]
                }
                """;

        CutsceneDefinition def = CutsceneLoader.loadString(json);
        CutsceneStep step = def.steps.get(0);

        assertEquals(CutsceneStepType.DIALOGUE, step.type);
        assertEquals("Linzi",       step.speaker);
        assertEquals("linzi.hello", step.textKey);
    }

    @Test
    void setFlagStepFieldsLoad() {
        String json = """
                {
                  "id": "flag_scene",
                  "steps": [
                    { "type": "set_flag", "flag": "act1_linzi_met", "value": "true" }
                  ]
                }
                """;

        CutsceneDefinition def = CutsceneLoader.loadString(json);
        CutsceneStep step = def.steps.get(0);

        assertEquals(CutsceneStepType.SET_FLAG, step.type);
        assertEquals("act1_linzi_met", step.flag);
        assertEquals("true",           step.value);
    }

    @Test
    void startConditionsLoad() {
        String json = """
                {
                  "id": "cond_scene",
                  "start_conditions": [
                    { "flag_not_set": "act1_linzi_met" }
                  ],
                  "steps": []
                }
                """;

        CutsceneDefinition def = CutsceneLoader.loadString(json);
        assertEquals(1, def.startConditions.size());
        assertEquals("act1_linzi_met", def.startConditions.get(0).flagNotSet);
    }

    @Test
    void loadIsIdempotent() {
        String json = """
                { "id": "idempotent_scene", "steps": [] }
                """;
        CutsceneDefinition a = CutsceneLoader.loadString(json);
        CutsceneDefinition b = CutsceneLoader.loadString(json);
        assertEquals(a.id, b.id);
        assertEquals(a.steps.size(), b.steps.size());
    }

    // ── Validation failures ────────────────────────────────────────────────────

    @Test
    void missingIdThrows() {
        String json = """
                { "steps": [] }
                """;
        CutsceneLoadException ex = assertThrows(CutsceneLoadException.class,
                () -> CutsceneLoader.loadString(json));
        assertTrue(ex.getMessage().contains("id"), "message should mention 'id': " + ex.getMessage());
    }

    @Test
    void unknownStepTypeThrows() {
        String json = """
                {
                  "id": "bad_step",
                  "steps": [ { "type": "fly_around" } ]
                }
                """;
        CutsceneLoadException ex = assertThrows(CutsceneLoadException.class,
                () -> CutsceneLoader.loadString(json));
        assertTrue(ex.getMessage().contains("fly_around"),
                "message should name the bad type: " + ex.getMessage());
    }

    @Test
    void invalidJsonThrows() {
        assertThrows(CutsceneLoadException.class,
                () -> CutsceneLoader.loadString("{ not valid json"));
    }

    @Test
    void unknownSkipPolicyThrows() {
        String json = """
                { "id": "bad_policy", "skip_policy": "whenever_i_feel_like_it", "steps": [] }
                """;
        CutsceneLoadException ex = assertThrows(CutsceneLoadException.class,
                () -> CutsceneLoader.loadString(json));
        assertTrue(ex.getMessage().contains("whenever_i_feel_like_it"),
                "message should name the bad policy: " + ex.getMessage());
    }

    @Test
    void toMapConvertsNumericAndBooleanFields() {
        CutsceneDefinition def = CutsceneLoader.loadString(
                """
                { "id": "map_test", "act": 2, "blocking": false,
                  "steps": [{ "type": "wait", "duration": 3.0 }] }
                """);
        assertEquals(2,    def.act);
        assertFalse(def.blocking);
        assertEquals(3.0f, def.steps.get(0).duration, 0.001f);
    }
}
