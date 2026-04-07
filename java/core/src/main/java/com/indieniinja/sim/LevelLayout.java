package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.physics.SpatialHash;
import com.indieniinja.physics.TileRect;
import com.indieniinja.world.WorldGenerator;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Immutable description of a zone's tile and entity layout.
 *
 * Built once per zone from the world generator seed and passed to
 * GameSimulator at construction time. The spatial hash is pre-built here
 * so the collision system can start immediately.
 *
 * In Phase B the layout is procedurally generated from the zone seed using
 * the same algorithm as Python's systems/world_generation.py.
 * For Phase B we use a simple deterministic test layout so the server can
 * run full physics — full world gen porting is Phase C prep work.
 */
public final class LevelLayout {

    public final long    seed;
    public final int     widthTiles;
    public final int     heightTiles;
    public final SpatialHash spatialHash;

    // Enemy spawn descriptors
    public final List<EnemySpawn> enemySpawns;
    // Pickup spawn descriptors
    public final List<PickupSpawn> pickupSpawns;
    // NPC spawn descriptors
    public final List<NPCSpawn> npcSpawns;
    // Falling platforms
    public final List<FallingPlatform> fallingPlatforms;
    // World height in pixels (used for enemy AI fall detection)
    public final float worldHeightPx;

    private LevelLayout(
            long seed, int widthTiles, int heightTiles,
            SpatialHash spatialHash,
            List<EnemySpawn> enemySpawns,
            List<PickupSpawn> pickupSpawns,
            List<NPCSpawn> npcSpawns,
            List<FallingPlatform> fallingPlatforms) {
        this.seed             = seed;
        this.widthTiles       = widthTiles;
        this.heightTiles      = heightTiles;
        this.spatialHash      = spatialHash;
        this.enemySpawns      = enemySpawns;
        this.pickupSpawns     = pickupSpawns;
        this.npcSpawns        = npcSpawns;
        this.fallingPlatforms = fallingPlatforms;
        this.worldHeightPx    = heightTiles * 32f;
    }

    /** Spawn descriptor for an enemy. */
    public record EnemySpawn(
        String type, float x, float y, float patrolMinX, float patrolMaxX) {}

    /** Spawn descriptor for a pickup. */
    public record PickupSpawn(String type, float x, float y) {}

    /**
     * Spawn descriptor for an NPC.
     * Python: entities/npc.py NPCDefinition — type ∈ {lore, shop, mission_giver, tutorial}.
     */
    public record NPCSpawn(String type, float x, float y, float patrolMinX, float patrolMaxX) {}

    // ── Factory ───────────────────────────────────────────────────────────────

    /**
     * Build a minimal deterministic test layout from a seed.
     * Produces a flat floor with walls, a few enemies, and a few pickups.
     * Used by Phase B until full world gen is ported to Java in Phase C.
     */
    public static LevelLayout buildTestLayout(long seed) {
        final int TILE  = 32;
        final int W     = 64;   // tiles wide
        final int H     = 32;   // tiles tall

        SpatialHash hash = new SpatialHash();

        // Floor (full width, 2 tiles thick)
        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false));
        }

        // Left and right walls
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0,             ty * TILE, TILE, TILE, false));
            hash.insert(new TileRect((W - 1) * TILE, ty * TILE, TILE, TILE, false));
        }

        // A mid-level platform (one-way)
        for (int tx = 8; tx < 20; tx++) {
            hash.insert(new TileRect(tx * TILE, 16 * TILE, TILE, TILE, true));
        }

        // Enemies — deterministic positions derived from seed
        java.util.Random rng = new java.util.Random(seed ^ 0xDEADBEEFL);
        List<EnemySpawn> enemies = new ArrayList<>();
        String[] types = {"goblin", "slime", "wolf"};
        for (int i = 0; i < 4; i++) {
            float ex = (8 + rng.nextInt(W - 16)) * TILE;
            float ey = (H - 4) * TILE;
            String t = types[i % types.length];
            enemies.add(new EnemySpawn(t, ex, ey, ex - 3 * TILE, ex + 3 * TILE));
        }

        // Pickups
        List<PickupSpawn> pickups = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            float px = (10 + rng.nextInt(W - 20)) * TILE;
            pickups.add(new PickupSpawn(i % 2 == 0 ? "health_potion" : "coin",
                px, (H - 3) * TILE));
        }

        // Falling platforms
        List<FallingPlatform> falling = new ArrayList<>();
        for (int i = 0; i < 2; i++) {
            float fx = (15 + i * 12) * TILE;
            float fy = (H - 6) * TILE;
            falling.add(new FallingPlatform("plat_" + (int)fx + "_" + (int)fy,
                fx, fy, 3 * TILE, TILE));
        }

        return new LevelLayout(seed, W, H, hash, enemies, pickups, new ArrayList<>(), falling);
    }

    /**
     * Build a procedurally generated layout from a seed.
     *
     * Uses WorldGenerator to create a 128×128 tile grid with layered platforms
     * and mid structures, then derives enemy and pickup spawn positions from
     * valid ground positions in the generated grid.
     *
     * Replaces buildTestLayout for Loop 3+.
     */
    /** Build layout with no door openings (solid walls on all sides). */
    public static LevelLayout buildProceduralLayout(long seed) {
        return buildProceduralLayout(seed, java.util.Collections.emptySet());
    }

    /**
     * Build a procedurally generated layout from a seed, carving door openings
     * in the boundary walls for each direction in {@code neighborDirs}.
     *
     * @param seed         room seed
     * @param neighborDirs directions where adjacent rooms exist ("up","down","left","right")
     */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs) {
        final int TILE = 32;
        final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
        final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128

        byte[][] grid = WorldGenerator.generate(seed, COLS, ROWS, neighborDirs);

        // Build spatial hash from every non-air tile
        SpatialHash hash = new SpatialHash();
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                byte tile = grid[r][c];
                if (tile == WorldGenerator.AIR) continue;
                boolean oneWay = (tile == WorldGenerator.PLATFORM);
                hash.insert(new TileRect(c * TILE, r * TILE, TILE, TILE, oneWay));
            }
        }

        // Collect valid ground positions (solid/platform tile with air directly above)
        List<float[]> groundPos = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);

        // Shuffle deterministically so enemy/pickup placement varies per seed
        java.util.Random rng = new java.util.Random(seed ^ 0xBEEF_CAFEL);
        Collections.shuffle(groundPos, rng);

        // Enemies — 3-5 at first available ground positions
        List<EnemySpawn> enemies = new ArrayList<>();
        String[] enemyTypes = {"goblin", "slime", "skeleton"};
        int numEnemies = 3 + rng.nextInt(3);   // 3-5
        for (int i = 0; i < numEnemies && i < groundPos.size(); i++) {
            float[] pos = groundPos.get(i);
            String t    = enemyTypes[i % enemyTypes.length];
            float patrol = 3 * TILE;
            // posY is top of tile; enemy bottom = posY, so entity posY = posY - entityHeight
            // GameSimulator spawns using posY directly — pass the tile-top so SimEnemy.y == floor
            enemies.add(new EnemySpawn(t, pos[0], pos[1],
                pos[0] - patrol, pos[0] + patrol));
        }

        // Pickups — 2-4 at next available positions
        List<PickupSpawn> pickups = new ArrayList<>();
        String[] pickupTypes = {"coin", "health_potion", "coin"};
        int numPickups  = 2 + rng.nextInt(3);   // 2-4
        int pickupStart = numEnemies;
        for (int i = 0; i < numPickups && (pickupStart + i) < groundPos.size(); i++) {
            float[] pos = groundPos.get(pickupStart + i);
            pickups.add(new PickupSpawn(
                pickupTypes[i % pickupTypes.length], pos[0], pos[1]));
        }

        // Falling platforms — 2, placed in the mid-zone
        List<FallingPlatform> falling = new ArrayList<>();
        int mid = ROWS / 2;
        for (int i = 0; i < 2; i++) {
            float fx = (20 + i * 30) * TILE;
            float fy = (mid - 10 + i * 8) * TILE;
            falling.add(new FallingPlatform(
                "plat_" + (int) fx + "_" + (int) fy, fx, fy, 3 * TILE, TILE));
        }

        // NPCs — 1-2 lore NPCs per room at ground positions after enemies+pickups.
        // Python: npc_manager.py spawns NPCs per story state; we spawn lore NPCs
        // procedurally here as a content placeholder until the story system is ported.
        List<NPCSpawn> npcs = new ArrayList<>();
        String[] npcTypes = {"lore", "shop"};
        int numNpcs     = 1 + rng.nextInt(2);   // 1-2 NPCs
        int npcStart    = numEnemies + numPickups;
        for (int i = 0; i < numNpcs && (npcStart + i) < groundPos.size(); i++) {
            float[] pos = groundPos.get(npcStart + i);
            String t    = npcTypes[i % npcTypes.length];
            float patrol = 2 * TILE;
            npcs.add(new NPCSpawn(t, pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
        }

        return new LevelLayout(seed, COLS, ROWS, hash, enemies, pickups, npcs, falling);
    }
}
