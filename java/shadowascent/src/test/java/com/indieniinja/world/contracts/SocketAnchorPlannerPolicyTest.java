package com.indieniinja.world.contracts;

import com.indieniinja.world.layout.HybridLayoutPlan;
import com.indieniinja.world.sections.SectionTemplateLibrary;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class SocketAnchorPlannerPolicyTest {

    @TempDir
    Path tempDir;

    @Test
    void marksCriticalPathConnectionsAsMandatory() throws Exception {
        Path sections = tempDir.resolve("sections");
        Files.createDirectories(sections);
        writeSection(sections.resolve("left.json"), "left", "forest", "key_trial", "east_mid_jump");
        writeSection(sections.resolve("right.json"), "right", "forest", "key_trial", "west_low_walk");
        SectionTemplateLibrary library = SectionTemplateLibrary.load(sections);

        HybridLayoutPlan layout = new HybridLayoutPlan(
            7L,
            new HybridLayoutPlan.Bounds(0, 0, 3, 1),
            List.of(
                new HybridLayoutPlan.SectionAssignment(
                    "left_node", "left", "forest", "key_trial", "p", 0, 0, 1, 1, false),
                new HybridLayoutPlan.SectionAssignment(
                    "right_node", "right", "forest", "key_trial", "p", 2, 0, 1, 1, false)
            ),
            List.of(new HybridLayoutPlan.Connection("left_node", "right_node", "progression_edge"))
        );

        SocketAnchorPlan plan = SocketAnchorPlanner.plan(7L, layout, library);

        assertThat(plan.connectionContracts()).hasSize(1);
        SocketAnchorPlan.ConnectionContract contract = plan.connectionContracts().get(0);
        assertThat(contract.mandatory()).isTrue();
        assertThat(contract.status()).isEqualTo("needs_transition");
        assertThat(contract.transitionStrategy()).isEqualTo("none");
    }

    @Test
    void keepsOptionalBranchConnectionsLenient() throws Exception {
        Path sections = tempDir.resolve("sections");
        Files.createDirectories(sections);
        writeSection(sections.resolve("left.json"), "left", "forest", "key_trial", "east_mid_jump");
        writeSection(sections.resolve("right.json"), "right", "forest", "key_trial", "west_low_walk");
        SectionTemplateLibrary library = SectionTemplateLibrary.load(sections);

        HybridLayoutPlan layout = new HybridLayoutPlan(
            8L,
            new HybridLayoutPlan.Bounds(0, 0, 3, 1),
            List.of(
                new HybridLayoutPlan.SectionAssignment(
                    "left_node", "left", "forest", "key_trial", "p", 0, 0, 1, 1, false),
                new HybridLayoutPlan.SectionAssignment(
                    "right_node", "right", "forest", "key_trial", "p", 2, 0, 1, 1, true)
            ),
            List.of(new HybridLayoutPlan.Connection("left_node", "right_node", "progression_edge"))
        );

        SocketAnchorPlan plan = SocketAnchorPlanner.plan(8L, layout, library);

        assertThat(plan.connectionContracts()).hasSize(1);
        SocketAnchorPlan.ConnectionContract contract = plan.connectionContracts().get(0);
        assertThat(contract.mandatory()).isFalse();
        assertThat(contract.policy()).isEqualTo("optional_progression_edge");
    }

    @Test
    void strictGrammarDowngradesUnknownSideToUnknownSocket() throws Exception {
        Path sections = tempDir.resolve("sections");
        Files.createDirectories(sections);
        writeSection(sections.resolve("left.json"), "left", "forest", "key_trial", "portal_mid_jump");
        writeSection(sections.resolve("right.json"), "right", "forest", "key_trial", "west_mid_jump");
        SectionTemplateLibrary library = SectionTemplateLibrary.load(sections);

        String prior = System.getProperty("ninja.socketContractStrict");
        System.setProperty("ninja.socketContractStrict", "true");
        try {
            HybridLayoutPlan layout = new HybridLayoutPlan(
                9L,
                new HybridLayoutPlan.Bounds(0, 0, 3, 1),
                List.of(
                    new HybridLayoutPlan.SectionAssignment(
                        "left_node", "left", "forest", "key_trial", "p", 0, 0, 1, 1, false),
                    new HybridLayoutPlan.SectionAssignment(
                        "right_node", "right", "forest", "key_trial", "p", 2, 0, 1, 1, false)
                ),
                List.of(new HybridLayoutPlan.Connection("left_node", "right_node", "progression_edge"))
            );

            SocketAnchorPlan plan = SocketAnchorPlanner.plan(9L, layout, library);
            SocketAnchorPlan.ConnectionContract contract = plan.connectionContracts().get(0);
            assertThat(contract.fromSocket().side()).isEqualTo("unknown");
            assertThat(contract.status()).isEqualTo("needs_transition");
        } finally {
            if (prior == null) {
                System.clearProperty("ninja.socketContractStrict");
            } else {
                System.setProperty("ninja.socketContractStrict", prior);
            }
        }
    }

    private static void writeSection(Path path, String id, String biome, String kind, String socket)
            throws Exception {
        Files.writeString(path, """
            {
              "id": "%s",
              "biome": "%s",
              "kind": "%s",
              "footprint": { "gridW": 1, "gridH": 1 },
              "nodeKinds": ["entry", "reward"],
              "edgeRules": [{ "from": "entry", "to": "reward" }],
              "requiredSockets": ["%s"],
              "anchors": [{ "id": "a", "kind": "reward" }]
            }
            """.formatted(id, biome, kind, socket));
    }
}
