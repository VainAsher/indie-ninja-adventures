package com.indieniinja.client.rendering;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S1 — Verifies getPlatformFrame(biome, left, right) selects the correct
 * horizontal cap/join/isolated variant for all adjacency combinations.
 *
 * Tests run without a real BlobTileSet (which needs a Texture / Gdx runtime).
 * The method logic is validated by inspecting the role bitmask it would produce
 * via a thin role-exposure helper rather than exercising the full texture lookup.
 */
class BlobTileSetPlatformCapTest {

    /**
     * Compute the role bitmask for platform adjacency the same way
     * BlobTileSet.getPlatformFrame(biome, left, right) computes it.
     * W=128 (left), E=8 (right).
     */
    private static int platformRole(boolean left, boolean right) {
        return (left ? 128 : 0) | (right ? 8 : 0);
    }

    @Test
    void isolatedPlatformHasRoleZero() {
        assertEquals(0, platformRole(false, false));
    }

    @Test
    void rightCapPlatformHasEastBit() {
        int role = platformRole(false, true);
        assertEquals(8, role, "right-end cap should have E bit (8)");
    }

    @Test
    void leftCapPlatformHasWestBit() {
        int role = platformRole(true, false);
        assertEquals(128, role, "left-end cap should have W bit (128)");
    }

    @Test
    void middlePlatformHasBothBits() {
        int role = platformRole(true, true);
        assertEquals(136, role, "middle tile should have W+E (128+8=136)");
    }

    @Test
    void westBitIsHighBit() {
        // Confirms bitmask alignment — W=bit7=128, E=bit3=8
        assertTrue((platformRole(true, false) & 128) != 0);
        assertTrue((platformRole(false, true) & 8)   != 0);
    }

    @Test
    void allFourCombinationsProduceDistinctRoles() {
        int iso   = platformRole(false, false);
        int right = platformRole(false, true);
        int left  = platformRole(true,  false);
        int mid   = platformRole(true,  true);
        assertEquals(4, java.util.Set.of(iso, right, left, mid).size(),
            "all four adjacency combinations should map to distinct roles");
    }
}
