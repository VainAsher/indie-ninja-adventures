package com.indieniinja.server;

import com.indieniinja.world.RoomGenerator;
import com.indieniinja.world.WorldGenerator;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S8 — Verifies cellular automata terrain smoothing behaviour.
 *
 * smoothCaveTerrain() is package-private (same package via test module)
 * so we access it directly via the world package.
 */
class TerrainSmoothingTest {

    private static final int ROWS = 128;
    private static final int COLS = 128;

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** Grid of all AIR except boundaries (SOLID). */
    private byte[][] airGrid() {
        byte[][] g = new byte[ROWS][COLS];
        for (int r = 0; r < ROWS; r++) g[r][0] = g[r][COLS - 1] = WorldGenerator.SOLID;
        for (int c = 0; c < COLS; c++) g[0][c] = g[ROWS - 1][c] = WorldGenerator.SOLID;
        return g;
    }

    /** Grid of all SOLID (interior). */
    private byte[][] solidGrid() {
        byte[][] g = new byte[ROWS][COLS];
        for (int r = 0; r < ROWS; r++)
            for (int c = 0; c < COLS; c++)
                g[r][c] = WorldGenerator.SOLID;
        return g;
    }

    // ── Isolation rules ───────────────────────────────────────────────────────

    @Test
    void isolatedSolidTile_removedInEarthBiome() {
        byte[][] g = airGrid();
        // Place a single isolated SOLID tile at centre — it has 0 SOLID neighbours
        int cr = ROWS / 2, cc = COLS / 2;
        g[cr][cc] = WorldGenerator.SOLID;

        RoomGenerator.smoothCaveTerrain(g, 0);  // biome 0 = EARTH

        assertEquals(WorldGenerator.AIR, g[cr][cc],
            "isolated SOLID tile should be removed by cave smoothing");
    }

    @Test
    void solidTileWithManyNeighbours_keptInEarthBiome() {
        byte[][] g = solidGrid();
        // Centre tile is surrounded by SOLID — should stay SOLID
        int cr = ROWS / 2, cc = COLS / 2;

        RoomGenerator.smoothCaveTerrain(g, 0);

        assertEquals(WorldGenerator.SOLID, g[cr][cc],
            "well-supported SOLID tile should not be removed");
    }

    @Test
    void smallAirPocket_filledInEarthBiome() {
        byte[][] g = solidGrid();
        // Single AIR tile at centre surrounded by 8 SOLID neighbours
        int cr = ROWS / 2, cc = COLS / 2;
        g[cr][cc] = WorldGenerator.AIR;

        RoomGenerator.smoothCaveTerrain(g, 0);

        assertEquals(WorldGenerator.SOLID, g[cr][cc],
            "tiny air pocket (8 SOLID neighbours) should be filled");
    }

    // ── Boundary safety ───────────────────────────────────────────────────────

    @Test
    void boundaryTilesNeverModified() {
        byte[][] g = airGrid();
        // Place SOLID on boundaries; smoothing must not change them
        RoomGenerator.smoothCaveTerrain(g, 0);

        for (int c = 0; c < COLS; c++) {
            assertEquals(WorldGenerator.SOLID, g[0][c],        "top boundary modified at col " + c);
            assertEquals(WorldGenerator.SOLID, g[ROWS - 1][c], "bottom boundary modified at col " + c);
        }
        for (int r = 0; r < ROWS; r++) {
            assertEquals(WorldGenerator.SOLID, g[r][0],        "left boundary modified at row " + r);
            assertEquals(WorldGenerator.SOLID, g[r][COLS - 1], "right boundary modified at row " + r);
        }
    }

    // ── Biome gating ─────────────────────────────────────────────────────────

    @Test
    void dungeonBiome_gridUnchanged() {
        // biomeIndex 4 = STONE/dungeon — smoothing must be a no-op
        byte[][] g = airGrid();
        int cr = ROWS / 2, cc = COLS / 2;
        g[cr][cc] = WorldGenerator.SOLID;  // isolated tile

        RoomGenerator.smoothCaveTerrain(g, 4);

        assertEquals(WorldGenerator.SOLID, g[cr][cc],
            "dungeon biome should NOT apply cave smoothing");
    }

    @Test
    void earthAltBiome_smoothingApplied() {
        // biomeIndex 5 = EARTH_ALT — smoothing must run
        byte[][] g = airGrid();
        int cr = ROWS / 2, cc = COLS / 2;
        g[cr][cc] = WorldGenerator.SOLID;  // isolated tile

        RoomGenerator.smoothCaveTerrain(g, 5);

        assertEquals(WorldGenerator.AIR, g[cr][cc],
            "EARTH_ALT biome should apply cave smoothing");
    }

    @Test
    void allNonCaveBiomes_noSmoothing() {
        int[] nonCaveBiomes = { 1, 2, 3, 4, 6, 7, 8, 9, 10, 11 };
        for (int bi : nonCaveBiomes) {
            byte[][] g = airGrid();
            int cr = ROWS / 2, cc = COLS / 2;
            g[cr][cc] = WorldGenerator.SOLID;
            RoomGenerator.smoothCaveTerrain(g, bi);
            assertEquals(WorldGenerator.SOLID, g[cr][cc],
                "biome " + bi + " should not apply smoothing");
        }
    }

    // ── Integration ───────────────────────────────────────────────────────────

    @Test
    void smoothingDoesNotCrashOnFullPipeline() {
        // Full generation with EARTH biome runs without exception
        assertDoesNotThrow(() -> {
            WorldGenerator.generate(777L, 128, 128,
                java.util.List.of("right", "down"), "combat", 0);
        });
    }
}
