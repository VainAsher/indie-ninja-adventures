package com.indieniinja.world.lab;

import com.indieniinja.world.RoomGeometryRules;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.ZonePlanner;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

public final class WorldgenLabAnalyzer {
    private static final RoomGeometryRules RULES = RoomGeometryRules.loadDefault();
    private static final Map<String, String> ZONE_LEGEND = zoneLegend();
    private static final Map<String, String> TILE_LEGEND = tileLegend();

    private WorldgenLabAnalyzer() {}

    public static WorldgenLabReport analyze(long worldSeed, WorldGraph graph) {
        return analyze(worldSeed, graph, QualitySignals.empty());
    }

    public static WorldgenLabReport analyze(
            long worldSeed,
            WorldGraph graph,
            QualitySignals qualitySignals) {
        Map<String, Integer> typeCounts = new LinkedHashMap<>();
        Map<String, Integer> warningCounts = new LinkedHashMap<>();
        List<WorldgenLabReport.RoomLabMetrics> rooms = graph.allRooms().stream()
            .sorted(Comparator
                .comparingInt((WorldGraph.RoomNode room) -> room.gridY)
                .thenComparingInt(room -> room.gridX))
            .map(room -> analyzeRoom(room, typeCounts, warningCounts))
            .toList();

        int warningTotal = warningCounts.values().stream().mapToInt(Integer::intValue).sum();
        ScoreBreakdown scores = computeScores(warningTotal, qualitySignals);
        String overallStatus = warningTotal == 0 && scores.transitionDebtPenalty() == 0 ? "pass" : "fail";
        return new WorldgenLabReport(
            worldSeed,
            overallStatus,
            scores.qualityScoreV2(),
            scores.qualityScoreV1(),
            scores.qualityScoreV2(),
            scores.transitionDebtPenalty(),
            scores.criticalPathVarietyScore(),
            scores.socketCompatibilityScore(),
            rooms.size(),
            ZONE_LEGEND,
            TILE_LEGEND,
            typeCounts,
            warningCounts,
            rooms
        );
    }

    static ScoreBreakdown computeScores(int warningTotal, QualitySignals rawSignals) {
        QualitySignals signals = rawSignals != null ? rawSignals.normalized() : QualitySignals.empty();
        int qualityScoreV1 = clampScore(100 - Math.max(0, warningTotal) * 10);
        int transitionDebtPenalty = percentage(
            signals.mandatoryTransitionDebtCount(),
            signals.mandatoryEdgeCount(),
            0
        );
        int criticalPathVarietyScore = percentage(
            signals.criticalPathUniqueTemplateCount(),
            signals.criticalPathTemplateCount(),
            100
        );
        int socketCompatibilityScore = percentage(
            signals.matchedSocketContracts(),
            signals.totalSocketContracts(),
            100
        );
        int qualityScoreV2 = clampScore((int) Math.round(
            qualityScoreV1 * 0.40
                + (100 - transitionDebtPenalty) * 0.30
                + criticalPathVarietyScore * 0.15
                + socketCompatibilityScore * 0.15
        ));
        return new ScoreBreakdown(
            qualityScoreV1,
            qualityScoreV2,
            transitionDebtPenalty,
            criticalPathVarietyScore,
            socketCompatibilityScore
        );
    }

    private static WorldgenLabReport.RoomLabMetrics analyzeRoom(
            WorldGraph.RoomNode room,
            Map<String, Integer> typeCounts,
            Map<String, Integer> warningCounts) {
        Set<String> dirs = new TreeSet<>(room.neighborDirs());
        String roomType = room.type.id();
        byte[][] zones = ZonePlanner.plan(room.seed, roomType, dirs);
        byte[][] grid = WorldGenerator.generate(
            room.seed,
            WorldGraph.ROOM_W,
            WorldGraph.ROOM_H,
            dirs,
            roomType,
            room.biomeIndex
        );
        typeCounts.merge(roomType, 1, Integer::sum);
        WorldgenLabReport.RoomLabMetrics metrics =
            analyzeRoomGrid(room.gridX + "," + room.gridY, roomType, dirs, room.biomeIndex, zones, grid);
        for (String warning : metrics.warnings()) {
            warningCounts.merge(warning, 1, Integer::sum);
        }
        return metrics;
    }

    public static WorldgenLabReport.RoomLabMetrics analyzeRoomGrid(
            String roomKey,
            String roomType,
            Collection<String> neighborDirs,
            byte[][] grid) {
        return analyzeRoomGrid(roomKey, roomType, neighborDirs, -1, new byte[0][0], grid);
    }

    public static WorldgenLabReport.RoomLabMetrics analyzeRoomGrid(
            String roomKey,
            String roomType,
            Collection<String> neighborDirs,
            int biomeIndex,
            byte[][] zones,
            byte[][] grid) {
        TileCounts counts = countTiles(grid);
        Set<String> dirs = new TreeSet<>(neighborDirs);
        List<String> warnings = edgeShellWarnings(grid, dirs);
        return new WorldgenLabReport.RoomLabMetrics(
            roomKey,
            roomType,
            new ArrayList<>(dirs),
            biomeIndex,
            counts.solidTiles(),
            counts.platformTiles(),
            counts.airTiles(),
            encodeZoneRows(zones),
            encodeTileRows(grid),
            warnings
        );
    }

    private static TileCounts countTiles(byte[][] grid) {
        int solid = 0;
        int platform = 0;
        int air = 0;
        if (grid == null) {
            return new TileCounts(0, 0, 0);
        }
        for (byte[] row : grid) {
            if (row == null) continue;
            for (byte tile : row) {
                if (tile == WorldGenerator.PLATFORM) {
                    platform++;
                } else if (isSolidLike(tile)) {
                    solid++;
                } else {
                    air++;
                }
            }
        }
        return new TileCounts(solid, platform, air);
    }

    private static List<String> edgeShellWarnings(byte[][] grid, Set<String> neighborDirs) {
        List<String> warnings = new ArrayList<>();
        if (grid == null || grid.length == 0 || grid[0].length == 0) {
            warnings.add("room_grid_empty");
            return warnings;
        }

        for (String direction : neighborDirs) {
            if (hasConnectedEdgeGapOutsideDoor(grid, direction)) {
                warnings.add("connected_" + direction + "_edge_open_outside_door");
            }
        }
        return warnings;
    }

    private static boolean hasConnectedEdgeGapOutsideDoor(byte[][] grid, String direction) {
        int rows = grid.length;
        int cols = grid[0].length;
        int midC = cols / 2;
        int midR = rows / 2;
        int half = RULES.doorHalfSpan();
        int edge = Math.min(RULES.edgeWallThickness(), Math.min(rows, cols));
        int floor = Math.min(RULES.floorThickness(), rows);

        return switch (direction) {
            case "up" -> hasHorizontalGapOutsideDoor(grid, 0, edge, midC, half);
            case "down" -> hasHorizontalGapOutsideDoor(grid, rows - floor, rows, midC, half);
            case "left" -> hasVerticalGapOutsideDoor(grid, 0, edge, midR, half);
            case "right" -> hasVerticalGapOutsideDoor(grid, cols - edge, cols, midR, half);
            default -> false;
        };
    }

    private static boolean hasHorizontalGapOutsideDoor(
            byte[][] grid,
            int rowStart,
            int rowEnd,
            int doorCenter,
            int doorHalf) {
        int cols = grid[0].length;
        for (int row = rowStart; row < rowEnd; row++) {
            for (int col = 0; col < cols; col++) {
                if (col >= doorCenter - doorHalf && col <= doorCenter + doorHalf) continue;
                if (!isSolidLike(grid[row][col])) return true;
            }
        }
        return false;
    }

    private static boolean hasVerticalGapOutsideDoor(
            byte[][] grid,
            int colStart,
            int colEnd,
            int doorCenter,
            int doorHalf) {
        for (int row = 0; row < grid.length; row++) {
            if (row >= doorCenter - doorHalf && row <= doorCenter + doorHalf) continue;
            for (int col = colStart; col < colEnd; col++) {
                if (!isSolidLike(grid[row][col])) return true;
            }
        }
        return false;
    }

    private static boolean isSolidLike(byte tile) {
        return tile == WorldGenerator.SOLID
            || tile == WorldGenerator.ICE
            || tile == WorldGenerator.LAVA
            || tile == WorldGenerator.DOOR_LOCKED
            || tile == WorldGenerator.CLIMBABLE;
    }

    private static List<String> encodeZoneRows(byte[][] zones) {
        List<String> rows = new ArrayList<>();
        if (zones == null) return rows;
        for (byte[] row : zones) {
            StringBuilder out = new StringBuilder();
            if (row != null) {
                for (byte zone : row) {
                    out.append(zoneSymbol(zone));
                }
            }
            rows.add(out.toString());
        }
        return rows;
    }

    private static List<String> encodeTileRows(byte[][] grid) {
        List<String> rows = new ArrayList<>();
        if (grid == null) return rows;
        for (byte[] row : grid) {
            StringBuilder out = new StringBuilder();
            if (row != null) {
                for (byte tile : row) {
                    out.append(tileSymbol(tile));
                }
            }
            rows.add(out.toString());
        }
        return rows;
    }

    private static char zoneSymbol(byte zone) {
        return switch (zone) {
            case ZonePlanner.DECOR -> '?';
            case ZonePlanner.WALK -> '.';
            case ZonePlanner.FILL -> '#';
            case ZonePlanner.PLAT -> '=';
            case ZonePlanner.DOOR -> 'D';
            case ZonePlanner.VOID -> ' ';
            case ZonePlanner.SAVE -> 'V';
            case ZonePlanner.SHOP -> '$';
            case ZonePlanner.LOOT -> 'T';
            case ZonePlanner.CHUTE -> 'v';
            case ZonePlanner.CLIMB -> 'C';
            case ZonePlanner.CONN -> '+';
            case ZonePlanner.LAVA -> '^';
            case ZonePlanner.ICE -> 'i';
            case ZonePlanner.WATER -> '~';
            default -> '!';
        };
    }

    private static char tileSymbol(byte tile) {
        return switch (tile) {
            case WorldGenerator.AIR -> '.';
            case WorldGenerator.SOLID -> '#';
            case WorldGenerator.PLATFORM -> '=';
            case WorldGenerator.ICE -> 'i';
            case WorldGenerator.WATER -> '~';
            case WorldGenerator.LAVA -> '^';
            case WorldGenerator.DOOR_LOCKED -> 'L';
            case WorldGenerator.GAS -> 'g';
            case WorldGenerator.CLIMBABLE -> 'c';
            default -> '!';
        };
    }

    private static Map<String, String> zoneLegend() {
        Map<String, String> out = new LinkedHashMap<>();
        out.put("?", "decor");
        out.put(".", "walk");
        out.put("#", "fill");
        out.put("=", "platform");
        out.put("D", "door");
        out.put(" ", "void");
        out.put("V", "save");
        out.put("$", "shop");
        out.put("T", "loot");
        out.put("v", "chute");
        out.put("C", "climb");
        out.put("+", "connector");
        out.put("^", "lava");
        out.put("i", "ice");
        out.put("~", "water");
        return out;
    }

    private static Map<String, String> tileLegend() {
        Map<String, String> out = new LinkedHashMap<>();
        out.put(".", "air");
        out.put("#", "solid");
        out.put("=", "platform");
        out.put("i", "ice");
        out.put("~", "water");
        out.put("^", "lava");
        out.put("L", "locked_door");
        out.put("g", "gas");
        out.put("c", "climbable");
        return out;
    }

    private static int percentage(int numerator, int denominator, int emptyFallback) {
        int safeNumerator = Math.max(0, numerator);
        int safeDenominator = Math.max(0, denominator);
        if (safeDenominator == 0) {
            return clampScore(emptyFallback);
        }
        double ratio = (double) Math.min(safeNumerator, safeDenominator) / safeDenominator;
        return clampScore((int) Math.round(ratio * 100.0));
    }

    private static int clampScore(int value) {
        return Math.max(0, Math.min(100, value));
    }

    public record QualitySignals(
            int mandatoryTransitionDebtCount,
            int mandatoryEdgeCount,
            int criticalPathUniqueTemplateCount,
            int criticalPathTemplateCount,
            int matchedSocketContracts,
            int totalSocketContracts) {
        public static QualitySignals empty() {
            return new QualitySignals(0, 0, 0, 0, 0, 0);
        }

        QualitySignals normalized() {
            int safeMandatoryEdgeCount = Math.max(0, mandatoryEdgeCount);
            int safeCriticalPathTemplateCount = Math.max(0, criticalPathTemplateCount);
            int safeTotalSocketContracts = Math.max(0, totalSocketContracts);
            return new QualitySignals(
                Math.max(0, mandatoryTransitionDebtCount),
                safeMandatoryEdgeCount,
                Math.max(0, criticalPathUniqueTemplateCount),
                safeCriticalPathTemplateCount,
                Math.max(0, matchedSocketContracts),
                safeTotalSocketContracts
            );
        }
    }

    record ScoreBreakdown(
            int qualityScoreV1,
            int qualityScoreV2,
            int transitionDebtPenalty,
            int criticalPathVarietyScore,
            int socketCompatibilityScore) {}

    private record TileCounts(int solidTiles, int platformTiles, int airTiles) {}
}
