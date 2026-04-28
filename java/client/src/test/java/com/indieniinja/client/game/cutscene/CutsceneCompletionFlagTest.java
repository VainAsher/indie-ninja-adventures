package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.*;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Completion flag behaviour that does not require SaveManager internals.
 * Round-trip persistence tests live in CutsceneSaveRoundtripTest (game package).
 */
class CutsceneCompletionFlagTest {

    private static CutsceneManager makeManager(StoryManager story,
                                               CutsceneDefinition def,
                                               Set<String> completedIds) {
        DialogueManager dialogue = new DialogueManager();
        return new CutsceneManager(
                Map.of(def.id, def), story, dialogue, lock -> {}, completedIds);
    }

    @Test
    void completionFlagWrittenToStoryManagerOnFinish() {
        StoryManager story = new StoryManager();
        CutsceneDefinition def = new CutsceneDefinition.Builder("cs_flag_write")
                .completionFlags(List.of("cs_flag_write_done"))
                .steps(List.of())
                .build();
        CutsceneManager mgr = makeManager(story, def, new HashSet<>());

        mgr.start("cs_flag_write");
        assertTrue(story.hasFlag("cs_flag_write_done"),
                "completion flag must be in StoryManager after cutscene finishes");
    }

    @Test
    void completedIdAddedToSetOnFinish() {
        Set<String> completed = new HashSet<>();
        CutsceneDefinition def = new CutsceneDefinition.Builder("cs_id_tracked")
                .steps(List.of())
                .build();
        CutsceneManager mgr = makeManager(new StoryManager(), def, completed);

        mgr.start("cs_id_tracked");
        assertTrue(completed.contains("cs_id_tracked"));
    }

    @Test
    void completedOneShotDoesNotRetriggerAfterReload() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("oneshot")
                .skipPolicy(SkipPolicy.NEVER)
                .steps(List.of())
                .build();
        Set<String> completed = new HashSet<>();

        // First play
        CutsceneManager mgr = makeManager(new StoryManager(), def, completed);
        assertTrue(mgr.start("oneshot"));

        // New manager reusing same completed set simulates post-reload state
        CutsceneManager mgr2 = makeManager(new StoryManager(), def, completed);
        assertFalse(mgr2.start("oneshot"), "one-shot must not restart after completion");
    }

    @Test
    void playerInputNotLockedAfterEmergencyStop() {
        boolean[] locked = {false};
        CutsceneDefinition def = new CutsceneDefinition.Builder("lock_stop")
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.LOCK_PLAYER).build(),
                        new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(99f).build()
                ))
                .build();
        StoryManager story = new StoryManager();
        DialogueManager dialogue = new DialogueManager();
        CutsceneManager mgr = new CutsceneManager(
                Map.of(def.id, def), story, dialogue, lock -> locked[0] = lock, new HashSet<>());

        mgr.start("lock_stop");
        assertTrue(locked[0]);
        mgr.emergencyStop();
        assertFalse(locked[0], "emergencyStop must release the player lock");
        assertFalse(mgr.isActive());
    }
}
