package com.indieniinja.world;

import java.util.Collection;

/**
 * Applies structural room geometry rules to tile grids.
 */
public final class RoomGeometryEnforcer {

    private RoomGeometryEnforcer() {}

    public static void enforce(byte[][] grid, Collection<String> neighborDirs, RoomGeometryRules rules) {
        addBoundaries(grid, neighborDirs, rules);
        carveDoors(grid, neighborDirs, rules);
    }

    public static void addBoundaries(
            byte[][] grid,
            Collection<String> neighborDirs,
            RoomGeometryRules rules) {
        if (grid == null || grid.length == 0 || grid[0].length == 0) return;

        int rows = grid.length;
        int cols = grid[0].length;
        int edge = Math.min(rules.edgeWallThickness(), Math.min(rows, cols));
        int floor = Math.min(rules.floorThickness(), rows);

        for (int r = 0; r < edge; r++) {
            for (int c = 0; c < cols; c++) {
                grid[r][c] = WorldGenerator.SOLID;
            }
        }

        for (int r = rows - floor; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                grid[r][c] = WorldGenerator.SOLID;
            }
        }

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < edge; c++) {
                grid[r][c] = WorldGenerator.SOLID;
            }
        }

        for (int r = 0; r < rows; r++) {
            for (int c = cols - edge; c < cols; c++) {
                grid[r][c] = WorldGenerator.SOLID;
            }
        }
    }

    public static void carveDoors(
            byte[][] grid,
            Collection<String> neighborDirs,
            RoomGeometryRules rules) {
        if (grid == null || grid.length == 0 || grid[0].length == 0) return;

        int rows = grid.length;
        int cols = grid[0].length;
        int midC = cols / 2;
        int midR = rows / 2;
        int doorHalf = rules.doorHalfSpan();
        int horizontalDepth = Math.min(rules.horizontalDoorDepth(), cols);
        int verticalDepth = Math.min(rules.verticalDoorDepth(), rows);

        for (String dir : neighborDirs) {
            switch (dir) {
                case "up" -> {
                    for (int r = 0; r < verticalDepth; r++) {
                        for (int c = midC - doorHalf; c <= midC + doorHalf; c++) {
                            if (inBounds(grid, r, c)) grid[r][c] = WorldGenerator.AIR;
                        }
                    }
                }
                case "down" -> {
                    for (int r = rows - verticalDepth; r < rows; r++) {
                        for (int c = midC - doorHalf; c <= midC + doorHalf; c++) {
                            if (inBounds(grid, r, c)) grid[r][c] = WorldGenerator.AIR;
                        }
                    }
                }
                case "left" -> {
                    for (int r = midR - doorHalf; r <= midR + doorHalf; r++) {
                        for (int c = 0; c < horizontalDepth; c++) {
                            if (inBounds(grid, r, c)) grid[r][c] = WorldGenerator.AIR;
                        }
                    }
                }
                case "right" -> {
                    for (int r = midR - doorHalf; r <= midR + doorHalf; r++) {
                        for (int c = cols - horizontalDepth; c < cols; c++) {
                            if (inBounds(grid, r, c)) grid[r][c] = WorldGenerator.AIR;
                        }
                    }
                }
                default -> {
                    // Ignore malformed directions.
                }
            }
        }
    }

    private static boolean inBounds(byte[][] grid, int row, int col) {
        return row >= 0 && row < grid.length && col >= 0 && col < grid[row].length;
    }
}
