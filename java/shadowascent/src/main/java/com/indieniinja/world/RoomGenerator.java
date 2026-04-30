package com.indieniinja.world;

import com.indieniinja.content.RoomTypeDefinition;
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
    private static final RoomGeometryRules RULES = RoomGeometryRules.loadDefault();

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
        return generate(zones, neighborDirs, roomSeed, "combat");
    }

    public static byte[][] generate(byte[][] zones, Collection<String> neighborDirs,
                                     long roomSeed, RoomTypeDefinition def) {
        return generate(zones, neighborDirs, roomSeed, def, 0);
    }

    public static byte[][] generate(byte[][] zones, Collection<String> neighborDirs,
                                     long roomSeed, RoomTypeDefinition def, int biomeIndex) {
        // Template-first: rooms that require a template try to load it before generating.
        if (def.requiresTemplate()) {
            byte[][] template = TmxRoomLoader.loadTemplate(def.id(), roomSeed);
            if (template != null) {
                RoomGeometryEnforcer.enforce(template, neighborDirs, RULES);
                return template;
            }
            // No template file found — fall through to procedural generation.
        }
        byte[][] grid = new byte[ROWS][COLS];
        boolean hasUp    = neighborDirs.contains("up");
        boolean hasDown  = neighborDirs.contains("down");
        boolean hasLeft  = neighborDirs.contains("left");
        boolean hasRight = neighborDirs.contains("right");
        RoomGeometryEnforcer.addBoundaries(grid, neighborDirs, RULES);
        if (!hasDown) {
            for (int c = 1; c < COLS - 1; c++)
                if (grid[ROWS - 2][c] == WorldGenerator.AIR)
                    grid[ROWS - 2][c] = WorldGenerator.PLATFORM;
        }
        for (int zy = 0; zy < ZonePlanner.H; zy++)
            for (int zx = 0; zx < ZonePlanner.W; zx++) {
                Random zoneRng = new Random(roomSeed * 31L + (long) zy * ZonePlanner.W + zx);
                expandZone(grid, zx, zy, zones[zy][zx], biomeIndex, zoneRng, hasUp, hasDown, hasLeft, hasRight);
            }
        RoomGeometryEnforcer.carveDoors(grid, neighborDirs, RULES);
        FeaturePlacer.place(grid, biomeIndex, roomSeed, neighborDirs);
        smoothCaveTerrain(grid, biomeIndex);
        addBlobVariationFromDef(grid, zones, roomSeed, def);
        RoomGeometryEnforcer.enforce(grid, neighborDirs, RULES);
        return grid;
    }

    public static byte[][] generate(byte[][] zones, Collection<String> neighborDirs,
                                     long roomSeed, String roomType) {
        return generate(zones, neighborDirs, roomSeed, roomType, 0);
    }

    public static byte[][] generate(byte[][] zones, Collection<String> neighborDirs,
                                     long roomSeed, String roomType, int biomeIndex) {
        // Template-first: any room type that has a matching .tmx file uses it.
        // Falls through to procedural generation when no template is found.
        byte[][] template = TmxRoomLoader.loadTemplate(roomType, roomSeed);
        if (template != null) {
            RoomGeometryEnforcer.enforce(template, neighborDirs, RULES);
            return template;
        }

        byte[][] grid = new byte[ROWS][COLS];

        boolean hasUp    = neighborDirs.contains("up");
        boolean hasDown  = neighborDirs.contains("down");
        boolean hasLeft  = neighborDirs.contains("left");
        boolean hasRight = neighborDirs.contains("right");

        RoomGeometryEnforcer.addBoundaries(grid, neighborDirs, RULES);

        if (!hasDown) {
            for (int c = 1; c < COLS - 1; c++) {
                if (grid[ROWS - 2][c] == WorldGenerator.AIR)
                    grid[ROWS - 2][c] = WorldGenerator.PLATFORM;
            }
        }

        for (int zy = 0; zy < ZonePlanner.H; zy++) {
            for (int zx = 0; zx < ZonePlanner.W; zx++) {
                Random zoneRng = new Random(roomSeed * 31L + (long) zy * ZonePlanner.W + zx);
                expandZone(grid, zx, zy, zones[zy][zx], biomeIndex, zoneRng, hasUp, hasDown, hasLeft, hasRight);
            }
        }

        RoomGeometryEnforcer.carveDoors(grid, neighborDirs, RULES);
        FeaturePlacer.place(grid, biomeIndex, roomSeed, neighborDirs);
        smoothCaveTerrain(grid, biomeIndex);
        addBlobVariation(grid, zones, roomSeed, roomType);
        RoomGeometryEnforcer.enforce(grid, neighborDirs, RULES);

        return grid;
    }

    // ── Step 1 — Boundaries ───────────────────────────────────────────────────

    private static void addBoundaries(byte[][] g,
                                       boolean hasUp, boolean hasDown,
                                       boolean hasLeft, boolean hasRight) {
        int edge = RULES.edgeWallThickness();
        int floor = RULES.floorThickness();

        // Top wall
        if (!hasUp) {
            for (int r = 0; r < edge; r++)
                for (int c = 0; c < COLS; c++)
                    g[r][c] = WorldGenerator.SOLID;
        }
        // Bottom wall
        if (!hasDown) {
            for (int r = ROWS - floor; r < ROWS; r++)
                for (int c = 0; c < COLS; c++)
                    g[r][c] = WorldGenerator.SOLID;
        }
        // Left wall
        if (!hasLeft) {
            for (int r = 0; r < ROWS; r++)
                for (int c = 0; c < edge; c++)
                    g[r][c] = WorldGenerator.SOLID;
        }
        // Right wall
        if (!hasRight) {
            for (int r = 0; r < ROWS; r++)
                for (int c = COLS - edge; c < COLS; c++)
                    g[r][c] = WorldGenerator.SOLID;
        }
    }

    // ── Step 3 — Zone expansion ───────────────────────────────────────────────

    private static void stampTemplate(byte[][] g, int zx, int zy, byte[][] t) {
        int txStart = zx * TPZ;
        int tyStart = zy * TPZ;
        for (int r = 0; r < TPZ; r++)
            for (int c = 0; c < TPZ; c++)
                if (inBounds(txStart + c, tyStart + r))
                    g[tyStart + r][txStart + c] = t[r][c];
    }

    private static void expandZone(byte[][] g, int zx, int zy, byte role,
                                    int biomeIndex, Random zoneRng,
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
                // S6: pick from template pool instead of always filling solid
                stampTemplate(g, zx, zy, ZoneTemplateLibrary.pick(ZonePlanner.FILL, biomeIndex, zoneRng));
            }
            case ZonePlanner.PLAT, ZonePlanner.CONN -> {
                // S6: pick from template pool instead of always placing a full-bar platform
                stampTemplate(g, zx, zy, ZoneTemplateLibrary.pick(ZonePlanner.PLAT, biomeIndex, zoneRng));
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
            case ZonePlanner.LAVA -> {
                // Lava floor at zone bottom — solid tile with LAVA type
                int floorY = tyEnd - 1;
                for (int tx = txStart; tx < txEnd; tx++)
                    if (inBounds(tx, floorY)) g[floorY][tx] = WorldGenerator.LAVA;
            }
            case ZonePlanner.ICE -> {
                // Ice platform at zone middle — solid with ICE type (low friction)
                int platY = tyStart + TPZ / 2;
                for (int tx = txStart; tx < txEnd; tx++)
                    if (inBounds(tx, platY)) g[platY][tx] = WorldGenerator.ICE;
            }
            case ZonePlanner.WATER -> {
                // Water fills the zone vertically — passable, slows movement
                for (int ty = tyStart; ty < tyEnd; ty++)
                    for (int tx = txStart; tx < txEnd; tx++)
                        if (inBounds(tx, ty) && g[ty][tx] == WorldGenerator.AIR)
                            g[ty][tx] = WorldGenerator.WATER;
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
        int doorHalf = RULES.doorHalfSpan();
        int horizontalDepth = RULES.horizontalDoorDepth();
        int verticalDepth = RULES.verticalDoorDepth();

        for (String dir : dirs) {
            switch (dir) {
                case "up" -> {
                    for (int r = 0; r < verticalDepth; r++)
                        for (int c = midC - doorHalf; c <= midC + doorHalf; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
                case "down" -> {
                    for (int r = ROWS - verticalDepth; r < ROWS; r++)
                        for (int c = midC - doorHalf; c <= midC + doorHalf; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
                case "left" -> {
                    for (int r = midR - doorHalf; r <= midR + doorHalf; r++)
                        for (int c = 0; c < horizontalDepth; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
                case "right" -> {
                    for (int r = midR - doorHalf; r <= midR + doorHalf; r++)
                        for (int c = COLS - horizontalDepth; c < COLS; c++)
                            if (inBounds(c, r)) g[r][c] = WorldGenerator.AIR;
                }
            }
        }
    }

    // ── Step 5 — Blob variation ───────────────────────────────────────────────

    private static void addBlobVariationFromDef(byte[][] g, byte[][] zones, long roomSeed,
                                                  RoomTypeDefinition def) {
        Random rng = new Random(roomSeed + 1337L);
        int blobCount = switch (def.terrainDensity()) {
            case 0 ->  4 + rng.nextInt(4);   //  4-7  (open/clean)
            case 1 -> 10 + rng.nextInt(8);   // 10-17 (moderate)
            case 2 -> 14 + rng.nextInt(10);  // 14-23 (dense)
            case 3 -> 18 + rng.nextInt(10);  // 18-27 (maze-like)
            default -> 8 + rng.nextInt(10);
        };
        for (int b = 0; b < blobCount; b++) {
            int blobW = 2 + rng.nextInt(31);
            int blobH = 2 + rng.nextInt(31);
            int cx    = 2 + rng.nextInt(COLS - 4);
            int cy    = 2 + rng.nextInt(ROWS - 4);
            stampBlob(g, zones, cx, cy, blobW, blobH, 0.35f + rng.nextFloat() * 0.55f, rng.nextBoolean(), rng);
        }
    }

    /**
     * Add elliptical solid/carved blobs inside FILL/VOID zones for visual richness.
     * Python parity: RoomGenerator._apply_tile_variation().
     */
    private static void addBlobVariation(byte[][] g, byte[][] zones, long roomSeed,
                                          String roomType) {
        Random rng = new Random(roomSeed + 1337L);

        // Blob count by terrainDensity (0=open, 1=moderate, 2=dense, 3=maze)
        // Legacy string path kept for callers that don't yet pass RoomTypeDefinition.
        int blobCount = switch (roomType != null ? roomType : "combat") {
            case "combat"   -> 14 + rng.nextInt(10);  // density 2: 14-23
            case "treasure" -> 18 + rng.nextInt(10);  // density 3: 18-27 (maze-like)
            case "platform" -> 10 + rng.nextInt(8);   // density 1: 10-17
            case "boss"     ->  6 + rng.nextInt(6);   // density 0:  6-11 (open arena)
            case "shop", "start", "exit" -> 4 + rng.nextInt(4); // density 0: 4-7
            default         ->  8 + rng.nextInt(10);  // density 1:  8-17
        };

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

    // ── S8 — Terrain Smoothing (cave biomes) ─────────────────────────────────

    /**
     * Single cellular automata pass to smooth jagged cave terrain.
     * Only applied to earth biomes (index 0 and 5); all others are unchanged.
     *
     * Rules:
     *   SOLID tile with fewer than 3 SOLID 8-neighbours → AIR  (remove isolated tile)
     *   AIR   tile with more than 5 SOLID 8-neighbours → SOLID (fill tiny pocket)
     *
     * Boundary rows/cols (index 0 and ROWS/COLS-1) are never modified.
     * replay=BREAKING from v0.12.09.
     */
    public static void smoothCaveTerrain(byte[][] grid, int biomeIndex) {
        // Cave smoothing only for EARTH (0) and EARTH_ALT (5)
        if (biomeIndex != 0 && biomeIndex != 5) return;

        byte[][] next = new byte[ROWS][COLS];
        for (int r = 0; r < ROWS; r++) next[r] = grid[r].clone();

        for (int r = 1; r < ROWS - 1; r++) {
            for (int c = 1; c < COLS - 1; c++) {
                int solidNeighbours = 0;
                for (int dr = -1; dr <= 1; dr++)
                    for (int dc = -1; dc <= 1; dc++) {
                        if (dr == 0 && dc == 0) continue;
                        byte nb = grid[r + dr][c + dc];
                        if (nb == WorldGenerator.SOLID || nb == WorldGenerator.CLIMBABLE) solidNeighbours++;
                    }

                byte cur = grid[r][c];
                if (cur == WorldGenerator.SOLID && solidNeighbours < 3) {
                    next[r][c] = WorldGenerator.AIR;
                } else if (cur == WorldGenerator.AIR && solidNeighbours > 5) {
                    next[r][c] = WorldGenerator.SOLID;
                }
            }
        }

        for (int r = 1; r < ROWS - 1; r++)
            for (int c = 1; c < COLS - 1; c++)
                grid[r][c] = next[r][c];
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
