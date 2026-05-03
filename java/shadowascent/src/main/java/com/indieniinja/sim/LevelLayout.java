package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.BossType;
import com.indieniinja.physics.SpatialHash;
import com.indieniinja.physics.TileRect;
import com.indieniinja.world.HubRegistry;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.postprocess.RoomContent;
import com.indieniinja.world.postprocess.RoomPostProcessor;
import com.indieniinja.world.puzzle.PuzzlePlan;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.room.GeneratedRoom;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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

    private static final Logger log = LoggerFactory.getLogger(LevelLayout.class);

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
    // Boss spawn (null if room is not a boss room)
    public final BossSpawn bossSpawn;
    // Portal spawns (empty list if no portals in this room)
    public final List<PortalSpawn> portalSpawns;
    // Falling platforms
    public final List<FallingPlatform> fallingPlatforms;
    // Moving (oscillating) platforms
    public final List<SimMovingPlatform> movingPlatforms;
    // World height in pixels (used for enemy AI fall detection)
    public final float worldHeightPx;
    /** Recommended player spawn position derived from the generated layout. */
    public final float spawnX;
    public final float spawnY;
    /**
     * Puzzle door tiles keyed by puzzleId (e.g. "kd_0", "ld_0").
     * GameSimulator removes these from the SpatialHash when the door is unlocked.
     * Empty map for layouts built without the post-processing pipeline.
     */
    public final Map<String, List<TileRect>> doorTiles;

    private LevelLayout(
            long seed, int widthTiles, int heightTiles,
            SpatialHash spatialHash,
            List<EnemySpawn> enemySpawns,
            List<PickupSpawn> pickupSpawns,
            List<NPCSpawn> npcSpawns,
            BossSpawn bossSpawn,
            List<PortalSpawn> portalSpawns,
            List<FallingPlatform> fallingPlatforms,
            List<SimMovingPlatform> movingPlatforms,
            float spawnX, float spawnY,
            Map<String, List<TileRect>> doorTiles) {
        this.seed             = seed;
        this.widthTiles       = widthTiles;
        this.heightTiles      = heightTiles;
        this.spatialHash      = spatialHash;
        this.enemySpawns      = enemySpawns;
        this.pickupSpawns     = pickupSpawns;
        this.npcSpawns        = npcSpawns;
        this.bossSpawn        = bossSpawn;
        this.portalSpawns     = portalSpawns != null ? portalSpawns : new ArrayList<>();
        this.fallingPlatforms = fallingPlatforms;
        this.movingPlatforms  = movingPlatforms != null ? movingPlatforms : new ArrayList<>();
        this.worldHeightPx    = heightTiles * 32f;
        this.spawnX           = spawnX;
        this.spawnY           = spawnY;
        this.doorTiles        = doorTiles != null ? doorTiles : Collections.emptyMap();
    }

    /** Return a copy of this layout with the boss spawn removed (used for hub zones). */
    public LevelLayout withoutBoss() {
        return new LevelLayout(seed, widthTiles, heightTiles, spatialHash,
            enemySpawns, pickupSpawns, npcSpawns, null,
            portalSpawns, fallingPlatforms, movingPlatforms, spawnX, spawnY, doorTiles);
    }

    /** Spawn descriptor for an enemy. */
    public record EnemySpawn(
        String type, float x, float y, float patrolMinX, float patrolMaxX) {}

    /** Spawn descriptor for a pickup. */
    public record PickupSpawn(String type, float x, float y) {}

    /**
     * Spawn descriptor for an NPC.
     * Python: entities/npc.py NPCDefinition — type ∈ {lore, shop, mission_giver, tutorial, siren}.
     */
    public record NPCSpawn(String type, float x, float y, float patrolMinX, float patrolMaxX) {}

    /**
     * Spawn descriptor for a boss.
     * One per "boss" room, positioned at the centre-bottom of the arena.
     */
    public record BossSpawn(String bossTypeWire, float x, float y) {}

    /**
     * Spawn descriptor for a portal.
     * portalType: "hub" for hub-to-hub travel, "mission" for dungeon entry.
     * requiredAbility: empty = always open; otherwise player must have unlocked that ability.
     */
    public record PortalSpawn(
        String portalType, String destinationId,
        float x, float y, String requiredAbility) {}

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

        // Spawn at centre of floor in the test layout
        float testSpawnX = (W / 2) * TILE;
        float testSpawnY = (H - 2) * TILE - 56f;   // player height = 56
        return new LevelLayout(seed, W, H, hash, enemies, pickups, new ArrayList<>(), null,
                new ArrayList<>(), falling, new ArrayList<>(), testSpawnX, testSpawnY, null);
    }

    /**
     * Deterministic traversal fixture:
     * - one CLIMBABLE wall column (for climb-only logic assertions)
     * - one plain SOLID wall column (negative control)
     * - one-way ledge strip for ledge-grab/ledge-climb state transitions
     */
    public static LevelLayout buildTraversalLedgeFixtureLayout(long seed) {
        final int TILE  = 32;
        final int W     = 64;
        final int H     = 32;

        SpatialHash hash = new SpatialHash();

        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        // Non-climbable wall (negative climb control)
        for (int ty = 14; ty <= 27; ty++) {
            hash.insert(new TileRect(14 * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        // Climbable wall (positive climb control)
        for (int ty = 14; ty <= 27; ty++) {
            hash.insert(new TileRect(20 * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.CLIMBABLE));
        }
        // One-way ledge strip for grab/hang/climb transitions
        for (int tx = 30; tx <= 33; tx++) {
            hash.insert(new TileRect(tx * TILE, 18 * TILE, TILE, TILE, true, WorldGenerator.PLATFORM));
        }

        float spawnX = 19 * TILE;
        float spawnY = 17 * TILE;
        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, null);
    }

    /**
     * Deterministic water-exit fixture:
     * - rectangular water basin
     * - explicit solid bank on the right side
     * Used to assert water->solid bank exit transitions.
     */
    public static LevelLayout buildWaterExitFixtureLayout(long seed) {
        final int TILE  = 32;
        final int W     = 64;
        final int H     = 32;

        SpatialHash hash = new SpatialHash();

        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        // Water basin interior.
        for (int ty = 20; ty <= 29; ty++) {
            for (int tx = 18; tx <= 23; tx++) {
                hash.insert(new TileRect(tx * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.WATER));
            }
        }
        // Solid right bank with open headroom to allow body placement on exit.
        for (int ty = 22; ty <= 31; ty++) {
            hash.insert(new TileRect(24 * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        float spawnX = 23 * TILE - 18f;
        float spawnY = 22 * TILE;
        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, null);
    }

    /**
     * Deterministic water-surface fixture:
     * - broad water column with no reachable side-bank within probe distance
     * Used to assert surface jump burst routing independent of bank exits.
     */
    public static LevelLayout buildWaterSurfaceFixtureLayout(long seed) {
        final int TILE  = 32;
        final int W     = 64;
        final int H     = 32;

        SpatialHash hash = new SpatialHash();

        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        for (int ty = 19; ty <= 29; ty++) {
            for (int tx = 28; tx <= 36; tx++) {
                hash.insert(new TileRect(tx * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.WATER));
            }
        }

        // Top of player sits above water top, but body still intersects water for at-surface context.
        float spawnX = 32 * TILE - 14f;
        float spawnY = 19 * TILE - 20f;
        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, null);
    }

    /**
     * Deterministic blocked-bank fixture:
     * - same water basin as water-exit fixture
     * - adds a blocking cap over the bank top-out region so bank-exit fails
     * Used to assert fallback to surface jump behavior.
     */
    public static LevelLayout buildBlockedWaterExitFixtureLayout(long seed) {
        LevelLayout base = buildWaterExitFixtureLayout(seed);
        SpatialHash hash = new SpatialHash();

        final int TILE = 32;
        final int W = 64;
        final int H = 32;

        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 20; ty <= 29; ty++) {
            for (int tx = 18; tx <= 23; tx++) {
                hash.insert(new TileRect(tx * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.WATER));
            }
        }
        for (int ty = 22; ty <= 31; ty++) {
            hash.insert(new TileRect(24 * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        // Blocking shoulder near bank top-out region. Positioned left of the
        // bank column so it blocks body placement without becoming the exit target.
        hash.insert(new TileRect(23 * TILE, 20 * TILE, TILE, TILE, false, WorldGenerator.SOLID));

        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), base.spawnX, base.spawnY, null);
    }

    /**
     * Deterministic interaction fixture:
     * - flat room with a single interactable puzzle marker NPC near spawn.
     * - markerType should be one of: "lever_<id>", "btn_<index>_<id>", "echo_trigger_<id>".
     */
    public static LevelLayout buildInteractionMarkerFixtureLayout(long seed, String markerType) {
        final int TILE  = 32;
        final int W     = 32;
        final int H     = 24;

        SpatialHash hash = new SpatialHash();

        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        float spawnX = 8 * TILE;
        float spawnY = (H - 2) * TILE - 56f;
        String marker = (markerType == null || markerType.isBlank()) ? "lever_fixture_0" : markerType;
        float markerX = spawnX + 36f;
        float markerY = (H - 2) * TILE - SimNPC.DEFAULT_HEIGHT;

        List<NPCSpawn> npcs = java.util.List.of(
            new NPCSpawn(marker, markerX, markerY, markerX - 4f, markerX + 4f)
        );

        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), npcs, null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, null);
    }

    /**
     * Fixture for ASYMMETRIC_ABILITY_LOCK tests.
     * Flat room; one aal_echo_ NPC at center-floor; one DOOR_LOCKED tile registered so
     * unlockDoor() can succeed. Player spawn is placed within AAL_PROXIMITY_PX (96px) of
     * the echo for easy "in range" tests.
     */
    public static LevelLayout buildAalFixtureLayout(long seed, String puzzleId) {
        final int TILE = 32;
        final int W = 32;
        final int H = 24;

        SpatialHash hash = new SpatialHash();
        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        float echoX = 15 * TILE;
        float echoY = (H - 2) * TILE - SimNPC.DEFAULT_HEIGHT;
        List<NPCSpawn> npcs = java.util.List.of(
            new NPCSpawn("aal_echo_" + puzzleId, echoX, echoY, echoX - 4f, echoX + 4f)
        );

        TileRect doorTile = new TileRect(20 * TILE, (float)(H - 2) * TILE, TILE, 3 * TILE, false, WorldGenerator.DOOR_LOCKED);
        hash.insert(doorTile);
        Map<String, List<TileRect>> doors = java.util.Map.of(
            "aal_door_" + puzzleId, java.util.List.of(doorTile));

        // Spawn just below echo so proximity check always passes (same x)
        float spawnX = echoX;
        float spawnY = (H - 2) * TILE - 56f;
        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), npcs, null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, doors);
    }

    /**
     * Fixture for SIMULTANEOUS_TIMING tests.
     * Flat room; one st_trigger_ NPC within interaction range of player spawn;
     * one DOOR_LOCKED tile registered so unlockDoor() can succeed.
     */
    public static LevelLayout buildStFixtureLayout(long seed, String puzzleId) {
        final int TILE = 32;
        final int W = 32;
        final int H = 24;

        SpatialHash hash = new SpatialHash();
        for (int tx = 0; tx < W; tx++) {
            hash.insert(new TileRect(tx * TILE, (H - 2) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect(tx * TILE, (H - 1) * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }
        for (int ty = 0; ty < H; ty++) {
            hash.insert(new TileRect(0, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
            hash.insert(new TileRect((W - 1) * TILE, (float) ty * TILE, TILE, TILE, false, WorldGenerator.SOLID));
        }

        float spawnX  = 8 * TILE;
        float spawnY  = (H - 2) * TILE - 56f;
        float markerX = spawnX + 36f;
        float markerY = (H - 2) * TILE - SimNPC.DEFAULT_HEIGHT;
        List<NPCSpawn> npcs = java.util.List.of(
            new NPCSpawn("st_trigger_" + puzzleId, markerX, markerY, markerX - 4f, markerX + 4f)
        );

        TileRect doorTile = new TileRect(20 * TILE, (float)(H - 2) * TILE, TILE, 3 * TILE, false, WorldGenerator.DOOR_LOCKED);
        hash.insert(doorTile);
        Map<String, List<TileRect>> doors = java.util.Map.of(
            "st_door_" + puzzleId, java.util.List.of(doorTile));

        return new LevelLayout(seed, W, H, hash,
            new ArrayList<>(), new ArrayList<>(), npcs, null,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, doors);
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
        return buildProceduralLayout(seed, java.util.Collections.emptySet(), "combat", "central_hub");
    }

    /** Build layout with door openings but default room type. */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs) {
        return buildProceduralLayout(seed, neighborDirs, "combat", "central_hub");
    }

    /** Build layout with room type but no hub context (defaults to central_hub for portals). */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs, String roomType) {
        return buildProceduralLayout(seed, neighborDirs, roomType, "central_hub");
    }

    /**
     * Build a procedurally generated layout using the zone-planning pipeline.
     * Overload that also stitches adjacent room tiles into the SpatialHash so
     * tiles visible at room boundaries have collision backing.
     *
     * @param seed          room seed
     * @param neighborDirs  directions where adjacent rooms exist
     * @param roomType      wire string
     * @param adjacentRooms map of direction → RoomNode for each existing neighbor
     */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs, String roomType,
            java.util.Map<String, WorldGraph.RoomNode> adjacentRooms) {
        return buildProceduralLayout(seed, neighborDirs, roomType, adjacentRooms, "central_hub");
    }

    /**
     * Full overload: stitches adjacent room tiles into the SpatialHash AND uses
     * masterHubId for HubRegistry portal destination lookup (Loop 15).
     */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs, String roomType,
            java.util.Map<String, WorldGraph.RoomNode> adjacentRooms, String masterHubId) {
        // Build the current room layout first
        LevelLayout base = buildProceduralLayout(seed, neighborDirs, roomType, masterHubId);

        if (adjacentRooms == null || adjacentRooms.isEmpty()) return base;

        final int TILE    = 32;
        final int COLS    = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
        final int ROWS    = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128
        final int ROOM_PX = COLS * TILE;                         // 4096

        // Clone the SpatialHash by re-inserting all existing tiles, then add neighbors.
        // (LevelLayout.spatialHash is immutable after build, so we need a fresh one.)
        SpatialHash extended = new SpatialHash();

        // Re-insert all current-room tiles from the existing hash by regenerating —
        // faster than exposing an iterator on SpatialHash.
        byte[][] grid = WorldGenerator.generate(seed, COLS, ROWS, neighborDirs, roomType);
        for (int r = 0; r < ROWS; r++)
            for (int c = 0; c < COLS; c++) {
                byte tile = grid[r][c];
                if (tile == WorldGenerator.AIR) continue;
                extended.insert(new TileRect(c * TILE, r * TILE, TILE, TILE,
                    tile == WorldGenerator.PLATFORM));
            }

        // Add each adjacent room's tiles at its relative offset
        for (java.util.Map.Entry<String, WorldGraph.RoomNode> e : adjacentRooms.entrySet()) {
            String dir      = e.getKey();
            WorldGraph.RoomNode nb = e.getValue();
            int offX = 0, offY = 0;
            switch (dir) {
                case "up"    -> offY = -ROOM_PX;
                case "down"  -> offY = +ROOM_PX;
                case "left"  -> offX = -ROOM_PX;
                case "right" -> offX = +ROOM_PX;
            }
            byte[][] adjGrid = WorldGenerator.generate(
                nb.seed, COLS, ROWS,
                new java.util.ArrayList<>(nb.neighborDirs()), nb.type.wire());
            for (int r = 0; r < ROWS; r++)
                for (int c = 0; c < COLS; c++) {
                    byte tile = adjGrid[r][c];
                    if (tile == WorldGenerator.AIR) continue;
                    extended.insert(new TileRect(
                        offX + c * TILE, offY + r * TILE, TILE, TILE,
                        tile == WorldGenerator.PLATFORM));
                }
            log.info("[LevelLayout] added neighbor '{}' seed={} to SpatialHash (offset {},{})px",
                dir, nb.seed, offX, offY);
        }

        return new LevelLayout(seed, COLS, ROWS, extended,
            base.enemySpawns, base.pickupSpawns, base.npcSpawns, base.bossSpawn,
            base.portalSpawns, base.fallingPlatforms, base.movingPlatforms, base.spawnX, base.spawnY, null);
    }

    /**
     * Build a procedurally generated layout using the zone-planning pipeline.
     *
     * @param seed         room seed
     * @param neighborDirs directions where adjacent rooms exist ("up","down","left","right")
     * @param roomType     wire string: "start","exit","shop","combat","platform","treasure","boss"
     * @param masterHubId  hub this room belongs to — used for HubRegistry portal destinations
     */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs, String roomType,
            String masterHubId) {
        final int TILE = 32;
        final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
        final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128

        byte[][] grid;
        if (Boolean.getBoolean("ninja.runtime.useProcgenRooms")) {
            grid = buildProcgenGrid(seed, COLS, ROWS, neighborDirs, roomType);
            log.info("[LevelLayout] useProcgenRooms=true seed={} type={}", seed, roomType);
        } else {
            grid = WorldGenerator.generate(seed, COLS, ROWS, neighborDirs, roomType);
        }

        // ── Diagnostic: grid fingerprint (server-side collision grid) ─────────
        int solidCount = 0, platCount = 0;
        for (int r = 0; r < ROWS; r++)
            for (int c = 0; c < COLS; c++) {
                if (grid[r][c] == WorldGenerator.SOLID)    solidCount++;
                else if (grid[r][c] == WorldGenerator.PLATFORM) platCount++;
            }
        // Sample rows 124-127 at column 64 (centre-bottom) — base floor area
        StringBuilder sample = new StringBuilder();
        for (int r = 124; r <= 127; r++)
            sample.append('r').append(r).append('=').append(grid[r][64]).append(' ');
        log.info("[LevelLayout] SERVER grid seed={} type={} dirs={} solid={} plat={} | centre-bottom: {}",
            seed, roomType, neighborDirs, solidCount, platCount, sample.toString().trim());

        // Build spatial hash from every non-air tile.
        // WATER tiles are passable (isPlatform=false, but collision system treats them
        // as fluid zones rather than solid blockers — checked via tileType).
        SpatialHash hash = new SpatialHash();
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                byte tile = grid[r][c];
                if (tile == WorldGenerator.AIR) continue;
                boolean oneWay = (tile == WorldGenerator.PLATFORM);
                hash.insert(new TileRect(c * TILE, r * TILE, TILE, TILE, oneWay, tile));
            }
        }

        // Collect valid ground positions (solid/platform tile with air directly above)
        List<float[]> groundPos = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);

        // Compute spawn: ground position nearest to room centre-bottom.
        // Search within ±3 zone widths of centre-x (centre ± 3*8*32 = ±768 px).
        float centreX   = COLS * TILE * 0.5f;  // 2048
        float spawnX    = centreX;
        float spawnY    = (ROWS - 2) * TILE - 56f;   // fallback: base floor − player height
        float bestScore = Float.MAX_VALUE;
        for (float[] pos : groundPos) {
            float dx = Math.abs(pos[0] - centreX);
            if (dx > 3 * 8 * TILE) continue;            // outside centre band
            float dy = (ROWS * TILE) - pos[1];           // distance from bottom (lower = better)
            float score = dy * 0.3f + dx;                // favour bottom-centre
            if (score < bestScore) {
                bestScore = score;
                spawnX = pos[0];
                spawnY = pos[1] - 56f;                   // entity top = floor top − height
            }
        }
        // No ground in the centre band (can happen for start/platform rooms with little
        // centre geometry). Retry without the band filter so we always find a valid spawn.
        if (bestScore == Float.MAX_VALUE) {
            for (float[] pos : groundPos) {
                float dx = Math.abs(pos[0] - centreX);
                float dy = (ROWS * TILE) - pos[1];
                float score = dy * 0.3f + dx;
                if (score < bestScore) {
                    bestScore = score;
                    spawnX = pos[0];
                    spawnY = pos[1] - 56f;
                }
            }
        }

        // Shuffle deterministically so enemy/pickup placement varies per seed
        java.util.Random rng = new java.util.Random(seed ^ 0xBEEF_CAFEL);
        Collections.shuffle(groundPos, rng);

        // ── Room-type-specific spawn rules ───────────────────────────────────────
        boolean isBossRoom     = "boss".equals(roomType);
        boolean isCombatRoom   = "combat".equals(roomType);
        boolean isPlatformRoom = "platform".equals(roomType);
        boolean isTreasureRoom = "treasure".equals(roomType);
        boolean isShopRoom     = "shop".equals(roomType);
        boolean isStartRoom    = "start".equals(roomType);

        // ── Boss room: one boss + 2-4 minion enemies; no regular pickups ─────
        BossSpawn bossSpawn = null;
        if (isBossRoom) {
            BossType bt = BossType.fromSeed(seed);
            bossSpawn = new BossSpawn(bt.wire, spawnX, spawnY);
        }

        // ── Enemy count/type by room type ─────────────────────────────────────
        // Combat: 5-8 enemies (dense); Boss: 2-4 minions; Platform: 1-3 (sparse, higher level);
        // Treasure: 0-1 guards; Shop/Start/Exit: 0
        List<EnemySpawn> enemies = new ArrayList<>();
        String[] heavyTypes  = {"skeleton", "wolf", "skeleton"};
        String[] standardTypes = {"goblin", "slime", "skeleton"};
        String[] lightTypes  = {"goblin", "slime", "goblin"};

        int numEnemies;
        String[] chosenTypes;
        float patrolMult = 1f;
        if (isBossRoom) {
            numEnemies = 2 + rng.nextInt(3);   // 2-4 minions around boss
            chosenTypes = heavyTypes;
        } else if (isCombatRoom) {
            numEnemies = 5 + rng.nextInt(4);   // 5-8 enemies
            chosenTypes = standardTypes;
            patrolMult = 1.5f;
        } else if (isPlatformRoom) {
            numEnemies = 1 + rng.nextInt(3);   // 1-3 enemies
            chosenTypes = heavyTypes;           // harder enemies, fewer of them
            patrolMult = 0.5f;                 // shorter patrol (height-constrained)
        } else if (isTreasureRoom) {
            numEnemies = rng.nextInt(2);        // 0-1 guards
            chosenTypes = heavyTypes;
        } else if (isShopRoom || isStartRoom || "exit".equals(roomType)) {
            numEnemies = 0;
            chosenTypes = standardTypes;
        } else {
            numEnemies = 3 + rng.nextInt(3);   // 3-5 for other types
            chosenTypes = standardTypes;
        }

        for (int i = 0; i < numEnemies && i < groundPos.size(); i++) {
            float[] pos = groundPos.get(i);
            String t    = chosenTypes[i % chosenTypes.length];
            float patrol = (3 + rng.nextInt(3)) * TILE * patrolMult;
            enemies.add(new EnemySpawn(t, pos[0], pos[1],
                pos[0] - patrol, pos[0] + patrol));
        }

        // ── Pickups by room type ───────────────────────────────────────────────
        // Combat: 2-4 coins + 1-2 health; Platform: 1-2 items in corners;
        // Treasure: 2-4 high-value items (gem, rare_potion, equip);
        // Boss: 4-6 high-value drops after kill; Shop/Start: minimal
        List<PickupSpawn> pickups = new ArrayList<>();
        int numPickups;
        String[] pickupTypes;
        if (isBossRoom) {
            numPickups  = 4 + rng.nextInt(3);   // 4-6 post-boss drops
            pickupTypes = new String[]{"gem", "rare_potion", "coin", "gem", "coin", "health_potion"};
        } else if (isTreasureRoom) {
            numPickups  = 2 + rng.nextInt(3);   // 2-4 high-value
            pickupTypes = new String[]{"gem", "rare_potion", "gem", "coin"};
        } else if (isCombatRoom) {
            numPickups  = 2 + rng.nextInt(3);   // 2-4 standard
            pickupTypes = new String[]{"coin", "health_potion", "coin", "coin"};
        } else if (isPlatformRoom) {
            numPickups  = 1 + rng.nextInt(3);   // 1-3
            pickupTypes = new String[]{"coin", "health_potion", "coin"};
        } else if (isShopRoom || isStartRoom) {
            numPickups  = 1 + rng.nextInt(2);   // 1-2 starter items
            pickupTypes = new String[]{"health_potion", "coin"};
        } else {
            numPickups  = 2 + rng.nextInt(3);
            pickupTypes = new String[]{"coin", "health_potion", "coin"};
        }
        int pickupStart = numEnemies;
        for (int i = 0; i < numPickups && (pickupStart + i) < groundPos.size(); i++) {
            float[] pos = groundPos.get(pickupStart + i);
            pickups.add(new PickupSpawn(
                pickupTypes[i % pickupTypes.length], pos[0], pos[1]));
        }

        // ── Adjacent-room health cache: if THIS room is adjacent to a combat
        //    room (caller passes type info), add 1-2 health pickups. ─────────
        // For now, combat and boss rooms always add a guaranteed health potion
        // at the spawn point for respawn safety.
        if ((isCombatRoom || isBossRoom) && !groundPos.isEmpty()) {
            float[] safePos = groundPos.get(Math.min(numEnemies + numPickups, groundPos.size()-1));
            pickups.add(new PickupSpawn("health_potion", safePos[0], safePos[1]));
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

        // NPCs — 1-3 per room: base types plus a crafter in crafting/shop rooms.
        // Python: npc_manager.py spawns NPCs per story state; we spawn procedurally here.
        List<NPCSpawn> npcs = new ArrayList<>();
        // Base NPC rotation: lore, shop, mission_giver.
        // Start-room onboarding guarantees Siren as the first quest-giver contact.
        String[] baseNpcTypes = {"lore", "shop", "mission_giver"};
        int numNpcs  = 1 + rng.nextInt(2);   // 1-2 base NPCs
        int npcStart = numEnemies + numPickups;
        for (int i = 0; i < numNpcs && (npcStart + i) < groundPos.size(); i++) {
            float[] pos = groundPos.get(npcStart + i);
            String t    = (isStartRoom && i == 0) ? "siren" : baseNpcTypes[i % baseNpcTypes.length];
            float patrol = 2 * TILE;
            npcs.add(new NPCSpawn(t, pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
        }
        // Crafting NPC: always spawned in shop/start rooms; 25% chance in other rooms.
        boolean isShopOrStart = "shop".equals(roomType) || "start".equals(roomType);
        boolean addCrafter    = isShopOrStart || (rng.nextInt(4) == 0);
        int crafterIdx = npcStart + numNpcs;
        if (addCrafter && crafterIdx < groundPos.size()) {
            float[] pos = groundPos.get(crafterIdx);
            float patrol = 2 * TILE;
            npcs.add(new NPCSpawn("crafter", pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
        }

        // Portals — placed only in exit rooms. Start rooms have no portal: the player
        // arrives there from the previous hub's exit portal, and the spawn point IS the
        // "entry" anchor. A start-room portal previously caused a self-loop (re-entered
        // the current hub) and confused testers who pressed E near spawn.
        List<PortalSpawn> portals = new ArrayList<>();
        if ("exit".equals(roomType)) {
            float portalW   = 64f;
            float portalH   = 96f;
            float minX      = 4 * TILE;
            float maxX      = COLS * TILE - 4 * TILE - portalW;
            float prefX     = COLS * TILE * 0.6f;  // prefer right portion
            float bestPortalScore = Float.MAX_VALUE;
            float portalX   = maxX;   // fallback to far-right edge
            float portalY   = spawnY;

            for (float[] pos : groundPos) {
                float gx = pos[0];
                float gy = pos[1] - portalH;   // portal top = floor − portalH
                if (gx < minX || gx > maxX) continue;
                float distFromPref = Math.abs(gx - prefX);
                if (gx < prefX) distFromPref *= 2f;
                if (distFromPref < bestPortalScore) {
                    bestPortalScore = distFromPref;
                    portalX = gx;
                    portalY = gy;
                }
            }

            // Exit rooms always link forward to the next hub in the registry chain.
            HubRegistry.HubDef dest = HubRegistry.nextHub(masterHubId);
            String gate = dest.requiredAbility();
            portals.add(new PortalSpawn("hub", dest.id(), portalX, portalY, gate));
        }

        // Moving platforms — room-type-aware count:
        // Platform rooms: 2-4 (central to the puzzle design)
        // Combat rooms: 1-2
        // Treasure rooms: 2-3 (to make loot harder to reach)
        // Boss rooms: 1 (arena feel)
        // Other: 0-1
        List<SimMovingPlatform> moving = new ArrayList<>();
        int numMoving;
        if (isPlatformRoom)     numMoving = 2 + rng.nextInt(3);  // 2-4
        else if (isTreasureRoom) numMoving = 2 + rng.nextInt(2); // 2-3
        else if (isCombatRoom)   numMoving = 1 + rng.nextInt(2); // 1-2
        else if (isBossRoom)     numMoving = 1;
        else                     numMoving = rng.nextInt(2);      // 0-1
        int platW = 4 * TILE;   // 4-tile wide platform (128 px)
        int platH = TILE / 2;   // half-tile tall (16 px)
        for (int i = 0; i < numMoving; i++) {
            // Place at a mid-height row: between 30% and 65% of room height
            int platRow  = (int)(ROWS * 0.30f) + rng.nextInt((int)(ROWS * 0.35f));
            float originX  = (4 + rng.nextInt(COLS - 16)) * TILE;
            int   rangeTiles = 12 + rng.nextInt(10);  // 12-21 tile travel range
            float leftBound  = originX;
            float rightBound = Math.min(originX + rangeTiles * TILE, (COLS - 4) * TILE);
            float platY      = platRow * TILE;
            float speed      = (1.5f + rng.nextFloat() * 1.5f) * (rng.nextBoolean() ? 1 : -1);
            String pid = "mplat_" + (int)originX + "_" + (int)platY;
            moving.add(new SimMovingPlatform(pid, originX, platY, platW, platH,
                leftBound, rightBound, speed));
        }

        return new LevelLayout(seed, COLS, ROWS, hash, enemies, pickups, npcs, bossSpawn, portals, falling,
                moving, spawnX, spawnY, null);
    }

    // ── New-pipeline entry point ──────────────────────────────────────────────

    /**
     * Build a LevelLayout from a pre-processed {@link RoomContent}.
     *
     * Called by the new post-processing pipeline when
     * {@code ZoneSimulationLoop.NEW_PIPELINE_ENABLED} is true.  The tile grid,
     * entity spawn lists, and spawn position have already been determined by
     * {@code RoomPostProcessor}; this method only builds the SpatialHash and
     * wraps everything in the immutable LevelLayout contract.
     *
     * Existing overloads of {@code buildProceduralLayout} are untouched.
     *
     * @param seed        room seed (for LevelLayout.seed field)
     * @param content     post-processed room content
     * @param masterHubId hub id — used only for portal destination fallback
     */
    public static LevelLayout buildFromRoomContent(
            long seed, RoomContent content, String masterHubId) {
        final int TILE = 32;
        final int COLS = content.tiles[0].length;
        final int ROWS = content.tiles.length;

        // Build SpatialHash from the (possibly ability-layer-reshaped) tile grid.
        // DOOR_LOCKED (value 6, added in Phase 4) is treated as SOLID for collision.
        SpatialHash hash = new SpatialHash();
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                byte tile = content.tiles[r][c];
                if (tile == WorldGenerator.AIR) continue;
                boolean oneWay = (tile == WorldGenerator.PLATFORM);
                hash.insert(new TileRect(c * TILE, r * TILE, TILE, TILE, oneWay, tile));
            }
        }

        log.info("[LevelLayout] buildFromRoomContent seed={} spawn=({},{})",
            seed, (int) content.spawnX, (int) content.spawnY);

        return new LevelLayout(
            seed, COLS, ROWS, hash,
            content.enemies,
            content.pickups,
            content.npcs,
            content.bossSpawn,
            content.portals,
            content.fallingPlatforms,
            content.movingPlatforms,
            content.spawnX,
            content.spawnY,
            null
        );
    }

    /**
     * Build a LevelLayout from a procgen-lab {@link com.indieniinja.procgen.room.GeneratedRoom}.
     *
     * Both grids are 128×128 tiles; each procgen tile maps to one 32px live tile (1:1).
     * Procgen column-major [tileX][tileY] is iterated and TileRects are placed at
     * (tileX*32, tileY*32). Tile constants are aligned between the two modules so
     * values 0-8 pass through unchanged. Procgen-only markers (PICKUP, ENEMY_SPAWN,
     * BOSS_SPAWN, SAVE_POINT, DOOR) become spawn descriptors or AIR. SPIKES → LAVA.
     *
     * Gated by system property {@code ninja.runtime.useProcgenRooms} — callers check
     * before invoking; this method does not check the flag itself.
     */
    public static LevelLayout fromProcgenRoom(GeneratedRoom room, long seed) {
        final int TILE = 32;
        final int W    = GenConfig.ROOM_W; // 128
        final int H    = GenConfig.ROOM_H; // 128

        SpatialHash       hash    = new SpatialHash();
        List<EnemySpawn>  enemies = new ArrayList<>();
        List<PickupSpawn> pickups = new ArrayList<>();
        List<NPCSpawn>    npcs    = new ArrayList<>();
        BossSpawn         boss    = null;

        // Fallback spawn: centre of room, near bottom
        float spawnX = (W / 2f) * TILE + 14f;
        float spawnY = (H - 4f) * TILE;

        for (int tx = 0; tx < W; tx++) {
            for (int ty = 0; ty < H; ty++) {
                byte procTile = room.tiles[tx][ty];
                float px = tx * TILE;
                float py = ty * TILE;

                // Extract spawn descriptors before remapping to live tile
                switch (procTile) {
                    case Tile.PICKUP ->
                        pickups.add(new PickupSpawn("coin", px + TILE / 2f, py));
                    case Tile.ENEMY_SPAWN ->
                        enemies.add(new EnemySpawn("goblin", px + TILE / 2f, py,
                            px - 3f * TILE, px + 3f * TILE));
                    case Tile.SAVE_POINT ->
                        npcs.add(new NPCSpawn("save_statue", px + TILE / 2f, py,
                            px - TILE, px + TILE));
                    case Tile.BOSS_SPAWN -> {
                        if (boss == null)
                            boss = new BossSpawn("shadow_warden", px + TILE / 2f, py);
                    }
                    default -> { /* no spawn for this tile */ }
                }

                byte liveTile = procgenToLiveTile(procTile);
                if (liveTile != WorldGenerator.AIR) {
                    boolean oneWay = (liveTile == WorldGenerator.PLATFORM);
                    hash.insert(new TileRect(px, py, TILE, TILE, oneWay, liveTile));
                }
            }
        }

        // Derive spawn: highest walkable AIR cell above SOLID floor, scanning from centre out.
        outer:
        for (int dx = 0; dx < W / 2; dx++) {
            for (int side = -1; side <= 1; side += 2) {
                int tx = W / 2 + side * dx;
                if (tx < 1 || tx >= W - 1) continue;
                for (int ty = 1; ty < H - 2; ty++) {
                    byte t     = room.tiles[tx][ty];
                    byte below = room.tiles[tx][ty + 1];
                    if ((t == Tile.AIR || t == Tile.DOOR)
                        && (below == Tile.SOLID || below == Tile.PLATFORM)) {
                        spawnX = tx * TILE + 14f;
                        spawnY = ty * TILE;
                        break outer;
                    }
                }
            }
        }

        log.info("[LevelLayout] fromProcgenRoom seed={} enemies={} pickups={} boss={}",
            seed, enemies.size(), pickups.size(),
            boss != null ? boss.bossTypeWire() : "none");

        return new LevelLayout(seed, W, H, hash, enemies, pickups, npcs, boss,
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), spawnX, spawnY, null);
    }

    /** Maps a procgen-lab tile byte to the corresponding live WorldGenerator tile byte.
     *  Constants 0-8 are aligned between modules and pass through unchanged. */
    private static byte procgenToLiveTile(byte procTile) {
        if (procTile <= 8) return procTile; // AIR, SOLID, PLATFORM, ICE, WATER, LAVA, LOCKED_DOOR, GAS, CLIMBABLE
        return switch (procTile) {
            case Tile.SPIKES -> WorldGenerator.LAVA;
            // PICKUP, ENEMY_SPAWN, SAVE_POINT, BOSS_SPAWN, DOOR → AIR (handled as spawns above)
            default -> WorldGenerator.AIR;
        };
    }

    /**
     * Generate a row-major tile grid using procgen-lab's RoomGenerator.
     * Used when {@code ninja.runtime.useProcgenRooms=true} to replace WorldGenerator.
     * Output is byte[ROWS][COLS] (row-major) so it is drop-in compatible with the
     * rest of buildProceduralLayout's grid iteration.
     */
    private static byte[][] buildProcgenGrid(
            long seed, int cols, int rows,
            java.util.Collection<String> neighborDirs, String roomType) {
        // Map wire strings to procgen enums
        com.indieniinja.procgen.model.RoomType pType = switch (roomType) {
            case "start"    -> com.indieniinja.procgen.model.RoomType.START;
            case "boss"     -> com.indieniinja.procgen.model.RoomType.BOSS;
            case "treasure" -> com.indieniinja.procgen.model.RoomType.TREASURE;
            case "shop"     -> com.indieniinja.procgen.model.RoomType.SHOP;
            case "exit"     -> com.indieniinja.procgen.model.RoomType.EXIT;
            case "platform" -> com.indieniinja.procgen.model.RoomType.TRAVERSAL;
            case "save"     -> com.indieniinja.procgen.model.RoomType.SAVE;
            default         -> com.indieniinja.procgen.model.RoomType.COMBAT;
        };
        java.util.Set<com.indieniinja.procgen.model.Direction> dirs =
            new java.util.HashSet<>();
        for (String d : neighborDirs) {
            switch (d) {
                case "left"  -> dirs.add(com.indieniinja.procgen.model.Direction.LEFT);
                case "right" -> dirs.add(com.indieniinja.procgen.model.Direction.RIGHT);
                case "up"    -> dirs.add(com.indieniinja.procgen.model.Direction.UP);
                case "down"  -> dirs.add(com.indieniinja.procgen.model.Direction.DOWN);
            }
        }
        com.indieniinja.procgen.intent.RoomIntent intent =
            new com.indieniinja.procgen.intent.RoomIntent(
                pType,
                com.indieniinja.procgen.model.Biome.DUNGEON,
                1,
                java.util.Set.of(),
                dirs,
                "neutral",
                "reach_exit",
                true);

        GeneratedRoom room = new com.indieniinja.procgen.room.RoomGenerator()
            .generate(intent, seed);

        // Transpose column-major [x][y] → row-major [row][col] for grid compatibility
        byte[][] grid = new byte[rows][cols];
        for (int x = 0; x < cols; x++)
            for (int y = 0; y < rows; y++)
                grid[y][x] = procgenToLiveTile(room.tiles[x][y]);
        return grid;
    }

    /**
     * Build a unified world-space layout covering ALL rooms in the WorldGraph.
     *
     * Each room's tiles and entity spawns are offset by their grid position so
     * the entire hub is simulated as one flat world — no zone transitions, no
     * boundary clamping.  The start room's spawn position becomes the overall
     * spawn in world-space.
     *
     * Client entities render at world-space coordinates directly (no roomWorldOff
     * transform needed).
     */
    public static LevelLayout buildUnifiedWorldLayout(WorldGraph graph, String masterHubId) {
        final int TILE    = 32;
        final int COLS    = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
        final int ROWS    = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128
        final int ROOM_PX = COLS * TILE;                         // 4096

        // ── Compute grid bounds ───────────────────────────────────────────────
        int minGX = Integer.MAX_VALUE, minGY = Integer.MAX_VALUE;
        int maxGX = Integer.MIN_VALUE, maxGY = Integer.MIN_VALUE;
        for (WorldGraph.RoomNode room : graph.allRooms()) {
            if (room.gridX < minGX) minGX = room.gridX;
            if (room.gridY < minGY) minGY = room.gridY;
            if (room.gridX > maxGX) maxGX = room.gridX;
            if (room.gridY > maxGY) maxGY = room.gridY;
        }
        int totalCols = (maxGX - minGX + 1) * COLS;
        int totalRows = (maxGY - minGY + 1) * ROWS;

        SpatialHash combinedHash = new SpatialHash();
        List<EnemySpawn>          allEnemies  = new ArrayList<>();
        List<PickupSpawn>         allPickups  = new ArrayList<>();
        List<NPCSpawn>            allNpcs     = new ArrayList<>();
        List<PortalSpawn>         allPortals  = new ArrayList<>();
        List<FallingPlatform>     allFalling  = new ArrayList<>();
        List<SimMovingPlatform>   allMoving   = new ArrayList<>();
        BossSpawn                 firstBoss   = null;
        float spawnX = 0f, spawnY = 0f;
        WorldGraph.RoomNode startRoom = graph.startRoom();

        sealMissingRoomCells(combinedHash, graph, minGX, minGY, maxGX, maxGY, COLS, ROWS, TILE);

        boolean bossExitFlag = graph.bossExit();
        WorldGraph.RoomNode exitRoom = graph.exitRoom();

        for (WorldGraph.RoomNode room : graph.allRooms()) {
            int offX = (room.gridX - minGX) * ROOM_PX;
            int offY = (room.gridY - minGY) * ROOM_PX;

            // Boss-exit override: exit room uses boss.tmx geometry + boss entity spawns
            String effectiveWire = room.type.wire();
            if (bossExitFlag && room.gridX == exitRoom.gridX && room.gridY == exitRoom.gridY) {
                effectiveWire = WorldGraph.RoomType.BOSS.wire();
            }

            // ── Insert tile grid ──────────────────────────────────────────────
            byte[][] grid = WorldGenerator.generate(
                room.seed, COLS, ROWS, room.neighborDirs(), effectiveWire);
            for (int r = 0; r < ROWS; r++) {
                for (int c = 0; c < COLS; c++) {
                    byte tile = grid[r][c];
                    if (tile == WorldGenerator.AIR) continue;
                    boolean oneWay = (tile == WorldGenerator.PLATFORM);
                    combinedHash.insert(new TileRect(
                        offX + c * TILE, offY + r * TILE, TILE, TILE, oneWay, tile));
                }
            }

            // ── Build per-room layout to get entity spawns (room-local) ──────
            LevelLayout roomLayout = buildProceduralLayout(
                room.seed, room.neighborDirs(), effectiveWire, masterHubId);

            // Offset all spawns into world-space
            for (EnemySpawn e : roomLayout.enemySpawns)
                allEnemies.add(new EnemySpawn(e.type(),
                    offX + e.x(), offY + e.y(),
                    offX + e.patrolMinX(), offX + e.patrolMaxX()));

            for (PickupSpawn p : roomLayout.pickupSpawns)
                allPickups.add(new PickupSpawn(p.type(), offX + p.x(), offY + p.y()));

            for (NPCSpawn n : roomLayout.npcSpawns)
                allNpcs.add(new NPCSpawn(n.type(),
                    offX + n.x(), offY + n.y(),
                    offX + n.patrolMinX(), offX + n.patrolMaxX()));

            for (PortalSpawn p : roomLayout.portalSpawns)
                allPortals.add(new PortalSpawn(
                    p.portalType(), p.destinationId(),
                    offX + p.x(), offY + p.y(),
                    p.requiredAbility()));

            for (FallingPlatform f : roomLayout.fallingPlatforms)
                allFalling.add(new FallingPlatform(
                    f.platformId, offX + f.originX, offY + f.originY, f.width, f.height));

            for (SimMovingPlatform m : roomLayout.movingPlatforms)
                allMoving.add(new SimMovingPlatform(
                    m.id, offX + m.x, offY + m.y, m.width, m.height,
                    offX + m.leftBound, offX + m.rightBound, m.vx));

            if (firstBoss == null && roomLayout.bossSpawn != null)
                firstBoss = new BossSpawn(
                    roomLayout.bossSpawn.bossTypeWire(),
                    offX + roomLayout.bossSpawn.x(),
                    offY + roomLayout.bossSpawn.y());

            // Spawn at start room
            if (room.gridX == startRoom.gridX && room.gridY == startRoom.gridY) {
                spawnX = offX + roomLayout.spawnX;
                spawnY = offY + roomLayout.spawnY;
            }
        }

        log.info("[LevelLayout] unified world: {}×{} tiles ({} rooms), spawn=({},{})",
            totalCols, totalRows, graph.size(), (int)spawnX, (int)spawnY);

        return new LevelLayout(startRoom.seed, totalCols, totalRows, combinedHash,
            allEnemies, allPickups, allNpcs, firstBoss,
            allPortals, allFalling, allMoving, spawnX, spawnY, null);
    }

    /**
     * Build a unified world-space layout using the extended post-processing pipeline.
     *
     * Replaces the inner {@code buildProceduralLayout} call in
     * {@link #buildUnifiedWorldLayout} with {@link RoomPostProcessor#process}, so
     * that AbilityLayer, PuzzleLayer, and EntityPlanner run on every room.
     *
     * Tile geometry inserted into the SpatialHash comes from the post-processed
     * grid (i.e. ability gates are already physically shaped into the tiles).
     *
     * @param graph       world graph for this hub
     * @param plan        pre-built PuzzlePlan (call PuzzlePlanner.plan() once per hub)
     * @param masterHubId hub id for portal destination lookup
     */
    public static LevelLayout buildUnifiedWorldLayoutFromPlan(
            WorldGraph graph, PuzzlePlan plan, String masterHubId) {
        final int TILE    = 32;
        final int COLS    = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
        final int ROWS    = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128
        final int ROOM_PX = COLS * TILE;                         // 4096

        // ── Compute grid bounds ───────────────────────────────────────────────
        int minGX = Integer.MAX_VALUE, minGY = Integer.MAX_VALUE;
        int maxGX = Integer.MIN_VALUE, maxGY = Integer.MIN_VALUE;
        for (WorldGraph.RoomNode room : graph.allRooms()) {
            if (room.gridX < minGX) minGX = room.gridX;
            if (room.gridY < minGY) minGY = room.gridY;
            if (room.gridX > maxGX) maxGX = room.gridX;
            if (room.gridY > maxGY) maxGY = room.gridY;
        }
        int totalCols = (maxGX - minGX + 1) * COLS;
        int totalRows = (maxGY - minGY + 1) * ROWS;

        SpatialHash             combinedHash = new SpatialHash();
        Map<String, List<TileRect>> allDoorTiles = new HashMap<>();
        List<EnemySpawn>        allEnemies   = new ArrayList<>();
        List<PickupSpawn>       allPickups   = new ArrayList<>();
        List<NPCSpawn>          allNpcs      = new ArrayList<>();
        List<PortalSpawn>       allPortals   = new ArrayList<>();
        List<FallingPlatform>   allFalling   = new ArrayList<>();
        List<SimMovingPlatform> allMoving    = new ArrayList<>();
        BossSpawn               firstBoss    = null;
        float spawnX = 0f, spawnY = 0f;
        WorldGraph.RoomNode startRoom = graph.startRoom();

        sealMissingRoomCells(combinedHash, graph, minGX, minGY, maxGX, maxGY, COLS, ROWS, TILE);

        for (WorldGraph.RoomNode room : graph.allRooms()) {
            int offX = (room.gridX - minGX) * ROOM_PX;
            int offY = (room.gridY - minGY) * ROOM_PX;

            // ── Generate raw tile geometry ────────────────────────────────────
            byte[][] rawGrid = WorldGenerator.generate(
                room.seed, COLS, ROWS, room.neighborDirs(), room.type.wire());

            // ── Run post-processing pipeline (ability gates, puzzles, entities) ─
            RoomContent content = RoomPostProcessor.process(
                rawGrid, room, plan, room.seed, masterHubId);

            // ── Build room-local door tile key set (row<<32|col → puzzleId) ──
            // Used below to tag DOOR_LOCKED TileRects with their puzzleId so
            // GameSimulator can remove them when the door is unlocked at runtime.
            Map<Long, String> doorTileKeys = new HashMap<>();
            for (RoomContent.PuzzleSpawn z : content.puzzles) {
                if ("door".equals(z.puzzleType())) {
                    int doorRow = (int)(z.y() / TILE);
                    int doorCol = (int)(z.x() / TILE);
                    for (int dc = doorCol - 1; dc <= doorCol + 1; dc++) {
                        doorTileKeys.put(((long) doorRow << 32) | (dc & 0xFFFFFFFFL), z.puzzleId());
                    }
                }
            }

            // ── Insert post-processed tiles into world-space SpatialHash ──────
            for (int r = 0; r < ROWS; r++) {
                for (int c = 0; c < COLS; c++) {
                    byte tile = content.tiles[r][c];
                    if (tile == WorldGenerator.AIR) continue;
                    boolean oneWay = (tile == WorldGenerator.PLATFORM);
                    TileRect tr = new TileRect(
                        offX + c * TILE, offY + r * TILE, TILE, TILE, oneWay, tile);
                    combinedHash.insert(tr);
                    String pid = doorTileKeys.get(((long) r << 32) | (c & 0xFFFFFFFFL));
                    if (pid != null)
                        allDoorTiles.computeIfAbsent(pid, k -> new ArrayList<>()).add(tr);
                }
            }

            // ── Offset entity spawns into world-space ─────────────────────────
            for (EnemySpawn e : content.enemies)
                allEnemies.add(new EnemySpawn(e.type(),
                    offX + e.x(), offY + e.y(),
                    offX + e.patrolMinX(), offX + e.patrolMaxX()));

            for (PickupSpawn p : content.pickups)
                allPickups.add(new PickupSpawn(p.type(), offX + p.x(), offY + p.y()));

            // Puzzle spawns: keys → pickups, levers/buttons → interactable NPCs
            for (RoomContent.PuzzleSpawn z : content.puzzles) {
                switch (z.puzzleType()) {
                    case "key" ->
                        allPickups.add(new PickupSpawn(z.puzzleId(), offX + z.x(), offY + z.y()));
                    case "lever", "button", "echo_trigger", "aal_echo", "st_trigger" -> {
                        float px = offX + z.x();
                        // NPC type = puzzleId (carries the "lever_" / "btn_" / "aal_echo_" / "st_trigger_" prefix)
                        allNpcs.add(new NPCSpawn(z.puzzleId(),
                            px, offY + z.y(), px - 16f, px + 16f));
                    }
                    // "door" tiles are already solid via DOOR_LOCKED in SpatialHash
                }
            }

            for (NPCSpawn n : content.npcs)
                allNpcs.add(new NPCSpawn(n.type(),
                    offX + n.x(), offY + n.y(),
                    offX + n.patrolMinX(), offX + n.patrolMaxX()));

            for (PortalSpawn p : content.portals)
                allPortals.add(new PortalSpawn(
                    p.portalType(), p.destinationId(),
                    offX + p.x(), offY + p.y(),
                    p.requiredAbility()));

            for (FallingPlatform f : content.fallingPlatforms)
                allFalling.add(new FallingPlatform(
                    f.platformId, offX + f.originX, offY + f.originY, f.width, f.height));

            for (SimMovingPlatform m : content.movingPlatforms)
                allMoving.add(new SimMovingPlatform(
                    m.id, offX + m.x, offY + m.y, m.width, m.height,
                    offX + m.leftBound, offX + m.rightBound, m.vx));

            if (firstBoss == null && content.bossSpawn != null)
                firstBoss = new BossSpawn(
                    content.bossSpawn.bossTypeWire(),
                    offX + content.bossSpawn.x(),
                    offY + content.bossSpawn.y());

            // Spawn point from start room
            if (room.gridX == startRoom.gridX && room.gridY == startRoom.gridY) {
                spawnX = offX + content.spawnX;
                spawnY = offY + content.spawnY;
            }
        }

        log.info("[LevelLayout] unified world (post-proc): {}×{} tiles ({} rooms), spawn=({},{})",
            totalCols, totalRows, graph.size(), (int)spawnX, (int)spawnY);

        return new LevelLayout(startRoom.seed, totalCols, totalRows, combinedHash,
            allEnemies, allPickups, allNpcs, firstBoss,
            allPortals, allFalling, allMoving, spawnX, spawnY, allDoorTiles);
    }

    private static void sealMissingRoomCells(
            SpatialHash hash,
            WorldGraph graph,
            int minGX,
            int minGY,
            int maxGX,
            int maxGY,
            int roomCols,
            int roomRows,
            int tileSize) {
        int roomPxW = roomCols * tileSize;
        int roomPxH = roomRows * tileSize;
        for (int gy = minGY; gy <= maxGY; gy++) {
            for (int gx = minGX; gx <= maxGX; gx++) {
                if (graph.roomAt(gx, gy) != null) {
                    continue;
                }
                int offX = (gx - minGX) * roomPxW;
                int offY = (gy - minGY) * roomPxH;
                hash.insert(new TileRect(offX, offY, roomPxW, roomPxH, false, WorldGenerator.SOLID));
            }
        }
    }
}
