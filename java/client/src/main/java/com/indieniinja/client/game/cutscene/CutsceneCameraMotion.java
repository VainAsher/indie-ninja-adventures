package com.indieniinja.client.game.cutscene;

import com.badlogic.gdx.math.MathUtils;

public final class CutsceneCameraMotion {
    private boolean overrideActive;
    private boolean panActive;
    private float x;
    private float y;
    private float panStartX;
    private float panStartY;
    private float panTargetX;
    private float panTargetY;
    private float panDuration;
    private float panElapsed;

    public void setFocus(float worldX, float worldY) {
        overrideActive = true;
        panActive = false;
        x = worldX;
        y = worldY;
    }

    public void panTo(float currentX, float currentY, float worldX, float worldY, float duration) {
        overrideActive = true;
        panStartX = currentX;
        panStartY = currentY;
        panTargetX = worldX;
        panTargetY = worldY;
        panDuration = Math.max(0f, duration);
        panElapsed = 0f;
        if (panDuration <= 0f) {
            setFocus(worldX, worldY);
            return;
        }
        x = currentX;
        y = currentY;
        panActive = true;
    }

    public void update(float delta) {
        if (!panActive) return;
        panElapsed = Math.min(panDuration, panElapsed + Math.max(0f, delta));
        float t = panDuration <= 0f ? 1f : panElapsed / panDuration;
        x = MathUtils.lerp(panStartX, panTargetX, t);
        y = MathUtils.lerp(panStartY, panTargetY, t);
        if (panElapsed >= panDuration) {
            panActive = false;
            x = panTargetX;
            y = panTargetY;
        }
    }

    public void restore(float currentX, float currentY) {
        overrideActive = false;
        panActive = false;
        x = currentX;
        y = currentY;
    }

    public boolean isOverrideActive() {
        return overrideActive;
    }

    public boolean isPanActive() {
        return panActive;
    }

    public float x() {
        return x;
    }

    public float y() {
        return y;
    }
}
