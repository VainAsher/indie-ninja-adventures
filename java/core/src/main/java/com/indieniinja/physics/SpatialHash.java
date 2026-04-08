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

        // Single-chunk fast path (most common case)
        if (x0 == x1 && y0 == y1) {
            List<TileRect> chunk = chunks.get(key(x0, y0));
            return chunk != null ? chunk : Collections.emptyList();
        }

        // Multi-chunk: accumulate into a temporary list
        List<TileRect> result = new ArrayList<>();
        for (int cx = x0; cx <= x1; cx++) {
            for (int cy = y0; cy <= y1; cy++) {
                List<TileRect> chunk = chunks.get(key(cx, cy));
                if (chunk != null) result.addAll(chunk);
            }
        }
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

    /** Number of tiles stored across all chunks. */
    public int size() {
        return chunks.values().stream().mapToInt(List::size).sum();
    }
}
