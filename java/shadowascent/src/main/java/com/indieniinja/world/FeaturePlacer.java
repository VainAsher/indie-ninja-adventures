package com.indieniinja.world;

import com.indieniinja.physics.PhysicsConstants;

import java.util.Collection;
import java.util.HashSet;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * S7 — Feature Placer.
 *
 * Places 1–2 named multi-tile structural features into the tile grid after
 * door carving and before blob variation. Features are small tile stamps
 * defined as int[][]{dc, dr, tile} entries relative to an anchor position.
 *
 * Placement is seeded deterministically from roomSeed ^ biomeIndex.
 * Stamps that would fall inside a door corridor are rejected and re-tried
 * up to MAX_ATTEMPTS times; if no valid position is found the feature is skipped.
 *
 * replay=BREAKING from v0.12.09.
 */
public final class FeaturePlacer {

    private static final int COLS      = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
    private static final int ROWS      = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128
    private static final int DOOR_HALF = PhysicsConstants.TILES_PER_ZONE / 2 + 1;  // 5
    private static final int MARGIN    = DOOR_HALF + 2;
    private static final int MAX_ATTEMPTS = 8;

    // Tile-value constants (mirrors WorldGenerator — avoid cross-module import risk)
    private static final byte SOLID    = WorldGenerator.SOLID;
    private static final byte PLATFORM = WorldGenerator.PLATFORM;
    private static final byte WATER    = WorldGenerator.WATER;
    private static final byte ICE      = WorldGenerator.ICE;

    private FeaturePlacer() {}

    // ── Feature stamps ────────────────────────────────────────────────────────
    // Each stamp: int[][] where each row is { colOffset, rowOffset, tileValue }

    private static final int[][] STALACTITE_COLUMN = {
        {0,0,SOLID},{1,0,SOLID},
        {0,1,SOLID},{1,1,SOLID},
        {0,2,SOLID},{1,2,SOLID},
        {0,3,SOLID},
    };

    private static final int[][] UNDERGROUND_POOL = {
        {0,0,WATER},{1,0,WATER},{2,0,WATER},{3,0,WATER},
    };

    private static final int[][] CAVE_BRIDGE = {
        {0,0,PLATFORM},{1,0,PLATFORM},{2,0,PLATFORM},
        {3,0,PLATFORM},{4,0,PLATFORM},{5,0,PLATFORM},
    };

    private static final int[][] ICE_PILLAR = {
        {0,0,ICE},{1,0,ICE},
        {0,1,ICE},{1,1,ICE},
        {0,2,ICE},{1,2,ICE},
    };

    private static final int[][] TREE_TRUNK = {
        {0,0,SOLID},{0,1,SOLID},{0,2,SOLID},{0,3,SOLID},
    };

    private static final int[][] ROOT_TANGLE = {
        {0,0,SOLID},{1,0,SOLID},{2,0,SOLID},
        {0,1,SOLID},            {2,1,SOLID},
    };

    private static final int[][] BRANCH_CLUSTER = {
        {0,0,PLATFORM},{1,0,PLATFORM},
        {3,2,PLATFORM},{4,2,PLATFORM},
        {1,4,PLATFORM},{2,4,PLATFORM},{3,4,PLATFORM},
    };

    private static final int[][] STONE_PILLAR_PAIR = {
        {0,0,SOLID},{0,1,SOLID},{0,2,SOLID},
        {3,0,SOLID},{3,1,SOLID},{3,2,SOLID},
    };

    private static final int[][] RAISED_DAIS = {
        {0,0,SOLID},{1,0,SOLID},{2,0,SOLID},{3,0,SOLID},
        {0,1,PLATFORM},{1,1,PLATFORM},{2,1,PLATFORM},{3,1,PLATFORM},
    };

    private static final int[][] ARCH_GATE = {
        {0,0,SOLID},{1,0,SOLID},{2,0,SOLID},{3,0,SOLID},{4,0,SOLID},
        {0,1,SOLID},                                    {4,1,SOLID},
        {0,2,SOLID},                                    {4,2,SOLID},
    };

    private static final int[][] DECORATIVE_PILLAR_PAIR = {
        {0,0,SOLID},{0,1,SOLID},{0,2,SOLID},{0,3,SOLID},
        {4,0,SOLID},{4,1,SOLID},{4,2,SOLID},{4,3,SOLID},
    };

    private static final int[][] WATER_FEATURE = {
        {0,0,WATER},{1,0,WATER},{2,0,WATER},{3,0,WATER},
        {0,1,WATER},{1,1,WATER},{2,1,WATER},{3,1,WATER},
    };

    private static final int[][] GATE_ARCH = {
        {0,0,SOLID},{0,1,SOLID},{0,2,SOLID},
        {4,0,SOLID},{4,1,SOLID},{4,2,SOLID},
        {0,3,PLATFORM},{1,3,PLATFORM},{2,3,PLATFORM},{3,3,PLATFORM},{4,3,PLATFORM},
    };

    private static final Map<String, int[][]> STAMPS = Map.ofEntries(
        Map.entry("stalactite_column",      STALACTITE_COLUMN),
        Map.entry("underground_pool",       UNDERGROUND_POOL),
        Map.entry("cave_bridge",            CAVE_BRIDGE),
        Map.entry("ice_pillar",             ICE_PILLAR),
        Map.entry("tree_trunk",             TREE_TRUNK),
        Map.entry("root_tangle",            ROOT_TANGLE),
        Map.entry("branch_cluster",         BRANCH_CLUSTER),
        Map.entry("stone_pillar_pair",      STONE_PILLAR_PAIR),
        Map.entry("raised_dais",            RAISED_DAIS),
        Map.entry("arch_gate",              ARCH_GATE),
        Map.entry("decorative_pillar_pair", DECORATIVE_PILLAR_PAIR),
        Map.entry("water_feature",          WATER_FEATURE),
        Map.entry("gate_arch",              GATE_ARCH)
    );

    // ── Biome → feature pool ──────────────────────────────────────────────────

    private static String[] featuresForBiome(int biomeIndex) {
        return switch (Math.max(0, Math.min(biomeIndex, 11))) {
            case 0, 5   -> new String[]{ "stalactite_column", "underground_pool", "cave_bridge" };
            case 1, 10  -> new String[]{ "tree_trunk", "root_tangle", "branch_cluster" };
            case 2      -> new String[]{ "stalactite_column", "ice_pillar" };
            case 3      -> new String[]{ "arch_gate", "raised_dais", "stone_pillar_pair" };
            case 4, 6   -> new String[]{ "stone_pillar_pair", "raised_dais", "arch_gate" };
            case 7, 8   -> new String[]{ "stalactite_column", "underground_pool" };
            case 9      -> new String[]{ "ice_pillar", "cave_bridge" };
            case 11     -> new String[]{ "decorative_pillar_pair", "water_feature", "gate_arch" };
            default     -> new String[]{ "stalactite_column" };
        };
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Place 1–2 biome features into {@code grid} after door carving.
     *
     * @param grid         128×128 tile grid (modified in place)
     * @param biomeIndex   0–11
     * @param roomSeed     per-room seed
     * @param neighborDirs connected directions ("up","down","left","right")
     */
    public static void place(byte[][] grid, int biomeIndex,
                              long roomSeed, Collection<String> neighborDirs) {
        String[] pool = featuresForBiome(biomeIndex);
        if (pool.length == 0) return;

        Random rng = new Random(roomSeed ^ ((long) biomeIndex << 20));

        int midC = COLS / 2;
        int midR = ROWS / 2;
        boolean hasUp    = neighborDirs.contains("up");
        boolean hasDown  = neighborDirs.contains("down");
        boolean hasLeft  = neighborDirs.contains("left");
        boolean hasRight = neighborDirs.contains("right");

        Set<Long> usedCells = new HashSet<>();

        int featureCount = 1 + rng.nextInt(2);
        for (int f = 0; f < featureCount; f++) {
            String name = pool[rng.nextInt(pool.length)];
            tryPlace(grid, name, rng, midC, midR, hasUp, hasDown, hasLeft, hasRight, usedCells);
        }
    }

    private static void tryPlace(byte[][] grid, String name, Random rng,
                                  int midC, int midR,
                                  boolean hasUp, boolean hasDown,
                                  boolean hasLeft, boolean hasRight,
                                  Set<Long> usedCells) {
        int[][] stamp = STAMPS.get(name);
        if (stamp == null) return;

        for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            int anchorC = MARGIN + rng.nextInt(COLS - 2 * MARGIN);
            int anchorR = MARGIN + rng.nextInt(ROWS - 2 * MARGIN);

            if (!canPlace(stamp, anchorC, anchorR, midC, midR,
                          hasUp, hasDown, hasLeft, hasRight, usedCells)) continue;

            for (int[] tile : stamp) {
                int tc = anchorC + tile[0];
                int tr = anchorR + tile[1];
                if (tr >= 0 && tr < ROWS && tc >= 0 && tc < COLS) {
                    grid[tr][tc] = (byte) tile[2];
                    usedCells.add((long) tr * COLS + tc);
                }
            }
            return;
        }
    }

    private static boolean canPlace(int[][] stamp, int anchorC, int anchorR,
                                     int midC, int midR,
                                     boolean hasUp, boolean hasDown,
                                     boolean hasLeft, boolean hasRight,
                                     Set<Long> usedCells) {
        for (int[] tile : stamp) {
            int tc = anchorC + tile[0];
            int tr = anchorR + tile[1];

            if (tr < 1 || tr >= ROWS - 1 || tc < 1 || tc >= COLS - 1) return false;
            if (usedCells.contains((long) tr * COLS + tc)) return false;

            // Reject positions inside door corridors
            if (hasUp    && tr <= DOOR_HALF && Math.abs(tc - midC) <= DOOR_HALF) return false;
            if (hasDown  && tr >= ROWS - DOOR_HALF && Math.abs(tc - midC) <= DOOR_HALF) return false;
            if (hasLeft  && tc <= DOOR_HALF && Math.abs(tr - midR) <= DOOR_HALF) return false;
            if (hasRight && tc >= COLS - DOOR_HALF && Math.abs(tr - midR) <= DOOR_HALF) return false;
        }
        return true;
    }
}
