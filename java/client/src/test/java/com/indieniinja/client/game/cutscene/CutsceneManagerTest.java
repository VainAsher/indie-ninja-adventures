package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneManagerTest {

    private StoryManager   story;
    private DialogueManager dialogue;
    private AtomicBoolean  playerLocked;
    private Set<String>    completed;
    private CutsceneManager manager;

    @BeforeEach
    void setUp() {
        story        = new StoryManager();
        dialogue     = new DialogueManager(); // headless-safe (no Gdx.app)
        playerLocked = new AtomicBoolean(false);
        completed    = new HashSet<>();
    }

    private CutsceneManager managerWith(CutsceneDefinition... defs) {
        Map<String, CutsceneDefinition> map = new LinkedHashMap<>();
        for (CutsceneDefinition d : defs) map.put(d.id, d);
        return new CutsceneManager(map, story, dialogue, playerLocked::set, completed);
    }

    private CutsceneDefinition simpleDef(String id, CutsceneStep... steps) {
        return new CutsceneDefinition.Builder(id)
                .steps(List.of(steps))
                .build();
    }

    private CutsceneStep step(CutsceneStepType type) {
        return new CutsceneStep.Builder(type).build();
    }

    // ── Start / active ─────────────────────────────────────────────────────────

    @Test
    void startKnownIdActivatesScene() {
        manager = managerWith(simpleDef("my_scene", step(CutsceneStepType.WAIT)));
        // WAIT with duration 0 completes synchronously, but we need duration > 0
        CutsceneDefinition def = new CutsceneDefinition.Builder("wait_scene")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()))
                .build();
        manager = managerWith(def);

        assertTrue(manager.start("wait_scene"));
        assertTrue(manager.isActive());
        assertEquals("wait_scene", manager.activeId());
    }

    @Test
    void startUnknownIdReturnsFalse() {
        manager = managerWith();
        assertFalse(manager.start("nonexistent"));
        assertFalse(manager.isActive());
    }

    @Test
    void secondStartWhileActiveIsRejected() {
        CutsceneDefinition def1 = new CutsceneDefinition.Builder("scene_a")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()))
                .build();
        CutsceneDefinition def2 = new CutsceneDefinition.Builder("scene_b")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()))
                .build();
        manager = managerWith(def1, def2);

        assertTrue(manager.start("scene_a"));
        assertFalse(manager.start("scene_b")); // rejected
        assertEquals("scene_a", manager.activeId());
    }

    // ── LOCK_PLAYER / UNLOCK_PLAYER ────────────────────────────────────────────

    @Test
    void lockPlayerStepSetsLockedFlag() {
        manager = managerWith(new CutsceneDefinition.Builder("lock_test")
                .steps(List.of(
                        step(CutsceneStepType.LOCK_PLAYER),
                        new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()
                ))
                .build());

        manager.start("lock_test");
        assertTrue(playerLocked.get(), "player should be locked after LOCK_PLAYER step");
    }

    @Test
    void unlockPlayerStepClearsLockedFlag() {
        manager = managerWith(new CutsceneDefinition.Builder("unlock_test")
                .steps(List.of(
                        step(CutsceneStepType.LOCK_PLAYER),
                        step(CutsceneStepType.UNLOCK_PLAYER),
                        new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()
                ))
                .build());

        manager.start("unlock_test");
        assertFalse(playerLocked.get(), "player should be unlocked after UNLOCK_PLAYER step");
    }

    // ── SET_FLAG ───────────────────────────────────────────────────────────────

    @Test
    void setFlagStepWritesToStoryManager() {
        manager = managerWith(new CutsceneDefinition.Builder("flag_test")
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.SET_FLAG)
                                .flag("my_flag").value("true").build()
                ))
                .build());

        manager.start("flag_test");
        assertTrue(story.hasFlag("my_flag"));
    }

    // ── WAIT ───────────────────────────────────────────────────────────────────

    @Test
    void waitStepCountsDownBeforeCompletion() {
        AtomicBoolean completed = new AtomicBoolean(false);
        CutsceneDefinition def = new CutsceneDefinition.Builder("wait_test")
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(1.0f).build()
                ))
                .build();
        manager = managerWith(def);
        manager.setOnCompleteCallback(id -> completed.set(true));

        manager.start("wait_test");
        assertTrue(manager.isActive(), "should still be active mid-wait");

        manager.tick(0.5f);
        assertTrue(manager.isActive(), "still active after 0.5s of 1.0s wait");
        assertFalse(completed.get());

        manager.tick(0.6f); // total 1.1s > 1.0s
        assertFalse(manager.isActive(), "should have completed after full wait");
        assertTrue(completed.get());
    }

    // ── DIALOGUE step pause ────────────────────────────────────────────────────

    @Test
    void dialogueStepPausesUntilDialogueEnds() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("dialogue_test")
                .completionFlags(List.of("dialogue_done"))
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.DIALOGUE)
                                .speaker("Linzi").textKey("linzi.hello").build()
                ))
                .build();
        manager = managerWith(def);

        manager.start("dialogue_test");
        assertTrue(manager.isActive(), "should remain active while dialogue is open");

        // Simulate player advancing the dialogue
        dialogue.advance();     // advances past the synthetic node → dialogue ends
        manager.tick(0.016f);   // tick lets manager detect dialogue finished
        assertFalse(manager.isActive(), "should complete after dialogue advanced");
        assertTrue(story.hasFlag("dialogue_done"));
    }

    // ── Complete ───────────────────────────────────────────────────────────────

    @Test
    void completionFlagsWrittenOnComplete() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("flag_scene")
                .completionFlags(List.of("scene_done", "extra_flag"))
                .steps(List.of()) // empty → completes immediately
                .build();
        manager = managerWith(def);

        manager.start("flag_scene");
        assertFalse(manager.isActive());
        assertTrue(story.hasFlag("scene_done"));
        assertTrue(story.hasFlag("extra_flag"));
    }

    @Test
    void completedIdAddedToCompletedSet() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("track_complete")
                .steps(List.of())
                .build();
        manager = managerWith(def);

        manager.start("track_complete");
        assertTrue(this.completed.contains("track_complete"));
    }

    @Test
    void playerUnlockedOnComplete() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("unlock_on_complete")
                .steps(List.of(step(CutsceneStepType.LOCK_PLAYER)))
                .build();
        manager = managerWith(def);

        manager.start("unlock_on_complete");
        assertFalse(playerLocked.get(), "complete() must always unlock player");
    }

    // ── emergencyStop ──────────────────────────────────────────────────────────

    @Test
    void emergencyStopAlwaysUnlocksPlayer() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("stop_test")
                .steps(List.of(
                        step(CutsceneStepType.LOCK_PLAYER),
                        new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(99f).build()
                ))
                .build();
        manager = managerWith(def);

        manager.start("stop_test");
        assertTrue(playerLocked.get());

        manager.emergencyStop();
        assertFalse(manager.isActive());
        assertFalse(playerLocked.get());
    }

    // ── resetCompleted ─────────────────────────────────────────────────────────

    @Test
    void resetCompletedAllowsReplay() {
        CutsceneDefinition def = new CutsceneDefinition.Builder("replay_test")
                .steps(List.of())
                .build();
        manager = managerWith(def);

        manager.start("replay_test");         // completes immediately
        assertFalse(manager.start("replay_test")); // already completed — blocked

        manager.resetCompleted("replay_test");
        assertTrue(manager.start("replay_test", true)); // force-start after reset
    }
}
