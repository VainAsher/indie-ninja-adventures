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
 * Draws a room-grid overview of the current world graph showing:
 * - Room type color coding (start, exit, shop, combat, platform, treasure, boss)
 * - Current room outline
 * - Connection lines between adjacent rooms
 * - Player position dot
 *
 * Port of Python rendering/minimap.py MinimapRenderer.
 * Uses WorldRoomDescriptor list from WorldSnapshot (sent on full snapshots).
 */
public final class MinimapRenderer {

    // ── Layout constants ──────────────────────────────────────────────────────
    private static final float ROOM_SIZE = 14f;  // pixels per room cell
    private static final float ROOM_PAD  =  2f;  // gap between cells
    private static final float PANEL_PAD = 10f;
    private static final float PANEL_X   = 10f;
    private static final float PANEL_Y_OFFSET = 80f; // from screen bottom

    // ── Room type colors (matches Python ROOM_COLORS) ─────────────────────────
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
        font.getData().setScale(0.75f);
    }

    public boolean isVisible() { return visible; }

    public void toggle() { visible = !visible; }

    public void hide()   { visible = false; }

    /**
     * Handle M-key input.
     * Returns true if input was consumed.
     */
    public boolean handleInput() {
        if (Gdx.input.isKeyJustPressed(Input.Keys.M)) {
            toggle();
            return true;
        }
        return false;
    }

    /**
     * Render the minimap in screen space.
     *
     * @param batch         SpriteBatch with screen-space projection already set.
     * @param rooms         Room descriptor list from WorldSnapshot.worldRooms.
     * @param currentGridX  Current room grid X from WorldSnapshot.
     * @param currentGridY  Current room grid Y from WorldSnapshot.
     * @param playerLocalX  Player X position in room-local coords.
     * @param playerLocalY  Player Y position in room-local coords.
     * @param roomWidthPx   Room width in pixels (for normalising player pos).
     * @param roomHeightPx  Room height in pixels.
     */
    public void render(SpriteBatch batch,
                       List<WorldRoomDescriptor> rooms,
                       int currentGridX, int currentGridY,
                       float playerLocalX, float playerLocalY,
                       float roomWidthPx, float roomHeightPx) {
        if (!visible || rooms == null || rooms.isEmpty()) return;

        // Compute bounds
        int minGX = rooms.stream().mapToInt(r -> r.gridX).min().getAsInt();
        int minGY = rooms.stream().mapToInt(r -> r.gridY).min().getAsInt();
        int maxGX = rooms.stream().mapToInt(r -> r.gridX).max().getAsInt();
        int maxGY = rooms.stream().mapToInt(r -> r.gridY).max().getAsInt();
        int spanW = maxGX - minGX + 1;
        int spanH = maxGY - minGY + 1;

        float step    = ROOM_SIZE + ROOM_PAD;
        float mapW    = spanW * step - ROOM_PAD + PANEL_PAD * 2f;
        float mapH    = spanH * step - ROOM_PAD + PANEL_PAD * 2f + 14f; // +14 for title
        float panelX  = PANEL_X;
        float panelY  = PANEL_Y_OFFSET;
        float gridOriX = panelX + PANEL_PAD;
        float gridOriY = panelY + PANEL_PAD;

        // ── Background ────────────────────────────────────────────────────────
        batch.end();
        shapes.setProjectionMatrix(batch.getProjectionMatrix());

        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.05f, 0.05f, 0.12f, 0.88f);
        shapes.rect(panelX, panelY, mapW, mapH);
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.4f, 0.4f, 0.6f, 1f);
        shapes.rect(panelX, panelY, mapW, mapH);
        shapes.end();

        // ── Connection lines (behind rooms) ───────────────────────────────────
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.3f, 0.3f, 0.4f, 1f);
        for (WorldRoomDescriptor room : rooms) {
            float cx1 = gridOriX + (room.gridX - minGX) * step + ROOM_SIZE * 0.5f;
            float cy1 = gridOriY + (room.gridY - minGY) * step + ROOM_SIZE * 0.5f;
            for (String dir : room.neighborDirs) {
                int nx = room.gridX, ny = room.gridY;
                switch (dir) {
                    case "up"    -> ny--;
                    case "down"  -> ny++;
                    case "left"  -> nx--;
                    case "right" -> nx++;
                }
                // Only draw line if neighbour is in our list (avoid duplicates by only right/down)
                if (("right".equals(dir) && nx <= maxGX) || ("down".equals(dir) && ny <= maxGY)) {
                    float cx2 = gridOriX + (nx - minGX) * step + ROOM_SIZE * 0.5f;
                    float cy2 = gridOriY + (ny - minGY) * step + ROOM_SIZE * 0.5f;
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
            shapes.rect(rx, ry, ROOM_SIZE, ROOM_SIZE);
        }
        shapes.end();

        // ── Current room highlight ─────────────────────────────────────────────
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(1f, 1f, 1f, 1f);
        float crx = gridOriX + (currentGridX - minGX) * step;
        float cry = gridOriY + (currentGridY - minGY) * step;
        shapes.rect(crx - 1f, cry - 1f, ROOM_SIZE + 2f, ROOM_SIZE + 2f);
        shapes.end();

        // ── Player dot ────────────────────────────────────────────────────────
        float normX = roomWidthPx  > 0 ? Math.min(1f, Math.max(0f, playerLocalX / roomWidthPx))  : 0.5f;
        float normY = roomHeightPx > 0 ? Math.min(1f, Math.max(0f, playerLocalY / roomHeightPx)) : 0.5f;
        float dotX  = crx + normX * ROOM_SIZE;
        float dotY  = cry + normY * ROOM_SIZE;

        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(Color.WHITE);
        shapes.circle(dotX, dotY, 2.5f, 8);
        shapes.end();

        // ── Title ─────────────────────────────────────────────────────────────
        batch.begin();
        font.setColor(0.7f, 0.7f, 1f, 1f);
        font.draw(batch, "[M] map", panelX + PANEL_PAD, panelY + mapH - 2f);

        // Legend dots (small inline)
        font.setColor(Color.LIGHT_GRAY);
        font.draw(batch, "■start ■exit ■shop ■boss",
            panelX + PANEL_PAD, panelY + 10f);
        font.setColor(Color.WHITE);
        batch.end();

        batch.begin(); // re-open for caller
    }

    public void dispose() {
        shapes.dispose();
        font.dispose();
    }
}
