package com.indieniinja.sim;

import com.indieniinja.physics.SpatialHash;
import com.indieniinja.physics.TileRect;

import java.util.ArrayList;
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
    // Falling platforms
    public final List<FallingPlatform> fallingPlatforms;
    // World height in pixels (used for enemy AI fall detection)
    public final float worldHeightPx;

    private LevelLayout(
            long seed, int widthTiles, int heightTiles,
            SpatialHash spatialHash,
            List<EnemySpawn> enemySpawns,
            List<PickupSpawn> pickupSpawns,
            List<FallingPlatform> fallingPlatforms) {
        this.seed             = seed;
        this.widthTiles       = widthTiles;
        this.heightTiles      = heightTiles;
        this.spatialHash      = spatialHash;
        this.enemySpawns      = enemySpawns;
        this.pickupSpawns     = pickupSpawns;
        this.fallingPlatforms = fallingPlatforms;
        this.worldHeightPx    = heightTiles * 32f;
    }

    /** Spawn descriptor for an enemy. */
    public record EnemySpawn(
        String type, float x, float y, float patrolMinX, float patrolMaxX) {}

    /** Spawn descriptor for a pickup. */
    public record PickupSpawn(String type, float x, float y) {}

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

        return new LevelLayout(seed, W, H, hash, enemies, pickups, falling);
    }
}
