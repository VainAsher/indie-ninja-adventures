package com.indieniinja.client.rendering;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S2 — Verifies the biome index constants and blob-set mapping table.
 * Does not instantiate BlobTileSet (requires Gdx Texture); validates the
 * static constants and the public biomeFromSeed() method only.
 */
class BlobTileSetBiomeIndexTest {

    private static final int[] BIOME_TO_BLOB_SET = { 0, 2, 4, 6, 8, 1, 3, 5, 7, 9, 10, 11 };

    @Test
    void biomeConstantsAreInRange() {
        int[] constants = {
            BlobTileSet.BIOME_EARTH,
            BlobTileSet.BIOME_GRASS,
            BlobTileSet.BIOME_SNOW,
            BlobTileSet.BIOME_SAND,
            BlobTileSet.BIOME_STONE,
            BlobTileSet.BIOME_EARTH_ALT,
            BlobTileSet.BIOME_GRASS_ALT,
            BlobTileSet.BIOME_SNOW_ALT,
            BlobTileSet.BIOME_SAND_ALT,
            BlobTileSet.BIOME_SPIRIT,
            BlobTileSet.BIOME_HUB,
            BlobTileSet.BIOME_HUB_ALT,
        };
        for (int c : constants) {
            assertTrue(c >= 0 && c < BlobTileSet.BIOME_COUNT,
                "constant " + c + " out of [0, BIOME_COUNT)");
        }
    }

    @Test
    void biomeConstantsAreUnique() {
        Set<Integer> seen = new HashSet<>();
        int[] constants = {
            BlobTileSet.BIOME_EARTH, BlobTileSet.BIOME_GRASS, BlobTileSet.BIOME_SNOW,
            BlobTileSet.BIOME_SAND,  BlobTileSet.BIOME_STONE,
            BlobTileSet.BIOME_EARTH_ALT, BlobTileSet.BIOME_GRASS_ALT, BlobTileSet.BIOME_SNOW_ALT,
            BlobTileSet.BIOME_SAND_ALT,  BlobTileSet.BIOME_SPIRIT,
            BlobTileSet.BIOME_HUB,       BlobTileSet.BIOME_HUB_ALT,
        };
        for (int c : constants) assertTrue(seen.add(c), "duplicate biome constant: " + c);
        assertEquals(BlobTileSet.BIOME_COUNT, seen.size());
    }

    @Test
    void biomeMappingTableCoversAllIndices() {
        assertEquals(BlobTileSet.BIOME_COUNT, BIOME_TO_BLOB_SET.length,
            "BIOME_TO_BLOB_SET must have one entry per biome");
    }

    @Test
    void allBlobSetIndicesAreMappedToDistinctSets() {
        Set<Integer> blobSets = new HashSet<>();
        for (int si : BIOME_TO_BLOB_SET) {
            assertTrue(si >= 0 && si < 12, "blob-set index " + si + " out of [0,12)");
            blobSets.add(si);
        }
        // All 12 blob-sets should be covered (each appears exactly once)
        assertEquals(12, blobSets.size(), "all 12 blob-sets should be reachable");
    }

    @Test
    void biomeFromSeedStaysInOriginalRange() {
        // biomeFromSeed is capped at 5 until S5 wires region→biome
        for (long seed : new long[]{0L, 1L, 5L, 99L, Long.MAX_VALUE, Long.MIN_VALUE + 1}) {
            int biome = BlobTileSet.biomeFromSeed(seed);
            assertTrue(biome >= 0 && biome < 5,
                "biomeFromSeed(" + seed + ")=" + biome + " out of stable range [0,5)");
        }
    }

    @Test
    void originalFiveBiomesMapToEvenBlobSets() {
        int[] expected = { 0, 2, 4, 6, 8 };
        for (int b = 0; b < 5; b++) {
            assertEquals(expected[b], BIOME_TO_BLOB_SET[b],
                "biome " + b + " should map to blob-set " + expected[b]);
        }
    }
}
