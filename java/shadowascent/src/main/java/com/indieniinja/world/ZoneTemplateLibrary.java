package com.indieniinja.world;

import java.util.Random;

/**
 * S6 — Zone Template Library.
 *
 * Replaces single fixed zone expansion with a weighted pool of named 8×8
 * tile patterns per zone role. Called by RoomGenerator.expandZone() for
 * FILL and PLAT roles; all other roles keep their existing expansion logic.
 *
 * Weight tables mirror biomes.json#zoneTemplateWeights — keep in sync
 * when adjusting biome tuning values in that file.
 *
 * replay=BREAKING from v0.12.09: any change here alters tile grid output.
 */
public final class ZoneTemplateLibrary {

    private static final int TPZ = 8;  // tiles per zone
    private static final ZonePatchTemplateLibrary AUTHORED_PATCHES = ZonePatchTemplateLibrary.loadDefault();

    private ZoneTemplateLibrary() {}

    // ── FILL templates ────────────────────────────────────────────────────────

    private static byte[][] fill_full() {
        byte[][] t = new byte[TPZ][TPZ];
        for (int r = 0; r < TPZ; r++)
            for (int c = 0; c < TPZ; c++)
                t[r][c] = WorldGenerator.SOLID;
        return t;
    }

    private static byte[][] fill_arch() {
        byte[][] t = fill_full();
        int mid = TPZ / 2;
        // Arch opening: bottom 3 rows, central 4 cols
        for (int r = TPZ - 3; r < TPZ; r++)
            for (int c = mid - 2; c < mid + 2; c++)
                if (c >= 0 && c < TPZ) t[r][c] = WorldGenerator.AIR;
        return t;
    }

    private static byte[][] fill_pillar() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int r = 0; r < TPZ; r++) {
            t[r][mid - 1] = WorldGenerator.SOLID;
            t[r][mid]     = WorldGenerator.SOLID;
        }
        return t;
    }

    private static byte[][] fill_overhang() {
        byte[][] t = new byte[TPZ][TPZ];
        // Top half solid
        for (int r = 0; r <= TPZ / 2; r++)
            for (int c = 0; c < TPZ; c++)
                t[r][c] = WorldGenerator.SOLID;
        return t;
    }

    private static byte[][] fill_tooth() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int r = 0; r < TPZ; r++) {
            int half = Math.max(0, mid - r / 2);
            for (int c = mid - half; c <= mid + half; c++)
                if (c >= 0 && c < TPZ) t[r][c] = WorldGenerator.SOLID;
        }
        return t;
    }

    private static byte[][] fill_l_block() {
        byte[][] t = new byte[TPZ][TPZ];
        for (int r = 0; r < TPZ; r++) t[r][0] = WorldGenerator.SOLID;
        for (int c = 0; c < TPZ; c++) t[TPZ - 1][c] = WorldGenerator.SOLID;
        return t;
    }

    private static byte[][] fill_steps() {
        byte[][] t = new byte[TPZ][TPZ];
        // Each column c has solid from row (TPZ-1-c) down to TPZ-1
        for (int c = 0; c < TPZ; c++)
            for (int r = TPZ - 1 - c; r < TPZ; r++)
                t[r][c] = WorldGenerator.SOLID;
        return t;
    }

    private static byte[][] fill_hollow() {
        byte[][] t = new byte[TPZ][TPZ];
        for (int r = 0; r < TPZ; r++)
            for (int c = 0; c < TPZ; c++)
                if (r == 0 || r == TPZ - 1 || c == 0 || c == TPZ - 1)
                    t[r][c] = WorldGenerator.SOLID;
        return t;
    }

    // ── PLAT templates ────────────────────────────────────────────────────────

    private static byte[][] plat_full_bar() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int c = 0; c < TPZ; c++) t[mid][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_left_ledge() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int c = 0; c < TPZ / 2; c++) t[mid][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_right_ledge() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int c = TPZ / 2; c < TPZ; c++) t[mid][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_centre_island() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int c = 2; c < TPZ - 2; c++) t[mid][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_step_left() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        // Ascending left to right: row mid+1 (cols 0-1), row mid (cols 2-3), row mid-1 (cols 4-5)
        if (mid + 1 < TPZ) for (int c = 0; c < 2; c++) t[mid + 1][c] = WorldGenerator.PLATFORM;
        for (int c = 2; c < 4; c++) t[mid][c] = WorldGenerator.PLATFORM;
        if (mid - 1 >= 0) for (int c = 4; c < 6; c++) t[mid - 1][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_step_right() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        // Ascending right to left
        if (mid + 1 < TPZ) for (int c = 6; c < TPZ; c++) t[mid + 1][c] = WorldGenerator.PLATFORM;
        for (int c = 4; c < 6; c++) t[mid][c] = WorldGenerator.PLATFORM;
        if (mid - 1 >= 0) for (int c = 2; c < 4; c++) t[mid - 1][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_split() {
        byte[][] t = new byte[TPZ][TPZ];
        int mid = TPZ / 2;
        for (int c = 0; c < 3; c++) t[mid][c] = WorldGenerator.PLATFORM;
        for (int c = TPZ - 3; c < TPZ; c++) t[mid][c] = WorldGenerator.PLATFORM;
        return t;
    }

    private static byte[][] plat_double_ledge() {
        byte[][] t = new byte[TPZ][TPZ];
        // Upper half: row 2
        for (int c = 0; c < TPZ / 2; c++) t[2][c] = WorldGenerator.PLATFORM;
        // Lower half: row 5
        for (int c = TPZ / 2; c < TPZ; c++) t[5][c] = WorldGenerator.PLATFORM;
        return t;
    }

    // ── Biome weight tables ───────────────────────────────────────────────────
    // Index order: biomeIndex 0..11 (EARTH, GRASS, SNOW, SAND, STONE,
    //              EARTH_ALT, STONE_ALT, CRYSTAL_ALT, LAVA_ALT, ICE_ALT,
    //              NATURE_ALT, HUB_ALT)
    // Template order for FILL: full, arch, pillar, overhang, tooth, l_block, steps, hollow
    // Template order for PLAT: full_bar, left_ledge, right_ledge, centre_island,
    //                          step_left, step_right, split, double_ledge

    private static final float[][] FILL_WEIGHTS = {
        // earth
        { 0.20f, 0.10f, 0.20f, 0.20f, 0.20f, 0.10f, 0.00f, 0.00f },
        // grass/forest
        { 0.15f, 0.15f, 0.30f, 0.00f, 0.00f, 0.25f, 0.15f, 0.00f },
        // snow/ice cavern
        { 0.25f, 0.00f, 0.15f, 0.25f, 0.25f, 0.10f, 0.00f, 0.00f },
        // sand/ruins
        { 0.20f, 0.25f, 0.00f, 0.00f, 0.00f, 0.20f, 0.20f, 0.15f },
        // stone/dungeon
        { 0.25f, 0.25f, 0.00f, 0.00f, 0.00f, 0.15f, 0.20f, 0.15f },
        // earth_alt (same as earth)
        { 0.20f, 0.10f, 0.20f, 0.20f, 0.20f, 0.10f, 0.00f, 0.00f },
        // stone_alt (same as stone)
        { 0.25f, 0.25f, 0.00f, 0.00f, 0.00f, 0.15f, 0.20f, 0.15f },
        // crystal_alt — pillar heavy
        { 0.20f, 0.15f, 0.35f, 0.10f, 0.10f, 0.10f, 0.00f, 0.00f },
        // lava_alt — overhang+tooth
        { 0.10f, 0.10f, 0.10f, 0.25f, 0.25f, 0.10f, 0.10f, 0.00f },
        // ice_alt — overhang+pillar
        { 0.20f, 0.00f, 0.20f, 0.25f, 0.20f, 0.15f, 0.00f, 0.00f },
        // nature_alt — organic
        { 0.10f, 0.15f, 0.25f, 0.10f, 0.10f, 0.20f, 0.10f, 0.00f },
        // hub_alt — structured
        { 0.40f, 0.30f, 0.00f, 0.00f, 0.00f, 0.00f, 0.30f, 0.00f },
    };

    private static final float[][] PLAT_WEIGHTS = {
        // earth
        { 0.20f, 0.15f, 0.15f, 0.10f, 0.15f, 0.15f, 0.10f, 0.00f },
        // grass/forest — step-heavy
        { 0.15f, 0.15f, 0.15f, 0.00f, 0.20f, 0.20f, 0.00f, 0.15f },
        // snow/ice — islands + double ledges
        { 0.25f, 0.15f, 0.15f, 0.20f, 0.00f, 0.00f, 0.15f, 0.10f },
        // sand/ruins — centre islands
        { 0.20f, 0.15f, 0.15f, 0.20f, 0.15f, 0.15f, 0.00f, 0.00f },
        // stone/dungeon — full bars + splits
        { 0.25f, 0.15f, 0.15f, 0.00f, 0.15f, 0.15f, 0.15f, 0.00f },
        // earth_alt
        { 0.20f, 0.15f, 0.15f, 0.10f, 0.15f, 0.15f, 0.10f, 0.00f },
        // stone_alt
        { 0.25f, 0.15f, 0.15f, 0.00f, 0.15f, 0.15f, 0.15f, 0.00f },
        // crystal_alt — centre+split
        { 0.10f, 0.10f, 0.10f, 0.30f, 0.10f, 0.10f, 0.20f, 0.00f },
        // lava_alt — full bars + steps
        { 0.30f, 0.10f, 0.10f, 0.10f, 0.15f, 0.15f, 0.10f, 0.00f },
        // ice_alt — islands + double
        { 0.20f, 0.10f, 0.10f, 0.20f, 0.05f, 0.05f, 0.15f, 0.15f },
        // nature_alt — steps
        { 0.15f, 0.15f, 0.15f, 0.05f, 0.20f, 0.20f, 0.05f, 0.05f },
        // hub_alt — full + symmetric ledges
        { 0.40f, 0.20f, 0.20f, 0.20f, 0.00f, 0.00f, 0.00f, 0.00f },
    };

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Pick an 8×8 tile template for the given zone role and biome.
     *
     * @param role       ZonePlanner.FILL or ZonePlanner.PLAT
     * @param biomeIndex 0–11; clamped to valid range
     * @param rng        per-zone deterministic Random
     * @return byte[8][8] tile pattern (AIR=0, SOLID=1, PLATFORM=2)
     */
    public static byte[][] pick(byte role, int biomeIndex, Random rng) {
        return pick(role, biomeIndex, rng, AUTHORED_PATCHES);
    }

    static byte[][] pick(byte role, int biomeIndex, Random rng, ZonePatchTemplateLibrary authoredPatches) {
        if (authoredPatches != null) {
            var authored = authoredPatches.pick(role, biomeIndex, rng);
            if (authored.isPresent()) {
                return authored.get();
            }
        }

        int bi = Math.max(0, Math.min(biomeIndex, FILL_WEIGHTS.length - 1));
        if (role == ZonePlanner.FILL) return pickFill(bi, rng);
        return pickPlat(bi, rng);
    }

    private static byte[][] pickFill(int bi, Random rng) {
        return switch (weightedIndex(FILL_WEIGHTS[bi], rng)) {
            case 1  -> fill_arch();
            case 2  -> fill_pillar();
            case 3  -> fill_overhang();
            case 4  -> fill_tooth();
            case 5  -> fill_l_block();
            case 6  -> fill_steps();
            case 7  -> fill_hollow();
            default -> fill_full();
        };
    }

    private static byte[][] pickPlat(int bi, Random rng) {
        return switch (weightedIndex(PLAT_WEIGHTS[bi], rng)) {
            case 1  -> plat_left_ledge();
            case 2  -> plat_right_ledge();
            case 3  -> plat_centre_island();
            case 4  -> plat_step_left();
            case 5  -> plat_step_right();
            case 6  -> plat_split();
            case 7  -> plat_double_ledge();
            default -> plat_full_bar();
        };
    }

    private static int weightedIndex(float[] weights, Random rng) {
        float roll = rng.nextFloat();
        float cum = 0f;
        for (int i = 0; i < weights.length; i++) {
            cum += weights[i];
            if (roll < cum) return i;
        }
        return 0;
    }
}
