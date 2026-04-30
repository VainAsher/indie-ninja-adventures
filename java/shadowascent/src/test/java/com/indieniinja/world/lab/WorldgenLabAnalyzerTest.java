package com.indieniinja.world.lab;

import com.indieniinja.world.WorldGraph;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class WorldgenLabAnalyzerTest {
    @Test
    void reportIsDeterministicForSameInputs() {
        WorldGraph graph = WorldGraph.generate(12345L, 12, WorldGraph.WorldShape.BLOB);

        WorldgenLabReport first = WorldgenLabAnalyzer.analyze(12345L, graph);
        WorldgenLabReport second = WorldgenLabAnalyzer.analyze(12345L, graph);

        assertThat(first.toMap()).isEqualTo(second.toMap());
    }

    @Test
    void reportFlagsConnectedEdgeShellDefects() {
        byte[][] grid = new byte[128][128];

        WorldgenLabReport.RoomLabMetrics metrics =
            WorldgenLabAnalyzer.analyzeRoomGrid("fixture", "combat", Set.of("down"), grid);

        assertThat(metrics.warnings()).contains("connected_down_edge_open_outside_door");
    }

    @Test
    void generatedRoomsHaveNoConnectedEdgeShellDefects() {
        WorldGraph graph = WorldGraph.generate(1777562291895L, 10, WorldGraph.WorldShape.BLOB);

        WorldgenLabReport report = WorldgenLabAnalyzer.analyze(1777562291895L, graph);

        assertThat(report.warningCounts().getOrDefault("connected_up_edge_open_outside_door", 0)).isZero();
        assertThat(report.warningCounts().getOrDefault("connected_down_edge_open_outside_door", 0)).isZero();
        assertThat(report.warningCounts().getOrDefault("connected_left_edge_open_outside_door", 0)).isZero();
        assertThat(report.warningCounts().getOrDefault("connected_right_edge_open_outside_door", 0)).isZero();
        assertThat(report.overallStatus()).isEqualTo("pass");
    }
}
