package com.indieniinja.client;

import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.math.MathUtils;
import com.indieniinja.client.game.cutscene.CutsceneCameraController;
import com.indieniinja.client.game.cutscene.CutsceneCameraMotion;

/**
 * Camera with deadzone + spring-lerp following — direct port of Python's
 * systems/camera_system.py CameraSystem.
 *
 * The camera only moves when the player leaves the deadzone rectangle.
 * Movement is damped by a spring (LERP) so the camera lags slightly behind,
 * giving a fluid feel without being jarring.
 */
public final class GameCamera implements CutsceneCameraController {

    // Deadzone size in world pixels — matches Python CameraSystem
    private static final float DEADZONE_W = 200f;
    private static final float DEADZONE_H = 150f;

    // Spring stiffness per tick (0.12 → ~7 ticks to cover 50% of remaining distance)
    private static final float SPRING = 0.12f;

    public final OrthographicCamera cam;

    private float targetX;
    private float targetY;
    private final CutsceneCameraMotion cutsceneMotion = new CutsceneCameraMotion();

    public GameCamera(float viewportW, float viewportH) {
        cam = new OrthographicCamera();
        cam.setToOrtho(true, viewportW, viewportH);  // Y-DOWN: matches physics/Python
        cam.update();
        targetX = cam.position.x;
        targetY = cam.position.y;
    }

    /**
     * Move the camera toward the player position.
     * Call once per logic tick (not per render frame) for deterministic feel.
     */
    public void follow(float px, float py) {
        if (cutsceneMotion.isOverrideActive()) return;

        float dx = px - cam.position.x;
        float dy = py - cam.position.y;

        // Expand deadzone tracking target when player exits the box
        if (Math.abs(dx) > DEADZONE_W / 2f)
            targetX = px - Math.signum(dx) * DEADZONE_W / 2f;
        if (Math.abs(dy) > DEADZONE_H / 2f)
            targetY = py - Math.signum(dy) * DEADZONE_H / 2f;

        // Spring interpolation toward target
        cam.position.x += (targetX - cam.position.x) * SPRING;
        cam.position.y += (targetY - cam.position.y) * SPRING;
        cam.update();
    }

    @Override
    public void setCutsceneFocus(float worldX, float worldY) {
        cutsceneMotion.setFocus(worldX, worldY);
        cam.position.x = cutsceneMotion.x();
        cam.position.y = cutsceneMotion.y();
        targetX = worldX;
        targetY = worldY;
        cam.update();
    }

    @Override
    public void panTo(float worldX, float worldY, float duration) {
        cutsceneMotion.panTo(cam.position.x, cam.position.y, worldX, worldY, duration);
        cam.position.x = cutsceneMotion.x();
        cam.position.y = cutsceneMotion.y();
        cam.update();
    }

    @Override
    public void updateCutscene(float delta) {
        if (!cutsceneMotion.isPanActive()) return;
        cutsceneMotion.update(delta);
        cam.position.x = cutsceneMotion.x();
        cam.position.y = cutsceneMotion.y();
        targetX = cam.position.x;
        targetY = cam.position.y;
        cam.update();
    }

    @Override
    public boolean isCutscenePanActive() {
        return cutsceneMotion.isPanActive();
    }

    public boolean isCutsceneOverrideActive() {
        return cutsceneMotion.isOverrideActive();
    }

    @Override
    public void restorePlayerFollow() {
        cutsceneMotion.restore(cam.position.x, cam.position.y);
        targetX = cam.position.x;
        targetY = cam.position.y;
        cam.update();
    }

    /**
     * Prevent the camera from showing area outside the world bounds.
     * Call after follow() each tick.
     */
    public void clampToBounds(float worldW, float worldH) {
        float halfW = cam.viewportWidth  / 2f;
        float halfH = cam.viewportHeight / 2f;
        cam.position.x = MathUtils.clamp(cam.position.x, halfW, Math.max(halfW, worldW  - halfW));
        cam.position.y = MathUtils.clamp(cam.position.y, halfH, Math.max(halfH, worldH  - halfH));
        cam.update();
    }

    /**
     * Instantly reposition the camera with no lerp — use on screen entry to
     * avoid the camera panning from world-origin to the spawn area.
     */
    public void snapTo(float x, float y) {
        cam.position.x = x;
        cam.position.y = y;
        targetX = x;
        targetY = y;
        if (cutsceneMotion.isOverrideActive()) {
            cutsceneMotion.restore(x, y);
        }
        cam.update();
    }

    /** Update viewport on window resize. Preserves Y-DOWN orientation set at construction. */
    public void resize(float w, float h) {
        cam.viewportWidth  = w;
        cam.viewportHeight = h;
        cam.update();
    }
}
