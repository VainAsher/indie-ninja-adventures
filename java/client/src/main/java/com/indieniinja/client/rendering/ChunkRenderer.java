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

    // Scratch rectangle for frustum test
    private final Rectangle frustum = new Rectangle();

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
                if      (tile == WorldGenerator.SOLID)    tileMap[r][c] = placeholderSolid;
                else if (tile == WorldGenerator.PLATFORM) tileMap[r][c] = placeholderPlatform;
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
                if (tile == WorldGenerator.SOLID) {
                    int role = AutotileResolver.computeRole(grid2d, r, c, rows, cols);
                    tileMap[r][c] = blobTiles.getFrame(biomeIndex, role);
                } else if (tile == WorldGenerator.PLATFORM) {
                    tileMap[r][c] = blobTiles.getPlatformFrame(biomeIndex);
                }
                // AIR → null, already null from array init
            }
        }
    }

    /** Expose placeholder textures so callers can build stitched megamap arrays. */
    public TextureRegion placeholderSolid()    { return placeholderSolid; }
    public TextureRegion placeholderPlatform() { return placeholderPlatform; }

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

    public void dispose() {
        if (placeholderSolid    != null) placeholderSolid.getTexture().dispose();
        if (placeholderPlatform != null) placeholderPlatform.getTexture().dispose();
    }
}
