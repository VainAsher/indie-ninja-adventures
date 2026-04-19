package com.indieniinja.world.postprocess;

import com.indieniinja.physics.PhysicsConstants;

import java.util.ArrayList;
import java.util.List;

/**
 * Filters a list of candidate spawn positions by removing those that fall
 * inside any registered exclusion zone.
 *
 * All exclusion zones are circular (centre + radius in pixels) so that
 * they work regardless of tile alignment.  Build up zones then call
 * {@link #filter} to get the safe subset.
 */
public final class PlacementFilter {

    private static final int TILE = PhysicsConstants.TILE_SIZE;  // 32

    /** Simple circle exclusion zone. */
    private record Zone(float cx, float cy, float radiusSq) {
        boolean contains(float x, float y) {
            float dx = x - cx, dy = y - cy;
            return dx * dx + dy * dy <= radiusSq;
        }
    }

    private final List<Zone> zones = new ArrayList<>();

    // ── Builder methods ───────────────────────────────────────────────────────

    /**
     * Exclude positions within {@code marginTiles} tiles of any door opening
     * (horizontal or vertical centre edge carve zone).
     */
    public PlacementFilter excludeAroundDoors(
            byte[][] grid, java.util.Collection<String> neighborDirs, int marginTiles) {
        int cols = grid[0].length;
        int rows = grid.length;
        float margin = marginTiles * TILE;

        for (String dir : neighborDirs) {
            float cx, cy;
            switch (dir) {
                case "up"    -> { cx = cols * TILE * 0.5f; cy = 0; }
                case "down"  -> { cx = cols * TILE * 0.5f; cy = rows * TILE; }
                case "left"  -> { cx = 0;                  cy = rows * TILE * 0.5f; }
                case "right" -> { cx = cols * TILE;         cy = rows * TILE * 0.5f; }
                default      -> { continue; }
            }
            zones.add(new Zone(cx, cy, margin * margin));
        }
        return this;
    }

    /** Exclude positions within {@code radiusTiles} tiles of the spawn point. */
    public PlacementFilter excludeAroundSpawn(float spawnX, float spawnY, float radiusTiles) {
        float r = radiusTiles * TILE;
        zones.add(new Zone(spawnX, spawnY, r * r));
        return this;
    }

    /** Exclude positions within {@code radiusTiles} tiles of a puzzle element. */
    public PlacementFilter excludePuzzleZone(float cx, float cy, float radiusTiles) {
        float r = radiusTiles * TILE;
        zones.add(new Zone(cx, cy, r * r));
        return this;
    }

    /**
     * Exclude the boss arena: a rectangular region in the centre-bottom third
     * of the room (4-tile radius around centre-bottom).
     */
    public PlacementFilter excludeBossArena(byte[][] grid) {
        int cols = grid[0].length;
        int rows = grid.length;
        float cx = cols * TILE * 0.5f;
        float cy = rows * TILE * 0.70f;  // bottom-third centre
        float r  = 5 * TILE;
        zones.add(new Zone(cx, cy, r * r));
        return this;
    }

    // ── Filter ────────────────────────────────────────────────────────────────

    /**
     * Returns the subset of {@code candidates} that do not fall inside any
     * registered exclusion zone.
     *
     * If the filtered list would be empty, returns the original list as a
     * safety fallback so placement always has candidates to work with.
     */
    public List<float[]> filter(List<float[]> candidates) {
        if (zones.isEmpty()) return candidates;

        List<float[]> result = new ArrayList<>(candidates.size());
        for (float[] pos : candidates) {
            boolean excluded = false;
            for (Zone z : zones) {
                if (z.contains(pos[0], pos[1])) { excluded = true; break; }
            }
            if (!excluded) result.add(pos);
        }
        // Safety fallback: never return an empty list
        return result.isEmpty() ? candidates : result;
    }
}
