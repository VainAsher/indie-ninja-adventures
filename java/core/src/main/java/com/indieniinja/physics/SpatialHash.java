package com.indieniinja.physics;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Chunk-based spatial hash for fast tile candidate lookup.
 *
 * Java equivalent of Python's collision_system.py spatial hashing logic.
 * Chunk size matches Python: 320 pixels (= 10 tiles × 32 px).
 *
 * Key encoding packs (chunk_x, chunk_y) into a single long to avoid
 * two-level map overhead and Long boxing on the lookup path.
 *
 * Thread-safety: build once (during world load), then read-only — safe to share.
 */
public final class SpatialHash {

    /** Must match Python CollisionSystem CHUNK_SIZE = 320. */
    public static final int CHUNK_SIZE = 320;

    private final Map<Long, List<TileRect>> chunks = new HashMap<>();

    /**
     * Dynamic tile overlay (moving/falling platforms).
     * Updated each tick via {@link #setDynamicTiles}; included in
     * {@link #candidates} results and {@link #raycast} queries.
     */
    private final List<TileRect> dynamicTiles = new ArrayList<>();

    /** Pack (cx, cy) chunk coordinates into a unique long key. */
    private static long key(int cx, int cy) {
        return ((long) cx << 32) | (cy & 0xFFFFFFFFL);
    }

    /** Insert a tile rect into all chunks it overlaps. */
    public void insert(TileRect rect) {
        int x0 = (int) Math.floor(rect.x() / CHUNK_SIZE);
        int x1 = (int) Math.floor((rect.x() + rect.w() - 1) / CHUNK_SIZE);
        int y0 = (int) Math.floor(rect.y() / CHUNK_SIZE);
        int y1 = (int) Math.floor((rect.y() + rect.h() - 1) / CHUNK_SIZE);

        for (int cx = x0; cx <= x1; cx++) {
            for (int cy = y0; cy <= y1; cy++) {
                chunks.computeIfAbsent(key(cx, cy), k -> new ArrayList<>()).add(rect);
            }
        }
    }

    /**
     * Return all tiles whose chunks overlap the given AABB.
     * The returned list may contain duplicates if a tile spans multiple chunks;
     * callers should de-duplicate by result (collision resolution is idempotent).
     *
     * Returns an unmodifiable empty list when no candidates are found.
     */
    public List<TileRect> candidates(float x, float y, float w, float h) {
        int x0 = (int) Math.floor(x / CHUNK_SIZE);
        int x1 = (int) Math.floor((x + w) / CHUNK_SIZE);
        int y0 = (int) Math.floor(y / CHUNK_SIZE);
        int y1 = (int) Math.floor((y + h) / CHUNK_SIZE);

        // Single-chunk fast path (most common case — zero allocation when no dynamic tiles)
        if (x0 == x1 && y0 == y1 && dynamicTiles.isEmpty()) {
            List<TileRect> chunk = chunks.get(key(x0, y0));
            return chunk != null ? chunk : Collections.emptyList();
        }

        // Multi-chunk or dynamic tiles present: accumulate into a temporary list
        List<TileRect> result = new ArrayList<>();
        for (int cx = x0; cx <= x1; cx++) {
            for (int cy = y0; cy <= y1; cy++) {
                List<TileRect> chunk = chunks.get(key(cx, cy));
                if (chunk != null) result.addAll(chunk);
            }
        }
        result.addAll(dynamicTiles);
        return result;
    }

    /**
     * Remove a tile rect from all chunks it was inserted into.
     * Used at runtime when a puzzle door is unlocked.
     * Value-based equality (TileRect is a record) — removes the first matching entry per chunk.
     */
    public void remove(TileRect rect) {
        int x0 = (int) Math.floor(rect.x() / CHUNK_SIZE);
        int x1 = (int) Math.floor((rect.x() + rect.w() - 1) / CHUNK_SIZE);
        int y0 = (int) Math.floor(rect.y() / CHUNK_SIZE);
        int y1 = (int) Math.floor((rect.y() + rect.h() - 1) / CHUNK_SIZE);
        for (int cx = x0; cx <= x1; cx++) {
            for (int cy = y0; cy <= y1; cy++) {
                List<TileRect> chunk = chunks.get(key(cx, cy));
                if (chunk != null) chunk.remove(rect);
            }
        }
    }

    /**
     * Cast a ray from (x0,y0) to (x1,y1) and return the first solid TileRect hit,
     * or {@code null} if no tile is intersected within the segment.
     *
     * Algorithm: bounding-box chunk walk + slab-method ray-vs-AABB test.
     * All chunks whose bounding box overlaps the ray's AABB are visited;
     * within each chunk every tile is tested and the closest entry-point wins.
     *
     * Passable tiles (AIR, WATER, GAS, PLATFORM) are skipped — the raycast
     * is intended for line-of-sight and projectile obstruction queries.
     *
     * @param x0 ray start X (pixels)
     * @param y0 ray start Y (pixels)
     * @param x1 ray end X (pixels)
     * @param y1 ray end Y (pixels)
     * @return first solid TileRect hit, or null
     */
    public TileRect raycast(float x0, float y0, float x1, float y1) {
        float minX = Math.min(x0, x1), maxX = Math.max(x0, x1);
        float minY = Math.min(y0, y1), maxY = Math.max(y0, y1);

        int cx0 = (int) Math.floor(minX / CHUNK_SIZE);
        int cx1 = (int) Math.floor(maxX / CHUNK_SIZE);
        int cy0 = (int) Math.floor(minY / CHUNK_SIZE);
        int cy1 = (int) Math.floor(maxY / CHUNK_SIZE);

        TileRect best = null;
        float bestT  = Float.MAX_VALUE;

        for (int cx = cx0; cx <= cx1; cx++) {
            for (int cy = cy0; cy <= cy1; cy++) {
                List<TileRect> chunk = chunks.get(key(cx, cy));
                if (chunk == null) continue;
                for (TileRect tile : chunk) {
                    if (isPassable(tile)) continue;
                    float t = rayVsRect(x0, y0, x1, y1, tile);
                    if (t >= 0f && t < bestT) {
                        bestT = t;
                        best  = tile;
                    }
                }
            }
        }

        // Also check dynamic tiles (they are not chunk-indexed)
        for (TileRect tile : dynamicTiles) {
            if (isPassable(tile)) continue;
            float t = rayVsRect(x0, y0, x1, y1, tile);
            if (t >= 0f && t < bestT) {
                bestT = t;
                best  = tile;
            }
        }

        return best;
    }

    /**
     * Returns true for tiles that rays pass through (AIR, WATER, GAS, PLATFORM).
     * PLATFORM is one-way — treated as transparent for line-of-sight raycasts.
     */
    private static boolean isPassable(TileRect tile) {
        TileType type = tile.tileTypeEnum();
        return type == TileType.AIR
            || type == TileType.WATER
            || type == TileType.GAS
            || tile.isPlatform();
    }

    /**
     * Slab-method ray-vs-AABB intersection.
     *
     * @return parametric t in [0,1] at the ray entry point, or -1 if no hit.
     *         t=0 means the ray starts inside/at the rect; t=1 means at the endpoint.
     */
    private static float rayVsRect(float x0, float y0, float x1, float y1, TileRect r) {
        float dx = x1 - x0;
        float dy = y1 - y0;

        float tMinX, tMaxX;
        if (dx == 0f) {
            // Ray is vertical — check if x0 is within [r.x, r.x+r.w]
            if (x0 < r.x() || x0 >= r.x() + r.w()) return -1f;
            tMinX = Float.NEGATIVE_INFINITY;
            tMaxX = Float.POSITIVE_INFINITY;
        } else {
            tMinX = (r.x()          - x0) / dx;
            tMaxX = (r.x() + r.w() - x0) / dx;
            if (tMinX > tMaxX) { float tmp = tMinX; tMinX = tMaxX; tMaxX = tmp; }
        }

        float tMinY, tMaxY;
        if (dy == 0f) {
            // Ray is horizontal — check if y0 is within [r.y, r.y+r.h]
            if (y0 < r.y() || y0 >= r.y() + r.h()) return -1f;
            tMinY = Float.NEGATIVE_INFINITY;
            tMaxY = Float.POSITIVE_INFINITY;
        } else {
            tMinY = (r.y()          - y0) / dy;
            tMaxY = (r.y() + r.h() - y0) / dy;
            if (tMinY > tMaxY) { float tmp = tMinY; tMinY = tMaxY; tMaxY = tmp; }
        }

        float tEntry = Math.max(tMinX, tMinY);
        float tExit  = Math.min(tMaxX, tMaxY);

        if (tEntry > tExit || tExit < 0f || tEntry > 1f) return -1f;
        return Math.max(tEntry, 0f);
    }

    /**
     * Replace the dynamic tile overlay with current platform positions.
     * Called by CollisionSystem.setDynamicTiles() before each tick.
     */
    public void setDynamicTiles(List<TileRect> tiles) {
        dynamicTiles.clear();
        dynamicTiles.addAll(tiles);
    }

    /** Number of tiles stored across all chunks. */
    public int size() {
        return chunks.values().stream().mapToInt(List::size).sum();
    }
}
