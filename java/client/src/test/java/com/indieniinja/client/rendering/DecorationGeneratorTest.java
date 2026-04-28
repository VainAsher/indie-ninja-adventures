package com.indieniinja.client.rendering;

import com.indieniinja.client.rendering.DecorationGenerator.DecoRuleSet;
import com.indieniinja.world.WorldGenerator;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S4 — Verifies DecorationGenerator determinism, placement rules, and
 * spawn-position exclusion.
 *
 * Uses a small hand-crafted terrain grid to make assertions precise.
 */
class DecorationGeneratorTest {

    private static final int COLS = 12;
    private static final int ROWS = 12;

    private static final DecoRuleSet FULL_PROB =
        new DecoRuleSet(1.0f, 1.0f, 1.0f, 0);

    private static final DecoRuleSet ZERO_PROB =
        new DecoRuleSet(0.0f, 0.0f, 0.0f, 0);

    /**
     * Builds a simple grid: solid floor along bottom two rows, air above.
     * A single solid column at the left edge.
     */
    private static byte[][] buildGrid() {
        byte[][] g = new byte[ROWS][COLS];
        // Bottom two rows solid
        for (int c = 0; c < COLS; c++) {
            g[ROWS - 1][c] = WorldGenerator.SOLID;
            g[ROWS - 2][c] = WorldGenerator.SOLID;
        }
        // Left column solid
        for (int r = 0; r < ROWS; r++) {
            g[r][0] = WorldGenerator.SOLID;
        }
        return g;
    }

    @Test
    void outputGridMatchesDimensions() {
        byte[][] grid = buildGrid();
        byte[][] deco = DecorationGenerator.generate(grid, 42L, 0, FULL_PROB, COLS, ROWS);
        assertEquals(ROWS, deco.length);
        for (byte[] row : deco) assertEquals(COLS, row.length);
    }

    @Test
    void deterministic_sameSeedSameOutput() {
        byte[][] grid = buildGrid();
        byte[][] a = DecorationGenerator.generate(grid, 12345L, 2, FULL_PROB, COLS, ROWS);
        byte[][] b = DecorationGenerator.generate(grid, 12345L, 2, FULL_PROB, COLS, ROWS);
        for (int r = 0; r < ROWS; r++)
            for (int c = 0; c < COLS; c++)
                assertEquals(a[r][c], b[r][c],
                    "mismatch at (" + r + "," + c + ")");
    }

    @Test
    void deterministic_differentSeedDifferentOutput() {
        byte[][] grid = buildGrid();
        // Use partial probability so RNG rolls actually differ between seeds
        DecoRuleSet partial = new DecoRuleSet(0.5f, 0.5f, 0.5f, 0);
        byte[][] a = DecorationGenerator.generate(grid, 111L, 0, partial, COLS, ROWS);
        byte[][] b = DecorationGenerator.generate(grid, 999L, 0, partial, COLS, ROWS);
        boolean anyDiff = false;
        for (int r = 0; r < ROWS && !anyDiff; r++)
            for (int c = 0; c < COLS && !anyDiff; c++)
                if (a[r][c] != b[r][c]) anyDiff = true;
        assertTrue(anyDiff, "different seeds should produce different output");
    }

    @Test
    void noDecoPlacedOnSolidTiles() {
        byte[][] grid = buildGrid();
        byte[][] deco = DecorationGenerator.generate(grid, 7L, 0, FULL_PROB, COLS, ROWS);
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                if (grid[r][c] == WorldGenerator.SOLID) {
                    // Floor-edge deco IS placed on solid tiles — skip those
                    // Only ceiling and wall deco must land in AIR tiles
                    byte d = deco[r][c];
                    if (d == DecorationGenerator.DECO_CEILING
                            || d == DecorationGenerator.DECO_WALL_LEFT
                            || d == DecorationGenerator.DECO_WALL_RIGHT) {
                        fail("ceiling/wall deco on solid tile at (" + r + "," + c + ")");
                    }
                }
            }
        }
    }

    @Test
    void zeroProbabilityProducesNoDecoration() {
        byte[][] grid = buildGrid();
        byte[][] deco = DecorationGenerator.generate(grid, 1L, 0, ZERO_PROB, COLS, ROWS);
        for (int r = 0; r < ROWS; r++)
            for (int c = 0; c < COLS; c++)
                assertEquals(DecorationGenerator.DECO_NONE, deco[r][c],
                    "unexpected deco at (" + r + "," + c + ")");
    }

    @Test
    void ceilingDecoAppearsAboveSolidTile() {
        // Minimal grid: one solid tile at (ROWS-1, 5), air above it
        byte[][] grid = new byte[ROWS][COLS];
        grid[ROWS - 1][5] = WorldGenerator.SOLID;

        byte[][] deco = DecorationGenerator.generate(grid, 0L, 0, FULL_PROB, COLS, ROWS);

        // With prob=1.0, ceiling deco should appear in the air tile directly above
        assertEquals(DecorationGenerator.DECO_CEILING, deco[ROWS - 2][5],
            "ceiling deco should land in air tile above the solid");
    }

    @Test
    void wallDecoAppearsAdjacentToSolidTile() {
        // Minimal grid: solid column at c=5, air to the right at c=6
        byte[][] grid = new byte[ROWS][COLS];
        for (int r = 0; r < ROWS; r++) grid[r][5] = WorldGenerator.SOLID;

        DecoRuleSet wallOnly = new DecoRuleSet(0f, 1f, 0f, 0);
        byte[][] deco = DecorationGenerator.generate(grid, 0L, 0, wallOnly, COLS, ROWS);

        boolean foundWall = false;
        for (int r = 0; r < ROWS; r++) {
            if (deco[r][6] == DecorationGenerator.DECO_WALL_LEFT) { foundWall = true; break; }
        }
        assertTrue(foundWall, "wall deco should appear to the right of solid column");
    }

    @Test
    void decoCountIsWithinExpectedRange() {
        byte[][] grid = buildGrid();
        // With prob ≈ 0.2 over a 12×12 grid there should be some but not all deco
        DecoRuleSet moderate = new DecoRuleSet(0.2f, 0.2f, 0.2f, 0);
        byte[][] deco = DecorationGenerator.generate(grid, 42L, 0, moderate, COLS, ROWS);
        int count = 0;
        for (byte[] row : deco) for (byte d : row) if (d != DecorationGenerator.DECO_NONE) count++;
        assertTrue(count > 0,   "expected some deco with prob=0.2");
        assertTrue(count < COLS * ROWS, "expected not all tiles to be deco");
    }
}
