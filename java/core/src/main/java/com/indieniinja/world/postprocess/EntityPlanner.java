package com.indieniinja.world.postprocess;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.BossType;
import com.indieniinja.sim.FallingPlatform;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimMovingPlatform;
import com.indieniinja.world.HubRegistry;
import com.indieniinja.world.SeedHierarchy;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.puzzle.PuzzlePlan;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Structured entity placement for the extended world-gen pipeline.
 *
 * Each placement method is a pure function: same (grid, room, plan, seed) inputs
 * always produce the same output.  Methods never share a {@link Random} instance —
 * each derives its own sub-seed from {@link SeedHierarchy} so that changing one
 * system does not shift results in another.
 *
 * This replaces the inline spawn logic previously embedded in
 * {@link com.indieniinja.sim.LevelLayout#buildProceduralLayout}.
 */
public final class EntityPlanner {

    private static final int TILE = PhysicsConstants.TILE_SIZE;   // 32
    private static final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;  // 128
    private static final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES; // 128

    private EntityPlanner() {}

    // ── Enemies ───────────────────────────────────────────────────────────────

    /**
     * Place enemies on valid ground positions, respecting exclusion zones and
     * scaling count/type with BFS depth from {@code plan}.
     */
    public static List<LevelLayout.EnemySpawn> placeEnemies(
            byte[][] grid,
            WorldGraph.RoomNode room,
            PuzzlePlan plan,
            long roomSeed,
            float spawnX, float spawnY) {

        long seed = SeedHierarchy.deriveFeature(roomSeed, "enemy");
        Random rng = new Random(seed);

        List<float[]> ground = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);

        PlacementFilter filter = new PlacementFilter()
            .excludeAroundDoors(grid, room.neighborDirs(), 3)
            .excludeAroundSpawn(spawnX, spawnY, 5);
        if (room.type == WorldGraph.RoomType.BOSS) filter.excludeBossArena(grid);

        List<float[]> valid = filter.filter(ground);
        Collections.shuffle(valid, rng);

        int depth = Math.max(0, plan.depthOf(room.gridX, room.gridY));
        int count = enemyCount(room.type, depth, rng);
        String[] pool = enemyPool(room.type, depth);
        float patrolMult = patrolMultiplier(room.type);

        List<LevelLayout.EnemySpawn> spawns = new ArrayList<>(count);
        for (int i = 0; i < count && i < valid.size(); i++) {
            float[] pos = valid.get(i);
            String type = pool[i % pool.length];
            float patrol = (3 + rng.nextInt(3)) * TILE * patrolMult;
            spawns.add(new LevelLayout.EnemySpawn(
                type, pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
        }
        return spawns;
    }

    private static int enemyCount(WorldGraph.RoomType type, int depth, Random rng) {
        return switch (type) {
            case BOSS      -> 2 + rng.nextInt(3);                             // 2-4 minions
            case COMBAT    -> 5 + rng.nextInt(4) + Math.min(depth / 2, 3);   // 5-8, depth-scaled
            case PLATFORM  -> 1 + rng.nextInt(3);                             // 1-3
            case TREASURE  -> rng.nextInt(2);                                 // 0-1 guard
            case SHOP, START, EXIT -> 0;
            default        -> 3 + rng.nextInt(3);                             // 3-5
        };
    }

    private static String[] enemyPool(WorldGraph.RoomType type, int depth) {
        // heavy rooms: skeleton shield + archer kiter
        String[] heavy = {"skeleton", "archer", "skeleton"};
        String[] light = {"goblin", "slime", "goblin"};

        if (type == WorldGraph.RoomType.BOSS || type == WorldGraph.RoomType.PLATFORM
                || type == WorldGraph.RoomType.TREASURE) return heavy;
        if (depth >= 6) return new String[]{"skeleton", "archer", "spearman"};
        if (depth >= 3) return new String[]{"goblin", "skeleton", "spearman"};
        return light;
    }

    private static float patrolMultiplier(WorldGraph.RoomType type) {
        return switch (type) {
            case COMBAT   -> 1.5f;
            case PLATFORM -> 0.5f;
            default       -> 1.0f;
        };
    }

    // ── Pickups ───────────────────────────────────────────────────────────────

    /**
     * Place pickups after enemies so reward drops cluster near combat zones.
     * Enemies' positions are used only to avoid direct overlap — they are not
     * required for this method to function.
     */
    public static List<LevelLayout.PickupSpawn> placePickups(
            byte[][] grid,
            WorldGraph.RoomNode room,
            List<LevelLayout.EnemySpawn> placedEnemies,
            long roomSeed,
            float spawnX, float spawnY) {

        long seed = SeedHierarchy.deriveFeature(roomSeed, "pickup");
        Random rng = new Random(seed);

        List<float[]> ground = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);

        PlacementFilter filter = new PlacementFilter()
            .excludeAroundDoors(grid, room.neighborDirs(), 2)
            .excludeAroundSpawn(spawnX, spawnY, 3);
        if (room.type == WorldGraph.RoomType.BOSS) filter.excludeBossArena(grid);

        List<float[]> valid = filter.filter(ground);
        Collections.shuffle(valid, rng);

        int count = pickupCount(room.type, rng);
        String[] types = pickupTypes(room.type);

        List<LevelLayout.PickupSpawn> spawns = new ArrayList<>(count + 1);

        // Offset past enemy positions so pickups don't sit on top of enemies
        int offset = placedEnemies.size();
        for (int i = 0; i < count && (offset + i) < valid.size(); i++) {
            float[] pos = valid.get(offset + i);
            spawns.add(new LevelLayout.PickupSpawn(types[i % types.length], pos[0], pos[1]));
        }

        // Guaranteed health_potion near spawn for combat/boss rooms
        if ((room.type == WorldGraph.RoomType.COMBAT || room.type == WorldGraph.RoomType.BOSS)
                && !valid.isEmpty()) {
            float[] safePos = valid.get(Math.min(offset + count, valid.size() - 1));
            spawns.add(new LevelLayout.PickupSpawn("health_potion", safePos[0], safePos[1]));
        }

        // Guaranteed fragment in BOSS and TREASURE rooms (M4 — GDD §3.3/§3.4)
        if ((room.type == WorldGraph.RoomType.BOSS || room.type == WorldGraph.RoomType.TREASURE)
                && valid.size() > offset + count + 1) {
            float[] fragPos = valid.get(offset + count + 1);
            spawns.add(new LevelLayout.PickupSpawn(
                pickFragment(room.gridX, room.gridY, roomSeed), fragPos[0], fragPos[1]));
        }

        return spawns;
    }

    /**
     * Select which fragment type to place in this room.
     * Cycles through yin → yang → lantern based on the room's grid position + seed
     * so that a generated world always has a balanced set across its rooms.
     */
    private static String pickFragment(int gridX, int gridY, long roomSeed) {
        int idx = (int)((Math.abs(roomSeed) + gridX * 31L + gridY * 17L) % 3);
        return switch (idx) {
            case 0  -> "yin_fragment";
            case 1  -> "yang_fragment";
            default -> "lantern_fragment";
        };
    }

    private static int pickupCount(WorldGraph.RoomType type, Random rng) {
        return switch (type) {
            case BOSS      -> 4 + rng.nextInt(3);   // 4-6 post-boss drops
            case TREASURE  -> 2 + rng.nextInt(3);   // 2-4 high-value
            case COMBAT    -> 2 + rng.nextInt(3);   // 2-4
            case PLATFORM  -> 1 + rng.nextInt(3);   // 1-3
            case SHOP, START -> 1 + rng.nextInt(2); // 1-2 starters
            default        -> 2 + rng.nextInt(3);
        };
    }

    private static String[] pickupTypes(WorldGraph.RoomType type) {
        return switch (type) {
            // Boss: rich loot including all three fragment types
            case BOSS     -> new String[]{
                "gem", "rare_potion", "coin", "gem", "coin", "health_potion",
                "yin_fragment", "yang_fragment", "lantern_fragment"};
            // Treasure: high-value including fragments
            case TREASURE -> new String[]{
                "gem", "rare_potion", "gem", "coin",
                "yin_fragment", "yang_fragment", "lantern_fragment"};
            // Combat: standard drops + rare fragment chance (1-in-6 slot)
            case COMBAT   -> new String[]{
                "coin", "health_potion", "coin", "coin",
                "yin_fragment", "yang_fragment"};
            // Platform: lighter loot, occasional fragment
            case PLATFORM -> new String[]{
                "coin", "health_potion", "coin", "lantern_fragment"};
            default -> new String[]{"health_potion", "coin", "yin_fragment"};
        };
    }

    // ── NPCs ──────────────────────────────────────────────────────────────────

    public static List<LevelLayout.NPCSpawn> placeNpcs(
            byte[][] grid,
            WorldGraph.RoomNode room,
            List<LevelLayout.EnemySpawn> placedEnemies,
            List<LevelLayout.PickupSpawn> placedPickups,
            long roomSeed) {

        long seed = SeedHierarchy.deriveFeature(roomSeed, "npc");
        Random rng = new Random(seed);

        List<float[]> ground = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);
        Collections.shuffle(ground, rng);

        String requiredQuestGiverType = switch (room.type) {
            case START -> "siren";
            case SHOP  -> "mission_giver";
            default    -> "";
        };
        boolean requireMissionGiver = !requiredQuestGiverType.isBlank();
        String[] baseTypes = {"lore", "shop", "mission_giver"};
        int numNpcs = requireMissionGiver ? 2 + rng.nextInt(2) : 1 + rng.nextInt(2);  // 2-3 or 1-2
        int offset  = placedEnemies.size() + placedPickups.size();
        float patrol = 2 * TILE;

        List<LevelLayout.NPCSpawn> spawns = new ArrayList<>(numNpcs + 1);
        boolean missionGiverPlaced = false;
        int i = 0;
        if (requireMissionGiver && offset < ground.size()) {
            float[] pos = ground.get(offset);
            spawns.add(new LevelLayout.NPCSpawn(
                requiredQuestGiverType, pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
            missionGiverPlaced = true;
            i = 1;
        }

        for (; i < numNpcs && (offset + i) < ground.size(); i++) {
            float[] pos = ground.get(offset + i);
            String type = baseTypes[(i - (missionGiverPlaced ? 1 : 0)) % baseTypes.length];
            if ("mission_giver".equals(type)) missionGiverPlaced = true;
            spawns.add(new LevelLayout.NPCSpawn(
                type, pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
        }

        if (requireMissionGiver && !missionGiverPlaced && !spawns.isEmpty()) {
            LevelLayout.NPCSpawn s = spawns.get(0);
            spawns.set(0, new LevelLayout.NPCSpawn(
                requiredQuestGiverType, s.x(), s.y(), s.patrolMinX(), s.patrolMaxX()));
        }

        // Crafter: always in shop/start rooms; 25% chance elsewhere
        boolean addCrafter = room.type == WorldGraph.RoomType.SHOP
            || room.type == WorldGraph.RoomType.START
            || rng.nextInt(4) == 0;
        int crafterIdx = offset + numNpcs;
        if (addCrafter && crafterIdx < ground.size()) {
            float[] pos = ground.get(crafterIdx);
            spawns.add(new LevelLayout.NPCSpawn(
                "crafter", pos[0], pos[1], pos[0] - patrol, pos[0] + patrol));
        }

        return spawns;
    }

    // ── Boss ──────────────────────────────────────────────────────────────────

    /**
     * Place the boss at the centre-bottom of the room and clear an arena around it.
     * Returns null if room is not a BOSS room.
     */
    public static LevelLayout.BossSpawn placeBoss(
            byte[][] grid,
            WorldGraph.RoomNode room,
            long roomSeed) {

        if (room.type != WorldGraph.RoomType.BOSS) return null;

        long seed = SeedHierarchy.deriveFeature(roomSeed, "boss");

        float centreX = COLS * TILE * 0.5f;
        float arenaY  = ROWS * TILE * 0.70f;   // bottom-third of room

        // Clear blob clutter in a 4-tile radius around arena centre
        clearArena(grid, centreX, arenaY, 4);
        // Guarantee flat floor directly under boss
        ensureFloor(grid, centreX, arenaY, 4);

        BossType bossType = BossType.fromSeed(seed);
        return new LevelLayout.BossSpawn(bossType.wire, centreX, arenaY);
    }

    /** Remove non-boundary tiles within radiusTiles of (cx, cy). */
    static void clearArena(byte[][] grid, float cx, float cy, int radiusTiles) {
        int tileX = (int)(cx / TILE);
        int tileY = (int)(cy / TILE);
        int r = radiusTiles;
        for (int row = tileY - r; row <= tileY + r; row++) {
            for (int col = tileX - r; col <= tileX + r; col++) {
                if (row < 2 || row >= ROWS - 4) continue;  // protect ceiling + floor
                if (col < 2 || col >= COLS - 2) continue;  // protect walls
                grid[row][col] = WorldGenerator.AIR;
            }
        }
    }

    /** Ensure a solid floor row of widthTiles centred on (cx, cy). */
    static void ensureFloor(byte[][] grid, float cx, float cy, int widthTiles) {
        int tileX  = (int)(cx / TILE);
        int floorR = (int)(cy / TILE);  // row directly at arena y
        for (int col = tileX - widthTiles; col <= tileX + widthTiles; col++) {
            if (col < 2 || col >= COLS - 2) continue;
            grid[floorR][col] = WorldGenerator.SOLID;
        }
    }

    // ── Portals ───────────────────────────────────────────────────────────────

    public static List<LevelLayout.PortalSpawn> placePortals(
            byte[][] grid,
            WorldGraph.RoomNode room,
            long roomSeed,
            String masterHubId) {

        List<LevelLayout.PortalSpawn> portals = new ArrayList<>();
        if (room.type != WorldGraph.RoomType.EXIT && room.type != WorldGraph.RoomType.START) {
            return portals;
        }

        long seed = SeedHierarchy.deriveFeature(roomSeed, "portal");
        Random rng = new Random(seed);

        List<float[]> ground = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);
        Collections.shuffle(ground, rng);

        float portalH  = 96f;
        float minX     = 4 * TILE;
        float maxX     = COLS * TILE - 4 * TILE - 64f;
        float prefX    = COLS * TILE * 0.6f;
        float bestScore = Float.MAX_VALUE;
        float portalX  = maxX;
        float portalY  = (ROWS - 6) * TILE;

        for (float[] pos : ground) {
            float gx = pos[0];
            if (gx < minX || gx > maxX) continue;
            float distFromPref = Math.abs(gx - prefX);
            if (gx < prefX) distFromPref *= 2f;
            if (distFromPref < bestScore) {
                bestScore = distFromPref;
                portalX   = gx;
                portalY   = pos[1] - portalH;
            }
        }

        HubRegistry.HubDef dest = room.type == WorldGraph.RoomType.EXIT
            ? HubRegistry.nextHub(masterHubId)
            : HubRegistry.get(masterHubId);
        portals.add(new LevelLayout.PortalSpawn(
            "hub", dest.id(), portalX, portalY, dest.requiredAbility()));
        return portals;
    }

    // ── Moving platforms ──────────────────────────────────────────────────────

    public static List<SimMovingPlatform> placeMovingPlatforms(
            WorldGraph.RoomNode room,
            long roomSeed) {

        long seed = SeedHierarchy.deriveFeature(roomSeed, "moving_plat");
        Random rng = new Random(seed);

        int numMoving = switch (room.type) {
            case PLATFORM -> 2 + rng.nextInt(3);   // 2-4
            case TREASURE -> 2 + rng.nextInt(2);   // 2-3
            case COMBAT   -> 1 + rng.nextInt(2);   // 1-2
            case BOSS     -> 1;
            default       -> rng.nextInt(2);        // 0-1
        };

        int   platW = 4 * TILE;
        int   platH = TILE / 2;
        List<SimMovingPlatform> moving = new ArrayList<>(numMoving);
        for (int i = 0; i < numMoving; i++) {
            int   platRow   = (int)(ROWS * 0.30f) + rng.nextInt((int)(ROWS * 0.35f));
            float originX   = (4 + rng.nextInt(COLS - 16)) * TILE;
            int   rangeTiles = 12 + rng.nextInt(10);
            float leftBound  = originX;
            float rightBound = Math.min(originX + rangeTiles * TILE, (COLS - 4) * TILE);
            float platY      = platRow * TILE;
            float speed      = (1.5f + rng.nextFloat() * 1.5f) * (rng.nextBoolean() ? 1 : -1);
            String pid = "mplat_" + (int) originX + "_" + (int) platY;
            moving.add(new SimMovingPlatform(
                pid, originX, platY, platW, platH, leftBound, rightBound, speed));
        }
        return moving;
    }

    // ── Falling platforms ─────────────────────────────────────────────────────

    public static List<FallingPlatform> placeFallingPlatforms(
            WorldGraph.RoomNode room,
            long roomSeed) {

        long seed = SeedHierarchy.deriveFeature(roomSeed, "falling_plat");
        Random rng = new Random(seed);

        List<FallingPlatform> falling = new ArrayList<>(2);
        int mid = ROWS / 2;
        for (int i = 0; i < 2; i++) {
            float fx = (20 + rng.nextInt(COLS - 40)) * TILE;
            float fy = (mid - 10 + rng.nextInt(16)) * TILE;
            falling.add(new FallingPlatform(
                "plat_" + (int) fx + "_" + (int) fy, fx, fy, 3 * TILE, TILE));
        }
        return falling;
    }

    // ── Spawn point ───────────────────────────────────────────────────────────

    /**
     * Compute the recommended player spawn point: ground position nearest to
     * the room's centre-bottom within a ±3-zone-width band.
     */
    public static float[] computeSpawn(byte[][] grid) {
        float centreX  = COLS * TILE * 0.5f;
        float spawnX   = centreX;
        float spawnY   = (ROWS - 2) * TILE - 56f;  // fallback: base floor
        float bestScore = Float.MAX_VALUE;

        List<float[]> ground = WorldGenerator.collectGroundPositions(grid, COLS, ROWS, TILE);
        for (float[] pos : ground) {
            float dx = Math.abs(pos[0] - centreX);
            if (dx > 3 * 8 * TILE) continue;
            float dy    = (ROWS * TILE) - pos[1];
            float score = dy * 0.3f + dx;
            if (score < bestScore) {
                bestScore = score;
                spawnX    = pos[0];
                spawnY    = pos[1] - 56f;
            }
        }
        return new float[]{spawnX, spawnY};
    }
}
