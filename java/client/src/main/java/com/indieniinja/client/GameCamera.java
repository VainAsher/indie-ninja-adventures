package com.indieniinja.client;

import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.math.MathUtils;

/**
 * Camera with deadzone + spring-lerp following — direct port of Python's
 * systems/camera_system.py CameraSystem.
 *
 * The camera only moves when the player leaves the deadzone rectangle.
 * Movement is damped by a spring (LERP) so the camera lags slightly behind,
 * giving a fluid feel without being jarring.
 */
public final class GameCamera {

    // Deadzone size in world pixels — matches Python CameraSystem
    private static final float DEADZONE_W = 200f;
    private static final float DEADZONE_H = 150f;

    // Spring stiffness per tick (0.12 → ~7 ticks to cover 50% of remaining distance)
    private static final float SPRING = 0.12f;

    public final OrthographicCamera cam;

    private float targetX;
    private float targetY;

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

    /** Update viewport on window resize. Preserves Y-DOWN orientation set at construction. */
    public void resize(float w, float h) {
        cam.viewportWidth  = w;
        cam.viewportHeight = h;
        cam.update();
    }
}
