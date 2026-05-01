package com.indieniinja.world.progression;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

class AuthoredProgressionLoaderTest {

    @Test
    void loadsAct1FileWithCorrectNodesAndCriticalPath(@TempDir Path tempDir) throws Exception {
        Path progressionRoot = tempDir.resolve("progressions");
        Files.createDirectories(progressionRoot);
        Path src = Path.of("src/test/resources/progressions/test_campaign.json");
        Files.copy(src, progressionRoot.resolve("test_campaign.json"));

        System.setProperty("ninja.progressionRoot", progressionRoot.toString());
        try {
            Optional<WorldProgressionGraph> result = AuthoredProgressionLoader.load("test_campaign", 42L);

            assertThat(result).isPresent();
            WorldProgressionGraph graph = result.get();

            assertThat(graph.source()).isEqualTo("authored");
            assertThat(graph.centralHub().id()).isEqualTo("test_hub");
            assertThat(graph.centralHub().kind()).isEqualTo(WorldProgressionGraph.NodeKind.CENTRAL_HUB);

            assertThat(graph.dungeonNodes()).hasSize(2);
            assertThat(graph.dungeonNodes().stream().map(WorldProgressionGraph.ProgressionNode::id))
                    .containsExactlyInAnyOrder("dungeon_a", "dungeon_b");

            // boss_arena kind maps to DUNGEON
            assertThat(graph.dungeonNodes().stream()
                    .filter(n -> n.id().equals("dungeon_b"))
                    .findFirst().orElseThrow().kind())
                    .isEqualTo(WorldProgressionGraph.NodeKind.DUNGEON);

            assertThat(graph.criticalPath().stream().map(WorldProgressionGraph.ProgressionNode::id))
                    .containsExactly("test_hub", "dungeon_a", "dungeon_b");
        } finally {
            System.clearProperty("ninja.progressionRoot");
        }
    }

    @Test
    void returnsEmptyForUnknownCampaignId(@TempDir Path tempDir) {
        System.setProperty("ninja.progressionRoot", tempDir.toString());
        try {
            Optional<WorldProgressionGraph> result = AuthoredProgressionLoader.load("nonexistent", 1L);
            assertThat(result).isEmpty();
        } finally {
            System.clearProperty("ninja.progressionRoot");
        }
    }

    @Test
    void returnsEmptyForNullCampaignId() {
        assertThat(AuthoredProgressionLoader.load(null, 1L)).isEmpty();
    }

    @Test
    void returnsEmptyForBlankCampaignId() {
        assertThat(AuthoredProgressionLoader.load("  ", 1L)).isEmpty();
    }

    @Test
    void snapshotIncludesSourceField(@TempDir Path tempDir) throws Exception {
        Path progressionRoot = tempDir.resolve("progressions");
        Files.createDirectories(progressionRoot);
        Files.copy(
                Path.of("src/test/resources/progressions/test_campaign.json"),
                progressionRoot.resolve("test_campaign.json"));

        System.setProperty("ninja.progressionRoot", progressionRoot.toString());
        try {
            WorldProgressionGraph graph = AuthoredProgressionLoader.load("test_campaign", 99L).orElseThrow();
            assertThat(graph.toSnapshot()).containsEntry("source", "authored");
        } finally {
            System.clearProperty("ninja.progressionRoot");
        }
    }

    @Test
    void proceduralGraphHasProceduralSourceInSnapshot() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(1L);
        assertThat(graph.source()).isEqualTo("procedural");
        assertThat(graph.toSnapshot()).containsEntry("source", "procedural");
    }
}
