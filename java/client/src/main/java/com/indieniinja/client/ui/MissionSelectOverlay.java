package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.GlyphLayout;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.client.game.MissionDefinition;
import com.indieniinja.client.game.MissionManager;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * Dedicated mission-selection overlay opened from dialogue events.
 *
 * Controls:
 * - Up/Down: select mission
 * - Enter/E: start selected mission
 * - Esc/M: close
 */
public final class MissionSelectOverlay {

    private static final float PANEL_W = 860f;
    private static final float PANEL_H = 520f;
    private static final float PAD = 18f;
    private static final float ROW_H = 74f;
    private static final int MAX_ROWS = 5;

    private final MissionManager missionManager;
    private final BitmapFont font;
    private final ShapeRenderer shapes;
    private final GlyphLayout layout = new GlyphLayout();

    private final List<MissionDefinition> visibleMissions = new ArrayList<>();
    private boolean visible = false;
    private int selected = 0;

    private Consumer<String> onStartMission = id -> {};
    private Runnable onClose = () -> {};

    public MissionSelectOverlay(MissionManager missionManager) {
        this.missionManager = missionManager;
        this.font = new BitmapFont();
        this.shapes = new ShapeRenderer();
    }

    public boolean isVisible() { return visible; }

    public void open(int currentAct) {
        visible = true;
        selected = 0;
        refresh(currentAct);
    }

    public void hide() { visible = false; }

    public void setOnStartMission(Consumer<String> cb) {
        onStartMission = cb != null ? cb : id -> {};
    }

    public void setOnClose(Runnable cb) {
        onClose = cb != null ? cb : () -> {};
    }

    public boolean handleInput(int currentAct) {
        if (!visible) return false;
        refresh(currentAct);

        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)
                || Gdx.input.isKeyJustPressed(Input.Keys.M)) {
            visible = false;
            onClose.run();
            return true;
        }

        if (visibleMissions.isEmpty()) return true;

        if (Gdx.input.isKeyJustPressed(Input.Keys.UP)) {
            selected = (selected - 1 + visibleMissions.size()) % visibleMissions.size();
            return true;
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN)) {
            selected = (selected + 1) % visibleMissions.size();
            return true;
        }

        if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER)
                || Gdx.input.isKeyJustPressed(Input.Keys.E)) {
            MissionDefinition def = visibleMissions.get(selected);
            onStartMission.accept(def.missionId);
            visible = false;
            onClose.run();
            return true;
        }
        return true;
    }

    public void render(SpriteBatch batch, int currentAct) {
        if (!visible) return;
        refresh(currentAct);

        float sw = Gdx.graphics.getWidth();
        float sh = Gdx.graphics.getHeight();
        float panelX = (sw - PANEL_W) * 0.5f;
        float panelY = (sh - PANEL_H) * 0.5f;

        batch.end();
        shapes.setProjectionMatrix(batch.getProjectionMatrix());
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0f, 0f, 0f, 0.70f);
        shapes.rect(0f, 0f, sw, sh);
        shapes.setColor(0.06f, 0.08f, 0.16f, 0.95f);
        shapes.rect(panelX, panelY, PANEL_W, PANEL_H);
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.35f, 0.55f, 0.95f, 1f);
        shapes.rect(panelX, panelY, PANEL_W, PANEL_H);
        shapes.end();
        batch.begin();

        font.setColor(Color.WHITE);
        font.getData().setScale(1.15f);
        font.draw(batch, "MISSION SELECT", panelX + PAD, panelY + PANEL_H - PAD);
        font.getData().setScale(1f);

        font.setColor(new Color(0.7f, 0.78f, 0.95f, 1f));
        font.draw(batch, "[UP/DOWN] Select   [ENTER/E] Start   [ESC/M] Close",
            panelX + PAD, panelY + PANEL_H - PAD - 22f);

        float listX = panelX + PAD;
        float listY = panelY + PANEL_H - 62f;

        if (visibleMissions.isEmpty()) {
            font.setColor(new Color(0.85f, 0.55f, 0.55f, 1f));
            font.draw(batch, "No available missions for current act.",
                listX, listY - 24f);
            font.setColor(Color.WHITE);
            return;
        }

        int start = 0;
        if (selected >= MAX_ROWS) {
            start = selected - MAX_ROWS + 1;
        }
        int end = Math.min(visibleMissions.size(), start + MAX_ROWS);

        for (int i = start; i < end; i++) {
            MissionDefinition m = visibleMissions.get(i);
            float rowTop = listY - (i - start) * ROW_H;
            float rowY = rowTop - ROW_H + 8f;
            boolean isSel = (i == selected);

            batch.end();
            shapes.begin(ShapeRenderer.ShapeType.Filled);
            if (isSel) {
                shapes.setColor(0.20f, 0.33f, 0.60f, 0.65f);
            } else {
                shapes.setColor(0.10f, 0.13f, 0.20f, 0.55f);
            }
            shapes.rect(listX, rowY, PANEL_W - PAD * 2f, ROW_H - 10f);
            shapes.end();
            batch.begin();

            font.setColor(isSel ? Color.WHITE : new Color(0.86f, 0.90f, 1f, 1f));
            font.draw(batch, m.missionName + "  (" + m.missionId + ")",
                listX + 12f, rowTop - 20f);

            font.setColor(new Color(0.72f, 0.82f, 1f, 1f));
            String meta = "Act " + m.act + "  |  Difficulty " + m.difficulty
                + "  |  Rooms " + m.roomCount + "  |  Region " + m.region;
            font.draw(batch, meta, listX + 12f, rowTop - 39f);

            font.setColor(new Color(0.76f, 0.76f, 0.82f, 1f));
            String desc = m.description != null ? m.description : "";
            if (desc.length() > 94) desc = desc.substring(0, 91) + "...";
            font.draw(batch, desc, listX + 12f, rowTop - 56f);
        }

        // Scroll hint
        if (visibleMissions.size() > MAX_ROWS) {
            String hint = "Showing " + (start + 1) + "-" + end + " of " + visibleMissions.size();
            layout.setText(font, hint);
            font.setColor(new Color(0.65f, 0.70f, 0.85f, 1f));
            font.draw(batch, hint,
                panelX + PANEL_W - PAD - layout.width,
                panelY + 20f);
        }

        font.setColor(Color.WHITE);
    }

    private void refresh(int currentAct) {
        visibleMissions.clear();
        visibleMissions.addAll(missionManager.availableMissions(currentAct));
        if (visibleMissions.isEmpty()) {
            selected = 0;
            return;
        }
        if (selected < 0) selected = 0;
        if (selected >= visibleMissions.size()) selected = visibleMissions.size() - 1;
    }

    public void dispose() {
        font.dispose();
        shapes.dispose();
    }
}
