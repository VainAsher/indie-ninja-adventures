package com.indieniinja.world;

import java.util.Collection;
import java.util.Random;

/**
 * Generates a deterministic procedural tile grid for a zone.
 *
 * Java port of Python's systems/world_generation.py / room_generation.py
 * for the dungeon biome. Single-room layout: boundaries + layered platforms
 * + mid structures (pillars/ledges).
 *
 * Tile values:
 *   AIR (0)        — empty cell, no collision
 *   SOLID (1)      — full solid tile, blocks all movement
 *   PLATFORM (2)   — one-way platform, blocks only downward movement
 *   ICE (3)        — solid tile with near-zero friction (sliding surface)
 *   WATER (4)      — passable liquid zone: reduces speed, disables dash, slows fall
 *   LAVA (5)       — solid tile that deals 1 HP damage per tick on contact
 *   DOOR_LOCKED (6)— solid tile stamped by PuzzleLayer; unlocked at runtime by puzzle solve
 *   GAS (7)        — passable gas zone with mild drag
 *   CLIMBABLE (8)  — solid climb-tag tile; wall-climb traversal can latch only to this type
 *
 * Coordinate system: Y-DOWN, row 0 = top of world (y = 0).
 * grid[row][col] — row-major.
 */
public final class WorldGenerator {

    public static final byte AIR         = 0;
    public static final byte SOLID       = 1;
    public static final byte PLATFORM    = 2;
    public static final byte ICE         = 3;
    public static final byte WATER       = 4;
    public static final byte LAVA        = 5;
    /** Locked door tile — stamped by PuzzleLayer, treated as SOLID for collision. */
    public static final byte DOOR_LOCKED = 6;
    /**
     * Gas tile (mist/smoke/wind zones) — passable like WATER but with lighter drag.
     * Entities inside a GAS tile receive GAS_DRAG per-axis velocity reduction each tick
     * unless ABILITY_GAS_RESIST is set on their PhysicsState.abilityFlags.
     * Excluded from collectGroundPositions() spawn-point scanning.
     */
    public static final byte GAS = 7;
    /** Solid climb-tag tile. Collision is solid; traversal logic treats this as climb-enabled. */
    public static final byte CLIMBABLE = 8;

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
    /**
     * Door half-width in tiles — matches Python TILES_PER_ZONE = 8.
     * Carves a 9-tile-wide opening (centre ± DOOR_HALF) at each neighboured edge.
     */
    /** Half-span of door opening in tiles (total width = DOOR_HALF*2+1 = 9 tiles). */
    private static final int DOOR_HALF = 4;

    /**
     * Generate a tile grid with no door openings.
     * Defaults to "combat" room type.
     */
    public static byte[][] generate(long seed, int cols, int rows) {
        return generate(seed, cols, rows, java.util.Collections.emptySet(), "combat");
    }

    /**
     * Generate a tile grid for the given neighborDirs.
     * Defaults to "combat" room type.
     */
    public static byte[][] generate(long seed, int cols, int rows,
                                    Collection<String> neighborDirs) {
        return generate(seed, cols, rows, neighborDirs, "combat");
    }

    /**
     * Full zone-planned generation: ZonePlanner → RoomGenerator pipeline.
     *
     * Matches Python's ZonePlanner.plan_room() + RoomGenerator.generate_tilemap()
     * pipeline for the given room type.
     *
     * @param seed         room seed
     * @param cols         must equal ROOM_WIDTH_TILES (128) — kept for API compat
     * @param rows         must equal ROOM_HEIGHT_TILES (128)
     * @param neighborDirs connected directions ("up","down","left","right")
     * @param roomType     wire string: "start","exit","shop","combat","platform","treasure","boss"
     * @return byte[rows][cols] tile grid
     */
    public static byte[][] generate(long seed, int cols, int rows,
                                    Collection<String> neighborDirs, String roomType) {
        return generate(seed, cols, rows, neighborDirs, roomType, 0);
    }

    /**
     * Full zone-planned generation with biome index (S6–S8 path).
     *
     * @param biomeIndex 0–11; selects zone templates, features, and cave smoothing
     */
    public static byte[][] generate(long seed, int cols, int rows,
                                    Collection<String> neighborDirs, String roomType,
                                    int biomeIndex) {
        byte[][] zones = ZonePlanner.plan(seed, roomType, neighborDirs);
        byte[][] grid  = RoomGenerator.generate(zones, neighborDirs, seed, roomType, biomeIndex);
        tagClimbableSurfaces(grid, cols, rows);
        return grid;
    }

    /**
     * Tag climbable surfaces using explicit tile IDs.
     *
     * Rule set:
     * - Promote boundary wall columns to CLIMBABLE for deterministic onboarding traversal.
     * - Promote interior SOLID tiles that expose a left/right face to passable space
     *   and are vertically continuous (avoid converting isolated top caps/floor tops).
     */
    static void tagClimbableSurfaces(byte[][] grid, int cols, int rows) {
        if (grid == null || rows < 4 || cols < 4) return;

        // Boundary wall tagging (inside faces of room borders).
        for (int r = 2; r < rows - 2; r++) {
            if (grid[r][1] == SOLID) grid[r][1] = CLIMBABLE;
            if (grid[r][cols - 2] == SOLID) grid[r][cols - 2] = CLIMBABLE;
        }

        for (int r = 2; r < rows - 2; r++) {
            for (int c = 2; c < cols - 2; c++) {
                if (grid[r][c] != SOLID) continue;
                if (grid[r + 1][c] == AIR) continue; // likely a top cap / floor lip

                boolean leftExposed  = isPassableForClimbNeighbor(grid[r][c - 1]);
                boolean rightExposed = isPassableForClimbNeighbor(grid[r][c + 1]);
                if (leftExposed || rightExposed) {
                    grid[r][c] = CLIMBABLE;
                }
            }
        }
    }

    private static boolean isPassableForClimbNeighbor(byte tile) {
        return tile == AIR || tile == WATER || tile == GAS;
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

    // ── Door carving ──────────────────────────────────────────────────────────

    /**
     * Carve door openings into the boundary walls.
     *
     * Each door is centred on the room edge (cols/2 or rows/2) and is
     * (DOOR_HALF * 2 + 1) tiles wide, matching Python's DoorPort span_tiles.
     *
     * "up"    → rows 0-1 carved at horizontal centre (2 rows = ceiling thickness)
     * "down"  → rows (rows-4)..(rows-1) carved at horizontal centre (4 rows = floor thickness)
     * "left"  → cols 0-3 carved at vertical centre (4 tiles: 2 wall + 2 interior buffer)
     * "right" → cols (cols-4)..(cols-1) carved at vertical centre (4 tiles: 2 interior + 2 wall)
     *
     * The "left"/"right" openings extend 2 tiles into the interior so that any
     * one-way platform tiles placed by addPlatformLayers in the door approach
     * zone are cleared.  Those platforms only block vertical movement, which
     * would make the door visually appear filled without blocking the player.
     */
    static void carveDoors(byte[][] grid, int cols, int rows,
                            Collection<String> neighborDirs) {
        int midC = cols / 2;
        int midR = rows / 2;

        for (String dir : neighborDirs) {
            switch (dir) {
                case "up" -> {
                    for (int r = 0; r < 2; r++)
                        for (int c = midC - DOOR_HALF; c <= midC + DOOR_HALF; c++)
                            if (c >= 0 && c < cols) grid[r][c] = AIR;
                }
                case "down" -> {
                    for (int r = rows - 4; r < rows; r++)
                        for (int c = midC - DOOR_HALF; c <= midC + DOOR_HALF; c++)
                            if (c >= 0 && c < cols) grid[r][c] = AIR;
                }
                case "left" -> {
                    // 4 tiles deep (2 wall + 2 interior) to clear approach-zone platforms
                    for (int r = midR - DOOR_HALF; r <= midR + DOOR_HALF; r++)
                        for (int c = 0; c < 4; c++)
                            if (r >= 0 && r < rows) grid[r][c] = AIR;
                }
                case "right" -> {
                    // 4 tiles deep (2 interior + 2 wall) to clear approach-zone platforms
                    for (int r = midR - DOOR_HALF; r <= midR + DOOR_HALF; r++)
                        for (int c = cols - 4; c < cols; c++)
                            if (r >= 0 && r < rows) grid[r][c] = AIR;
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
                // Exclude hazard/passable tiles as valid spawn/patrol surfaces
                if (below != AIR && below != WATER && below != LAVA && below != GAS && above == AIR) {
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
