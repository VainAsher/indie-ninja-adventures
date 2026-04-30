package com.indieniinja.world.layout;

import com.indieniinja.world.progression.WorldProgressionGenerator;
import com.indieniinja.world.progression.WorldProgressionGraph;
import com.indieniinja.world.sections.SectionTemplateLibrary;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class HybridLayoutPlannerTest {

    @Test
    void planIsDeterministicForSameSeedAndInputs() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(12345L);
        SectionTemplateLibrary sections = SectionTemplateLibrary.loadDefault();

        HybridLayoutPlan first = HybridLayoutPlanner.plan(12345L, graph, sections);
        HybridLayoutPlan second = HybridLayoutPlanner.plan(12345L, graph, sections);

        assertThat(first.toSnapshot()).isEqualTo(second.toSnapshot());
    }

    @Test
    void assignsSectionsToNonOverlappingGridFootprints() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(777L);
        SectionTemplateLibrary sections = SectionTemplateLibrary.loadDefault();

        HybridLayoutPlan plan = HybridLayoutPlanner.plan(777L, graph, sections);

        assertThat(plan.assignments()).isNotEmpty();
        Set<String> occupied = new HashSet<>();
        for (HybridLayoutPlan.SectionAssignment assignment : plan.assignments()) {
            assertThat(assignment.templateId()).isNotBlank();
            assertThat(assignment.w()).isGreaterThan(0);
            assertThat(assignment.h()).isGreaterThan(0);
            for (int y = assignment.y(); y < assignment.y() + assignment.h(); y++) {
                for (int x = assignment.x(); x < assignment.x() + assignment.w(); x++) {
                    assertThat(occupied.add(x + "," + y))
                        .as("overlap at %s,%s from %s", x, y, assignment.nodeId())
                        .isTrue();
                }
            }
        }
    }

    @Test
    void connectsAssignedProgressionChildren() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(42L);
        SectionTemplateLibrary sections = SectionTemplateLibrary.loadDefault();

        HybridLayoutPlan plan = HybridLayoutPlanner.plan(42L, graph, sections);

        assertThat(plan.connections()).isNotEmpty();
        assertThat(plan.connections()).allSatisfy(connection -> {
            assertThat(plan.assignmentByNodeId(connection.fromNodeId())).isPresent();
            assertThat(plan.assignmentByNodeId(connection.toNodeId())).isPresent();
        });
    }

    @Test
    void snapshotIncludesBoundsAssignmentsAndConnections() {
        WorldProgressionGraph graph = WorldProgressionGenerator.generate(99L);
        SectionTemplateLibrary sections = SectionTemplateLibrary.loadDefault();

        HybridLayoutPlan plan = HybridLayoutPlanner.plan(99L, graph, sections);

        assertThat(plan.toSnapshot()).containsKeys("bounds", "assignments", "connections");
        assertThat(plan.toSnapshot().get("assignments").toString()).contains("templateId");
    }
}
