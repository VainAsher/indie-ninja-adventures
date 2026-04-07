package com.indieniinja.client.rendering;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;

/**
 * Loads the mk_16_16 nature blob-autotile spritesheet and provides per-biome
 * tile lookup.
 *
 * The spritesheet (assets/tileset/mk_nature.png, 128×1136 px, 16×16 tiles)
 * contains 12 blob sets defined in assets/tileset/mk_nature_blob_sets.json.
 * Each blob set has 47 tiles covering all autotile neighbour combinations.
 *
 * Biome → blob set mapping (user's visual grouping):
 *   BIOME_EARTH  (0) → set  0  — earth / above-ground caves
 *   BIOME_GRASS  (1) → set  2  — grassland / forests
 *   BIOME_SNOW   (2) → set  4  — snowy grass
 *   BIOME_SAND   (3) → set  6  — sandy / desert
 *   BIOME_STONE  (4) → set  8  — stone cave / dungeon
 *
 * Role encoding (from mk_nature_blob_sets.json):
 *   bit7(128)=W  bit6(64)=NW  bit5(32)=N  bit4(16)=NE
 *   bit3(  8)=E  bit2( 4)=SE  bit1( 2)=S  bit0( 1)=SW
 */
public final class BlobTileSet {

    // ── Biome constants (caller-friendly names) ───────────────────────────────
    public static final int BIOME_EARTH = 0;
    public static final int BIOME_GRASS = 1;
    public static final int BIOME_SNOW  = 2;
    public static final int BIOME_SAND  = 3;
    public static final int BIOME_STONE = 4;
    public static final int BIOME_COUNT = 5;

    // Maps biome 0-4 to JSON blob-set index 0-11
    private static final int[] BIOME_TO_BLOB_SET = { 0, 2, 4, 6, 8 };

    // ── Spritesheet geometry ──────────────────────────────────────────────────
    private static final int TILE_PX    = 16;   // source tile size in pixels
    private static final int SHEET_COLS = 8;    // tiles per row (128px / 16px)

    // ── State ─────────────────────────────────────────────────────────────────
    private final Texture sheet;

    /** lookup[jsonSetIndex][role 0-255] → TextureRegion (null if role absent in set) */
    private final TextureRegion[][] lookup;

    /** Fallback tile per set when requested role is absent (role=0, isolated tile). */
    private final TextureRegion[] fallback;

    private final int numBlobSets;

    // ── Construction ──────────────────────────────────────────────────────────

    /**
     * Load the tileset.
     *
     * @param pngFile  mk_nature.png
     * @param jsonFile mk_nature_blob_sets.json (the renamed .txt file)
     */
    public BlobTileSet(FileHandle pngFile, FileHandle jsonFile) {
        sheet = new Texture(pngFile);

        int sheetRows  = sheet.getHeight() / TILE_PX;
        int totalTiles = SHEET_COLS * sheetRows;

        // Pre-slice all tiles.  PNG is Y-DOWN (origin top-left); libGDX loads
        // textures with V=0 at bottom (OpenGL convention), so we flip vertically
        // to match the Y-DOWN world camera (same correction used by ChunkRenderer
        // for biome tile assets).
        TextureRegion[] tiles = new TextureRegion[totalTiles];
        for (int id = 0; id < totalTiles; id++) {
            int col = id % SHEET_COLS;
            int row = id / SHEET_COLS;
            TextureRegion r = new TextureRegion(
                sheet, col * TILE_PX, row * TILE_PX, TILE_PX, TILE_PX);
            r.flip(false, true);
            tiles[id] = r;
        }

        // Parse blob sets from JSON
        JsonValue root      = new JsonReader().parse(jsonFile);
        JsonValue blobSetsJ = root.get("blob_sets");
        numBlobSets = blobSetsJ.size;

        lookup   = new TextureRegion[numBlobSets][256];
        fallback = new TextureRegion[numBlobSets];

        for (int si = 0; si < numBlobSets; si++) {
            JsonValue members = blobSetsJ.get(si).get("members");
            for (JsonValue member : members) {
                int id   = member.getInt("id");
                int role = member.getInt("role");
                if (id >= 0 && id < totalTiles) {
                    lookup[si][role] = tiles[id];
                    if (role == 0 || fallback[si] == null) {
                        fallback[si] = tiles[id];   // role=0 preferred fallback
                    }
                }
            }
        }
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Get the tile for a given biome and autotile role.
     *
     * @param biomeIndex game biome index (0–4, use BIOME_* constants)
     * @param role       neighbour bitmask from {@link com.indieniinja.world.AutotileResolver}
     * @return TextureRegion (never null — falls back to role=0 isolated tile)
     */
    public TextureRegion getFrame(int biomeIndex, int role) {
        int si = blobSetFor(biomeIndex);
        TextureRegion r = lookup[si][role & 0xFF];
        return r != null ? r : fallback[si];
    }

    /**
     * Platform tile — uses the role=0 (isolated) variant which renders as a
     * clean single block.  Caller should use this for PLATFORM tiles rather
     * than computing a role from neighbours.
     *
     * @param biomeIndex game biome index (0–4)
     */
    public TextureRegion getPlatformFrame(int biomeIndex) {
        int si = blobSetFor(biomeIndex);
        return fallback[si];  // fallback is always role=0 (isolated)
    }

    /**
     * Derive a biome index (0–4) deterministically from a zone seed.
     * Both client (ChunkRenderer) and server (WorldGenerator) call this so
     * they agree on the biome without extra wire data.
     */
    public static int biomeFromSeed(long seed) {
        return (int)(Math.abs(seed) % BIOME_COUNT);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** Map game biome 0-4 to JSON blob-set index 0-11. */
    private int blobSetFor(int biomeIndex) {
        int b = Math.max(0, Math.min(BIOME_COUNT - 1, biomeIndex));
        int si = BIOME_TO_BLOB_SET[b];
        return Math.min(si, numBlobSets - 1);
    }

    public void dispose() {
        sheet.dispose();
    }
}
