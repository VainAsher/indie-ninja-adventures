package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.BossState;
import com.indieniinja.network.EnemyState;
import com.indieniinja.network.NPCState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.PortalState;
import com.indieniinja.network.WorldRoomDescriptor;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.world.WorldGenerator;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Minimap overlay — toggled with TAB key.
 *
 * Three toggleable features (press 1/2/3 while minimap is open):
 *   [1] Tile detail  — pixel mask of the actual tile layout per room
 *   [2] Fog of war   — unvisited rooms remain dark until explored
 *   [3] Entities     — enemies, pickups, boss, NPCs, portals, players
 *
 * The room-graph overview (connections, current-room highlight, player dot)
 * is always visible.
 */
public final class MinimapRenderer {

    // ── Layout ────────────────────────────────────────────────────────────────
    private static final float MAX_PANEL_W = 860f;
    private static final float MAX_PANEL_H = 680f;
    private static final float PANEL_PAD   =  20f;
    private static final float ROOM_PAD    =   4f;
    private static final float TITLE_H     =  22f;
    /** Footer holds room-type legend + toggle-state row. */
    private static final float FOOTER_H    =  46f;

    // ── Tile detail texture: 64×64 downsampled from the 128×128 tile grid ─────
    private static final int TEX_SZ    = 64;
    private static final int GRID_COLS = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
    private static final int GRID_ROWS = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128

    // Pixel colours for the tile-detail Pixmap
    private static final int PIX_SOLID    = Color.rgba8888(0.72f, 0.72f, 0.78f, 1f);
    private static final int PIX_PLATFORM = Color.rgba8888(0.55f, 0.44f, 0.30f, 1f);
    private static final int PIX_AIR      = 0x00000000;  // transparent

    // ── Room type colours + labels ────────────────────────────────────────────
    private static String roomLabel(String type) {
        return switch (type != null ? type : "combat") {
            case "start"    -> "START";
            case "exit"     -> "EXIT";
            case "shop"     -> "SHOP";
            case "platform" -> "PLAT";
            case "treasure" -> "TREAS";
            case "boss"     -> "BOSS";
            default         -> "CMB";
        };
    }

    private static Color roomColor(String type) {
        return switch (type != null ? type : "combat") {
            case "start"    -> new Color(0.31f, 0.86f, 0.31f, 1f);
            case "exit"     -> new Color(0.86f, 0.31f, 0.31f, 1f);
            case "shop"     -> new Color(0.86f, 0.70f, 0.31f, 1f);
            case "platform" -> new Color(0.47f, 0.47f, 0.63f, 1f);
            case "treasure" -> new Color(0.86f, 0.86f, 0.31f, 1f);
            case "boss"     -> new Color(0.70f, 0.31f, 0.70f, 1f);
            default         -> new Color(0.70f, 0.31f, 0.31f, 1f);
        };
    }

    // ── State ─────────────────────────────────────────────────────────────────
    private boolean visible        = false;
    private boolean showTileDetail = false;
    private boolean showFog        = true;
    private boolean showEntities   = true;

    // Zoom: 1 = full world, 2 = 8-room window, 4 = 4-room window
    private int     zoomLevel  = 1;
    // Focused room — MIN_VALUE means "follow current player room"
    private int     focusGX    = Integer.MIN_VALUE;
    private int     focusGY    = Integer.MIN_VALUE;

    private final ShapeRenderer        shapes;
    private final BitmapFont           font;
    /** Cached tile-detail textures, keyed "gx,gy". */
    private final Map<String, Texture> detailTextures = new HashMap<>();

    // ── Colours reused per-frame ──────────────────────────────────────────────
    private static final Color COL_UNVISITED = new Color(0.10f, 0.10f, 0.16f, 1f);
    private static final Color COL_ENEMY     = new Color(1f,    0.22f, 0.22f, 0.90f);
    private static final Color COL_BOSS      = new Color(0.82f, 0.25f, 0.82f, 1f);
    private static final Color COL_NPC       = new Color(1f,    0.55f, 0.12f, 0.90f);
    private static final Color COL_PORTAL    = new Color(0.25f, 0.90f, 0.90f, 0.90f);
    private static final Color COL_SELF      = new Color(1f,    1f,    1f,    1f);
    private static final Color COL_OTHER     = new Color(0.25f, 0.55f, 1f,    0.95f);
    private static final Color COL_ON        = new Color(0.40f, 1f,    0.40f, 1f);
    private static final Color COL_OFF       = new Color(0.50f, 0.50f, 0.50f, 1f);

    public MinimapRenderer() {
        shapes = new ShapeRenderer();
        font   = new BitmapFont();
        font.getData().setScale(0.85f);
    }

    public boolean isVisible() { return visible; }
    public void    toggle()    { visible = !visible; }
    public void    hide()      { visible = false; }

    /**
     * Call on hub/world transition to discard cached tile textures and visited state.
     * The visited-room set lives in GameScreen; this only releases GPU textures.
     */
    public void clearState() {
        for (Texture t : detailTextures.values()) t.dispose();
        detailTextures.clear();
    }

    /**
     * Handle TAB / ESC / 1 / 2 / 3 / + / - / arrow keys.
     * Returns true if the event was consumed.
     */
    public boolean handleInput() {
        if (Gdx.input.isKeyJustPressed(Input.Keys.TAB)) { toggle(); return true; }
        if (!visible) return false;
        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) { visible = false; return true; }
        if (Gdx.input.isKeyJustPressed(Input.Keys.NUM_1)) { showTileDetail = !showTileDetail; return true; }
        if (Gdx.input.isKeyJustPressed(Input.Keys.NUM_2)) { showFog        = !showFog;        return true; }
        if (Gdx.input.isKeyJustPressed(Input.Keys.NUM_3)) { showEntities   = !showEntities;   return true; }
        // Zoom in/out: + / - keys
        if (Gdx.input.isKeyJustPressed(Input.Keys.EQUALS) || Gdx.input.isKeyJustPressed(Input.Keys.PLUS)) {
            zoomLevel = Math.min(4, zoomLevel * 2);
            return true;
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.MINUS)) {
            zoomLevel = Math.max(1, zoomLevel / 2);
            if (zoomLevel == 1) { focusGX = Integer.MIN_VALUE; focusGY = Integer.MIN_VALUE; }
            return true;
        }
        // Pan focused room with arrow keys when zoomed
        if (zoomLevel > 1) {
            if (Gdx.input.isKeyJustPressed(Input.Keys.LEFT))  { if (focusGX != Integer.MIN_VALUE) focusGX--; return true; }
            if (Gdx.input.isKeyJustPressed(Input.Keys.RIGHT)) { if (focusGX != Integer.MIN_VALUE) focusGX++; return true; }
            if (Gdx.input.isKeyJustPressed(Input.Keys.UP))    { if (focusGY != Integer.MIN_VALUE) focusGY--; return true; }
            if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN))  { if (focusGY != Integer.MIN_VALUE) focusGY++; return true; }
        }
        return false;
    }

    /** Returns a distinct colour per pickup type for the minimap dot. */
    private static Color pickupTypeColor(String type) {
        return switch (type != null ? type : "") {
            case "coin"             -> new Color(1.00f, 0.85f, 0.00f, 0.9f);
            case "health_potion"    -> new Color(0.90f, 0.20f, 0.20f, 0.9f);
            case "rare_potion"      -> new Color(0.80f, 0.10f, 0.90f, 0.9f);
            case "gem"              -> new Color(0.10f, 0.90f, 0.90f, 0.9f);
            case "yin_fragment"     -> new Color(0.40f, 0.55f, 1.00f, 1.0f);
            case "yang_fragment"    -> new Color(1.00f, 0.55f, 0.15f, 1.0f);
            case "lantern_fragment" -> new Color(1.00f, 1.00f, 0.35f, 1.0f);
            default                 -> new Color(1.00f, 0.90f, 0.20f, 0.9f);
        };
    }

    /**
     * Render the minimap overlay.
     *
     * Caller must NOT have the batch open — this method manages its own
     * batch/shape passes and leaves both closed when it returns.
     *
     * @param batch          SpriteBatch with screen-space projection set.
     * @param rooms          Cached room descriptor list (never null/empty here).
     * @param currentGridX   Player's current room grid X.
     * @param currentGridY   Player's current room grid Y.
     * @param playerLocalX   Player X in room-local pixels.
     * @param playerLocalY   Player Y in room-local pixels.
     * @param roomWidthPx    Room width  in pixels (for entity normalisation).
     * @param roomHeightPx   Room height in pixels.
     * @param tileGrids      Cached tile grids keyed "gx,gy" — may be empty.
     * @param visitedRooms   Set of visited room keys "gx,gy".
     * @param snap           Latest snapshot for entity positions (may be null).
     * @param cachedEnemies  Stable enemy list (not wiped on delta frames).
     * @param cachedPickups  Stable pickup list.
     * @param cachedPortals  Stable portal list.
     * @param localSlot      Local player slot (for self/other colouring).
     */
    public void render(SpriteBatch batch,
                       List<WorldRoomDescriptor> rooms,
                       int currentGridX, int currentGridY,
                       float playerLocalX, float playerLocalY,
                       float roomWidthPx, float roomHeightPx,
                       Map<String, byte[][]> tileGrids,
                       Set<String>           visitedRooms,
                       com.indieniinja.network.WorldSnapshot snap,
                       List<EnemyState>  cachedEnemies,
                       List<PickupState> cachedPickups,
                       List<PortalState> cachedPortals,
                       int localSlot) {
        if (!visible || rooms == null || rooms.isEmpty()) return;

        float sw = Gdx.graphics.getWidth();
        float sh = Gdx.graphics.getHeight();

        // ── Grid bounds ───────────────────────────────────────────────────────
        int minGX = rooms.stream().mapToInt(r -> r.gridX).min().getAsInt();
        int minGY = rooms.stream().mapToInt(r -> r.gridY).min().getAsInt();
        int maxGX = rooms.stream().mapToInt(r -> r.gridX).max().getAsInt();
        int maxGY = rooms.stream().mapToInt(r -> r.gridY).max().getAsInt();
        int spanW = maxGX - minGX + 1;
        int spanH = maxGY - minGY + 1;

        // ── Zoom: clamp visible grid to a window centred on focus room ────────
        if (zoomLevel > 1) {
            if (focusGX == Integer.MIN_VALUE) { focusGX = currentGridX; focusGY = currentGridY; }
            // Half-width/-height of the visible window (in rooms), at least 2 each side
            int halfW = Math.max(2, spanW / (zoomLevel * 2));
            int halfH = Math.max(2, spanH / (zoomLevel * 2));
            minGX = Math.max(minGX, focusGX - halfW);
            maxGX = Math.min(maxGX, focusGX + halfW);
            minGY = Math.max(minGY, focusGY - halfH);
            maxGY = Math.min(maxGY, focusGY + halfH);
            spanW = maxGX - minGX + 1;
            spanH = maxGY - minGY + 1;
        }

        // ── Fit room cell size ────────────────────────────────────────────────
        float innerW    = MAX_PANEL_W - PANEL_PAD * 2f;
        float innerH    = MAX_PANEL_H - PANEL_PAD * 2f - TITLE_H - FOOTER_H;
        float roomSizeW = (innerW - (spanW - 1) * ROOM_PAD) / spanW;
        float roomSizeH = (innerH - (spanH - 1) * ROOM_PAD) / spanH;
        float roomSize  = Math.max(12f, Math.min(Math.min(roomSizeW, roomSizeH), 80f));

        // ── Panel dimensions ──────────────────────────────────────────────────
        float gridW  = spanW * roomSize + (spanW - 1) * ROOM_PAD;
        float gridH  = spanH * roomSize + (spanH - 1) * ROOM_PAD;
        float panelW = gridW + PANEL_PAD * 2f;
        float panelH = gridH + PANEL_PAD * 2f + TITLE_H + FOOTER_H;

        float panelX   = (sw - panelW) * 0.5f;
        float panelY   = (sh - panelH) * 0.5f;
        float gridOriX = panelX + PANEL_PAD;
        float gridOriY = panelY + PANEL_PAD + FOOTER_H;

        final int   fMaxGY    = maxGY;
        final float fGridOriY = gridOriY;
        final float fStep     = roomSize + ROOM_PAD;

        shapes.setProjectionMatrix(batch.getProjectionMatrix());
        Gdx.gl.glEnable(GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA);

        // ═════════════════════════════════════════════════════════════════════
        // Pass 1 — panel background + room base fills
        // ═════════════════════════════════════════════════════════════════════
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.04f, 0.04f, 0.12f, 0.93f);
        shapes.rect(panelX, panelY, panelW, panelH);

        for (WorldRoomDescriptor room : rooms) {
            if (room.gridX < minGX || room.gridX > maxGX) continue;
            if (room.gridY < minGY || room.gridY > maxGY) continue;
            boolean visited = !showFog || visitedRooms.contains(roomKey(room.gridX, room.gridY));
            float rx = gridOriX + (room.gridX - minGX) * fStep;
            float ry = fGridOriY + (fMaxGY - room.gridY) * fStep;
            if (visited) {
                Color rc = roomColor(room.roomType);
                shapes.setColor(rc.r, rc.g, rc.b, 1f);
            } else {
                shapes.setColor(COL_UNVISITED);
            }
            shapes.rect(rx, ry, roomSize, roomSize);
        }
        shapes.end();

        // ═════════════════════════════════════════════════════════════════════
        // Pass 2 — panel border + title divider + connection lines
        // ═════════════════════════════════════════════════════════════════════
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.45f, 0.45f, 0.75f, 1f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.line(panelX, panelY + FOOTER_H + gridH + PANEL_PAD * 2f,
                    panelX + panelW, panelY + FOOTER_H + gridH + PANEL_PAD * 2f);

        shapes.setColor(0.28f, 0.28f, 0.42f, 1f);
        for (WorldRoomDescriptor room : rooms) {
            if (room.gridX < minGX || room.gridX > maxGX) continue;
            if (room.gridY < minGY || room.gridY > maxGY) continue;
            if (showFog && !visitedRooms.contains(roomKey(room.gridX, room.gridY))) continue;
            float cx1 = gridOriX + (room.gridX - minGX) * fStep + roomSize * 0.5f;
            float cy1 = fGridOriY + (fMaxGY - room.gridY) * fStep + roomSize * 0.5f;
            for (String dir : room.neighborDirs) {
                int nx = room.gridX, ny = room.gridY;
                switch (dir) {
                    case "up"    -> ny--;
                    case "down"  -> ny++;
                    case "left"  -> nx--;
                    case "right" -> nx++;
                }
                if (("right".equals(dir) && nx <= maxGX) || ("down".equals(dir) && ny <= maxGY)) {
                    if (showFog && !visitedRooms.contains(roomKey(nx, ny))) continue;
                    float cx2 = gridOriX + (nx - minGX) * fStep + roomSize * 0.5f;
                    float cy2 = fGridOriY + (fMaxGY - ny) * fStep + roomSize * 0.5f;
                    shapes.line(cx1, cy1, cx2, cy2);
                }
            }
        }
        shapes.end();

        // ═════════════════════════════════════════════════════════════════════
        // Pass 3 — tile detail textures (batch, blended over room fills)
        // ═════════════════════════════════════════════════════════════════════
        if (showTileDetail && !tileGrids.isEmpty()) {
            batch.begin();
            batch.setColor(1f, 1f, 1f, 0.88f);
            for (WorldRoomDescriptor room : rooms) {
                if (room.gridX < minGX || room.gridX > maxGX) continue;
                if (room.gridY < minGY || room.gridY > maxGY) continue;
                String key = roomKey(room.gridX, room.gridY);
                if (showFog && !visitedRooms.contains(key)) continue;
                byte[][] grid = tileGrids.get(key);
                if (grid == null) continue;
                Texture tex = getOrBuildTexture(key, grid);
                float rx = gridOriX + (room.gridX - minGX) * fStep;
                float ry = fGridOriY + (fMaxGY - room.gridY) * fStep;
                batch.draw(tex, rx, ry, roomSize, roomSize);
            }
            batch.setColor(Color.WHITE);
            batch.end();
        }

        // ═════════════════════════════════════════════════════════════════════
        // Pass 4 — entity markers
        // Entity positions are world-space; convert to minimap-space using the
        // room grid derived from the entity's own position.
        // ═════════════════════════════════════════════════════════════════════
        float crx = gridOriX + (currentGridX - minGX) * fStep;
        float cry = fGridOriY + (fMaxGY - currentGridY) * fStep;

        shapes.begin(ShapeRenderer.ShapeType.Filled);
        if (showEntities && roomWidthPx > 0 && roomHeightPx > 0) {
            float dotR = Math.max(2f, roomSize * 0.055f);

            // Enemies
            if (cachedEnemies != null) {
                shapes.setColor(COL_ENEMY);
                for (EnemyState e : cachedEnemies) {
                    if ("dead".equals(e.aiState)) continue;
                    float[] sc = worldToMinimap(e.x, e.y, roomWidthPx, roomHeightPx,
                        minGX, minGY, maxGX, maxGY, gridOriX, fGridOriY, fMaxGY, fStep, roomSize);
                    if (sc != null) shapes.circle(sc[0], sc[1], dotR, 8);
                }
            }

            // Pickups — per-type colour
            if (cachedPickups != null) {
                for (PickupState p : cachedPickups) {
                    if (!p.alive) continue;
                    shapes.setColor(pickupTypeColor(p.pickupType));
                    float[] sc = worldToMinimap(p.x, p.y, roomWidthPx, roomHeightPx,
                        minGX, minGY, maxGX, maxGY, gridOriX, fGridOriY, fMaxGY, fStep, roomSize);
                    if (sc != null) shapes.circle(sc[0], sc[1], dotR * 0.85f, 8);
                }
            }

            // Portals
            if (cachedPortals != null) {
                shapes.setColor(COL_PORTAL);
                for (PortalState p : cachedPortals) {
                    if (!p.isActive) continue;
                    float[] sc = worldToMinimap(p.x + p.width * 0.5f, p.y + p.height * 0.5f,
                        roomWidthPx, roomHeightPx,
                        minGX, minGY, maxGX, maxGY, gridOriX, fGridOriY, fMaxGY, fStep, roomSize);
                    if (sc != null) shapes.circle(sc[0], sc[1], dotR * 1.4f, 10);
                }
            }

            // NPCs / POIs
            if (snap != null) {
                shapes.setColor(COL_NPC);
                for (NPCState n : snap.npcs) {
                    float[] sc = worldToMinimap(n.x, n.y, roomWidthPx, roomHeightPx,
                        minGX, minGY, maxGX, maxGY, gridOriX, fGridOriY, fMaxGY, fStep, roomSize);
                    if (sc != null) {
                        float half = dotR * 0.85f;
                        shapes.rect(sc[0] - half, sc[1] - half, half * 2f, half * 2f);
                    }
                }

                // Boss
                shapes.setColor(COL_BOSS);
                for (BossState b : snap.bosses) {
                    if (!b.alive) continue;
                    float[] sc = worldToMinimap(b.x, b.y, roomWidthPx, roomHeightPx,
                        minGX, minGY, maxGX, maxGY, gridOriX, fGridOriY, fMaxGY, fStep, roomSize);
                    if (sc != null) shapes.circle(sc[0], sc[1], dotR * 2f, 12);
                }

                // Players — self = white, others = blue
                for (PlayerState p : snap.players) {
                    float[] sc = worldToMinimap(p.posX, p.posY, roomWidthPx, roomHeightPx,
                        minGX, minGY, maxGX, maxGY, gridOriX, fGridOriY, fMaxGY, fStep, roomSize);
                    if (sc != null) {
                        shapes.setColor(p.slot == localSlot ? COL_SELF : COL_OTHER);
                        shapes.circle(sc[0], sc[1], dotR * (p.slot == localSlot ? 1.6f : 1.3f), 10);
                    }
                }
            }
        } else {
            // Entities off — still draw the local player dot using pre-computed room-local coords
            float normX = roomWidthPx  > 0 ? clamp01(playerLocalX / roomWidthPx)  : 0.5f;
            float normY = roomHeightPx > 0 ? clamp01(playerLocalY / roomHeightPx) : 0.5f;
            shapes.setColor(COL_SELF);
            shapes.circle(crx + normX * roomSize,
                          cry + (1f - normY) * roomSize,
                          Math.max(3f, roomSize * 0.13f), 10);
        }
        shapes.end();

        // ═════════════════════════════════════════════════════════════════════
        // Pass 5 — current-room outline (only if visible in window)
        // ═════════════════════════════════════════════════════════════════════
        if (currentGridX >= minGX && currentGridX <= maxGX
                && currentGridY >= minGY && currentGridY <= maxGY) {
            shapes.begin(ShapeRenderer.ShapeType.Line);
            shapes.setColor(1f, 1f, 1f, 1f);
            shapes.rect(crx - 1.5f, cry - 1.5f, roomSize + 3f, roomSize + 3f);
            shapes.end();
        }

        // ═════════════════════════════════════════════════════════════════════
        // Pass 5b — room type labels when zoomed in enough (roomSize > 28 px)
        // ═════════════════════════════════════════════════════════════════════
        if (roomSize > 28f) {
            batch.begin();
            font.getData().setScale(Math.min(0.68f, roomSize * 0.014f));
            for (WorldRoomDescriptor room : rooms) {
                if (room.gridX < minGX || room.gridX > maxGX) continue;
                if (room.gridY < minGY || room.gridY > maxGY) continue;
                if (showFog && !visitedRooms.contains(roomKey(room.gridX, room.gridY))) continue;
                Color rc = roomColor(room.roomType);
                font.setColor(Math.min(1f, rc.r * 0.6f + 0.45f),
                              Math.min(1f, rc.g * 0.6f + 0.45f),
                              Math.min(1f, rc.b * 0.6f + 0.45f), 1f);
                float rx = gridOriX + (room.gridX - minGX) * fStep;
                float ry = fGridOriY + (fMaxGY - room.gridY) * fStep;
                font.draw(batch, roomLabel(room.roomType), rx + roomSize * 0.06f, ry + roomSize * 0.52f);
            }
            font.getData().setScale(0.85f);
            font.setColor(Color.WHITE);
            batch.end();
        }

        // ═════════════════════════════════════════════════════════════════════
        // Pass 6 — title + legend + toggle state
        // ═════════════════════════════════════════════════════════════════════
        batch.begin();
        font.setColor(0.75f, 0.75f, 1f, 1f);
        font.draw(batch, "MAP  [TAB] toggle  [ESC] close", panelX + PANEL_PAD, panelY + panelH - 5f);

        float lx = panelX + PANEL_PAD;

        // Room type legend row
        font.getData().setScale(0.72f);
        float ly = panelY + FOOTER_H - 4f;
        font.setColor(0.31f, 0.86f, 0.31f, 1f); font.draw(batch, "■ start",    lx,         ly);
        font.setColor(0.86f, 0.31f, 0.31f, 1f); font.draw(batch, "■ exit",     lx +  60f,  ly);
        font.setColor(0.86f, 0.70f, 0.31f, 1f); font.draw(batch, "■ shop",     lx + 108f,  ly);
        font.setColor(0.70f, 0.31f, 0.70f, 1f); font.draw(batch, "■ boss",     lx + 156f,  ly);
        font.setColor(0.86f, 0.86f, 0.31f, 1f); font.draw(batch, "■ treasure", lx + 204f,  ly);

        // Toggle state row
        font.getData().setScale(0.68f);
        float ty = panelY + FOOTER_H - 21f;
        font.setColor(showTileDetail ? COL_ON : COL_OFF); font.draw(batch, "[1] Detail",   lx,        ty);
        font.setColor(showFog        ? COL_ON : COL_OFF); font.draw(batch, "[2] Fog",      lx +  78f, ty);
        font.setColor(showEntities   ? COL_ON : COL_OFF); font.draw(batch, "[3] Entities", lx + 128f, ty);
        font.setColor(0.72f, 0.88f, 1f, 1f);
        String zoomText = "[+/-] Zoom: " + zoomLevel + "x" + (zoomLevel > 1 ? "  [Arrows] Pan" : "");
        font.draw(batch, zoomText, lx + 258f, ty);

        font.getData().setScale(0.85f);
        font.setColor(Color.WHITE);
        batch.end();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static String roomKey(int gx, int gy) { return gx + "," + gy; }

    private static float clamp01(float v) { return v < 0f ? 0f : (v > 1f ? 1f : v); }

    /**
     * Convert a world-space entity position to minimap screen coordinates.
     * Returns {screenX, screenY} or null if outside the known room grid.
     */
    private static float[] worldToMinimap(
            float worldX, float worldY,
            float roomWidthPx, float roomHeightPx,
            int minGX, int minGY, int maxGX, int maxGY,
            float gridOriX, float gridOriY, int maxGY2,
            float step, float roomSize) {
        // Physics world is 0-based: the room at grid (minGX, minGY) starts at
        // physics (0, 0).  Convert to actual grid coordinates before bounds check.
        int gx = (int) Math.floor(worldX / roomWidthPx) + minGX;
        int gy = (int) Math.floor(worldY / roomHeightPx) + minGY;
        if (gx < minGX || gx > maxGX || gy < minGY || gy > maxGY) return null;
        // Room-local pixel coords — (gx-minGX) is the 0-based room index.
        float localX = worldX - (gx - minGX) * roomWidthPx;
        float localY = worldY - (gy - minGY) * roomHeightPx;
        float rx = gridOriX + (gx - minGX) * step;
        float ry = gridOriY + (maxGY2 - gy) * step;
        return new float[]{
            rx + (localX / roomWidthPx)  * roomSize,
            ry + (1f - localY / roomHeightPx) * roomSize
        };
    }

    /**
     * Build or retrieve a cached tile-detail Texture for the given room.
     * The Pixmap is downsampled 2× (128→64 per axis) and uses Nearest filtering
     * so it renders as crisp pixel art when scaled to the room cell.
     */
    private Texture getOrBuildTexture(String key, byte[][] grid) {
        Texture tex = detailTextures.get(key);
        if (tex != null) return tex;

        Pixmap px = new Pixmap(TEX_SZ, TEX_SZ, Pixmap.Format.RGBA8888);
        px.setBlending(Pixmap.Blending.None);

        int scaleC = GRID_COLS / TEX_SZ;  // 2
        int scaleR = GRID_ROWS / TEX_SZ;  // 2

        for (int tr = 0; tr < TEX_SZ; tr++) {
            for (int tc = 0; tc < TEX_SZ; tc++) {
                int gr = Math.min(tr * scaleR, GRID_ROWS - 1);
                int gc = Math.min(tc * scaleC, GRID_COLS - 1);
                byte tile = grid[gr][gc];
                int color;
                if      (tile == WorldGenerator.SOLID)    color = PIX_SOLID;
                else if (tile == WorldGenerator.PLATFORM) color = PIX_PLATFORM;
                else                                      color = PIX_AIR;
                px.drawPixel(tc, tr, color);
            }
        }

        tex = new Texture(px);
        tex.setFilter(Texture.TextureFilter.Nearest, Texture.TextureFilter.Nearest);
        px.dispose();
        detailTextures.put(key, tex);
        return tex;
    }

    public void dispose() {
        shapes.dispose();
        font.dispose();
        clearState();
    }
}
