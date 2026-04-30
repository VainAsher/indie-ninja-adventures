package com.indieniinja.world.validation;

import com.indieniinja.world.contracts.SocketAnchorPlan;
import com.indieniinja.world.contracts.SocketAnchorPlanner;
import com.indieniinja.world.layout.HybridLayoutPlan;
import com.indieniinja.world.layout.HybridLayoutPlanner;
import com.indieniinja.world.progression.WorldProgressionGenerator;
import com.indieniinja.world.progression.WorldProgressionGraph;
import com.indieniinja.world.sections.SectionTemplateLibrary;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class GenerationValidationPlannerTest {

    @Test
    void reportIsDeterministicForSameInputs() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary templates = SectionTemplateLibrary.loadDefault();
        HybridLayoutPlan layout = HybridLayoutPlanner.plan(12345L, graph, templates);
        SocketAnchorPlan socketAnchorPlan = SocketAnchorPlanner.plan(12345L, layout, templates);

        GenerationValidationReport first = GenerationValidationPlanner.validate(graph, layout, socketAnchorPlan);
        GenerationValidationReport second = GenerationValidationPlanner.validate(graph, layout, socketAnchorPlan);

        assertThat(first.toSnapshot()).isEqualTo(second.toSnapshot());
    }

    @Test
    void validGeneratedPlanIncludesProgressionAndAnchorChecks() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary templates = SectionTemplateLibrary.loadDefault();
        HybridLayoutPlan layout = HybridLayoutPlanner.plan(12345L, graph, templates);
        SocketAnchorPlan socketAnchorPlan = SocketAnchorPlanner.plan(12345L, layout, templates);

        GenerationValidationReport report = GenerationValidationPlanner.validate(graph, layout, socketAnchorPlan);

        assertThat(report.valid()).isTrue();
        assertThat(report.progressionValid()).isTrue();
        assertThat(report.reachableCriticalAnchorCount()).isGreaterThanOrEqualTo(1);
        assertThat(report.toSnapshot().get("issueCount")).isEqualTo(0);
    }

    @Test
    void missingConnectionContractCreatesBoundedRepairRecommendation() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary templates = SectionTemplateLibrary.loadDefault();
        HybridLayoutPlan layout = HybridLayoutPlanner.plan(12345L, graph, templates);
        SocketAnchorPlan emptyContracts = new SocketAnchorPlan(
            12345L,
            List.of(),
            SocketAnchorPlanner.plan(12345L, layout, templates).resolvedAnchors()
        );

        GenerationValidationReport report = GenerationValidationPlanner.validate(graph, layout, emptyContracts);

        assertThat(report.valid()).isFalse();
        assertThat(report.issues()).extracting(GenerationValidationReport.Issue::kind)
            .contains("missing_connection_contract");
        assertThat(report.repairActions()).extracting(GenerationValidationReport.RepairAction::tier)
            .contains("replace");
    }
}
