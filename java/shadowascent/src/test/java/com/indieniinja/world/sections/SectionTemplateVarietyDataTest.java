package com.indieniinja.world.sections;

import org.junit.jupiter.api.Test;

import java.util.Comparator;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class SectionTemplateVarietyDataTest {

    @Test
    void actOneRequiredBiomeKindPairsHaveMinimumVariantCounts() {
        SectionTemplateLibrary library = SectionTemplateLibrary.loadDefault();

        assertThat(candidates(library, "forest", "key_trial"))
            .as("forest key_trial variants")
            .hasSizeGreaterThanOrEqualTo(3);
        assertThat(candidates(library, "lantern", "boss_approach"))
            .as("lantern boss_approach variants")
            .hasSizeGreaterThanOrEqualTo(2);
    }

    @Test
    void deterministicSelectionUsesSortedIdModulo() {
        SectionTemplateLibrary library = SectionTemplateLibrary.loadDefault();
        assertSelectionFollowsModuloRule(library, "forest", "key_trial");
        assertSelectionFollowsModuloRule(library, "lantern", "boss_approach");
    }

    private static void assertSelectionFollowsModuloRule(
            SectionTemplateLibrary library, String biome, String kind) {
        List<String> ids = candidates(library, biome, kind).stream()
            .map(SectionTemplate::id)
            .sorted()
            .toList();
        assertThat(ids).isNotEmpty();

        for (long seed = 0; seed < 20; seed++) {
            String selected = library.select(biome, kind, seed).orElseThrow().id();
            String expected = ids.get(Math.floorMod(seed, ids.size()));
            assertThat(selected)
                .as("seed=%s biome=%s kind=%s", seed, biome, kind)
                .isEqualTo(expected);
        }
    }

    private static List<SectionTemplate> candidates(
            SectionTemplateLibrary library, String biome, String kind) {
        return library.templates().stream()
            .filter(template -> template.biome().equals(biome))
            .filter(template -> template.kind().equals(kind))
            .sorted(Comparator.comparing(SectionTemplate::id))
            .toList();
    }
}
