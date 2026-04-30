package com.indieniinja.world.sections;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class SectionTemplateLibraryTest {

    @TempDir
    Path tempDir;

    @Test
    void loadsSectionTemplateWithEdgesSocketsAnchorsAndMutableZones() throws Exception {
        Path root = tempDir.resolve("sections");
        Files.createDirectories(root);
        writeSection(root.resolve("forest_key_trial.json"), "forest_key_trial", "forest", "key_trial", 3, 2);

        SectionTemplateLibrary library = SectionTemplateLibrary.load(root);

        assertThat(library.templates()).hasSize(1);
        SectionTemplate template = library.templates().get(0);
        assertThat(template.id()).isEqualTo("forest_key_trial");
        assertThat(template.biome()).isEqualTo("forest");
        assertThat(template.kind()).isEqualTo("key_trial");
        assertThat(template.footprint().gridW()).isEqualTo(3);
        assertThat(template.footprint().gridH()).isEqualTo(2);
        assertThat(template.nodeKinds()).containsExactly("entry", "platform_trial", "reward", "shortcut");
        assertThat(template.edgeRules()).extracting(SectionTemplate.EdgeRule::from)
            .containsExactly("entry", "platform_trial", "reward");
        assertThat(template.requiredSockets()).containsExactly("west_low_walk", "east_mid_jump");
        assertThat(template.mutableZones()).extracting(SectionTemplate.MutableZone::role)
            .containsExactly("enemy_pool");
        assertThat(template.anchors()).extracting(SectionTemplate.Anchor::kind)
            .containsExactly("key_reward");
    }

    @Test
    void deterministicSelectionFiltersByBiomeAndKind() throws Exception {
        Path root = tempDir.resolve("sections");
        Files.createDirectories(root);
        writeSection(root.resolve("forest_a.json"), "forest_a", "forest", "key_trial", 2, 1);
        writeSection(root.resolve("forest_b.json"), "forest_b", "forest", "key_trial", 2, 1);
        writeSection(root.resolve("cave_a.json"), "cave_a", "cave", "key_trial", 2, 1);
        writeSection(root.resolve("forest_shop.json"), "forest_shop", "forest", "shop_loop", 1, 1);

        SectionTemplateLibrary library = SectionTemplateLibrary.load(root);

        List<String> selected = List.of(
            library.select("forest", "key_trial", 0L).orElseThrow().id(),
            library.select("forest", "key_trial", 1L).orElseThrow().id(),
            library.select("forest", "key_trial", 2L).orElseThrow().id()
        );

        assertThat(selected).containsExactly("forest_a", "forest_b", "forest_a");
        assertThat(library.select("cave", "key_trial", 0L).orElseThrow().id()).isEqualTo("cave_a");
        assertThat(library.select("forest", "boss_approach", 0L)).isEmpty();
    }

    @Test
    void snapshotIsStableAndSortedByTemplateId() throws Exception {
        Path root = tempDir.resolve("sections");
        Files.createDirectories(root);
        writeSection(root.resolve("z.json"), "z_shortcut", "hollow", "shortcut", 1, 1);
        writeSection(root.resolve("a.json"), "a_entry", "hollow", "region_entrance", 1, 1);

        SectionTemplateLibrary library = SectionTemplateLibrary.load(root);

        assertThat(library.toSnapshot()).extracting(node -> node.get("id"))
            .containsExactly("a_entry", "z_shortcut");
    }

    private static void writeSection(
            Path path, String id, String biome, String kind, int gridW, int gridH) throws Exception {
        Files.writeString(path, """
            {
              "id": "%s",
              "biome": "%s",
              "kind": "%s",
              "footprint": { "gridW": %d, "gridH": %d },
              "nodeKinds": ["entry", "platform_trial", "reward", "shortcut"],
              "edgeRules": [
                { "from": "entry", "to": "platform_trial" },
                { "from": "platform_trial", "to": "reward" },
                { "from": "reward", "to": "shortcut" }
              ],
              "requiredSockets": ["west_low_walk", "east_mid_jump"],
              "mutableZones": [
                { "x": 8, "y": 10, "w": 12, "h": 5, "role": "enemy_pool" }
              ],
              "anchors": [
                {
                  "id": "reward_anchor",
                  "kind": "key_reward",
                  "phase": "global",
                  "localBounds": { "x": 42, "y": 12, "w": 3, "h": 2 },
                  "tags": ["critical", "visible"],
                  "weight": 1.0,
                  "quotaGroup": "critical_rewards",
                  "minDistance": 0,
                  "requires": [],
                  "forbids": []
                }
              ]
            }
            """.formatted(id, biome, kind, gridW, gridH));
    }
}
