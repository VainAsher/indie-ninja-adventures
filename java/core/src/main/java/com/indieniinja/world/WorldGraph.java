package com.indieniinja.world;

import java.util.*;

/**
 * Procedural multi-room world graph generator.
 *
 * Direct port of Python systems/world_generation.py WorldGenerator.
 * Generates a graph of RoomNodes connected by cardinal doors using a
 * frontier-based BFS with configurable shape parameters.
 *
 * Usage:
 *   WorldGraph graph = WorldGraph.generate(seed, numRooms, WorldShape.BLOB);
 *   RoomNode start   = graph.startRoom();
 *   RoomNode exit    = graph.exitRoom();
 *   RoomNode room    = graph.roomAt(gx, gy);   // null if not present
 */
public final class WorldGraph {

    // ── Enums ─────────────────────────────────────────────────────────────────

    public enum RoomType {
        START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS;
        public String wire() { return name().toLowerCase(); }
    }

    /**
     * World shape styles — matches Python WorldShape enum.
     * rev = probability to pick from recent frontier (high → snake-like).
     * straight = probability to continue same direction (high → long corridors).
     */
    public enum WorldShape {
        SNAKE   (0.80f, 0.70f),
        BRANCHY (0.25f, 0.30f),
        BLOB    (0.40f, 0.40f),
        SPIRAL  (0.90f, 0.15f),
        TREE    (0.10f, 0.60f),
        GRID    (0.50f, 0.85f);

        public final float rev;
        public final float straight;
        WorldShape(float rev, float straight) { this.rev = rev; this.straight = straight; }
    }

    // ── RoomNode ──────────────────────────────────────────────────────────────

    /**
     * A single room in the procedural world.
     * neighborDirs: set of cardinal directions ("up","down","left","right")
     *               that lead to adjacent rooms.
     * biomeIndex:   0-4 (matches BlobTileSet biome constants)
     */
    public static final class RoomNode {
        public final int      gridX, gridY;
        public final RoomType type;
        public final long     seed;
        public final int      biomeIndex;
        private final Set<String> neighborDirs = new LinkedHashSet<>();

        RoomNode(int gx, int gy, RoomType type, long seed, int biomeIndex) {
            this.gridX      = gx;
            this.gridY      = gy;
            this.type       = type;
            this.seed       = seed;
            this.biomeIndex = biomeIndex;
        }

        public Set<String> neighborDirs() { return Collections.unmodifiableSet(neighborDirs); }

        /** World-space tile offset of this room. Each room is ROOM_W × ROOM_H tiles. */
        public int tileOffsetX() { return gridX * ROOM_W; }
        public int tileOffsetY() { return gridY * ROOM_H; }

        @Override public String toString() {
            return String.format("Room(%d,%d %s biome=%d seed=%d)",
                gridX, gridY, type, biomeIndex, seed);
        }
    }

    // ── Constants ─────────────────────────────────────────────────────────────

    /** Each room occupies this many tiles in each dimension. */
    public static final int ROOM_W = 128;
    public static final int ROOM_H = 128;

    // Biome count (matches BlobTileSet.BIOME_COUNT)
    private static final int BIOME_COUNT = 5;

    // Direction vectors
    private static final String[] DIR_NAMES   = {"up", "down", "left", "right"};
    private static final int[]    DIR_DX       = { 0,    0,    -1,     1};
    private static final int[]    DIR_DY       = {-1,    1,     0,     0};
    private static final String[] OPPOSITE     = {"down","up","right","left"};

    // ── State ─────────────────────────────────────────────────────────────────

    private final Map<Long, RoomNode> rooms;
    private final RoomNode            startRoom;
    private final RoomNode            exitRoom;

    private WorldGraph(Map<Long, RoomNode> rooms, RoomNode startRoom, RoomNode exitRoom) {
        this.rooms     = rooms;
        this.startRoom = startRoom;
        this.exitRoom  = exitRoom;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    public RoomNode           startRoom()           { return startRoom; }
    public RoomNode           exitRoom()            { return exitRoom; }
    public Collection<RoomNode> allRooms()          { return rooms.values(); }
    public RoomNode           roomAt(int gx, int gy){ return rooms.get(key(gx, gy)); }
    public int                size()                { return rooms.size(); }

    // ── Generation ────────────────────────────────────────────────────────────

    /**
     * Generate a world graph.
     *
     * @param seed     master world seed
     * @param numRooms target number of rooms (actual may be slightly less if grid fills)
     * @param shape    world topology style
     * @return complete WorldGraph
     */
    public static WorldGraph generate(long seed, int numRooms, WorldShape shape) {
        Random rng = new Random(seed);

        // Dynamic grid size based on room count (mirrors Python)
        int base   = Math.max(8, (int)(Math.sqrt(numRooms) * 3.0));
        int gridW  = base + rng.nextInt(7);               // base .. base+6
        int gridH  = Math.max(6, base - 2) + rng.nextInt(7); // base-2..base+4

        int sx = gridW / 2;
        int sy = gridH / 2;

        // Build room map
        Map<Long, RoomNode> rooms = new LinkedHashMap<>();
        long startSeed = nextSeed(rng);
        RoomNode startNode = new RoomNode(sx, sy, RoomType.START, startSeed,
                                          biomeForDepth(0, seed));
        rooms.put(key(sx, sy), startNode);

        // Frontier BFS
        List<long[]> frontier = new ArrayList<>();  // each entry: [gx, gy]
        frontier.add(new long[]{sx, sy});
        String lastDir = null;

        while (rooms.size() < numRooms && !frontier.isEmpty()) {
            // Pick from frontier based on shape.rev
            long[] current;
            if (rng.nextFloat() < shape.rev) {
                // Prefer recent frontier (snake-like)
                int limit = Math.min(6, frontier.size());
                current = frontier.get(frontier.size() - 1 - rng.nextInt(limit));
            } else {
                current = frontier.get(rng.nextInt(frontier.size()));
            }
            int cx = (int) current[0];
            int cy = (int) current[1];

            // Get valid directions
            List<Integer> available = availableDirections(cx, cy, rooms, gridW, gridH);
            if (available.isEmpty()) {
                frontier.remove(current);
                continue;
            }

            // Choose direction with shape bias
            int chosenIdx;
            if (shape == WorldShape.SPIRAL && lastDir != null) {
                // Rotate clockwise: up→right→down→left→up
                String preferred = clockwiseRotate(lastDir);
                int pi = dirIndex(preferred);
                chosenIdx = (pi >= 0 && available.contains(pi)) ? pi
                           : available.get(rng.nextInt(available.size()));
            } else {
                int lastIdx = lastDir != null ? dirIndex(lastDir) : -1;
                if (lastIdx >= 0 && available.contains(lastIdx)
                        && rng.nextFloat() < shape.straight) {
                    chosenIdx = lastIdx;
                } else {
                    chosenIdx = available.get(rng.nextInt(available.size()));
                }
            }

            int nx = cx + DIR_DX[chosenIdx];
            int ny = cy + DIR_DY[chosenIdx];
            lastDir = DIR_NAMES[chosenIdx];

            // Create new room
            long roomSeed    = nextSeed(rng);
            int  depth       = Math.abs(nx - sx) + Math.abs(ny - sy);
            int  biomeIndex  = biomeForDepth(depth, seed);
            RoomNode newRoom = new RoomNode(nx, ny, RoomType.COMBAT, roomSeed, biomeIndex);
            rooms.put(key(nx, ny), newRoom);

            // Connect bidirectionally
            rooms.get(key(cx, cy)).neighborDirs.add(lastDir);
            newRoom.neighborDirs.add(OPPOSITE[chosenIdx]);

            frontier.add(new long[]{nx, ny});

            // Prune frontier by shape
            pruneF(frontier, shape, rng);
        }

        // Assign exit to farthest room from start
        long startKey = key(sx, sy);
        Long exitKey = rooms.keySet().stream()
            .filter(k -> !k.equals(startKey))
            .max(Comparator.comparingInt(k ->
                Math.abs(keyX(k) - sx) + Math.abs(keyY(k) - sy)))
            .orElseGet(() -> rooms.keySet().stream()
                .filter(k -> !k.equals(startKey)).findFirst().orElse(startKey));
        int ex = keyX(exitKey), ey = keyY(exitKey);

        // Specialize room types (mirrors Python take() logic)
        List<Long> candidates = new ArrayList<>(rooms.keySet());
        candidates.remove(Long.valueOf(startKey));
        candidates.remove(Long.valueOf(exitKey));
        Collections.shuffle(candidates, rng);

        int n = rooms.size();
        assignTypes(rooms, candidates, RoomType.SHOP,      Math.max(1, n / 10));
        assignTypes(rooms, candidates, RoomType.TREASURE,  Math.max(1, n / 12));
        assignTypes(rooms, candidates, RoomType.BOSS,      Math.max(1, n / 16));
        assignTypes(rooms, candidates, RoomType.PLATFORM,  Math.max(2, n /  4));
        // Remaining stay as COMBAT

        // Fix start/exit room types (overridden above if they fell in candidate pool)
        setType(rooms, startKey, RoomType.START);
        setType(rooms, exitKey, RoomType.EXIT);

        return new WorldGraph(rooms,
                              rooms.get(key(sx, sy)),
                              rooms.get(key(ex, ey)));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static long key(int x, int y) {
        return (long)(x + 50000) * 100000L + (y + 50000);
    }
    private static int keyX(long k) { return (int)(k / 100000L) - 50000; }
    private static int keyY(long k) { return (int)(k % 100000L) - 50000; }

    private static long nextSeed(Random rng) {
        return rng.nextLong() & Long.MAX_VALUE;
    }

    /** Derive biome index (0–4) from world depth and master seed. */
    private static int biomeForDepth(int depth, long worldSeed) {
        return (int)((Math.abs(worldSeed) + depth) % BIOME_COUNT);
    }

    private static List<Integer> availableDirections(
            int cx, int cy, Map<Long, RoomNode> rooms, int gridW, int gridH) {
        List<Integer> out = new ArrayList<>(4);
        for (int i = 0; i < 4; i++) {
            int nx = cx + DIR_DX[i];
            int ny = cy + DIR_DY[i];
            if (nx > 0 && nx < gridW - 1 && ny > 0 && ny < gridH - 1
                    && !rooms.containsKey(key(nx, ny))) {
                out.add(i);
            }
        }
        return out;
    }

    private static String clockwiseRotate(String dir) {
        return switch (dir) {
            case "up"    -> "right";
            case "right" -> "down";
            case "down"  -> "left";
            case "left"  -> "up";
            default      -> "right";
        };
    }

    private static int dirIndex(String dir) {
        for (int i = 0; i < DIR_NAMES.length; i++)
            if (DIR_NAMES[i].equals(dir)) return i;
        return -1;
    }

    private static void pruneF(List<long[]> frontier, WorldShape shape, Random rng) {
        switch (shape) {
            case SNAKE   -> { if (frontier.size() > 6)  frontier.subList(0, frontier.size() - 6).clear(); }
            case SPIRAL  -> { if (frontier.size() > 3)  frontier.subList(0, frontier.size() - 3).clear(); }
            case TREE    -> { if (frontier.size() > 12 && rng.nextFloat() < 0.2f) frontier.remove(rng.nextInt(frontier.size())); }
            case GRID    -> { if (frontier.size() > 6  && rng.nextFloat() < 0.4f) frontier.remove(rng.nextInt(frontier.size())); }
            default      -> { if (frontier.size() > 8  && rng.nextFloat() < 0.3f) frontier.remove(rng.nextInt(frontier.size())); }
        }
    }

    private static void assignTypes(Map<Long, RoomNode> rooms,
                                    List<Long> candidates,
                                    RoomType type, int count) {
        for (int i = 0; i < count && !candidates.isEmpty(); i++) {
            setType(rooms, candidates.remove(0), type);
        }
    }

    /** Replace a RoomNode in the map with a new one of the given type. */
    private static void setType(Map<Long, RoomNode> rooms, long k, RoomType type) {
        RoomNode old = rooms.get(k);
        if (old == null) return;
        RoomNode updated = new RoomNode(old.gridX, old.gridY, type, old.seed, old.biomeIndex);
        updated.neighborDirs.addAll(old.neighborDirs);
        rooms.put(k, updated);
    }
}
