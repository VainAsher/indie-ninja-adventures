package com.indieniinja.world;

import com.indieniinja.physics.PhysicsConstants;

import java.util.Collection;
import java.util.Random;

/**
 * Converts a 16×16 zone grid to a 128×128 tile grid.
 *
 * Java port of Python systems/room_generation.py RoomGenerator.
 *
 * Each zone is TILES_PER_ZONE × TILES_PER_ZONE (8×8) tiles.
 * 16 zones × 8 tiles = 128 tiles per dimension.
 *
 * Output tile values:
 *   AIR (0)      — empty, no collision
 *   SOLID (1)    — full solid
 *   PLATFORM (2) — one-way, top-only collision
 *
 * Pipeline matches Python:
 *   1. Add room boundaries (walls only on edges without connections)
 *   2. Add base platform (penultimate row, unless connected downward)
 *   3. Expand each zone to TILES_PER_ZONE×TILES_PER_ZONE tiles
 *   4. Carve door openings at connected edges
 *   5. Blob variation — elliptical carve/stamp passes for visual richness
 */
public final class RoomGenerator {

    private static final int TPZ  = PhysicsConstants.TILES_PER_ZONE;  // 8
    private static final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;  // 128
    private static final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES; // 128

    /** Half-span of door opening in tiles. Total = DOOR_HALF*2+1 = 9 tiles. */
    private static final int DOOR_HALF = TPZ / 2 + 1;  // 5

    private RoomGenerator() {}

    /**
     * Generate a 128×128 tile grid from a 16×16 zone grid.
     *
     * @param zones        16×16 zone grid from ZonePlanner
     * @param neighborDirs connected directions ("up","down","left","right")
     * @param roomSeed     per-room seed for blob variation
     * @return byte[128][128] tile grid
     */
    public static byte[][] generate(byte[][] zones, Collection<String> neighborDirs,
                                     long roomSeed) {
        byte[][] grid = new byte[ROWS][COLS];

        boolean hasUp    = neighborDirs.contains("up");
        boolean hasDown  = neighborDirs.contains("down");
        boolean hasLeft  = neighborDirs.contains("left");
        boolean hasRight = neighborDirs.contains("right");

        // Step 1 — room boundaries (only on unconnected edges)
        addBoundaries(grid, hasUp, hasDown, hasLeft, hasRight);

        // Step 2 — base floor platform (row ROWS-2), only if not connected down
        if (!hasDown) {
            for (int c = 1; c < COLS - 1; c++) {
                if (grid[ROWS - 2][c] == WorldGenerator.AIR)
                    grid[ROWS - 2][c] = WorldGenerator.PLATFORM;
            }
        }

        // Step 3 — expand zones to tiles
        for (int zy = 0; zy < ZonePlanner.H; zy++) {
            for (int zx = 0; zx < ZonePlanner.W; zx++) {
                expandZone(grid, zx, zy, zones[zy][zx], hasUp, hasDown, hasLeft, hasRight);
            }
        }

        // Step 4 — carve door openings
        carveDoors(grid, neighborDirs);

        // Step 5 — blob variation for visual richness
        addBlobVariation(grid, zones, roomSeed);

        return grid;
    }

    // ── Step 1 — Boundaries ───────────────────────────────────────────────────

    private static void addBoundaries(byte[][] g,
                                       boolean hasUp, boolean hasDown,
                                       boolean hasLeft, boolean hasRight) {
        // Top wall
        if (!hasUp) {
            for (int c = 0; c < COLS; c++) g[0][c] = WorldGenerator.SOLID;
        }
        // Bottom wall
        if (!hasDown) {
            for (int c = 0; c < COLS; c++) g[ROWS - 1][c] = WorldGenerator.SOLID;
        }
        // Left wall
        if (!hasLeft) {
            for (int r = 0; r < ROWS; r++) g[r][0] = WorldGenerator.SOLID;
        }
        // Right wall
        if (!hasRight) {
            for (int r = 0; r < ROWS; r++) g[r][COLS - 1] = WorldGenerator.SOLID;
        }
    }

    // ── Step 3 — Zone expansion ───────────────────────────────────────────────

    private static void expandZone(byte[][] g, int zx, int zy, byte role,
                                    boolean hasUp, boolean hasDown,
                                    boolean hasLeft, boolean hasRight) {
        int txStart = zx * TPZ;
        int tyStart = zy * TPZ;
        int txEnd   = txStart + TPZ;
        int tyEnd   = tyStart + TPZ;

        boolean isTopEdge    = (zy == 0)               && hasUp;
        boolean isBottomEdge = (zy == ZonePlanner.H-1) && hasDown;

        switch (role) {
            case ZonePlanner.FILL -> {
                // Solid terrain — fill entire zone
                for (int ty = tyStart; ty < tyEnd; ty++)
                    for (int tx = txStart; tx < txEnd; tx++)
                        if (inBounds(tx, ty)) g[ty][tx] = WorldGenerator.SOLID;
            }
            case ZonePlanner.PLAT, ZonePlanner.CONN -> {
                // Horizontal platform at zone middle row
                int platY = tyStart + TPZ / 2;
                for (int tx = txStart; tx < txEnd; tx++)
                    if (inBounds(tx, platY)) g[platY][tx] = WorldGenerator.PLATFORM;
            }
            case ZonePlanner.WALK, ZonePlanner.DOOR, ZonePlanner.SAVE,
                 ZonePlanner.SHOP, ZonePlanner.LOOT, ZonePlanner.DECOR -> {
                // One-way platform at bottom of zone — lets player land from above but
                // jump through from below, preventing sealed vertical chambers.
                // UNLESS this zone is on a connected edge (door traversal must stay clear).
                if (!isBottomEdge && !isTopEdge) {
                    int floorY = tyEnd - 1;
                    for (int tx = txStart; tx < txEnd; tx++)
                        if (inBounds(tx, floorY) && g[floorY][tx] == WorldGenerator.AIR)
                            g[floorY][tx] = WorldGenerator.PLATFORM;
                }
            }
            case ZonePlanner.CHUTE -> {
                // Vertical chute — empty (player falls through to room below)
                // No tiles placed; already AIR
            }
            case ZonePlanner.CLIMB -> {
                // Stepped platforms for vertical ascent (staircase)
                for (int i = 0; i < TPZ; i++) {
                    int platY = tyEnd - 1 - (i / 2);
                    int tx    = txStart + i;
                    if (inBounds(tx, platY)) g[platY][tx] = WorldGenerator.PLATFORM;
                }
            }
            case ZonePlanner.VOID -> {
                // Empty space — already AIR
            }
        }
    }

    private static boolean inBounds(int tx, int ty) {
        return tx >= 0 && tx < COLS && ty >= 0 && ty < ROWS;
    }

    // ── Step 4 — Door carving ─────────────────────────────────────────────────

    private static void carveDoors(byte[][] g, Collection<String> dirs) {
        int midC = COLS / 2;
        int midR = ROWS / 2;

        for (String dir : dirs) {
            switch (dir) {
                case "up" -> {
                    for (int r = 0; r < 2; r++)
                        for (int c = midC - DOOR_HALF; c <= midC + DOOR_HALF; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
                case "down" -> {
                    for (int r = ROWS - 2; r < ROWS; r++)
                        for (int c = midC - DOOR_HALF; c <= midC + DOOR_HALF; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
                case "left" -> {
                    // 4 tiles deep (2 wall + 2 interior) to clear approach platforms
                    for (int r = midR - DOOR_HALF; r <= midR + DOOR_HALF; r++)
                        for (int c = 0; c < 4; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
                case "right" -> {
                    for (int r = midR - DOOR_HALF; r <= midR + DOOR_HALF; r++)
                        for (int c = COLS - 4; c < COLS; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
            }
        }
    }

    // ── Step 5 — Blob variation ───────────────────────────────────────────────

    /**
     * Add elliptical solid/carved blobs inside FILL/VOID zones for visual richness.
     * Python parity: RoomGenerator._apply_tile_variation().
     */
    private static void addBlobVariation(byte[][] g, byte[][] zones, long roomSeed) {
        Random rng = new Random(roomSeed + 1337L);

        // Blob count varies with room type (average ~11)
        int blobCount = 8 + rng.nextInt(10);  // 8-17

        for (int b = 0; b < blobCount; b++) {
            int blobW = 2 + rng.nextInt(31);   // 2-32
            int blobH = 2 + rng.nextInt(31);
            int cx    = 2 + rng.nextInt(COLS - 4);
            int cy    = 2 + rng.nextInt(ROWS - 4);

            float density = 0.35f + rng.nextFloat() * 0.55f;
            boolean carve = rng.nextBoolean();  // carve (in FILL) or stamp (in VOID)

            stampBlob(g, zones, cx, cy, blobW, blobH, density, carve, rng);
        }
    }

    private static void stampBlob(byte[][] g, byte[][] zones,
                                   int cx, int cy, int bw, int bh,
                                   float density, boolean carve, Random rng) {
        int halfW = Math.max(1, bw / 2);
        int halfH = Math.max(1, bh / 2);
        int minX = Math.max(1, cx - halfW);
        int maxX = Math.min(COLS - 2, cx + halfW);
        int minY = Math.max(1, cy - halfH);
        int maxY = Math.min(ROWS - 2, cy + halfH);

        for (int ty = minY; ty <= maxY; ty++) {
            for (int tx = minX; tx <= maxX; tx++) {
                float nx = (float)(tx - cx) / halfW;
                float ny = (float)(ty - cy) / halfH;
                float dist = nx * nx + ny * ny;
                if (dist > 1.0f + rng.nextFloat() * 0.3f - 0.15f) continue;

                float falloff = Math.max(0f, 1f - dist);
                if (rng.nextFloat() > density * (0.4f + 0.6f * falloff)) continue;

                // Zone-role check: only modify tiles in FILL (carve) or VOID (stamp)
                int zx = Math.min(ZonePlanner.W - 1, Math.max(0, tx / TPZ));
                int zy = Math.min(ZonePlanner.H - 1, Math.max(0, ty / TPZ));
                byte zoneRole = zones[zy][zx];

                if (carve) {
                    if (zoneRole == ZonePlanner.FILL && g[ty][tx] == WorldGenerator.SOLID)
                        g[ty][tx] = WorldGenerator.AIR;
                } else {
                    if (zoneRole == ZonePlanner.VOID && g[ty][tx] == WorldGenerator.AIR)
                        g[ty][tx] = WorldGenerator.SOLID;
                }
            }
        }
    }
}
