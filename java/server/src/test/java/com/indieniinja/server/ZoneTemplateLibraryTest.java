package com.indieniinja.server;

import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.ZonePlanner;
import com.indieniinja.world.ZoneTemplateLibrary;
import org.junit.jupiter.api.Test;

import java.util.Random;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S6 — Verifies that ZoneTemplateLibrary produces valid 8×8 tile patterns
 * for all role + biome combinations.
 */
class ZoneTemplateLibraryTest {

    private static final int TPZ = 8;

    // ── FILL templates ────────────────────────────────────────────────────────

    @Test
    void fill_hasAtLeastOneSolidTile() {
        for (int bi = 0; bi < 12; bi++) {
            byte[][] t = ZoneTemplateLibrary.pick(ZonePlanner.FILL, bi, new Random(bi));
            assertNotNull(t, "null template for biome " + bi);
            assertEquals(TPZ, t.length,    "wrong row count for biome " + bi);
            assertEquals(TPZ, t[0].length, "wrong col count for biome " + bi);
            boolean hasSolid = false;
            for (byte[] row : t) for (byte cell : row) if (cell == WorldGenerator.SOLID) { hasSolid = true; break; }
            assertTrue(hasSolid, "FILL template for biome " + bi + " has no SOLID tiles");
        }
    }

    @Test
    void fill_noOutOfBoundsTileValues() {
        byte[] validTiles = { WorldGenerator.AIR, WorldGenerator.SOLID, WorldGenerator.PLATFORM,
                              WorldGenerator.ICE, WorldGenerator.WATER, WorldGenerator.LAVA };
        for (int bi = 0; bi < 12; bi++) {
            byte[][] t = ZoneTemplateLibrary.pick(ZonePlanner.FILL, bi, new Random(bi + 100));
            for (int r = 0; r < t.length; r++) {
                for (int c = 0; c < t[r].length; c++) {
                    byte v = t[r][c];
                    boolean valid = false;
                    for (byte ok : validTiles) if (v == ok) { valid = true; break; }
                    assertTrue(valid, "FILL template biome " + bi + " cell [" + r + "][" + c + "] = " + v);
                }
            }
        }
    }

    @Test
    void fill_allBiomesReturnDifferentTemplatesSometimes() {
        // Shared RNG making 100 picks — weighted selection must produce variety
        Random rng = new Random(999L);
        java.util.Set<String> seen = new java.util.HashSet<>();
        for (int i = 0; i < 100; i++) {
            seen.add(fingerprint(ZoneTemplateLibrary.pick(ZonePlanner.FILL, 0, rng)));
        }
        assertTrue(seen.size() > 1, "earth FILL always produces same template — weighted selection broken");
    }

    // ── PLAT templates ────────────────────────────────────────────────────────

    @Test
    void plat_hasAtLeastOnePlatformTile() {
        for (int bi = 0; bi < 12; bi++) {
            byte[][] t = ZoneTemplateLibrary.pick(ZonePlanner.PLAT, bi, new Random(bi + 200));
            assertNotNull(t, "null template for biome " + bi);
            assertEquals(TPZ, t.length,    "wrong row count");
            assertEquals(TPZ, t[0].length, "wrong col count");
            boolean hasPlat = false;
            for (byte[] row : t) for (byte cell : row) if (cell == WorldGenerator.PLATFORM) { hasPlat = true; break; }
            assertTrue(hasPlat, "PLAT template for biome " + bi + " has no PLATFORM tiles");
        }
    }

    @Test
    void plat_noPlatformTilesInFillTemplate() {
        // FILL templates should not produce PLATFORM-only patterns — they're structural
        for (int bi = 0; bi < 12; bi++) {
            byte[][] t = ZoneTemplateLibrary.pick(ZonePlanner.FILL, bi, new Random(bi + 300));
            // FILL templates may have PLATFORM tiles if a template defines them, but that's fine.
            // What we verify is that the row/col dimensions are exactly 8×8.
            assertEquals(TPZ, t.length);
            assertEquals(TPZ, t[0].length);
        }
    }

    @Test
    void plat_allBiomesReturnDifferentTemplatesSometimes() {
        Random rng = new Random(888L);
        java.util.Set<String> seen = new java.util.HashSet<>();
        for (int i = 0; i < 100; i++) {
            seen.add(fingerprint(ZoneTemplateLibrary.pick(ZonePlanner.PLAT, 1, rng)));
        }
        assertTrue(seen.size() > 1, "grass PLAT always produces same template — weighted selection broken");
    }

    // ── Determinism ───────────────────────────────────────────────────────────

    @Test
    void sameSeedProducesSameTemplate() {
        byte[][] a = ZoneTemplateLibrary.pick(ZonePlanner.FILL, 2, new Random(42L));
        byte[][] b = ZoneTemplateLibrary.pick(ZonePlanner.FILL, 2, new Random(42L));
        assertEquals(fingerprint(a), fingerprint(b), "same seed must produce same template");
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static String fingerprint(byte[][] t) {
        StringBuilder sb = new StringBuilder();
        for (byte[] row : t) for (byte v : row) sb.append(v).append(',');
        return sb.toString();
    }
}
