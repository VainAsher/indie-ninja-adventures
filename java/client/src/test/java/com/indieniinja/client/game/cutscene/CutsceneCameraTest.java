package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneCameraTest {

    @Test
    void focusSetsCutsceneOverrideTarget() {
        CutsceneCameraMotion camera = new CutsceneCameraMotion();

        camera.setFocus(900f, 800f);

        assertTrue(camera.isOverrideActive());
        assertEquals(900f, camera.x(), 0.001f);
        assertEquals(800f, camera.y(), 0.001f);
    }

    @Test
    void restorePlayerFollowClearsOverride() {
        CutsceneCameraMotion camera = new CutsceneCameraMotion();
        camera.setFocus(900f, 800f);

        camera.restore(300f, 200f);

        assertFalse(camera.isOverrideActive());
        assertFalse(camera.isPanActive());
        assertEquals(300f, camera.x(), 0.001f);
        assertEquals(200f, camera.y(), 0.001f);
    }

    @Test
    void panToInterpolatesAndCompletesAfterDuration() {
        CutsceneCameraMotion camera = new CutsceneCameraMotion();

        camera.panTo(100f, 100f, 300f, 500f, 1f);
        camera.update(0.5f);

        assertTrue(camera.isOverrideActive());
        assertTrue(camera.isPanActive());
        assertEquals(200f, camera.x(), 0.001f);
        assertEquals(300f, camera.y(), 0.001f);

        camera.update(0.5f);

        assertFalse(camera.isPanActive());
        assertEquals(300f, camera.x(), 0.001f);
        assertEquals(500f, camera.y(), 0.001f);
    }

    @Test
    void cameraFocusStepCallsControllerWithCoordinateTarget() {
        RecordingCameraController camera = new RecordingCameraController();
        CutsceneDefinition def = new CutsceneDefinition.Builder("camera_focus")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.CAMERA_FOCUS)
                        .target("120,240")
                        .build()))
                .build();
        CutsceneManager manager = managerWith(camera, def);

        assertTrue(manager.start("camera_focus"));

        assertEquals(1, camera.focusCalls);
        assertEquals(120f, camera.focusX, 0.001f);
        assertEquals(240f, camera.focusY, 0.001f);
        assertFalse(manager.isActive());
    }

    @Test
    void cameraPanStepWaitsForControllerCompletion() {
        RecordingCameraController camera = new RecordingCameraController();
        camera.panActive = true;
        CutsceneDefinition def = new CutsceneDefinition.Builder("camera_pan")
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.CAMERA_PAN)
                                .target("10,20")
                                .duration(1f)
                                .build(),
                        new CutsceneStep.Builder(CutsceneStepType.SET_FLAG)
                                .flag("after_pan")
                                .build()))
                .build();
        StoryManager story = new StoryManager();
        CutsceneManager manager = managerWith(story, camera, def);

        assertTrue(manager.start("camera_pan"));
        assertTrue(manager.isActive());
        assertEquals(1, camera.panCalls);
        assertFalse(story.hasFlag("after_pan"));

        manager.tick(0.5f);
        assertTrue(manager.isActive());
        assertFalse(story.hasFlag("after_pan"));

        camera.panActive = false;
        manager.tick(0.5f);

        assertFalse(manager.isActive());
        assertTrue(story.hasFlag("after_pan"));
    }

    @Test
    void cameraRestoreRunsOnCompleteSkipAndEmergencyStop() {
        RecordingCameraController camera = new RecordingCameraController();
        CutsceneDefinition completeDef = new CutsceneDefinition.Builder("complete")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.CAMERA_FOCUS)
                        .target("1,2")
                        .build()))
                .build();
        managerWith(camera, completeDef).start("complete");
        assertEquals(1, camera.restoreCalls);

        camera.restoreCalls = 0;
        CutsceneDefinition skipDef = new CutsceneDefinition.Builder("skip")
                .skipPolicy(SkipPolicy.ALWAYS)
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()))
                .build();
        CutsceneManager skipManager = managerWith(camera, skipDef);
        skipManager.start("skip");
        skipManager.skip();
        assertEquals(1, camera.restoreCalls);

        camera.restoreCalls = 0;
        CutsceneDefinition stopDef = new CutsceneDefinition.Builder("stop")
                .steps(List.of(new CutsceneStep.Builder(CutsceneStepType.WAIT).duration(5f).build()))
                .build();
        CutsceneManager stopManager = managerWith(camera, stopDef);
        stopManager.start("stop");
        stopManager.emergencyStop();
        assertEquals(1, camera.restoreCalls);
    }

    private static CutsceneManager managerWith(CutsceneCameraController camera,
                                               CutsceneDefinition def) {
        return managerWith(new StoryManager(), camera, def);
    }

    private static CutsceneManager managerWith(StoryManager story,
                                               CutsceneCameraController camera,
                                               CutsceneDefinition def) {
        HashMap<String, CutsceneDefinition> defs = new HashMap<>();
        defs.put(def.id, def);
        return new CutsceneManager(
                defs,
                story,
                new DialogueManager(),
                locked -> {},
                new HashSet<>(),
                camera);
    }

    private static final class RecordingCameraController implements CutsceneCameraController {
        int focusCalls;
        int panCalls;
        int restoreCalls;
        float focusX;
        float focusY;
        boolean panActive;
        final AtomicInteger ticks = new AtomicInteger();

        @Override
        public void setCutsceneFocus(float worldX, float worldY) {
            focusCalls++;
            focusX = worldX;
            focusY = worldY;
        }

        @Override
        public void panTo(float worldX, float worldY, float duration) {
            panCalls++;
            panActive = duration > 0f;
        }

        @Override
        public void updateCutscene(float delta) {
            ticks.incrementAndGet();
        }

        @Override
        public boolean isCutscenePanActive() {
            return panActive;
        }

        @Override
        public void restorePlayerFollow() {
            restoreCalls++;
            panActive = false;
        }
    }
}
