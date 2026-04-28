package com.indieniinja.client.rendering;

import com.indieniinja.world.WorldGenerator;

import java.util.HashSet;
import java.util.Random;
import java.util.Set;

/**
 * S4 — Client-side decoration layer generator.
 *
 * Produces a second {@code byte[rows][cols]} grid that is rendered before
 * terrain tiles as a visual-only pass. No decoration value ever travels
 * over the wire — the grid is regenerated from seed + biome on every room load.
 *
 * Generation rules (per biome probabilities from deco_rules.json):
 *  - SOLID tile with AIR directly above → ceilingProb chance: ceiling deco in the air tile
 *  - SOLID tile with AIR to left or right → wallProb chance: wall deco in adjacent air tile
 *  - SOLID tile at ground surface → floorEdgeProb chance: floor-edge deco in that tile
 *
 * Spawn positions returned by WorldGenerator.collectGroundPositions() are
 * excluded — deco must never obscure playable surfaces.
 *
 * Deco tile values in the returned grid:
 *   0 = no deco
 *   1 = ceiling deco
 *   2 = wall deco (left face)
 *   3 = wall deco (right face)
 *   4 = floor-edge deco
 */
public final class DecorationGenerator {

    // Deco tile type constants
    public static final byte DECO_NONE        = 0;
    public static final byte DECO_CEILING     = 1;
    public static final byte DECO_WALL_LEFT   = 2;
    public static final byte DECO_WALL_RIGHT  = 3;
    public static final byte DECO_FLOOR_EDGE  = 4;

    private DecorationGenerator() {}

    /**
     * Generate a decoration grid deterministically from seed and biome.
     *
     * @param terrainGrid  byte[rows][cols] from WorldGenerator.generate()
     * @param roomSeed     seed used to generate this room
     * @param biomeIndex   biome constant from BlobTileSet (0–11)
     * @param rules        decoration probability rules for this biome
     * @param cols         grid width in tiles
     * @param rows         grid height in tiles
     * @return byte[rows][cols] decoration grid (DECO_* constants, 0 = empty)
     */
    public static byte[][] generate(byte[][] terrainGrid, long roomSeed, int biomeIndex,
                                    DecoRuleSet rules, int cols, int rows) {
        byte[][] deco = new byte[rows][cols];
        Random rng = new Random(roomSeed ^ ((long) biomeIndex << 32));

        // Build spawn-exclusion set from ground positions (tile coords, not world coords)
        Set<Long> spawnTiles = collectSpawnTileKeys(terrainGrid, cols, rows);

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                byte tile = terrainGrid[r][c];
                if (tile != WorldGenerator.SOLID && tile != WorldGenerator.CLIMBABLE) continue;

                // Ceiling deco: solid tile with air directly above it
                if (r > 0 && terrainGrid[r - 1][c] == WorldGenerator.AIR) {
                    int targetR = r - 1;
                    if (!isSpawnTile(spawnTiles, targetR, c)
                            && rng.nextFloat() < rules.ceilingProb) {
                        deco[targetR][c] = DECO_CEILING;
                    }
                }

                // Wall deco: solid tile with air to the left
                if (c > 0 && terrainGrid[r][c - 1] == WorldGenerator.AIR) {
                    int targetC = c - 1;
                    if (!isSpawnTile(spawnTiles, r, targetC)
                            && deco[r][targetC] == DECO_NONE
                            && rng.nextFloat() < rules.wallProb) {
                        deco[r][targetC] = DECO_WALL_RIGHT;  // right-face of the air tile
                    }
                }

                // Wall deco: solid tile with air to the right
                if (c < cols - 1 && terrainGrid[r][c + 1] == WorldGenerator.AIR) {
                    int targetC = c + 1;
                    if (!isSpawnTile(spawnTiles, r, targetC)
                            && deco[r][targetC] == DECO_NONE
                            && rng.nextFloat() < rules.wallProb) {
                        deco[r][targetC] = DECO_WALL_LEFT;   // left-face of the air tile
                    }
                }

                // Floor-edge deco: solid tile at top of a solid surface (air below or boundary)
                boolean groundSurface = (r == rows - 1) || terrainGrid[r + 1][c] == WorldGenerator.AIR
                        || terrainGrid[r + 1][c] == WorldGenerator.PLATFORM;
                if (groundSurface && !isSpawnTile(spawnTiles, r, c)
                        && deco[r][c] == DECO_NONE
                        && rng.nextFloat() < rules.floorEdgeProb) {
                    deco[r][c] = DECO_FLOOR_EDGE;
                }
            }
        }

        return deco;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static Set<Long> collectSpawnTileKeys(byte[][] grid, int cols, int rows) {
        int tilePx = com.indieniinja.physics.PhysicsConstants.TILE_SIZE;
        java.util.List<float[]> positions = WorldGenerator.collectGroundPositions(
            grid, cols, rows, tilePx);
        Set<Long> keys = new HashSet<>(positions.size() * 2);
        for (float[] pos : positions) {
            int tileR = (int)(pos[1] / tilePx);
            int tileC = (int)(pos[0] / tilePx);
            keys.add(tileKey(tileR, tileC));
        }
        return keys;
    }

    private static boolean isSpawnTile(Set<Long> spawnTiles, int r, int c) {
        return spawnTiles.contains(tileKey(r, c));
    }

    private static long tileKey(int r, int c) {
        return ((long) r << 20) | (c & 0xFFFFF);
    }

    // ── DecoRuleSet record ────────────────────────────────────────────────────

    /**
     * Parsed decoration rule set — one entry from deco_rules.json.
     * All probabilities are in [0, 1].
     */
    public static final class DecoRuleSet {
        public final float ceilingProb;
        public final float wallProb;
        public final float floorEdgeProb;
        public final int   tileOffset;

        public DecoRuleSet(float ceilingProb, float wallProb, float floorEdgeProb, int tileOffset) {
            this.ceilingProb   = ceilingProb;
            this.wallProb      = wallProb;
            this.floorEdgeProb = floorEdgeProb;
            this.tileOffset    = tileOffset;
        }

        /** Parse from a libGDX JsonValue node (a single entry in deco_rules.json "sets"). */
        public static DecoRuleSet fromJson(com.badlogic.gdx.utils.JsonValue node) {
            return new DecoRuleSet(
                node.getFloat("ceilingProb",   0f),
                node.getFloat("wallProb",       0f),
                node.getFloat("floorEdgeProb",  0f),
                node.getInt("tileOffset",       0)
            );
        }

        /** Default rule set used when no biome-specific rules are available. */
        public static DecoRuleSet defaultRules() {
            return new DecoRuleSet(0.1f, 0.1f, 0.1f, 0);
        }
    }
}
