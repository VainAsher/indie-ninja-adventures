package com.indieniinja.client.game.cutscene;

public final class CutsceneTriggerRouter {
    private final CutsceneManager manager;

    public CutsceneTriggerRouter(CutsceneManager manager) {
        this.manager = manager;
    }

    public boolean onNpcInteract(String npcId) {
        return startFirst(CutsceneTriggerType.NPC_INTERACT, npcId);
    }

    public boolean onMissionComplete(String missionId) {
        return startFirst(CutsceneTriggerType.MISSION_COMPLETE, missionId);
    }

    public boolean onFlagChange(String flag) {
        return startFirst(CutsceneTriggerType.FLAG_CHANGE, flag);
    }

    public boolean onCampaignStart() {
        if (manager == null) return false;
        for (CutsceneDefinition def : manager.definitions().values()) {
            if (def.hasTrigger(CutsceneTriggerType.CAMPAIGN_START, "") && manager.start(def.id)) {
                return true;
            }
        }
        return false;
    }

    private boolean startFirst(CutsceneTriggerType type, String id) {
        if (manager == null || id == null || id.isBlank()) return false;
        for (CutsceneDefinition def : manager.definitions().values()) {
            if (def.hasTrigger(type, id) && manager.start(def.id)) {
                return true;
            }
        }
        return false;
    }
}
