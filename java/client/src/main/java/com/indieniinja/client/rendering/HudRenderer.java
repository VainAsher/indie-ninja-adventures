package com.indieniinja.client.rendering;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;

/**
 * Renders the in-game HUD using ShapeRenderer (health bars) + BitmapFont (text).
 *
 * Equivalent of Python's rendering/hud_renderer.py.
 *
 * Drawn in screen space — the SpriteBatch projection must be set to the screen
 * (identity or screen-space camera) before calling render(). NinjaGameClient
 * resets the projection after world rendering.
 *
 * Layout (top-left origin, Y up):
 *   [10, screenH - 10]  Slot 0 health bar
 *   [10, screenH - 35]  Slot 1 health bar (if second player connected)
 *   …
 *   [screenW - 80, 10]  Connection indicator
 *   [screenW - 80, 25]  FPS counter (debug)
 */
public final class HudRenderer {

    // Health bar dimensions
    private static final float BAR_W     = 100f;
    private static final float BAR_H     = 12f;
    private static final float BAR_GAP   = 20f;
    private static final int   MAX_HP    = 5;

    private final ShapeRenderer shapes;
    private final SpriteBatch   hudBatch;
    private final BitmapFont    font;

    private final OrthographicCamera screenCam;

    public HudRenderer() {
        shapes    = new ShapeRenderer();
        hudBatch  = new SpriteBatch();
        font      = new BitmapFont();   // built-in libGDX 15px font
        font.setColor(Color.WHITE);

        screenCam = new OrthographicCamera();
        screenCam.setToOrtho(false, Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
    }

    /**
     * Render the full HUD for this frame.
     *
     * @param snap        latest world snapshot (may be null before first server message)
     * @param connected   whether the network client has an active connection
     * @param fps         current frames per second (for debug overlay)
     * @param localSlot   which player slot belongs to this client (for highlighting)
     */
    public void render(WorldSnapshot snap, boolean connected, int fps, int localSlot) {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();

        screenCam.setToOrtho(false, sw, sh);
        screenCam.update();

        // ── Health bars (ShapeRenderer pass) ──────────────────────────────────
        shapes.setProjectionMatrix(screenCam.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);

        if (snap != null) {
            for (int i = 0; i < snap.players.size(); i++) {
                PlayerState p = snap.players.get(i);
                float barX = 10f;
                float barY = sh - 14f - i * BAR_GAP;

                // Background (dark grey)
                shapes.setColor(0.2f, 0.2f, 0.2f, 0.8f);
                shapes.rect(barX, barY, BAR_W, BAR_H);

                // Filled portion
                float ratio = Math.max(0f, Math.min(1f, (float) p.health / MAX_HP));
                Color barColor = healthColor(ratio);
                shapes.setColor(barColor);
                shapes.rect(barX, barY, BAR_W * ratio, BAR_H);

                // Highlight local player
                if (p.slot == localSlot) {
                    shapes.setColor(1f, 1f, 0f, 0.5f);
                    shapes.rect(barX - 2, barY - 2, BAR_W + 4, BAR_H + 4);
                }
            }
        }

        // Connection indicator dot
        shapes.setColor(connected ? Color.GREEN : Color.RED);
        shapes.circle(sw - 12f, 12f, 6f);

        shapes.end();

        // ── Text pass (SpriteBatch) ───────────────────────────────────────────
        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();

        // Player health labels
        if (snap != null) {
            for (int i = 0; i < snap.players.size(); i++) {
                PlayerState p = snap.players.get(i);
                float labelX = 10f + BAR_W + 5f;
                float labelY = sh - 4f - i * BAR_GAP;
                String label = (p.slot == localSlot ? "You" : "P" + (p.slot + 1))
                    + "  " + p.health + "/" + MAX_HP;
                font.draw(hudBatch, label, labelX, labelY);
            }
        }

        // Connection status
        String connText = connected ? "Online" : "Offline";
        font.draw(hudBatch, connText, sw - 65f, 25f);

        // FPS counter
        font.draw(hudBatch, fps + " fps", sw - 60f, 40f);

        // Frame number (debug)
        if (snap != null) {
            font.draw(hudBatch, "f:" + snap.frame, sw - 60f, 55f);
        }

        hudBatch.end();
    }

    public void resize(int w, int h) {
        screenCam.setToOrtho(false, w, h);
        screenCam.update();
    }

    public void dispose() {
        shapes.dispose();
        hudBatch.dispose();
        font.dispose();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static Color healthColor(float ratio) {
        if (ratio > 0.6f) return Color.GREEN;
        if (ratio > 0.3f) return Color.YELLOW;
        return Color.RED;
    }
}
