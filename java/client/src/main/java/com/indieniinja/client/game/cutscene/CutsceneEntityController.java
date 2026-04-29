package com.indieniinja.client.game.cutscene;

public interface CutsceneEntityController {
    void faceEntity(String entityId, float worldX, float worldY);

    void moveEntityTo(String entityId, float worldX, float worldY, float duration);

    void setVisible(String entityId, boolean visible);

    void playAnimation(String entityId, String animationKey);

    void updateCutsceneEntities(float delta);

    boolean isEntityMoveActive(String entityId);
}
