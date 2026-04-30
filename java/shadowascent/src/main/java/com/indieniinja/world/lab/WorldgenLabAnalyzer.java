package com.indieniinja.world.lab;

import com.indieniinja.world.RoomGeometryRules;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;

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

    private WorldgenLabAnalyzer() {}

    public static WorldgenLabReport analyze(long worldSeed, WorldGraph graph) {
        Map<String, Integer> typeCounts = new LinkedHashMap<>();
        Map<String, Integer> warningCounts = new LinkedHashMap<>();
        List<WorldgenLabReport.RoomLabMetrics> rooms = graph.allRooms().stream()
            .sorted(Comparator
                .comparingInt((WorldGraph.RoomNode room) -> room.gridY)
                .thenComparingInt(room -> room.gridX))
            .map(room -> analyzeRoom(room, typeCounts, warningCounts))
            .toList();

        int warningTotal = warningCounts.values().stream().mapToInt(Integer::intValue).sum();
        int qualityScore = Math.max(0, 100 - warningTotal * 10);
        String overallStatus = warningTotal == 0 ? "pass" : "fail";
        return new WorldgenLabReport(
            worldSeed,
            overallStatus,
            qualityScore,
            rooms.size(),
            typeCounts,
            warningCounts,
            rooms
        );
    }

    private static WorldgenLabReport.RoomLabMetrics analyzeRoom(
            WorldGraph.RoomNode room,
            Map<String, Integer> typeCounts,
            Map<String, Integer> warningCounts) {
        Set<String> dirs = new TreeSet<>(room.neighborDirs());
        String roomType = room.type.id();
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
            analyzeRoomGrid(room.gridX + "," + room.gridY, roomType, dirs, grid);
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
        TileCounts counts = countTiles(grid);
        List<String> warnings = edgeShellWarnings(grid, new TreeSet<>(neighborDirs));
        return new WorldgenLabReport.RoomLabMetrics(
            roomKey,
            roomType,
            counts.solidTiles(),
            counts.platformTiles(),
            counts.airTiles(),
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

    private record TileCounts(int solidTiles, int platformTiles, int airTiles) {}
}
