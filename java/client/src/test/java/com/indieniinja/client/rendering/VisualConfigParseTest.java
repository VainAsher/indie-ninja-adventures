package com.indieniinja.client.rendering;

import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S0 — asserts that all three visual config JSONs parse without exception
 * and that required fields are present and consistent with BlobTileSet constants.
 */
class VisualConfigParseTest {

    private static Path visualDir;

    @BeforeAll
    static void locateAssets() {
        // Tests run from java/client/ — assets are two levels up in the repo root.
        Path candidate = Paths.get("../../assets/visual").toAbsolutePath().normalize();
        if (!Files.isDirectory(candidate)) {
            // Fallback: walk up from CWD looking for assets/visual
            Path cwd = Paths.get("").toAbsolutePath();
            while (cwd != null && !Files.isDirectory(cwd.resolve("assets/visual"))) {
                cwd = cwd.getParent();
            }
            candidate = cwd != null ? cwd.resolve("assets/visual") : candidate;
        }
        visualDir = candidate;
    }

    private JsonValue parse(String filename) throws IOException {
        Path file = visualDir.resolve(filename);
        assertTrue(Files.exists(file), "Missing: " + file);
        String json = Files.readString(file);
        return new JsonReader().parse(json);
    }

    // ── biomes.json ───────────────────────────────────────────────────────────

    @Test
    void biomesJsonParsesWithoutException() throws IOException {
        assertNotNull(parse("biomes.json"));
    }

    @Test
    void biomesJsonHasRequiredFields() throws IOException {
        JsonValue root = parse("biomes.json");
        JsonValue biomes = root.get("biomes");
        assertNotNull(biomes, "biomes array missing");
        assertTrue(biomes.size > 0, "biomes array is empty");

        Set<String> knownBiomeIds = Set.of("earth","grass","snow","sand","stone","spirit","hub");
        for (JsonValue biome : biomes) {
            String id = biome.getString("id", null);
            assertNotNull(id, "biome entry missing 'id'");
            assertTrue(knownBiomeIds.contains(id), "unknown biome id: " + id);

            assertNotNull(biome.get("blobSetIndex"), "'" + id + "' missing blobSetIndex");
            assertNotNull(biome.getString("parallaxSet", null), "'" + id + "' missing parallaxSet");
            assertNotNull(biome.getString("decoRuleSet", null), "'" + id + "' missing decoRuleSet");
            assertNotNull(biome.get("zoneTemplateWeights"), "'" + id + "' missing zoneTemplateWeights");

            JsonValue weights = biome.get("zoneTemplateWeights");
            assertNotNull(weights.get("fill"), "'" + id + "' zoneTemplateWeights missing 'fill'");
            assertNotNull(weights.get("plat"), "'" + id + "' zoneTemplateWeights missing 'plat'");
        }
    }

    @Test
    void biomesJsonBlobSetIndicesMatchKnownConstants() throws IOException {
        JsonValue root = parse("biomes.json");
        // Known mapping from BlobTileSet: earth=0, grass=1, snow=2, sand=3, stone=4
        java.util.Map<String,Integer> expectedBlobSet = java.util.Map.of(
            "earth", 0, "grass", 1, "snow", 2, "sand", 3, "stone", 4
        );
        for (JsonValue biome : root.get("biomes")) {
            String id = biome.getString("id", "");
            if (expectedBlobSet.containsKey(id)) {
                assertEquals(
                    (int) expectedBlobSet.get(id),
                    biome.getInt("blobSetIndex"),
                    "blobSetIndex mismatch for biome '" + id + "'"
                );
            }
        }
    }

    // ── parallax.json ─────────────────────────────────────────────────────────

    @Test
    void parallaxJsonParsesWithoutException() throws IOException {
        assertNotNull(parse("parallax.json"));
    }

    @Test
    void parallaxJsonHasRequiredLayerFields() throws IOException {
        JsonValue root = parse("parallax.json");
        JsonValue sets = root.get("sets");
        assertNotNull(sets, "parallax 'sets' block missing");
        assertTrue(sets.size > 0);

        String[] layers = {"far", "mid", "near"};
        String[] requiredFields = {"texturePath", "scrollX", "scrollY"};

        for (JsonValue set : sets) {
            String setName = set.name();
            for (String layer : layers) {
                JsonValue layerNode = set.get(layer);
                assertNotNull(layerNode, "parallax set '" + setName + "' missing layer '" + layer + "'");
                for (String field : requiredFields) {
                    assertNotNull(layerNode.get(field),
                        "parallax '" + setName + "." + layer + "' missing '" + field + "'");
                }
                // Scroll factors must be in (0,1]
                float scrollX = layerNode.getFloat("scrollX", 0f);
                assertTrue(scrollX > 0f && scrollX <= 1f,
                    "scrollX out of range for '" + setName + "." + layer + "': " + scrollX);
            }
        }
    }

    // ── deco_rules.json ───────────────────────────────────────────────────────

    @Test
    void decoRulesJsonParsesWithoutException() throws IOException {
        assertNotNull(parse("deco_rules.json"));
    }

    @Test
    void decoRulesJsonHasRequiredProbabilityFields() throws IOException {
        JsonValue root = parse("deco_rules.json");
        JsonValue sets = root.get("sets");
        assertNotNull(sets, "deco_rules 'sets' block missing");
        assertTrue(sets.size > 0);

        String[] probFields = {"ceilingProb", "wallProb", "floorEdgeProb"};

        for (JsonValue set : sets) {
            String setName = set.name();
            for (String field : probFields) {
                assertNotNull(set.get(field),
                    "deco_rules set '" + setName + "' missing '" + field + "'");
                float prob = set.getFloat(field, -1f);
                assertTrue(prob >= 0f && prob <= 1f,
                    field + " out of [0,1] for '" + setName + "': " + prob);
            }
            assertNotNull(set.get("tileOffset"),
                "deco_rules set '" + setName + "' missing 'tileOffset'");
        }
    }

    @Test
    void allThreeConfigsHaveMatchingBiomeCoverage() throws IOException {
        JsonValue biomes   = parse("biomes.json").get("biomes");
        JsonValue parallax = parse("parallax.json").get("sets");
        JsonValue decoSets = parse("deco_rules.json").get("sets");

        for (JsonValue biome : biomes) {
            String parallaxSet = biome.getString("parallaxSet", null);
            String decoSet     = biome.getString("decoRuleSet", null);
            assertNotNull(parallax.get(parallaxSet),
                "parallax.json missing set '" + parallaxSet + "' referenced by biome '" + biome.getString("id","?") + "'");
            assertNotNull(decoSets.get(decoSet),
                "deco_rules.json missing set '" + decoSet + "' referenced by biome '" + biome.getString("id","?") + "'");
        }
    }
}
