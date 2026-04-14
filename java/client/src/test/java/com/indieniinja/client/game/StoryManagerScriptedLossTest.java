package com.indieniinja.client.game;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class StoryManagerScriptedLossTest {

    @Test
    void scriptedLossCollapsesHubAndForcesActThreeMinimum() {
        StoryManager story = new StoryManager();
        story.setAct(Act.ACT_I_RISE);

        story.onVeilMaidenDefeatedAct1();

        Map<String, String> ctx = story.toConditionContext();
        assertEquals(String.valueOf(Act.ACT_III_LABYRINTH.wire()), ctx.get("act"));
        assertEquals("EMPTY", ctx.get("hub_state"));
        assertEquals("9", ctx.get("hub_degradation_level"));
        assertEquals("true", ctx.get("veil_maiden_defeated_act1"));
        assertEquals("false", ctx.get("yin_yang_present"));
    }

    @Test
    void restoreSnapshotRehydratesSavedHubState() {
        StoryManager story = new StoryManager();
        story.restoreSnapshot(
            Act.ACT_V_HEARTH.wire(),
            "RECOVERING",
            4,
            2,
            true,
            false,
            false,
            true,
            Map.of("custom_flag", "ok")
        );

        Map<String, String> ctx = story.toConditionContext();
        assertEquals(String.valueOf(Act.ACT_V_HEARTH.wire()), ctx.get("act"));
        assertEquals("RECOVERING", ctx.get("hub_state"));
        assertEquals("4", ctx.get("hub_degradation_level"));
        assertEquals("ok", ctx.get("custom_flag"));
    }
}
