package com.indieniinja.world.progression;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class WorldProgressionGeneratorTest {

    @Test
    void sameSeedProducesSameProgressionGraph() {
        WorldProgressionGraph first = WorldProgressionGenerator.generate(12345L);
        WorldProgressionGraph second = WorldProgressionGenerator.generate(12345L);

        assertThat(first.toSnapshot()).isEqualTo(second.toSnapshot());
    }

    @Test
    void generatedGraphHasCentralHubRegionsAndDungeons() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(777L);

        assertThat(graph.worldNodes()).isNotEmpty();
        assertThat(graph.regionHubs()).hasSizeGreaterThanOrEqualTo(3);
        assertThat(graph.dungeonNodes()).hasSizeGreaterThanOrEqualTo(9);
        assertThat(graph.centralHub().kind()).isEqualTo(WorldProgressionGraph.NodeKind.CENTRAL_HUB);
    }

    @Test
    void generatedGraphIsSolvableAcrossManySeeds() {
        for (long seed = 1; seed <= 250; seed++) {
            WorldProgressionGraph graph = WorldProgressionGenerator.generate(seed);

            ProgressionValidationResult result = ProgressionValidator.validate(graph);

            assertThat(result.valid()).as("seed " + seed + ": " + result.message()).isTrue();
        }
    }

    @Test
    void grantsAppearBeforeRequirementsOnCriticalPath() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(42L);

        assertThat(graph.criticalPath()).extracting(WorldProgressionGraph.ProgressionNode::id)
            .startsWith("central_hub");
        assertThat(ProgressionValidator.validate(graph).reachableNodeIds())
            .containsAll(graph.criticalPath().stream().map(WorldProgressionGraph.ProgressionNode::id).toList());
    }

    @Test
    void validatorRejectsRequiredNodeLockedBehindMissingGrant() {
        WorldProgressionGraph.ProgressionNode central = new WorldProgressionGraph.ProgressionNode(
            "central_hub",
            WorldProgressionGraph.NodeKind.CENTRAL_HUB,
            "nexus",
            java.util.List.of(),
            java.util.List.of(),
            java.util.List.of("locked_region"),
            java.util.List.of("hub"),
            "low",
            false
        );
        WorldProgressionGraph.ProgressionNode locked = new WorldProgressionGraph.ProgressionNode(
            "locked_region",
            WorldProgressionGraph.NodeKind.REGION_HUB,
            "forest",
            java.util.List.of("dash"),
            java.util.List.of(),
            java.util.List.of(),
            java.util.List.of("region_hub"),
            "low",
            false
        );
        WorldProgressionGraph graph = new WorldProgressionGraph(
            1L,
            central,
            java.util.List.of(central, locked),
            java.util.List.of(),
            java.util.List.of(),
            java.util.List.of(central, locked)
        );

        ProgressionValidationResult result = ProgressionValidator.validate(graph);

        assertThat(result.valid()).isFalse();
        assertThat(result.blockedNodeIds()).containsExactly("locked_region");
    }
}
