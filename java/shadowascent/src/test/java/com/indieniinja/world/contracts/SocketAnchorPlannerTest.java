package com.indieniinja.world.contracts;

import com.indieniinja.world.layout.HybridLayoutPlan;
import com.indieniinja.world.layout.HybridLayoutPlanner;
import com.indieniinja.world.progression.WorldProgressionGenerator;
import com.indieniinja.world.progression.WorldProgressionGraph;
import com.indieniinja.world.sections.SectionTemplateLibrary;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class SocketAnchorPlannerTest {

    @Test
    void planIsDeterministicForSameInputs() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary templates = SectionTemplateLibrary.loadDefault();
        HybridLayoutPlan layout = HybridLayoutPlanner.plan(12345L, graph, templates);

        SocketAnchorPlan first = SocketAnchorPlanner.plan(12345L, layout, templates);
        SocketAnchorPlan second = SocketAnchorPlanner.plan(12345L, layout, templates);

        assertThat(first.toSnapshot()).isEqualTo(second.toSnapshot());
    }

    @Test
    void resolvesSectionAnchorsIntoWorldBounds() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary templates = SectionTemplateLibrary.loadDefault();
        HybridLayoutPlan layout = HybridLayoutPlanner.plan(12345L, graph, templates);

        SocketAnchorPlan plan = SocketAnchorPlanner.plan(12345L, layout, templates);

        assertThat(plan.resolvedAnchors()).isNotEmpty();
        assertThat(plan.resolvedAnchors())
            .allSatisfy(anchor -> {
                assertThat(anchor.nodeId()).isNotBlank();
                assertThat(anchor.templateId()).isNotBlank();
                assertThat(anchor.worldBounds().w()).isGreaterThan(0);
                assertThat(anchor.worldBounds().h()).isGreaterThan(0);
            });
        assertThat(plan.toSnapshot().get("resolvedAnchors").toString()).contains("worldBounds");
    }

    @Test
    void createsConnectionContractsFromRequiredSockets() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary templates = SectionTemplateLibrary.loadDefault();
        HybridLayoutPlan layout = HybridLayoutPlanner.plan(12345L, graph, templates);

        SocketAnchorPlan plan = SocketAnchorPlanner.plan(12345L, layout, templates);

        assertThat(plan.connectionContracts()).isNotEmpty();
        assertThat(plan.connectionContracts())
            .allSatisfy(contract -> {
                assertThat(contract.fromNodeId()).isNotBlank();
                assertThat(contract.toNodeId()).isNotBlank();
                assertThat(contract.fromSocket().side()).isNotBlank();
                assertThat(contract.toSocket().side()).isNotBlank();
                assertThat(contract.status()).isIn("matched", "needs_transition");
            });
    }
}
