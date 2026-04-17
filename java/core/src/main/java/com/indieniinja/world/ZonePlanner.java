package com.indieniinja.world;

import java.util.*;

/**
 * Plans a 16×16 zone grid for a single room.
 *
 * Java port of Python systems/zone_planning.py ZonePlanner.
 *
 * Each zone is later expanded to TILES_PER_ZONE × TILES_PER_ZONE (8×8) tiles
 * by RoomGenerator, producing the final 128×128 tilemap.
 *
 * Zone roles are encoded as bytes — see the Z_* constants.
 *
 * Pipeline:
 *   1. Initialise all zones to DECOR (unassigned)
 *   2. Place DOOR zones at edges based on neighborDirs
 *   3. Place feature zones (SHOP, LOOT, SAVE) based on roomType
 *   4. BFS paths between doors and features → mark intermediate zones WALK
 *   5. Apply logic rules (CHUTE / CLIMB / CONNECTOR / dead-end bonus)
 *   6. Sprinkle FILL obstacle zones (connectivity-checked)
 *   7. Finalise remaining DECOR zones with room-type probabilities
 */
public final class ZonePlanner {

    // ── Zone-role byte constants ──────────────────────────────────────────────

    public static final byte DECOR = 0;   // unassigned — resolved in step 7
    public static final byte WALK  = 1;   // walkable floor
    public static final byte FILL  = 2;   // solid obstacle
    public static final byte PLAT  = 3;   // one-way platform
    public static final byte DOOR  = 4;   // door connection opening
    public static final byte VOID  = 5;   // empty space / pit
    public static final byte SAVE  = 6;   // save point
    public static final byte SHOP  = 7;   // shop NPC
    public static final byte LOOT  = 8;   // treasure
    public static final byte CHUTE = 9;   // vertical drop chute (no floor)
    public static final byte CLIMB = 10;  // stepped platform ascent path
    public static final byte CONN  = 11;  // connector platform for hub rooms
    public static final byte LAVA  = 12;  // lava hazard zone (solid, damages on contact)
    public static final byte ICE   = 13;  // ice hazard zone (solid, near-zero friction)
    public static final byte WATER = 14;  // water hazard zone (passable, slows movement)

    // ── Grid dimensions ───────────────────────────────────────────────────────

    /** Matches Python ZONES_W / ZONES_H = 16. */
    static final int W = 16;
    static final int H = 16;

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Plan a 16×16 zone grid for the given room.
     *
     * @param roomSeed     per-room random seed
     * @param roomType     wire string: "start","exit","shop","combat","platform","treasure","boss"
     * @param neighborDirs set of connected directions ("up","down","left","right")
     * @return byte[H][W] zone grid
     */
    public static byte[][] plan(long roomSeed, String roomType,
                                 Collection<String> neighborDirs) {
        byte[][] zones = new byte[H][W];
        Random rng = new Random(roomSeed);

        // Step 1: doors at connected edges
        List<int[]> doorZones = placeDoors(zones, neighborDirs);

        // Step 2: feature zones by room type
        List<int[]> featureZones = placeFeatures(zones, roomType, doorZones, rng);

        // Step 3: BFS connectivity
        List<int[]> mustConnect = new ArrayList<>(doorZones);
        mustConnect.addAll(featureZones);
        if (mustConnect.size() >= 2) ensureConnectivity(zones, mustConnect);

        // Step 4: context-aware logic rules
        applyLogicRules(zones, roomType, neighborDirs);

        // Step 5: fill obstacles (with connectivity check)
        addFillZones(zones, roomType, mustConnect, rng);

        // Step 5b: thicken room perimeters — fill border zones that are still DECOR,
        // except within the door corridor. This limits traversal to intentional paths
        // and makes the dungeon feel enclosed rather than open at room edges.
        thickenPerimeter(zones, neighborDirs, mustConnect);

        // Step 6: finalize DECOR
        finalizeDecor(zones, roomType, rng);

        return zones;
    }

    // ── Step 1 — Door zones ───────────────────────────────────────────────────

    private static List<int[]> placeDoors(byte[][] z, Collection<String> dirs) {
        List<int[]> doorZones = new ArrayList<>();
        int centerX = W / 2;   // 8
        int centerY = H / 2;   // 8

        for (String dir : dirs) {
            int zx, zy;
            switch (dir) {
                case "up"    -> { zx = centerX; zy = 0; }
                case "down"  -> { zx = centerX; zy = H - 1; }
                case "left"  -> { zx = 0;       zy = centerY; }
                case "right" -> { zx = W - 1;   zy = centerY; }
                default      -> { continue; }
            }
            z[zy][zx] = DOOR;
            doorZones.add(new int[]{zx, zy});
        }
        return doorZones;
    }

    // ── Step 2 — Feature zones ────────────────────────────────────────────────

    private static List<int[]> placeFeatures(byte[][] z, String roomType,
                                               List<int[]> doorZones, Random rng) {
        List<int[]> features = new ArrayList<>();
        int cx = W / 2, cy = H / 2;

        switch (roomType != null ? roomType : "combat") {
            case "shop" -> {
                // Shop NPC at centre, loot in far corner
                z[cy][cx] = SHOP;  features.add(new int[]{cx, cy});
                int[] corner = farCorner(doorZones, rng);
                z[corner[1]][corner[0]] = LOOT;  features.add(corner);
            }
            case "treasure" -> {
                z[cy][cx] = LOOT;  features.add(new int[]{cx, cy});
            }
            case "start" -> {
                // Centre is spawn area; save point near first door (if any)
                features.add(new int[]{cx, cy});
                if (!doorZones.isEmpty()) {
                    int[] door = doorZones.get(0);
                    int[] closest = closestInterior(z, door, doorZones, features);
                    if (closest != null) {
                        z[closest[1]][closest[0]] = SAVE;
                        features.add(closest);
                    }
                }
            }
            case "exit" -> {
                z[cy][cx] = LOOT;  features.add(new int[]{cx, cy});
            }
            case "trial" -> {
                // Save point at centre (mid-trial checkpoint); proof-token loot at far corner
                z[cy][cx] = SAVE;  features.add(new int[]{cx, cy});
                int[] corner = farCorner(doorZones, rng);
                z[corner[1]][corner[0]] = LOOT;  features.add(corner);
            }
            default -> {
                // Random loot 25% chance
                if (rng.nextFloat() < 0.25f) {
                    int[] candidate = randomInterior(z, doorZones, features, rng);
                    if (candidate != null) {
                        z[candidate[1]][candidate[0]] = LOOT;
                        features.add(candidate);
                    }
                }
            }
        }
        return features;
    }

    // ── Step 3 — BFS connectivity ─────────────────────────────────────────────

    private static void ensureConnectivity(byte[][] z, List<int[]> mustConnect) {
        int[] start = mustConnect.get(0);
        for (int i = 1; i < mustConnect.size(); i++) {
            List<int[]> path = bfsPath(z, start, mustConnect.get(i));
            if (path != null) {
                for (int[] cell : path) {
                    if (z[cell[1]][cell[0]] == DECOR) z[cell[1]][cell[0]] = WALK;
                }
            }
        }
    }

    /** BFS — returns path from start to goal through non-FILL/non-VOID zones. */
    private static List<int[]> bfsPath(byte[][] z, int[] start, int[] goal) {
        if (Arrays.equals(start, goal)) return List.of();

        int[][] prev = new int[H][W];
        for (int[] row : prev) Arrays.fill(row, -1);

        Queue<int[]> queue = new ArrayDeque<>();
        queue.add(start);
        prev[start[1]][start[0]] = start[1] * W + start[0];   // self-link = visited marker

        int[] DX = {0, 0, 1, -1};
        int[] DY = {1, -1, 0, 0};

        while (!queue.isEmpty()) {
            int[] cur = queue.poll();
            int cx = cur[0], cy = cur[1];

            if (cx == goal[0] && cy == goal[1]) {
                // Reconstruct path
                List<int[]> path = new ArrayList<>();
                int x = goal[0], y = goal[1];
                while (!(x == start[0] && y == start[1])) {
                    path.add(new int[]{x, y});
                    int p = prev[y][x];
                    x = p % W;
                    y = p / W;
                }
                return path;
            }

            for (int d = 0; d < 4; d++) {
                int nx = cx + DX[d], ny = cy + DY[d];
                if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
                if (prev[ny][nx] != -1) continue;
                byte role = z[ny][nx];
                if (role == FILL || role == VOID) continue;
                prev[ny][nx] = cy * W + cx;
                queue.add(new int[]{nx, ny});
            }
        }
        return null;
    }

    private static boolean checkConnectivity(byte[][] z, List<int[]> mustConnect) {
        if (mustConnect.size() < 2) return true;
        int[] start = mustConnect.get(0);
        for (int i = 1; i < mustConnect.size(); i++) {
            if (bfsPath(z, start, mustConnect.get(i)) == null) return false;
        }
        return true;
    }

    // ── Step 4 — Logic rules ──────────────────────────────────────────────────

    private static void applyLogicRules(byte[][] z, String roomType,
                                         Collection<String> dirs) {
        // DOWN door → CHUTE at bottom-centre (vertical drop path)
        if (dirs.contains("down") && z[H-1][W/2] == DOOR) {
            z[H-1][W/2] = DOOR;  // already door; nothing extra needed
        } else if (dirs.contains("down")) {
            z[H-1][W/2] = CHUTE;
        }
        // UP door → CLIMB at top-centre (ascent path)
        if (dirs.contains("up")) {
            if (z[0][W/2] == DECOR || z[0][W/2] == WALK) z[0][W/2] = CLIMB;
        }
        // 3+ doors → CONNECTOR at centre (hub room)
        if (dirs.size() >= 3) {
            int cx = W/2, cy = H/2;
            if (z[cy][cx] == DECOR || z[cy][cx] == WALK) z[cy][cx] = CONN;
        }
        // Dead-end (1 door) → bonus LOOT in a corner
        if (dirs.size() == 1) {
            // Pick corner least likely to conflict
            int[][] corners = {{1, 1}, {W-2, 1}, {1, H-2}, {W-2, H-2}};
            for (int[] c : corners) {
                if (z[c[1]][c[0]] == DECOR) {
                    z[c[1]][c[0]] = LOOT;
                    break;
                }
            }
        }
    }

    // ── Step 5 — Fill obstacles ───────────────────────────────────────────────

    private static void addFillZones(byte[][] z, String roomType,
                                      List<int[]> mustConnect, Random rng) {
        // Fill count by room type — significantly increased to create denser, more dungeon-like rooms.
        // Higher values mean more solid-obstacle zones placed per room, limiting open traversal paths.
        int fillCount;
        switch (roomType != null ? roomType : "combat") {
            case "combat"   -> fillCount = 10 + rng.nextInt(7);  // 10-16 (dense combat arena)
            case "platform" -> fillCount =  8 + rng.nextInt(6);  // 8-13  (multi-level obstacles)
            case "treasure" -> fillCount = 12 + rng.nextInt(5);  // 12-16 (maze-like)
            case "boss"     -> fillCount =  5 + rng.nextInt(4);  // 5-8   (arena, moderate clutter)
            case "trial"    -> fillCount =  7 + rng.nextInt(4);  // 7-10  (skill room, open lanes)
            case "shop", "start", "exit" -> fillCount = 3 + rng.nextInt(3);  // 3-5 (navigable but not empty)
            default         -> fillCount =  8 + rng.nextInt(5);  // 8-12
        }

        // Candidate DECOR zones not in mustConnect
        Set<Long> mustSet = new HashSet<>();
        for (int[] c : mustConnect) mustSet.add((long) c[0] * H + c[1]);

        List<int[]> candidates = new ArrayList<>();
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                if (z[y][x] == DECOR && !mustSet.contains((long) x * H + y))
                    candidates.add(new int[]{x, y});

        Collections.shuffle(candidates, rng);

        // Hazard zone probabilities by room type
        // Each placed zone has a chance to become a hazard instead of a plain FILL.
        float lavaChance, iceChance, waterChance;
        switch (roomType != null ? roomType : "combat") {
            case "combat"   -> { lavaChance = 0.20f; iceChance = 0.10f; waterChance = 0.10f; }
            case "platform" -> { lavaChance = 0.10f; iceChance = 0.25f; waterChance = 0.15f; }
            case "boss"     -> { lavaChance = 0.35f; iceChance = 0.10f; waterChance = 0.05f; }
            case "treasure" -> { lavaChance = 0.05f; iceChance = 0.15f; waterChance = 0.20f; }
            case "trial"    -> { lavaChance = 0.25f; iceChance = 0.20f; waterChance = 0.10f; }
            default         -> { lavaChance = 0.10f; iceChance = 0.10f; waterChance = 0.10f; }
        }

        int placed = 0;
        for (int[] c : candidates) {
            if (placed >= fillCount) break;
            float roll = rng.nextFloat();
            byte chosen;
            if      (roll < lavaChance)               chosen = LAVA;
            else if (roll < lavaChance + iceChance)   chosen = ICE;
            else if (roll < lavaChance + iceChance + waterChance) chosen = WATER;
            else                                      chosen = FILL;
            z[c[1]][c[0]] = chosen;
            if (!checkConnectivity(z, mustConnect)) {
                z[c[1]][c[0]] = DECOR;  // revert
            } else {
                placed++;
            }
        }
    }

    // ── Step 6 — Finalize DECOR zones ────────────────────────────────────────

    private static void finalizeDecor(byte[][] z, String roomType, Random rng) {
        // DECOR zone final resolution probabilities by room type.
        // Higher fillProb = more solid terrain; higher platProb = more one-way platforms.
        // combat:   dense solid terrain + many platforms (obstacle-rich arena)
        // platform: moderate solid + very high platforms (vertical puzzle room)
        // treasure: high solid (maze walls) + moderate platforms + some void pits
        // boss:     open arena with scattered platforms
        // shop/start: open and navigable
        // Higher fillProb = more solid walls in remaining DECOR zones after explicit fills.
        // Reduced void/walk so dungeon reads as enclosed rather than open.
        float fillProb, platProb, walkProb;
        switch (roomType != null ? roomType : "combat") {
            case "platform" -> { fillProb = 0.30f; platProb = 0.50f; walkProb = 0.12f; }
            case "combat"   -> { fillProb = 0.38f; platProb = 0.38f; walkProb = 0.14f; }
            case "treasure" -> { fillProb = 0.45f; platProb = 0.22f; walkProb = 0.15f; }
            case "boss"     -> { fillProb = 0.18f; platProb = 0.30f; walkProb = 0.22f; }
            case "trial"    -> { fillProb = 0.20f; platProb = 0.55f; walkProb = 0.15f; }
            case "shop", "start", "exit" -> { fillProb = 0.12f; platProb = 0.28f; walkProb = 0.30f; }
            default         -> { fillProb = 0.25f; platProb = 0.30f; walkProb = 0.20f; }
        }

        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                if (z[y][x] != DECOR) continue;
                float r = rng.nextFloat();
                if      (r < fillProb)                    z[y][x] = FILL;
                else if (r < fillProb + platProb)         z[y][x] = PLAT;
                else if (r < fillProb + platProb + walkProb) z[y][x] = WALK;
                else                                      z[y][x] = VOID;
            }
        }
    }

    // ── Step 5b — Perimeter thickening ───────────────────────────────────────

    /**
     * Fill the 2-zone-deep perimeter ring with FILL wherever the zone is still DECOR,
     * skipping a ±1 zone corridor around each door opening.
     * This blocks off accidental open paths near room edges and forces traversal
     * through intentional corridors (doors) only.
     */
    private static void thickenPerimeter(byte[][] z, Collection<String> dirs,
                                          List<int[]> mustConnect) {
        Set<Long> mustSet = new HashSet<>();
        for (int[] c : mustConnect) mustSet.add((long) c[0] * H + c[1]);

        int depth = 2;  // how many zones deep from each wall to fill

        // Collect door centre positions so we can exempt a narrow corridor
        // Door is at (W/2, 0), (W/2, H-1), (0, H/2), (W-1, H/2) — see placeDoors()
        Set<Long> doorCorridor = new HashSet<>();
        int cx = W / 2, cy = H / 2;
        if (dirs.contains("up"))    { for (int x = cx - 1; x <= cx + 1; x++) for (int y = 0; y < depth; y++) doorCorridor.add((long) x * H + y); }
        if (dirs.contains("down"))  { for (int x = cx - 1; x <= cx + 1; x++) for (int y = H - depth; y < H; y++) doorCorridor.add((long) x * H + y); }
        if (dirs.contains("left"))  { for (int y = cy - 1; y <= cy + 1; y++) for (int x = 0; x < depth; x++) doorCorridor.add((long) x * H + y); }
        if (dirs.contains("right")) { for (int y = cy - 1; y <= cy + 1; y++) for (int x = W - depth; x < W; x++) doorCorridor.add((long) x * H + y); }

        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                boolean onPerimeter = (x < depth || x >= W - depth || y < depth || y >= H - depth);
                if (!onPerimeter) continue;
                if (z[y][x] != DECOR) continue;
                long key = (long) x * H + y;
                if (mustSet.contains(key)) continue;
                if (doorCorridor.contains(key)) continue;
                z[y][x] = FILL;
            }
        }
        // Connectivity check — revert fills that disconnect required zones
        // (iterate in reverse insertion order so reversions are cheap)
        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                boolean onPerimeter = (x < depth || x >= W - depth || y < depth || y >= H - depth);
                if (!onPerimeter) continue;
                if (z[y][x] != FILL) continue;
                // Temporarily revert and check
                z[y][x] = DECOR;
                if (checkConnectivity(z, mustConnect)) {
                    z[y][x] = FILL;  // restore — connectivity maintained without this zone
                }
                // else leave as DECOR — this fill would disconnect a required path
            }
        }
    }

    // ── Helper utilities ──────────────────────────────────────────────────────

    /** Pick a corner zone far from existing doors. */
    private static int[] farCorner(List<int[]> doorZones, Random rng) {
        int[][] corners = {{1, 1}, {W-2, 1}, {1, H-2}, {W-2, H-2}};
        if (doorZones.isEmpty()) return corners[rng.nextInt(corners.length)];
        int[] door = doorZones.get(0);
        int[] best = corners[0];
        int bestDist = 0;
        for (int[] c : corners) {
            int d = Math.abs(c[0] - door[0]) + Math.abs(c[1] - door[1]);
            if (d > bestDist) { bestDist = d; best = c; }
        }
        return best;
    }

    /** Closest interior zone to a reference point, not in excluded lists. */
    private static int[] closestInterior(byte[][] z, int[] ref,
                                          List<int[]> excludeA, List<int[]> excludeB) {
        Set<Long> excl = new HashSet<>();
        for (int[] c : excludeA) excl.add((long) c[0] * H + c[1]);
        for (int[] c : excludeB) excl.add((long) c[0] * H + c[1]);

        int[] best = null;
        int bestDist = Integer.MAX_VALUE;
        for (int y = 1; y < H-1; y++) {
            for (int x = 1; x < W-1; x++) {
                if (excl.contains((long) x * H + y)) continue;
                if (z[y][x] != DECOR) continue;
                int d = Math.abs(x - ref[0]) + Math.abs(y - ref[1]);
                if (d < bestDist) { bestDist = d; best = new int[]{x, y}; }
            }
        }
        return best;
    }

    /** Random interior DECOR zone not in excluded lists. */
    private static int[] randomInterior(byte[][] z, List<int[]> excludeA,
                                         List<int[]> excludeB, Random rng) {
        Set<Long> excl = new HashSet<>();
        for (int[] c : excludeA) excl.add((long) c[0] * H + c[1]);
        for (int[] c : excludeB) excl.add((long) c[0] * H + c[1]);

        List<int[]> candidates = new ArrayList<>();
        for (int y = 1; y < H-1; y++)
            for (int x = 1; x < W-1; x++)
                if (z[y][x] == DECOR && !excl.contains((long) x * H + y))
                    candidates.add(new int[]{x, y});

        return candidates.isEmpty() ? null : candidates.get(rng.nextInt(candidates.size()));
    }
}
