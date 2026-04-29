package com.indieniinja.client.game.cutscene;

import com.indieniinja.network.NPCState;
import com.indieniinja.network.WorldSnapshot;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

public final class CutsceneEntityOverrides implements CutsceneEntityController {
    private final Map<String, OverrideState> overrides = new HashMap<>();

    @Override
    public void faceEntity(String entityId, float worldX, float worldY) {
        if (blank(entityId)) return;
        OverrideState state = state(entityId);
        state.faceTargetSet = true;
        state.faceTargetX = worldX;
    }

    @Override
    public void moveEntityTo(String entityId, float worldX, float worldY, float duration) {
        if (blank(entityId)) return;
        OverrideState state = state(entityId);
        state.moveTargetSet = true;
        state.moveTargetX = worldX;
        state.moveTargetY = worldY;
        state.moveDuration = Math.max(0f, duration);
        state.moveElapsed = 0f;
        state.moveActive = state.moveDuration > 0f;
        if (!state.moveActive) {
            state.xSet = true;
            state.x = worldX;
            state.y = worldY;
        }
    }

    @Override
    public void setVisible(String entityId, boolean visible) {
        if (blank(entityId)) return;
        OverrideState state = state(entityId);
        state.visibleSet = true;
        state.visible = visible;
    }

    @Override
    public void playAnimation(String entityId, String animationKey) {
        if (blank(entityId) || blank(animationKey)) return;
        OverrideState state = state(entityId);
        state.animKey = animationKey;
    }

    @Override
    public void updateCutsceneEntities(float delta) {
        float dt = Math.max(0f, delta);
        for (OverrideState state : overrides.values()) {
            if (!state.moveActive) continue;
            state.moveElapsed = Math.min(state.moveDuration, state.moveElapsed + dt);
            if (state.moveElapsed >= state.moveDuration) {
                state.moveActive = false;
                state.xSet = true;
                state.x = state.moveTargetX;
                state.y = state.moveTargetY;
            }
        }
    }

    @Override
    public boolean isEntityMoveActive(String entityId) {
        OverrideState state = overrides.get(entityId);
        return state != null && state.moveActive;
    }

    public void clear() {
        overrides.clear();
    }

    public void apply(WorldSnapshot snap) {
        if (snap == null || overrides.isEmpty()) return;
        applyList(snap.npcs);
        applyList(snap.overflowNpcs);
    }

    private void applyList(java.util.List<NPCState> npcs) {
        for (Iterator<NPCState> it = npcs.iterator(); it.hasNext();) {
            NPCState npc = it.next();
            OverrideState state = findState(npc);
            if (state == null) continue;
            if (state.visibleSet && !state.visible) {
                it.remove();
                continue;
            }
            if (state.xSet) {
                npc.x = state.x;
                npc.y = state.y;
            } else if (state.moveTargetSet && state.moveDuration <= 0f) {
                npc.x = state.moveTargetX;
                npc.y = state.moveTargetY;
            }
            if (state.faceTargetSet) {
                float centerX = npc.x + npc.width * 0.5f;
                npc.facing = state.faceTargetX < centerX ? -1 : 1;
            }
            if (!blank(state.animKey)) {
                npc.animState = state.animKey;
            }
        }
    }

    private OverrideState findState(NPCState npc) {
        if (npc == null) return null;
        OverrideState state = overrides.get(npc.npcId);
        if (state != null) return state;
        return overrides.get(npc.characterId);
    }

    private OverrideState state(String entityId) {
        return overrides.computeIfAbsent(entityId, ignored -> new OverrideState());
    }

    private static boolean blank(String value) {
        return value == null || value.isBlank();
    }

    private static final class OverrideState {
        boolean visibleSet;
        boolean visible = true;
        boolean faceTargetSet;
        float faceTargetX;
        boolean moveTargetSet;
        boolean moveActive;
        float moveTargetX;
        float moveTargetY;
        float moveDuration;
        float moveElapsed;
        boolean xSet;
        float x;
        float y;
        String animKey;
    }
}
