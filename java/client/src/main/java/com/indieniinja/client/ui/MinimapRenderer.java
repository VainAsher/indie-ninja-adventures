package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.WorldRoomDescriptor;

import java.util.List;

/**
 * Minimap overlay — toggled with M key.
 *
 * Draws a large centred overlay showing the world room graph:
 * - Room type colour coding (start, exit, shop, combat, platform, treasure, boss)
 * - Current room outline
 * - Connection lines between adjacent rooms
 * - Player position dot
 *
 * Port of Python rendering/minimap.py MinimapRenderer.
 * Uses WorldRoomDescriptor list (cached in GameScreen from full snapshots).
 */
public final class MinimapRenderer {

    // ── Layout constants ──────────────────────────────────────────────────────
    /** Max panel dimensions — actual size scales to fit the room grid. */
    private static final float MAX_PANEL_W  = 520f;
    private static final float MAX_PANEL_H  = 420f;
    private static final float PANEL_PAD    =  20f;
    /** Gap between room cells. */
    private static final float ROOM_PAD     =   3f;
    /** Title bar height. */
    private static final float TITLE_H      =  22f;
    /** Footer / legend height. */
    private static final float LEGEND_H     =  18f;

    // ── Room type colours (matches Python ROOM_COLORS) ────────────────────────
    private static Color roomColor(String type) {
        return switch (type != null ? type : "combat") {
            case "start"    -> new Color(0.31f, 0.86f, 0.31f, 1f);  // green
            case "exit"     -> new Color(0.86f, 0.31f, 0.31f, 1f);  // red
            case "shop"     -> new Color(0.86f, 0.70f, 0.31f, 1f);  // gold
            case "platform" -> new Color(0.47f, 0.47f, 0.63f, 1f);  // blue-gray
            case "treasure" -> new Color(0.86f, 0.86f, 0.31f, 1f);  // yellow
            case "boss"     -> new Color(0.70f, 0.31f, 0.70f, 1f);  // purple
            default         -> new Color(0.70f, 0.31f, 0.31f, 1f);  // combat = dark red
        };
    }

    // ── State ─────────────────────────────────────────────────────────────────
    private boolean visible = false;

    private final ShapeRenderer shapes;
    private final BitmapFont    font;

    public MinimapRenderer() {
        shapes = new ShapeRenderer();
        font   = new BitmapFont();
        font.getData().setScale(0.85f);
    }

    public boolean isVisible() { return visible; }

    public void toggle() { visible = !visible; }

    public void hide()   { visible = false; }

    /**
     * Handle M-key / ESC input.
     * Returns true if input was consumed.
     */
    public boolean handleInput() {
        if (Gdx.input.isKeyJustPressed(Input.Keys.M)) {
            toggle();
            return true;
        }
        if (visible && Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            visible = false;
            return true;
        }
        return false;
    }

    /**
     * Render the minimap as a large centred overlay.
     *
     * Caller must NOT have the batch open — this method manages its own
     * batch.begin/end around the ShapeRenderer passes, and leaves the batch
     * closed when it returns.
     *
     * @param batch         SpriteBatch with screen-space projection already set.
     * @param rooms         Cached room descriptor list (never null/empty here).
     * @param currentGridX  Current room grid X from WorldSnapshot.
     * @param currentGridY  Current room grid Y from WorldSnapshot.
     * @param playerLocalX  Player X in room-local coords (for dot inside current room).
     * @param playerLocalY  Player Y in room-local coords.
     * @param roomWidthPx   Room width in pixels.
     * @param roomHeightPx  Room height in pixels.
     */
    public void render(SpriteBatch batch,
                       List<WorldRoomDescriptor> rooms,
                       int currentGridX, int currentGridY,
                       float playerLocalX, float playerLocalY,
                       float roomWidthPx, float roomHeightPx) {
        if (!visible || rooms == null || rooms.isEmpty()) return;

        float sw = Gdx.graphics.getWidth();
        float sh = Gdx.graphics.getHeight();

        // ── Compute grid bounds ───────────────────────────────────────────────
        int minGX = rooms.stream().mapToInt(r -> r.gridX).min().getAsInt();
        int minGY = rooms.stream().mapToInt(r -> r.gridY).min().getAsInt();
        int maxGX = rooms.stream().mapToInt(r -> r.gridX).max().getAsInt();
        int maxGY = rooms.stream().mapToInt(r -> r.gridY).max().getAsInt();
        int spanW = maxGX - minGX + 1;
        int spanH = maxGY - minGY + 1;

        // ── Fit room size to panel ────────────────────────────────────────────
        float innerW = MAX_PANEL_W - PANEL_PAD * 2f;
        float innerH = MAX_PANEL_H - PANEL_PAD * 2f - TITLE_H - LEGEND_H;
        float roomSizeW = (innerW - (spanW - 1) * ROOM_PAD) / spanW;
        float roomSizeH = (innerH - (spanH - 1) * ROOM_PAD) / spanH;
        float roomSize  = Math.max(10f, Math.min(roomSizeW, roomSizeH));

        // ── Actual panel dimensions (may be smaller than MAX if fewer rooms) ──
        float gridW  = spanW * roomSize + (spanW - 1) * ROOM_PAD;
        float gridH  = spanH * roomSize + (spanH - 1) * ROOM_PAD;
        float panelW = gridW + PANEL_PAD * 2f;
        float panelH = gridH + PANEL_PAD * 2f + TITLE_H + LEGEND_H;

        // ── Centre on screen ──────────────────────────────────────────────────
        float panelX  = (sw - panelW) * 0.5f;
        float panelY  = (sh - panelH) * 0.5f;
        float gridOriX = panelX + PANEL_PAD;
        float gridOriY = panelY + PANEL_PAD + LEGEND_H;

        shapes.setProjectionMatrix(batch.getProjectionMatrix());

        // ── Background panel ──────────────────────────────────────────────────
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.04f, 0.04f, 0.12f, 0.93f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.45f, 0.45f, 0.75f, 1f);
        shapes.rect(panelX, panelY, panelW, panelH);
        // Title divider
        shapes.line(panelX, panelY + LEGEND_H + gridH + PANEL_PAD * 2f,
                    panelX + panelW, panelY + LEGEND_H + gridH + PANEL_PAD * 2f);
        shapes.end();

        // ── Connection lines (behind rooms) ───────────────────────────────────
        float step = roomSize + ROOM_PAD;
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.28f, 0.28f, 0.42f, 1f);
        for (WorldRoomDescriptor room : rooms) {
            float cx1 = gridOriX + (room.gridX - minGX) * step + roomSize * 0.5f;
            float cy1 = gridOriY + (room.gridY - minGY) * step + roomSize * 0.5f;
            for (String dir : room.neighborDirs) {
                int nx = room.gridX, ny = room.gridY;
                switch (dir) {
                    case "up"    -> ny--;
                    case "down"  -> ny++;
                    case "left"  -> nx--;
                    case "right" -> nx++;
                }
                if (("right".equals(dir) && nx <= maxGX) || ("down".equals(dir) && ny <= maxGY)) {
                    float cx2 = gridOriX + (nx - minGX) * step + roomSize * 0.5f;
                    float cy2 = gridOriY + (ny - minGY) * step + roomSize * 0.5f;
                    shapes.line(cx1, cy1, cx2, cy2);
                }
            }
        }
        shapes.end();

        // ── Room cells ────────────────────────────────────────────────────────
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        for (WorldRoomDescriptor room : rooms) {
            float rx = gridOriX + (room.gridX - minGX) * step;
            float ry = gridOriY + (room.gridY - minGY) * step;
            shapes.setColor(roomColor(room.roomType));
            shapes.rect(rx, ry, roomSize, roomSize);
        }
        shapes.end();

        // ── Current room highlight ─────────────────────────────────────────────
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(1f, 1f, 1f, 1f);
        float crx = gridOriX + (currentGridX - minGX) * step;
        float cry = gridOriY + (currentGridY - minGY) * step;
        shapes.rect(crx - 1.5f, cry - 1.5f, roomSize + 3f, roomSize + 3f);
        shapes.end();

        // ── Player dot ────────────────────────────────────────────────────────
        float normX = roomWidthPx  > 0 ? Math.min(1f, Math.max(0f, playerLocalX / roomWidthPx))  : 0.5f;
        float normY = roomHeightPx > 0 ? Math.min(1f, Math.max(0f, playerLocalY / roomHeightPx)) : 0.5f;
        float dotX  = crx + normX * roomSize;
        float dotY  = cry + normY * roomSize;
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(1f, 1f, 1f, 1f);
        shapes.circle(dotX, dotY, Math.max(3f, roomSize * 0.15f), 10);
        shapes.end();

        // ── Text: title + legend ──────────────────────────────────────────────
        batch.begin();
        font.setColor(0.75f, 0.75f, 1f, 1f);
        font.draw(batch, "MAP  [M] close",
            panelX + PANEL_PAD,
            panelY + panelH - 5f);

        // Legend
        font.getData().setScale(0.72f);
        font.setColor(0.31f, 0.86f, 0.31f, 1f);  font.draw(batch, "■ start",   panelX + PANEL_PAD,          panelY + LEGEND_H - 4f);
        font.setColor(0.86f, 0.31f, 0.31f, 1f);  font.draw(batch, "■ exit",    panelX + PANEL_PAD + 65f,    panelY + LEGEND_H - 4f);
        font.setColor(0.86f, 0.70f, 0.31f, 1f);  font.draw(batch, "■ shop",    panelX + PANEL_PAD + 120f,   panelY + LEGEND_H - 4f);
        font.setColor(0.70f, 0.31f, 0.70f, 1f);  font.draw(batch, "■ boss",    panelX + PANEL_PAD + 178f,   panelY + LEGEND_H - 4f);
        font.setColor(0.86f, 0.86f, 0.31f, 1f);  font.draw(batch, "■ treasure",panelX + PANEL_PAD + 228f,   panelY + LEGEND_H - 4f);
        font.setColor(Color.LIGHT_GRAY);          font.draw(batch, "● you",     panelX + PANEL_PAD + 316f,   panelY + LEGEND_H - 4f);
        font.getData().setScale(0.85f);
        font.setColor(Color.WHITE);
        batch.end();
    }

    public void dispose() {
        shapes.dispose();
        font.dispose();
    }
}
