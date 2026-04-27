package com.indieniinja.client.rendering;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.math.Rectangle;
import com.indieniinja.client.GameCamera;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.world.AutotileResolver;
import com.indieniinja.world.WorldGenerator;

/**
 * Renders the tile world with camera frustum culling.
 * Direct equivalent of Python's rendering/tile_loader.py + draw_world().
 *
 * Tile layout is deterministic from a seed — ChunkRenderer receives the
 * tile grid and only draws what is visible in the camera frustum each frame.
 *
 * Asset notes:
 *  - Tiles are loaded from assets/biomes/<biome>/ (PNG per tile variant).
 *  - If no assets are present, a coloured placeholder grid is drawn so the
 *    client can run during development without the full asset pack.
 */
public final class ChunkRenderer {

    private static final int TILE = PhysicsConstants.TILE_SIZE;  // 32 px

    // Tile map — row-major [row][col], null = empty (air)
    private TextureRegion[][] tileMap;
    private int mapCols;
    private int mapRows;

    private TextureRegion placeholderSolid;
    private TextureRegion placeholderPlatform;
    private TextureRegion placeholderLava;
    private TextureRegion placeholderIce;
    private TextureRegion placeholderWater;

    // Scratch rectangle for frustum test
    private final Rectangle frustum = new Rectangle();

    // ── Lantern vignette (M4) ─────────────────────────────────────────────────
    /** Current lantern value [0.0–1.0].  Set each frame from PlayerState. */
    private float lanternValue = 0.8f;

    /** Update the lantern value used for vignette intensity this frame. */
    public void setLanternValue(float value) {
        this.lanternValue = Math.max(0f, Math.min(1f, value));
    }

    // ── Setup ─────────────────────────────────────────────────────────────────

    /**
     * Load the tile map.
     *
     * @param tiles    row-major 2D array of TextureRegions (null = air)
     * @param cols     grid width in tiles
     * @param rows     grid height in tiles
     */
    public void loadTileMap(TextureRegion[][] tiles, int cols, int rows) {
        this.tileMap = tiles;
        this.mapCols = cols;
        this.mapRows = rows;
    }

    /**
     * Fall back to coloured placeholder tiles when running without assets.
     * Generates a simple floor + wall layout matching LevelLayout.buildTestLayout().
     *
     * @param cols total tile columns in the level
     * @param rows total tile rows in the level
     */
    public void loadPlaceholderLayout(int cols, int rows) {
        this.mapCols = cols;
        this.mapRows = rows;

        if (placeholderSolid == null) {
            // Solid tile (grey)
            Pixmap solid = new Pixmap(TILE, TILE, Pixmap.Format.RGBA8888);
            solid.setColor(0.35f, 0.35f, 0.38f, 1f);
            solid.fill();
            solid.setColor(0.25f, 0.25f, 0.28f, 1f);
            solid.drawRectangle(0, 0, TILE - 1, TILE - 1);
            placeholderSolid = new TextureRegion(new Texture(solid));
            solid.dispose();
        }

        if (placeholderPlatform == null) {
            // Platform tile (brown)
            Pixmap plat = new Pixmap(TILE, TILE / 2, Pixmap.Format.RGBA8888);
            plat.setColor(0.55f, 0.38f, 0.20f, 1f);
            plat.fill();
            placeholderPlatform = new TextureRegion(new Texture(plat));
            plat.dispose();
        }

        if (placeholderLava == null) {
            Pixmap lava = new Pixmap(TILE, TILE, Pixmap.Format.RGBA8888);
            lava.setColor(0.90f, 0.25f, 0.05f, 1f);
            lava.fill();
            lava.setColor(1.00f, 0.55f, 0.10f, 1f);
            lava.drawRectangle(2, 2, TILE - 5, TILE - 5);
            placeholderLava = new TextureRegion(new Texture(lava));
            lava.dispose();
        }

        if (placeholderIce == null) {
            Pixmap ice = new Pixmap(TILE, TILE, Pixmap.Format.RGBA8888);
            ice.setColor(0.55f, 0.80f, 1.00f, 1f);
            ice.fill();
            ice.setColor(0.75f, 0.92f, 1.00f, 1f);
            ice.drawRectangle(1, 1, TILE - 3, TILE - 3);
            placeholderIce = new TextureRegion(new Texture(ice));
            ice.dispose();
        }

        if (placeholderWater == null) {
            Pixmap water = new Pixmap(TILE, TILE, Pixmap.Format.RGBA8888);
            water.setColor(0.10f, 0.35f, 0.80f, 0.75f);
            water.fill();
            placeholderWater = new TextureRegion(new Texture(water));
            water.dispose();
        }

        rebuildTestLayout(cols, rows);
    }

    /**
     * Load real tile textures from a biome directory and rebuild the tile map.
     * Falls back to whichever placeholder is already set for any missing file.
     *
     * Expected files in biomeDir:
     *   tile_terrain.png   — solid terrain
     *   tile_platform.png  — one-way platform
     *
     * Call after loadPlaceholderLayout so the grid dimensions are already set.
     */
    public void loadTileTextures(FileHandle biomeDir, int cols, int rows) {
        FileHandle terrainFh  = biomeDir.child("tile_terrain.png");
        FileHandle platformFh = biomeDir.child("tile_platform.png");

        if (terrainFh.exists()) {
            if (placeholderSolid != null) placeholderSolid.getTexture().dispose();
            placeholderSolid = new TextureRegion(new Texture(terrainFh));
            placeholderSolid.flip(false, true);  // Y-DOWN camera correction
        }
        if (platformFh.exists()) {
            if (placeholderPlatform != null) placeholderPlatform.getTexture().dispose();
            placeholderPlatform = new TextureRegion(new Texture(platformFh));
            placeholderPlatform.flip(false, true);  // Y-DOWN camera correction
        }

        rebuildTestLayout(cols, rows);
    }

    /**
     * Load a procedurally generated tile grid produced by WorldGenerator.
     *
     * Tile values: 0=air (null), 1=solid, 2=one-way platform.
     * Call this after placeholderSolid/placeholderPlatform are initialised
     * (i.e. after loadPlaceholderLayout or loadTileTextures).
     *
     * @param grid flat byte[rows*cols] from WorldGenerator.generate() (row-major)
     * @param cols grid width in tiles
     * @param rows grid height in tiles
     */
    public void loadProceduralTiles(byte[] grid, int cols, int rows) {
        this.mapCols = cols;
        this.mapRows = rows;
        this.tileMap = new TextureRegion[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                byte tile = grid[r * cols + c];
                tileMap[r][c] = tileTexture(tile);
            }
        }
    }

    /**
     * Load a procedurally generated tile grid using the mk_nature blob autotile set.
     *
     * For each solid tile the neighbour bitmask is computed via {@link AutotileResolver}
     * and the correct textured variant is looked up from the blob set.  Platform tiles
     * use a fixed isolated-tile variant (role=0) from the same biome.
     *
     * Falls back to the placeholder textures for any role not found in the set.
     *
     * @param blobTiles  loaded BlobTileSet (PNG + JSON)
     * @param biomeIndex biome constant from BlobTileSet (0–4)
     * @param grid2d     byte[rows][cols] from WorldGenerator.generate()
     * @param cols       grid width in tiles
     * @param rows       grid height in tiles
     */
    public void loadBlobTiles(BlobTileSet blobTiles, int biomeIndex,
                              byte[][] grid2d, int cols, int rows) {
        this.mapCols = cols;
        this.mapRows = rows;
        this.tileMap = new TextureRegion[rows][cols];

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                byte tile = grid2d[r][c];
                if (tile == WorldGenerator.SOLID || tile == WorldGenerator.CLIMBABLE) {
                    int role = AutotileResolver.computeRole(grid2d, r, c, rows, cols);
                    tileMap[r][c] = blobTiles.getFrame(biomeIndex, role);
                } else if (tile == WorldGenerator.PLATFORM) {
                    boolean leftP  = c > 0        && grid2d[r][c - 1] == WorldGenerator.PLATFORM;
                    boolean rightP = c < cols - 1 && grid2d[r][c + 1] == WorldGenerator.PLATFORM;
                    tileMap[r][c] = blobTiles.getPlatformFrame(biomeIndex, leftP, rightP);
                } else {
                    // Hazard tiles fall back to colour-coded placeholders
                    tileMap[r][c] = tileTexture(tile);
                }
            }
        }
    }

    /** Expose placeholder textures so callers can build stitched megamap arrays. */
    public TextureRegion placeholderSolid()    { return placeholderSolid; }
    public TextureRegion placeholderPlatform() { return placeholderPlatform; }
    public TextureRegion placeholderLava()     { return placeholderLava; }
    public TextureRegion placeholderIce()      { return placeholderIce; }
    public TextureRegion placeholderWater()    { return placeholderWater; }

    /** Map a WorldGenerator tile byte to its placeholder TextureRegion (null = air). */
    public TextureRegion tileTexture(byte tile) {
        return switch (tile) {
            case com.indieniinja.world.WorldGenerator.SOLID    -> placeholderSolid;
            case com.indieniinja.world.WorldGenerator.PLATFORM -> placeholderPlatform;
            case com.indieniinja.world.WorldGenerator.LAVA     -> placeholderLava;
            case com.indieniinja.world.WorldGenerator.ICE      -> placeholderIce;
            case com.indieniinja.world.WorldGenerator.WATER    -> placeholderWater;
            case com.indieniinja.world.WorldGenerator.CLIMBABLE -> placeholderSolid;
            default -> null;  // AIR and unknowns
        };
    }

    /** Rebuild tileMap grid from the current solid/platform TextureRegions. */
    private void rebuildTestLayout(int cols, int rows) {
        this.mapCols = cols;
        this.mapRows = rows;

        // Coordinate system is Y-DOWN: row 0 = top of world (y=0), row rows-1 = bottom.
        //  - rows rows-4 .. rows-1 : floor across full width  (matches buildProceduralLayout)
        //  - col 0-1 and cols-2..cols-1: solid walls
        this.tileMap = new TextureRegion[rows][cols];
        for (int c = 0; c < cols; c++) {
            for (int r = rows - 4; r < rows; r++) tileMap[r][c] = placeholderSolid;
        }
        for (int r = 0; r < rows; r++) {
            tileMap[r][0]        = placeholderSolid;
            tileMap[r][1]        = placeholderSolid;
            tileMap[r][cols - 2] = placeholderSolid;
            tileMap[r][cols - 1] = placeholderSolid;
        }
    }

    // ── Render ────────────────────────────────────────────────────────────────

    /**
     * Draw all tiles visible inside the camera frustum.
     * SpriteBatch must be begun before this call.
     */
    public void render(SpriteBatch batch, GameCamera camera) {
        if (tileMap == null) return;

        // Camera frustum in world coordinates
        float camX   = camera.cam.position.x;
        float camY   = camera.cam.position.y;
        float halfW  = camera.cam.viewportWidth  / 2f;
        float halfH  = camera.cam.viewportHeight / 2f;
        frustum.set(camX - halfW, camY - halfH, halfW * 2f, halfH * 2f);

        // Tile column/row range visible on screen (with 1-tile margin for partial tiles)
        int colMin = Math.max(0,          (int) Math.floor(frustum.x / TILE) - 1);
        int colMax = Math.min(mapCols - 1,(int) Math.ceil((frustum.x + frustum.width)  / TILE) + 1);
        int rowMin = Math.max(0,          (int) Math.floor(frustum.y / TILE) - 1);
        int rowMax = Math.min(mapRows - 1,(int) Math.ceil((frustum.y + frustum.height) / TILE) + 1);

        for (int r = rowMin; r <= rowMax; r++) {
            for (int c = colMin; c <= colMax; c++) {
                TextureRegion tile = tileMap[r][c];
                if (tile == null) continue;
                float wx = c * TILE;
                float wy = r * TILE;
                batch.draw(tile, wx, wy, TILE, TILE);
            }
        }
    }

    /**
     * Render the Lantern vignette as a screen-space overlay.
     *
     * <p>Must be called <em>after</em> the SpriteBatch world-rendering pass is ended
     * and before the HUD pass begins.  The ShapeRenderer is not begun/ended by the caller
     * — this method wraps its own begin/end.
     *
     * <p>Vignette intensity: when {@code lanternValue} = 1.0 the overlay is fully transparent
     * (no effect).  At 0.0 the screen is heavily darkened with a deep-red tint.
     *
     * <p>Implementation: a base uniform dim pass followed by {@value #VIGNETTE_LAYERS}
     * concentric hollow-rectangle layers that fade toward the centre.  Corner overlap is
     * eliminated by shrinking the horizontal strips so they do not reach the corner regions
     * (vertical strips own the corners).  The per-layer alpha uses an exponential (²)
     * curve for a smoother, more natural falloff.
     *
     * @param shapes   a ShapeRenderer owned by the HUD layer (already has projection set)
     * @param screenW  current screen width in pixels
     * @param screenH  current screen height in pixels
     */
    public void renderVignette(com.badlogic.gdx.graphics.glutils.ShapeRenderer shapes,
                               int screenW, int screenH) {
        // vignetteIntensity: 0 = clear (high lantern), 1 = full dark (low lantern)
        float low  = 0.3f;
        float high = 0.7f;
        float intensity = 1.0f - Math.min(1.0f, Math.max(0f,
            (lanternValue - low) / (high - low)));

        if (intensity < 0.01f) return;

        // Warm-red tint grows as lantern drops below 0.3
        float redBoost = Math.max(0f, 1.0f - lanternValue / low) * 0.30f;
        float r = 0.04f + redBoost;
        float g = 0.00f;
        float b = 0.01f;

        // SpriteBatch.end() (called by the entity/tile render passes above us)
        // disables GL_BLEND.  ShapeRenderer.begin() does NOT re-enable it, so
        // every rect would render as solid-opaque without this call.
        com.badlogic.gdx.Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        com.badlogic.gdx.Gdx.gl.glBlendFunc(
            com.badlogic.gdx.graphics.GL20.GL_SRC_ALPHA,
            com.badlogic.gdx.graphics.GL20.GL_ONE_MINUS_SRC_ALPHA);

        shapes.begin(com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType.Filled);

        // ── Pass 1: uniform full-screen base dim ──────────────────────────────
        // Subtle global darkening so the edge gradient does not float on a
        // bright background.  Only meaningful at low lantern (< 0.3).
        float baseDim = intensity * 0.15f;
        shapes.setColor(r * 0.5f, g, b * 0.4f, baseDim);
        shapes.rect(0, 0, screenW, screenH);

        // ── Pass 2: concentric hollow-rect layers (edge → centre) ────────────
        // Each layer is 4 strips; horizontal strips do NOT reach the side edges
        // so that vertical strips own the corners — eliminates double-alpha bleed.
        int   layers     = VIGNETTE_LAYERS;
        float reach      = Math.min(screenW, screenH) * 0.42f;  // max inset depth
        float stripThick = reach / layers;                       // px per layer
        float maxAlpha   = intensity * 0.82f;

        for (int i = 0; i < layers; i++) {
            float t     = (float) i / layers;           // 0 = outermost, 1 = innermost
            float alpha = maxAlpha * (1.0f - t * t);   // quadratic: sharp edge, soft centre
            float inset = t * reach;

            shapes.setColor(r, g, b, alpha);

            float hInset  = inset + stripThick;         // left/right boundary of horiz strips
            float hWidth  = screenW - hInset * 2f;      // horiz strip spans only the middle
            float vHeight = screenH - inset * 2f;       // vert strips span full remaining height

            // Top strip (middle section only — corners excluded)
            if (hWidth > 0)
                shapes.rect(hInset, screenH - inset - stripThick, hWidth, stripThick);
            // Bottom strip (middle section only)
            if (hWidth > 0)
                shapes.rect(hInset, inset, hWidth, stripThick);
            // Left strip (full height including corners)
            if (vHeight > 0)
                shapes.rect(inset, inset, stripThick, vHeight);
            // Right strip (full height including corners)
            if (vHeight > 0)
                shapes.rect(screenW - inset - stripThick, inset, stripThick, vHeight);
        }

        shapes.end();
    }

    /** Number of concentric layers in the vignette gradient. */
    private static final int VIGNETTE_LAYERS = 20;

    public void dispose() {
        if (placeholderSolid    != null) placeholderSolid.getTexture().dispose();
        if (placeholderPlatform != null) placeholderPlatform.getTexture().dispose();
    }
}
