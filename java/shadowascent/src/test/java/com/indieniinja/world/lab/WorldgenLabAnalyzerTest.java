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

    @Test
    void generatedRoomMetricsIncludeZoneAndTileDetail() {
        WorldGraph graph = WorldGraph.generate(12345L, 4, WorldGraph.WorldShape.BLOB);

        WorldgenLabReport report = WorldgenLabAnalyzer.analyze(12345L, graph);
        WorldgenLabReport.RoomLabMetrics room = report.rooms().get(0);
        @SuppressWarnings("unchecked")
        var roomMap = (java.util.Map<String, Object>) room.toMap();

        assertThat(room.biomeIndex()).isBetween(0, 11);
        assertThat(room.neighborDirs()).isNotNull();
        assertThat(room.zoneRows()).hasSize(16);
        assertThat(room.zoneRows()).allSatisfy(row -> assertThat(row).hasSize(16));
        assertThat(room.tilePreviewRows()).hasSize(128);
        assertThat(room.tilePreviewRows()).allSatisfy(row -> assertThat(row).hasSize(128));
        assertThat(report.zoneLegend()).containsEntry("D", "door");
        assertThat(report.tileLegend()).containsEntry("#", "solid");
        assertThat(roomMap).containsKeys(
            "neighborDirs",
            "biomeIndex",
            "zoneRows",
            "tilePreviewRows"
        );
    }

    @Test
    void v2ScorePenalizesTraversalDebtWhenShellWarningsAreZero() {
        WorldgenLabAnalyzer.ScoreBreakdown scores = WorldgenLabAnalyzer.computeScores(
            0,
            new WorldgenLabAnalyzer.QualitySignals(
                3, 3,
                1, 3,
                0, 3
            )
        );

        assertThat(scores.qualityScoreV1()).isEqualTo(100);
        assertThat(scores.transitionDebtPenalty()).isEqualTo(100);
        assertThat(scores.criticalPathVarietyScore()).isEqualTo(33);
        assertThat(scores.socketCompatibilityScore()).isEqualTo(0);
        assertThat(scores.qualityScoreV2()).isLessThan(scores.qualityScoreV1());
    }

    @Test
    void scoreComputationClampsEdgeCasesIntoValidRange() {
        WorldgenLabAnalyzer.ScoreBreakdown scores = WorldgenLabAnalyzer.computeScores(
            999,
            new WorldgenLabAnalyzer.QualitySignals(
                -4, -1,
                -2, -3,
                -5, -6
            )
        );

        assertThat(scores.qualityScoreV1()).isBetween(0, 100);
        assertThat(scores.qualityScoreV2()).isBetween(0, 100);
        assertThat(scores.transitionDebtPenalty()).isBetween(0, 100);
        assertThat(scores.criticalPathVarietyScore()).isBetween(0, 100);
        assertThat(scores.socketCompatibilityScore()).isBetween(0, 100);
    }
}
