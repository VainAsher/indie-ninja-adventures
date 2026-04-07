package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.BossType;
import com.indieniinja.physics.SpatialHash;
import com.indieniinja.physics.TileRect;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
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
    // World height in pixels (used for enemy AI fall detection)
    public final float worldHeightPx;
    /** Recommended player spawn position derived from the generated layout. */
    public final float spawnX;
    public final float spawnY;

    private LevelLayout(
            long seed, int widthTiles, int heightTiles,
            SpatialHash spatialHash,
            List<EnemySpawn> enemySpawns,
            List<PickupSpawn> pickupSpawns,
            List<NPCSpawn> npcSpawns,
            BossSpawn bossSpawn,
            List<PortalSpawn> portalSpawns,
            List<FallingPlatform> fallingPlatforms,
            float spawnX, float spawnY) {
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
        this.worldHeightPx    = heightTiles * 32f;
        this.spawnX           = spawnX;
        this.spawnY           = spawnY;
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
                new ArrayList<>(), falling, testSpawnX, testSpawnY);
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
        return buildProceduralLayout(seed, java.util.Collections.emptySet(), "combat");
    }

    /** Build layout with door openings but default room type. */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs) {
        return buildProceduralLayout(seed, neighborDirs, "combat");
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
        // Build the current room layout first
        LevelLayout base = buildProceduralLayout(seed, neighborDirs, roomType);

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
            base.portalSpawns, base.fallingPlatforms, base.spawnX, base.spawnY);
    }

    /**
     * Build a procedurally generated layout using the zone-planning pipeline.
     *
     * @param seed         room seed
     * @param neighborDirs directions where adjacent rooms exist ("up","down","left","right")
     * @param roomType     wire string: "start","exit","shop","combat","platform","treasure","boss"
     */
    public static LevelLayout buildProceduralLayout(
            long seed, java.util.Collection<String> neighborDirs, String roomType) {
        final int TILE = 32;
        final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
        final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128

        byte[][] grid = WorldGenerator.generate(seed, COLS, ROWS, neighborDirs, roomType);

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

        // Shuffle deterministically so enemy/pickup placement varies per seed
        java.util.Random rng = new java.util.Random(seed ^ 0xBEEF_CAFEL);
        Collections.shuffle(groundPos, rng);

        // Boss room: spawn one boss at centre-bottom; no regular enemies
        boolean isBossRoom = "boss".equals(roomType);
        BossSpawn bossSpawn = null;
        if (isBossRoom) {
            BossType bt = BossType.fromSeed(seed);
            bossSpawn = new BossSpawn(bt.wire, spawnX, spawnY);
        }

        // Enemies — 3-5 at first available ground positions (skip for boss rooms)
        List<EnemySpawn> enemies = new ArrayList<>();
        String[] enemyTypes = {"goblin", "slime", "skeleton"};
        int numEnemies = isBossRoom ? 0 : (3 + rng.nextInt(3));   // 3-5, or 0 in boss rooms
        for (int i = 0; i < numEnemies && i < groundPos.size(); i++) {
            float[] pos = groundPos.get(i);
            String t    = enemyTypes[i % enemyTypes.length];
            float patrol = 3 * TILE;
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

        // NPCs — 1-3 per room: base types plus a crafter in crafting/shop rooms.
        // Python: npc_manager.py spawns NPCs per story state; we spawn procedurally here.
        List<NPCSpawn> npcs = new ArrayList<>();
        // Base NPC rotation: lore, shop, mission_giver
        String[] baseNpcTypes = {"lore", "shop", "mission_giver"};
        int numNpcs  = 1 + rng.nextInt(2);   // 1-2 base NPCs
        int npcStart = numEnemies + numPickups;
        for (int i = 0; i < numNpcs && (npcStart + i) < groundPos.size(); i++) {
            float[] pos = groundPos.get(npcStart + i);
            String t    = baseNpcTypes[i % baseNpcTypes.length];
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

        // Portals — placed in exit/start rooms near the far-right edge at spawn elevation.
        List<PortalSpawn> portals = new ArrayList<>();
        if ("exit".equals(roomType) || "start".equals(roomType)) {
            float px = COLS * TILE - 4 * TILE;
            // 30% chance the portal requires dash to enter (depth-scaling gate placeholder)
            String gate = (rng.nextInt(100) < 30) ? "dash" : "";
            portals.add(new PortalSpawn("hub", "hub_" + Long.toHexString(seed ^ 0xEEEEL), px, spawnY, gate));
        }

        return new LevelLayout(seed, COLS, ROWS, hash, enemies, pickups, npcs, bossSpawn, portals, falling,
                spawnX, spawnY);
    }
}
