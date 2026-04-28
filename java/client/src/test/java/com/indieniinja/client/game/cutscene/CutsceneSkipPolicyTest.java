package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneSkipPolicyTest {

    private CutsceneManager makeManager(CutsceneDefinition def, Set<String> completed) {
        StoryManager    story    = new StoryManager();
        DialogueManager dialogue = new DialogueManager();
        boolean[]       locked   = {false};
        return new CutsceneManager(
                Map.of(def.id, def), story, dialogue, lock -> locked[0] = lock, completed);
    }

    private CutsceneDefinition longScene(String id, SkipPolicy policy) {
        return new CutsceneDefinition.Builder(id)
                .skipPolicy(policy)
                .completionFlags(List.of(id + "_done"))
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(99f).build()))
                .build();
    }

    // ── NEVER ─────────────────────────────────────────────────────────────────

    @Test
    void neverPolicyBlocksSkip() {
        CutsceneDefinition def = longScene("never_scene", SkipPolicy.NEVER);
        Set<String> completed = new HashSet<>();
        CutsceneManager mgr = makeManager(def, completed);

        mgr.start("never_scene");
        boolean skipped = mgr.skip();

        assertFalse(skipped, "NEVER policy must block skip");
        assertTrue(mgr.isActive(), "scene must still be active after blocked skip");
    }

    // ── ALWAYS ────────────────────────────────────────────────────────────────

    @Test
    void alwaysPolicyAllowsSkip() {
        CutsceneDefinition def = longScene("always_scene", SkipPolicy.ALWAYS);
        Set<String> completed = new HashSet<>();
        CutsceneManager mgr = makeManager(def, completed);

        mgr.start("always_scene");
        assertTrue(mgr.isActive());
        boolean skipped = mgr.skip();

        assertTrue(skipped, "ALWAYS policy must allow skip");
        assertFalse(mgr.isActive(), "scene must be inactive after skip");
    }

    @Test
    void alwaysSkipStillWritesCompletionFlags() {
        StoryManager story = new StoryManager();
        DialogueManager dialogue = new DialogueManager();
        Set<String> completed = new HashSet<>();
        CutsceneDefinition def = longScene("always_flags", SkipPolicy.ALWAYS);
        CutsceneManager mgr = new CutsceneManager(
                Map.of(def.id, def), story, dialogue, lock -> {}, completed);

        mgr.start("always_flags");
        mgr.skip();

        assertTrue(story.hasFlag("always_flags_done"),
                "skip must still write completion flags");
        assertTrue(completed.contains("always_flags"),
                "skip must add id to completedIds");
    }

    @Test
    void alwaysSkipReleasesPlayerLock() {
        boolean[] locked = {false};
        CutsceneDefinition def = new CutsceneDefinition.Builder("always_lock")
                .skipPolicy(SkipPolicy.ALWAYS)
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.LOCK_PLAYER).build(),
                        new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(99f).build()
                ))
                .build();
        StoryManager story = new StoryManager();
        DialogueManager dialogue = new DialogueManager();
        CutsceneManager mgr = new CutsceneManager(
                Map.of(def.id, def), story, dialogue, lock -> locked[0] = lock, new HashSet<>());

        mgr.start("always_lock");
        assertTrue(locked[0], "should be locked during scene");
        mgr.skip();
        assertFalse(locked[0], "skip must release player lock");
    }

    // ── ALLOW_AFTER_FIRST_VIEW ─────────────────────────────────────────────────

    @Test
    void allowAfterFirstViewBlocksOnFirstRun() {
        CutsceneDefinition def = longScene("first_view_scene", SkipPolicy.ALLOW_AFTER_FIRST_VIEW);
        Set<String> completed = new HashSet<>(); // empty = never seen
        CutsceneManager mgr = makeManager(def, completed);

        mgr.start("first_view_scene");
        boolean skipped = mgr.skip();

        assertFalse(skipped, "ALLOW_AFTER_FIRST_VIEW must block skip on first view");
        assertTrue(mgr.isActive());
    }

    @Test
    void allowAfterFirstViewPermitsSkipOnReplay() {
        CutsceneDefinition def = longScene("replay_scene", SkipPolicy.ALLOW_AFTER_FIRST_VIEW);

        // Pre-populate completed so the scene is treated as already seen
        Set<String> completed = new HashSet<>(Set.of("replay_scene"));
        CutsceneManager mgr = makeManager(def, completed);

        mgr.start("replay_scene", true); // force-start despite already completed
        boolean skipped = mgr.skip();

        assertTrue(skipped, "ALLOW_AFTER_FIRST_VIEW must allow skip after first view");
        assertFalse(mgr.isActive());
    }

    // ── DEBUG_ONLY ────────────────────────────────────────────────────────────

    @Test
    void debugOnlyPolicyBlocksNormalSkip() {
        CutsceneDefinition def = longScene("debug_scene", SkipPolicy.DEBUG_ONLY);
        Set<String> completed = new HashSet<>();
        CutsceneManager mgr = makeManager(def, completed);

        mgr.start("debug_scene");
        boolean skipped = mgr.skip(); // normal runtime path

        assertFalse(skipped, "DEBUG_ONLY must block normal skip");
        assertTrue(mgr.isActive());
    }
}
