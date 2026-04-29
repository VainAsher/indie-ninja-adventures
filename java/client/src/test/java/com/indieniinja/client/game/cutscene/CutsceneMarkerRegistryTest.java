package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneMarkerRegistryTest {

    @Test
    void loadsMarkersFromJsonArray() {
        CutsceneMarkerRegistry markers = CutsceneMarkerRegistry.loadString("""
                [
                  { "id": "marker_linzi_bridge", "x": 320, "y": 448 },
                  { "id": "marker_tai_dojo", "x": 96.5, "y": 144.25 }
                ]
                """);

        assertTrue(markers.resolve("marker_linzi_bridge").isPresent());
        assertEquals(320f, markers.resolve("marker_linzi_bridge").get().worldX(), 0.001f);
        assertEquals(448f, markers.resolve("marker_linzi_bridge").get().worldY(), 0.001f);
        assertEquals(96.5f, markers.resolve("marker_tai_dojo").get().worldX(), 0.001f);
        assertEquals(144.25f, markers.resolve("marker_tai_dojo").get().worldY(), 0.001f);
    }

    @Test
    void missingMarkerReturnsEmpty() {
        CutsceneMarkerRegistry markers = CutsceneMarkerRegistry.loadString("""
                [{ "id": "known", "x": 1, "y": 2 }]
                """);

        assertTrue(markers.resolve("missing").isEmpty());
    }

    @Test
    void cameraFocusStepResolvesMarkerTarget() {
        RecordingCameraController camera = new RecordingCameraController();
        CutsceneMarkerRegistry markers = CutsceneMarkerRegistry.loadString("""
                [{ "id": "marker_linzi_bridge", "x": 320, "y": 448 }]
                """);
        CutsceneDefinition def = new CutsceneDefinition.Builder("marker_focus")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.CAMERA_FOCUS)
                        .target("marker_linzi_bridge")
                        .build()))
                .build();
        HashMap<String, CutsceneDefinition> defs = new HashMap<>();
        defs.put(def.id, def);

        CutsceneManager manager = new CutsceneManager(
                defs,
                new StoryManager(),
                new DialogueManager(),
                locked -> {},
                new HashSet<>(),
                camera,
                markers);

        assertTrue(manager.start("marker_focus"));
        assertEquals(1, camera.focusCalls);
        assertEquals(320f, camera.focusX, 0.001f);
        assertEquals(448f, camera.focusY, 0.001f);
    }

    private static final class RecordingCameraController implements CutsceneCameraController {
        int focusCalls;
        float focusX;
        float focusY;

        @Override
        public void setCutsceneFocus(float worldX, float worldY) {
            focusCalls++;
            focusX = worldX;
            focusY = worldY;
        }

        @Override
        public void panTo(float worldX, float worldY, float duration) {}

        @Override
        public void updateCutscene(float delta) {}

        @Override
        public boolean isCutscenePanActive() {
            return false;
        }

        @Override
        public void restorePlayerFollow() {}
    }
}
