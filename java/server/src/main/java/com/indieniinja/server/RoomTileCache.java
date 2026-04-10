package com.indieniinja.server;

import redis.clients.jedis.JedisPool;
import redis.clients.jedis.Jedis;

import java.nio.ByteBuffer;
import java.util.Collection;
import java.util.TreeSet;
import java.util.stream.Collectors;

/**
 * Cache-through layer for procedurally generated room tile grids (WORLD-2).
 *
 * Key format:  {@code room_tile:{seed}:{roomType}:{sortedNeighborDirs}}
 * Value:       compact binary — 4-byte rows, 4-byte cols, then rows×cols tile bytes
 * TTL:         1 hour (3 600 s) — generation is deterministic so the grid never
 *              changes for a given (seed, roomType, neighborDirs) triple.
 *
 * Usage (in ZoneInstance or WorldGenerator call-site):
 * <pre>
 *   byte[][] grid = tileCache.get(seed, roomType, neighborDirs);
 *   if (grid == null) {
 *       grid = WorldGenerator.generate(seed, COLS, ROWS, neighborDirs, roomType);
 *       tileCache.put(seed, roomType, neighborDirs, grid);
 *   }
 * </pre>
 *
 * The cache is optional: if Redis is unavailable (constructor receives {@code null}
 * pool) every call is a cache miss and generation falls back to the normal path.
 */
public final class RoomTileCache {

    private static final int TTL_SECONDS = 3_600;   // 1 hour
    private static final String KEY_PREFIX = "room_tile:";

    /** Null-safe pool — a null pool means the cache is disabled. */
    private final JedisPool pool;

    public RoomTileCache(JedisPool pool) {
        this.pool = pool;
    }

    /**
     * Look up a cached tile grid.
     *
     * @return the cached {@code byte[rows][cols]} grid, or {@code null} on a miss.
     */
    public byte[][] get(long seed, String roomType, Collection<String> neighborDirs) {
        if (pool == null) return null;
        byte[] keyBytes = buildKey(seed, roomType, neighborDirs);
        try (Jedis j = pool.getResource()) {
            byte[] raw = j.get(keyBytes);
            return raw != null ? deserialize(raw) : null;
        } catch (Exception e) {
            // Redis unavailable — treat as cache miss, never crash the sim loop
            return null;
        }
    }

    /**
     * Store a tile grid in Redis with a 1-hour TTL.
     */
    public void put(long seed, String roomType, Collection<String> neighborDirs,
                    byte[][] grid) {
        if (pool == null) return;
        byte[] keyBytes = buildKey(seed, roomType, neighborDirs);
        byte[] value    = serialize(grid);
        try (Jedis j = pool.getResource()) {
            j.setex(keyBytes, TTL_SECONDS, value);
        } catch (Exception e) {
            // Redis write failure is non-fatal — the grid was generated successfully
        }
    }

    // ── Key construction ──────────────────────────────────────────────────────

    /**
     * Build the Redis key as UTF-8 bytes.
     * Neighbor dirs are sorted so key is direction-order-independent.
     */
    private static byte[] buildKey(long seed, String roomType,
                                    Collection<String> neighborDirs) {
        String dirs = new TreeSet<>(neighborDirs).stream()
                .collect(Collectors.joining(","));
        String key = KEY_PREFIX + seed + ":" + roomType + ":" + dirs;
        return key.getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    // ── Serialization ─────────────────────────────────────────────────────────

    /**
     * Serialize a row-major tile grid to a compact byte[].
     * Format: [4 bytes: rows][4 bytes: cols][rows*cols tile bytes]
     */
    static byte[] serialize(byte[][] grid) {
        int rows = grid.length;
        int cols = (rows > 0) ? grid[0].length : 0;
        ByteBuffer buf = ByteBuffer.allocate(8 + rows * cols);
        buf.putInt(rows);
        buf.putInt(cols);
        for (byte[] row : grid) buf.put(row);
        return buf.array();
    }

    /**
     * Deserialize a byte[] back to a row-major tile grid.
     */
    static byte[][] deserialize(byte[] raw) {
        ByteBuffer buf = ByteBuffer.wrap(raw);
        int rows = buf.getInt();
        int cols = buf.getInt();
        byte[][] grid = new byte[rows][cols];
        for (int r = 0; r < rows; r++) buf.get(grid[r]);
        return grid;
    }
}
