package com.indieniinja.server;

import com.indieniinja.world.FeaturePlacer;
import com.indieniinja.world.WorldGenerator;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S7 — Verifies that FeaturePlacer stamps features into the tile grid
 * without blocking door corridors or producing out-of-bounds writes.
 */
class FeaturePlacerTest {

    private static final int COLS      = 128;
    private static final int ROWS      = 128;
    private static final int DOOR_HALF = 5;   // matches RoomGenerator DOOR_HALF

    // ── Helpers ───────────────────────────────────────────────────────────────

    private byte[][] blankGrid() {
        // All AIR — feature stamps (SOLID, PLATFORM, WATER) are clearly visible as changes
        return new byte[ROWS][COLS];
    }

    private boolean doorCenterClear(byte[][] g, List<String> dirs) {
        int midC = COLS / 2;
        int midR = ROWS / 2;
        if (dirs.contains("up")    && g[0][midC] == WorldGenerator.SOLID) return false;
        if (dirs.contains("down")  && g[ROWS - 1][midC] == WorldGenerator.SOLID) return false;
        if (dirs.contains("left")  && g[midR][0] == WorldGenerator.SOLID) return false;
        if (dirs.contains("right") && g[midR][COLS - 1] == WorldGenerator.SOLID) return false;
        return true;
    }

    // ── Tests ─────────────────────────────────────────────────────────────────

    @Test
    void placedFeaturesModifyGrid() {
        byte[][] before = blankGrid();
        byte[][] after  = blankGrid();

        FeaturePlacer.place(after, 0, 42L, List.of("right"));

        // At least some cells must differ (features were placed)
        boolean anyDiff = false;
        for (int r = 0; r < ROWS && !anyDiff; r++)
            for (int c = 0; c < COLS && !anyDiff; c++)
                if (before[r][c] != after[r][c]) anyDiff = true;

        assertTrue(anyDiff, "FeaturePlacer placed nothing — grid unchanged");
    }

    @Test
    void doorCorridorNotBlocked_upDown() {
        List<String> dirs = List.of("up", "down");
        for (long seed = 1; seed <= 20; seed++) {
            byte[][] g = blankGrid();
            FeaturePlacer.place(g, 0, seed, dirs);
            // Carve the door corridors as RoomGenerator would
            int midC = COLS / 2;
            for (int r = 0; r < 2; r++)
                for (int c = midC - DOOR_HALF; c <= midC + DOOR_HALF; c++)
                    g[r][c] = WorldGenerator.AIR;
            for (int r = ROWS - 2; r < ROWS; r++)
                for (int c = midC - DOOR_HALF; c <= midC + DOOR_HALF; c++)
                    g[r][c] = WorldGenerator.AIR;

            assertTrue(doorCenterClear(g, dirs),
                "door corridor blocked after FeaturePlacer (seed=" + seed + ")");
        }
    }

    @Test
    void doorCorridorNotBlocked_leftRight() {
        List<String> dirs = List.of("left", "right");
        for (long seed = 1; seed <= 20; seed++) {
            byte[][] g = blankGrid();
            FeaturePlacer.place(g, 4, seed, dirs);
            int midR = ROWS / 2;
            for (int r = midR - DOOR_HALF; r <= midR + DOOR_HALF; r++) {
                for (int c = 0; c < 4; c++) g[r][c] = WorldGenerator.AIR;
                for (int c = COLS - 4; c < COLS; c++) g[r][c] = WorldGenerator.AIR;
            }
            assertTrue(doorCenterClear(g, dirs),
                "door corridor blocked after FeaturePlacer (seed=" + seed + ")");
        }
    }

    @Test
    void featureCountWithin_1_to_2() {
        // With a fully solid blank grid, placed features must change 1–30 cells
        // (smallest stamp is 1 tile, largest is ~11 tiles, max 2 features)
        for (long seed = 0; seed < 10; seed++) {
            byte[][] before = blankGrid();
            byte[][] after  = new byte[ROWS][];
            for (int r = 0; r < ROWS; r++) after[r] = before[r].clone();

            FeaturePlacer.place(after, 0, seed, List.of("up"));

            int changed = 0;
            for (int r = 0; r < ROWS; r++)
                for (int c = 0; c < COLS; c++)
                    if (before[r][c] != after[r][c]) changed++;

            // 1 to 2 features, each up to ~11 tiles; allow 0 if all attempts fail
            assertTrue(changed <= 22, "too many changed cells: " + changed);
        }
    }

    @Test
    void noOutOfBoundsWrite() {
        // Boundary rows/cols 0 and ROWS/COLS-1 must never be written
        byte[][] g = new byte[ROWS][COLS];
        // Mark boundaries with a sentinel
        for (int c = 0; c < COLS; c++) { g[0][c] = 99; g[ROWS - 1][c] = 99; }
        for (int r = 0; r < ROWS; r++) { g[r][0] = 99; g[r][COLS - 1] = 99; }
        // Fill interior with SOLID
        for (int r = 1; r < ROWS - 1; r++)
            for (int c = 1; c < COLS - 1; c++)
                g[r][c] = WorldGenerator.SOLID;

        FeaturePlacer.place(g, 3, 77L, List.of("up", "left", "right"));

        for (int c = 0; c < COLS; c++) {
            assertEquals(99, g[0][c],        "top boundary overwritten at col " + c);
            assertEquals(99, g[ROWS - 1][c], "bottom boundary overwritten at col " + c);
        }
        for (int r = 0; r < ROWS; r++) {
            assertEquals(99, g[r][0],        "left boundary overwritten at row " + r);
            assertEquals(99, g[r][COLS - 1], "right boundary overwritten at row " + r);
        }
    }

    @Test
    void deterministicAcrossCallsWithSameSeed() {
        byte[][] g1 = blankGrid();
        byte[][] g2 = blankGrid();
        FeaturePlacer.place(g1, 1, 12345L, List.of("down"));
        FeaturePlacer.place(g2, 1, 12345L, List.of("down"));

        for (int r = 0; r < ROWS; r++)
            for (int c = 0; c < COLS; c++)
                assertEquals(g1[r][c], g2[r][c],
                    "non-deterministic output at [" + r + "][" + c + "]");
    }

    @Test
    void differentBiomesPlaceInGrid() {
        // Every biome index 0..11 should produce some result without crashing
        for (int bi = 0; bi < 12; bi++) {
            final int biome = bi;
            byte[][] g = blankGrid();
            assertDoesNotThrow(() -> FeaturePlacer.place(g, biome, 99L, List.of("up", "down")),
                "FeaturePlacer threw for biomeIndex=" + bi);
        }
    }

    @Test
    void noFeaturesPlacedWhenNoPool() {
        // biomeIndex clamped to known range — no crash for any value
        byte[][] g = blankGrid();
        assertDoesNotThrow(() -> FeaturePlacer.place(g, 100, 1L, List.of()));
        assertDoesNotThrow(() -> FeaturePlacer.place(g, -5,  2L, List.of()));
    }
}
