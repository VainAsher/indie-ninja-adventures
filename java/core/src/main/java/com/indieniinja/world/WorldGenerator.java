package com.indieniinja.world;

import java.util.Random;

/**
 * Generates a deterministic procedural tile grid for a zone.
 *
 * Java port of Python's systems/world_generation.py / room_generation.py
 * for the dungeon biome. Single-room layout: boundaries + layered platforms
 * + mid structures (pillars/ledges).
 *
 * Tile values:
 *   AIR (0)      — empty cell, no collision
 *   SOLID (1)    — full solid tile, blocks all movement
 *   PLATFORM (2) — one-way platform, blocks only downward movement
 *
 * Coordinate system: Y-DOWN, row 0 = top of world (y = 0).
 * grid[row][col] — row-major.
 */
public final class WorldGenerator {

    public static final byte AIR      = 0;
    public static final byte SOLID    = 1;
    public static final byte PLATFORM = 2;

    private WorldGenerator() {}

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Generate a tile grid of the given dimensions from {@code seed}.
     *
     * @param seed  zone seed (used to derive sub-seeds for each pass)
     * @param cols  grid width in tiles
     * @param rows  grid height in tiles
     * @return byte[rows][cols] tile grid
     */
    public static byte[][] generate(long seed, int cols, int rows) {
        byte[][] grid = new byte[rows][cols];

        addBoundaries(grid, cols, rows);

        long platSeed = SeedHierarchy.deriveFeature(
            SeedHierarchy.deriveSubroom((int) seed, 0), "platforms");
        addPlatformLayers(grid, cols, rows, platSeed);

        long structSeed = SeedHierarchy.deriveFeature(
            SeedHierarchy.deriveSubroom((int) seed, 0), "structures");
        addMidStructures(grid, cols, rows, structSeed);

        return grid;
    }

    // ── Generation passes ─────────────────────────────────────────────────────

    /**
     * Pass 1 — hard boundaries.
     *
     * Ceiling: rows 0-1 (solid across full width)
     * Floor:   rows (rows-4) .. (rows-1)
     * Walls:   cols 0-1 and cols (cols-2)..(cols-1)
     */
    static void addBoundaries(byte[][] grid, int cols, int rows) {
        // Ceiling
        for (int c = 0; c < cols; c++) {
            grid[0][c] = SOLID;
            grid[1][c] = SOLID;
        }
        // Floor (4 tiles thick — matches buildTestLayout's 2-thick floor; 4 is sturdier)
        for (int r = rows - 4; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                grid[r][c] = SOLID;
            }
        }
        // Left and right walls (2 tiles thick)
        for (int r = 0; r < rows; r++) {
            grid[r][0]       = SOLID;
            grid[r][1]       = SOLID;
            grid[r][cols - 2] = SOLID;
            grid[r][cols - 1] = SOLID;
        }
    }

    /**
     * Pass 2 — layered one-way platforms.
     *
     * Distributes 3-6 horizontal platform layers across the play-space.
     * Each layer has 2-4 separate segments, leaving gaps for navigation.
     * Heights are seeded so the same seed always produces the same layout.
     */
    static void addPlatformLayers(byte[][] grid, int cols, int rows, long seed) {
        Random rng = new Random(seed);
        int numLayers = 3 + rng.nextInt(4);   // 3-6 layers

        // Spread layers across the play-space (avoid ceiling zone and floor zone)
        int minRow = 8;
        int maxRow = rows - 10;
        int spacing = (maxRow - minRow) / (numLayers + 1);

        for (int layer = 0; layer < numLayers; layer++) {
            int baseRow = minRow + (layer + 1) * spacing;
            // Jitter each layer by ±3 rows
            int row = baseRow + rng.nextInt(7) - 3;
            row = Math.max(minRow, Math.min(maxRow, row));

            // 2-4 segments per layer
            int numSegs = 2 + rng.nextInt(3);
            int innerW  = cols - 6;           // playable column range (skip walls)
            int segZone = innerW / (numSegs + 1);

            for (int seg = 0; seg < numSegs; seg++) {
                int segLen = 8 + rng.nextInt(14);   // 8-21 tiles long
                int centre = 3 + (seg + 1) * segZone;
                int c0 = Math.max(3, centre - segLen / 2);
                int c1 = Math.min(cols - 3, c0 + segLen);

                for (int c = c0; c < c1; c++) {
                    if (grid[row][c] == AIR) {
                        grid[row][c] = PLATFORM;
                    }
                }
            }
        }
    }

    /**
     * Pass 3 — mid structures (solid pillars anchored to the floor).
     *
     * 2-5 pillars of height 3-7 tiles, width 2, rising from the floor surface.
     * Breaks up ground traversal and creates wall-jump opportunities.
     */
    static void addMidStructures(byte[][] grid, int cols, int rows, long seed) {
        Random rng = new Random(seed);
        int numPillars = 2 + rng.nextInt(4);   // 2-5
        int floorTop   = rows - 4;             // topmost solid floor row

        for (int i = 0; i < numPillars; i++) {
            int col    = 4 + rng.nextInt(cols - 8);
            int height = 3 + rng.nextInt(5);   // 3-7 tiles tall
            int c0     = col;
            int c1     = Math.min(cols - 3, col + 2);  // 2-tile wide pillar

            for (int r = floorTop - height; r < floorTop; r++) {
                if (r < 2) continue;   // never overwrite ceiling
                for (int c = c0; c <= c1; c++) {
                    if (c < 2 || c >= cols - 2) continue;
                    if (grid[r][c] == AIR) grid[r][c] = SOLID;
                }
            }
        }
    }

    // ── Utility ───────────────────────────────────────────────────────────────

    /**
     * Scan grid for all cells that are solid/platform with air directly above.
     * Returns world-pixel spawn positions [{x_centre, y_top}].
     *
     * @param grid  tile grid (byte[rows][cols])
     * @param cols  grid width
     * @param rows  grid height
     * @param tile  tile size in pixels
     * @return list of float[]{worldX, worldY} spawn positions
     */
    public static java.util.List<float[]> collectGroundPositions(
            byte[][] grid, int cols, int rows, int tile) {
        java.util.List<float[]> out = new java.util.ArrayList<>();
        for (int r = 3; r < rows - 1; r++) {
            for (int c = 3; c < cols - 3; c++) {
                byte below = grid[r][c];
                byte above = grid[r - 1][c];
                if (below != AIR && above == AIR) {
                    // place entity so its bottom aligns with the top of this tile
                    float wx = c * tile + tile * 0.5f;
                    float wy = r * tile;   // top of the solid tile = entity bottom
                    out.add(new float[]{wx, wy});
                }
            }
        }
        return out;
    }
}
