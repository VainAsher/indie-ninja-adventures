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
    // Named biomes — these select the primary blob-set for each visual theme.
    public static final int BIOME_EARTH = 0;
    public static final int BIOME_GRASS = 1;
    public static final int BIOME_SNOW  = 2;
    public static final int BIOME_SAND  = 3;
    public static final int BIOME_STONE = 4;
    // S2 — named expansion biomes (blob-sets 1/3/5/7/9/10/11)
    public static final int BIOME_EARTH_ALT = 5;   // blob-set 1  (earth variant)
    public static final int BIOME_GRASS_ALT = 6;   // blob-set 3  (grass variant)
    public static final int BIOME_SNOW_ALT  = 7;   // blob-set 5  (snow variant)
    public static final int BIOME_SAND_ALT  = 8;   // blob-set 7  (sand variant)
    public static final int BIOME_SPIRIT    = 9;   // blob-set 9  (spirit realm)
    public static final int BIOME_HUB       = 10;  // blob-set 10 (bamboo hub)
    public static final int BIOME_HUB_ALT   = 11;  // blob-set 11 (hub variant)
    public static final int BIOME_COUNT = 12;

    // Maps biome 0-11 to JSON blob-set index 0-11
    private static final int[] BIOME_TO_BLOB_SET = { 0, 2, 4, 6, 8, 1, 3, 5, 7, 9, 10, 11 };

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

        // Pre-slice all tiles.
        // The mk_nature tileset is authored for Y-DOWN rendering without a V-flip:
        // surface/cap pixels sit at the BOTTOM of each 16 px tile image so that
        // SpriteBatch in Y-DOWN camera (setToOrtho(true)) naturally places them at
        // the player-facing top.  Applying flip(false, true) would invert that,
        // putting cap art at the screen-bottom and interior art at the screen-top.
        TextureRegion[] tiles = new TextureRegion[totalTiles];
        for (int id = 0; id < totalTiles; id++) {
            int col = id % SHEET_COLS;
            int row = id / SHEET_COLS;
            tiles[id] = new TextureRegion(
                sheet, col * TILE_PX, row * TILE_PX, TILE_PX, TILE_PX);
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
     * Platform tile with horizontal cap/join awareness.
     *
     * Maps adjacency to the bitmask subset used by the blob autotile system:
     *   W=128 (left neighbour), E=8 (right neighbour).
     * Roles covered: 0 (isolated), 8 (right-cap), 128 (left-cap), 136 (middle).
     * Falls back to role=0 when the computed role is absent in the set.
     *
     * @param biomeIndex    game biome index (0–4)
     * @param leftNeighbour true if the tile immediately to the left is also PLATFORM
     * @param rightNeighbour true if the tile immediately to the right is also PLATFORM
     */
    public TextureRegion getPlatformFrame(int biomeIndex,
                                          boolean leftNeighbour, boolean rightNeighbour) {
        int role = (leftNeighbour ? 128 : 0) | (rightNeighbour ? 8 : 0);
        int si = blobSetFor(biomeIndex);
        TextureRegion r = lookup[si][role];
        return r != null ? r : fallback[si];
    }

    /**
     * Derive a biome index (0–4) deterministically from a zone seed.
     * Capped at 5 (original biome count) until S5 wires world regions to biomes —
     * this keeps existing rooms visually stable while constants for S2–S4 biomes
     * are available for DevConsole set_biome and future region assignment.
     */
    public static int biomeFromSeed(long seed) {
        return (int)(Math.abs(seed) % 5);  // 0-4: original biomes only until S5
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** Map game biome 0-11 to JSON blob-set index 0-11. */
    private int blobSetFor(int biomeIndex) {
        int b = Math.max(0, Math.min(BIOME_TO_BLOB_SET.length - 1, biomeIndex));
        int si = BIOME_TO_BLOB_SET[b];
        return Math.min(si, numBlobSets - 1);
    }

    public void dispose() {
        sheet.dispose();
    }
}
