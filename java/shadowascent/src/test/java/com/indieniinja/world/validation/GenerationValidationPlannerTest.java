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

        assertThat(report.valid()).isFalse();
        assertThat(report.progressionValid()).isTrue();
        assertThat(report.reachableCriticalAnchorCount()).isGreaterThanOrEqualTo(1);
        assertThat(report.issues()).extracting(GenerationValidationReport.Issue::kind)
            .contains("critical_path_transition_debt");
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

    @Test
    void optionalTransitionDebtDoesNotInvalidateReport() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        HybridLayoutPlan layout = new HybridLayoutPlan(
            1L,
            new HybridLayoutPlan.Bounds(0, 0, 0, 0),
            List.of(),
            List.of()
        );
        SocketAnchorPlan socketAnchorPlan = new SocketAnchorPlan(
            1L,
            List.of(new SocketAnchorPlan.ConnectionContract(
                "region_a_entry",
                "region_a_treasure",
                new SocketAnchorPlan.SocketContract("east_mid_jump", "east", "mid", List.of("jump"), 3, 3, 6),
                new SocketAnchorPlan.SocketContract("west_low_walk", "west", "low", List.of("walk"), 4, 4, 4),
                "needs_transition",
                "optional_progression_edge",
                false,
                "none"
            )),
            List.of()
        );

        GenerationValidationReport report = GenerationValidationPlanner.validate(graph, layout, socketAnchorPlan);

        assertThat(report.valid()).isTrue();
        assertThat(report.issues()).extracting(GenerationValidationReport.Issue::kind)
            .contains("optional_transition_debt");
        assertThat(report.issues()).extracting(GenerationValidationReport.Issue::severity)
            .contains("warning");
    }
}
