package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import com.indieniinja.network.NPCState;
import com.indieniinja.network.WorldSnapshot;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class CutsceneEntityStepTest {

    @Test
    void entityStepsDispatchToController() {
        RecordingEntityController entities = new RecordingEntityController();
        CutsceneDefinition def = new CutsceneDefinition.Builder("entity_steps")
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.ENTITY_FACE)
                                .entity("linzi")
                                .target("20,30")
                                .build(),
                        new CutsceneStep.Builder(CutsceneStepType.ENTITY_SET_VISIBLE)
                                .entity("linzi")
                                .value("false")
                                .build(),
                        new CutsceneStep.Builder(CutsceneStepType.ENTITY_PLAY_ANIM)
                                .entity("linzi")
                                .value("gesture")
                                .build()))
                .build();

        CutsceneManager manager = managerWith(def, entities);

        assertTrue(manager.start("entity_steps"));
        assertEquals("linzi", entities.faceEntity);
        assertEquals(20f, entities.faceX, 0.001f);
        assertEquals(30f, entities.faceY, 0.001f);
        assertEquals("linzi", entities.visibleEntity);
        assertFalse(entities.visible);
        assertEquals("linzi", entities.animEntity);
        assertEquals("gesture", entities.animKey);
    }

    @Test
    void entityMoveStepWaitsUntilControllerReportsComplete() {
        RecordingEntityController entities = new RecordingEntityController();
        entities.moveActive = true;
        CutsceneDefinition def = new CutsceneDefinition.Builder("entity_move")
                .steps(List.of(
                        new CutsceneStep.Builder(CutsceneStepType.ENTITY_MOVE_TO)
                                .entity("linzi")
                                .target("100,120")
                                .duration(1f)
                                .build(),
                        new CutsceneStep.Builder(CutsceneStepType.SET_FLAG)
                                .flag("after_move")
                                .build()))
                .build();
        StoryManager story = new StoryManager();
        CutsceneManager manager = managerWith(story, def, entities);

        assertTrue(manager.start("entity_move"));
        assertTrue(manager.isActive());
        assertEquals("linzi", entities.moveEntity);
        assertEquals(100f, entities.moveX, 0.001f);
        assertEquals(120f, entities.moveY, 0.001f);
        assertFalse(story.hasFlag("after_move"));

        manager.tick(0.5f);
        assertTrue(manager.isActive());
        assertEquals(1, entities.updateCalls);

        entities.moveActive = false;
        manager.tick(0.5f);
        assertFalse(manager.isActive());
        assertTrue(story.hasFlag("after_move"));
    }

    @Test
    void entityOverridesMutateMatchingSnapshotNpcs() {
        CutsceneEntityOverrides overrides = new CutsceneEntityOverrides();
        WorldSnapshot snap = new WorldSnapshot();
        NPCState linzi = npc("hub_named_linzi", "linzi", 10f, 20f);
        NPCState tai = npc("hub_named_instructor_tai", "instructor_tai", 100f, 20f);
        snap.npcs.add(linzi);
        snap.npcs.add(tai);

        overrides.faceEntity("linzi", 0f, 20f);
        overrides.playAnimation("linzi", "gesture");
        overrides.setVisible("instructor_tai", false);
        overrides.moveEntityTo("linzi", 50f, 60f, 0f);
        overrides.apply(snap);

        assertEquals(1, snap.npcs.size());
        assertSame(linzi, snap.npcs.get(0));
        assertEquals(-1, linzi.facing);
        assertEquals("gesture", linzi.animState);
        assertEquals(50f, linzi.x, 0.001f);
        assertEquals(60f, linzi.y, 0.001f);
    }

    private static NPCState npc(String npcId, String characterId, float x, float y) {
        NPCState npc = new NPCState();
        npc.npcId = npcId;
        npc.characterId = characterId;
        npc.x = x;
        npc.y = y;
        npc.width = 28;
        npc.height = 56;
        npc.facing = 1;
        npc.animState = "idle";
        npc.isInteractable = true;
        return npc;
    }

    private static CutsceneManager managerWith(CutsceneDefinition def,
                                               CutsceneEntityController entities) {
        return managerWith(new StoryManager(), def, entities);
    }

    private static CutsceneManager managerWith(StoryManager story,
                                               CutsceneDefinition def,
                                               CutsceneEntityController entities) {
        HashMap<String, CutsceneDefinition> defs = new HashMap<>();
        defs.put(def.id, def);
        return new CutsceneManager(
                defs,
                story,
                new DialogueManager(),
                locked -> {},
                new HashSet<>(),
                null,
                CutsceneMarkerRegistry.empty(),
                entities);
    }

    private static final class RecordingEntityController implements CutsceneEntityController {
        String faceEntity;
        float faceX;
        float faceY;
        String visibleEntity;
        boolean visible;
        String animEntity;
        String animKey;
        String moveEntity;
        float moveX;
        float moveY;
        int updateCalls;
        boolean moveActive;

        @Override
        public void faceEntity(String entityId, float worldX, float worldY) {
            faceEntity = entityId;
            faceX = worldX;
            faceY = worldY;
        }

        @Override
        public void moveEntityTo(String entityId, float worldX, float worldY, float duration) {
            moveEntity = entityId;
            moveX = worldX;
            moveY = worldY;
        }

        @Override
        public void setVisible(String entityId, boolean visible) {
            visibleEntity = entityId;
            this.visible = visible;
        }

        @Override
        public void playAnimation(String entityId, String animationKey) {
            animEntity = entityId;
            animKey = animationKey;
        }

        @Override
        public void updateCutsceneEntities(float delta) {
            updateCalls++;
        }

        @Override
        public boolean isEntityMoveActive(String entityId) {
            return moveActive;
        }
    }
}
