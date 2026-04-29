package com.indieniinja.client.game.cutscene;

import com.badlogic.gdx.files.FileHandle;
import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneG0RouteTest {

    @Test
    void allActOneCutscenesLoadFromManifestSet() {
        Map<String, CutsceneDefinition> defs = loadActOneCutscenes();

        assertEquals(6, defs.size());
        assertTrue(defs.containsKey("act1_title_sequence"));
        assertTrue(defs.containsKey("act1_aen_of_lantern_heights"));
        assertTrue(defs.containsKey("act1_first_patrol_briefing"));
        assertTrue(defs.containsKey("act1_linzi_first_appearance"));
        assertTrue(defs.containsKey("act1_linzi_guiding_voice"));
        assertTrue(defs.containsKey("act1_first_thinning"));
    }

    @Test
    void linziFirstAppearancePrecedesFirstThinningAndSetsExpectedFlags() {
        Map<String, CutsceneDefinition> defs = loadActOneCutscenes();
        StoryManager story = new StoryManager();
        DialogueManager dialogue = new DialogueManager();
        CutsceneManager manager = new CutsceneManager(
                defs,
                story,
                dialogue,
                locked -> {},
                new HashSet<>(),
                new InstantCameraController(),
                CutsceneMarkerRegistry.loadString(read("data/cutscenes/markers.json")),
                new CutsceneEntityOverrides());
        CutsceneTriggerRouter router = new CutsceneTriggerRouter(manager);

        assertTrue(router.onNpcInteract("linzi"));
        drain(manager, dialogue);

        assertTrue(story.hasFlag("act1_linzi_met"));
        assertTrue(story.hasFlag("linzi_arrived"));
        assertTrue(manager.completedIds().contains("act1_linzi_first_appearance"));
        assertFalse(manager.completedIds().contains("act1_first_thinning"));

        assertTrue(router.onMissionComplete("linzi_q1"));
        drain(manager, dialogue);

        assertTrue(story.hasFlag("act1_first_thinning_seen"));
        assertTrue(story.hasFlag("lantern_heights_first_thinning"));
        assertTrue(manager.completedIds().contains("act1_first_thinning"));
    }

    private static Map<String, CutsceneDefinition> loadActOneCutscenes() {
        Map<String, CutsceneDefinition> defs = new LinkedHashMap<>();
        String[] names = {
                "act1_aen_of_lantern_heights",
                "act1_first_patrol_briefing",
                "act1_first_thinning",
                "act1_linzi_first_appearance",
                "act1_linzi_guiding_voice",
                "act1_title_sequence"
        };
        for (String name : names) {
            CutsceneDefinition def = CutsceneLoader.loadFile(new FileHandle(file("data/cutscenes/" + name + ".json")));
            defs.put(def.id, def);
        }
        return defs;
    }

    private static void drain(CutsceneManager manager, DialogueManager dialogue) {
        int guard = 0;
        while (manager.isActive() && guard++ < 100) {
            if (dialogue.isActive()) {
                dialogue.advance();
            }
            manager.tick(1f);
        }
        assertFalse(manager.isActive(), "cutscene should drain without softlock");
    }

    private static String read(String path) {
        try {
            return java.nio.file.Files.readString(file(path).toPath());
        } catch (java.io.IOException e) {
            throw new AssertionError(e);
        }
    }

    private static File file(String path) {
        File dir = new File(System.getProperty("user.dir")).getAbsoluteFile();
        while (dir != null && !new File(dir, "data/cutscenes").isDirectory()) {
            dir = dir.getParentFile();
        }
        if (dir == null) {
            throw new AssertionError("could not locate repository root from " + System.getProperty("user.dir"));
        }
        return dir.toPath().resolve(path).toFile();
    }

    private static final class InstantCameraController implements CutsceneCameraController {
        @Override public void setCutsceneFocus(float worldX, float worldY) {}
        @Override public void panTo(float worldX, float worldY, float duration) {}
        @Override public void updateCutscene(float delta) {}
        @Override public boolean isCutscenePanActive() { return false; }
        @Override public void restorePlayerFollow() {}
    }
}
