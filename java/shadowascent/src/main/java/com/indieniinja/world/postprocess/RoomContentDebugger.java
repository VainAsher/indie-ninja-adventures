package com.indieniinja.world.postprocess;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.puzzle.AbilityGate;
import com.indieniinja.world.puzzle.Puzzle;
import com.indieniinja.world.puzzle.PuzzlePlan;

import java.util.List;

/**
 * Server-side debug utilities for inspecting world generation output.
 *
 * Activated by the JVM flag {@code -Dninja.debug.worldgen=true}.
 *
 * <pre>
 * ASCII map legend:
 *   # = SOLID      C = CLIMBABLE  _ = PLATFORM   ~ = WATER   ^ = LAVA   * = ICE
 *   D = DOOR_LOCKED  . = AIR
 *   E = enemy      P = pickup     Z = puzzle   B = boss
 * </pre>
 */
public final class RoomContentDebugger {

    private static final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;  // 128
    private static final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES; // 128

    /** System property key to enable debug output. */
    public static final String DEBUG_FLAG = "ninja.debug.worldgen";

    private RoomContentDebugger() {}

    /** Returns true if worldgen debug output is enabled. */
    public static boolean isEnabled() {
        return Boolean.getBoolean(DEBUG_FLAG);
    }

    // ── Map print ─────────────────────────────────────────────────────────────

    /**
     * Print a 4:1 downsampled ASCII map of the tile grid with entity overlays.
     * Writes to System.out.
     */
    public static void printMap(byte[][] grid, RoomContent content) {
        int TILE = PhysicsConstants.TILE_SIZE;
        char[][] display = new char[ROWS][COLS];

        // Fill tiles
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                display[r][c] = tileChar(grid[r][c]);
            }
        }

        // Overlay entities
        for (LevelLayout.EnemySpawn e : content.enemies)
            mark(display, e.x(), e.y(), TILE, 'E');
        for (LevelLayout.PickupSpawn p : content.pickups)
            mark(display, p.x(), p.y(), TILE, 'P');
        for (RoomContent.PuzzleSpawn z : content.puzzles)
            mark(display, z.x(), z.y(), TILE, 'Z');
        if (content.bossSpawn != null)
            mark(display, content.bossSpawn.x(), content.bossSpawn.y(), TILE, 'B');

        // Print downsampled 4:1 (every 4th row and column)
        System.out.println("=== Room Map (" + COLS + "x" + ROWS + " tiles, shown 1:4) ===");
        for (int r = 0; r < ROWS; r += 4) {
            StringBuilder sb = new StringBuilder(COLS / 4);
            for (int c = 0; c < COLS; c += 4) sb.append(display[r][c]);
            System.out.println(sb);
        }
        System.out.println("  E=enemy P=pickup Z=puzzle B=boss  (spawn at "
            + (int) content.spawnX + "," + (int) content.spawnY + ")");
    }

    private static char tileChar(byte tile) {
        return switch (tile) {
            case WorldGenerator.SOLID    -> '#';
            case WorldGenerator.PLATFORM -> '_';
            case WorldGenerator.WATER    -> '~';
            case WorldGenerator.LAVA     -> '^';
            case WorldGenerator.ICE      -> '*';
            case WorldGenerator.DOOR_LOCKED -> 'D';
            case WorldGenerator.CLIMBABLE -> 'C';
            default                      -> '.';
        };
    }

    private static void mark(char[][] display, float wx, float wy, int tile, char ch) {
        int c = (int)(wx / tile);
        int r = (int)(wy / tile);
        if (r >= 0 && r < ROWS && c >= 0 && c < COLS) display[r][c] = ch;
    }

    // ── Plan summary ──────────────────────────────────────────────────────────

    /**
     * Print a summary of the PuzzlePlan for every room in the WorldGraph.
     */
    public static void printPlan(WorldGraph graph, PuzzlePlan plan) {
        System.out.println("=== PuzzlePlan Summary ("
            + graph.size() + " rooms) ===");
        for (WorldGraph.RoomNode room : graph.allRooms()) {
            String key   = PuzzlePlan.roomKey(room.gridX, room.gridY);
            int depth    = plan.depthOf(key);
            List<Puzzle> puzzles = plan.puzzlesFor(key);

            System.out.printf("  [%2d,%2d] %-9s depth=%-2d puzzles=%d%n",
                room.gridX, room.gridY, room.type, depth, puzzles.size());

            for (String dir : room.neighborDirs()) {
                AbilityGate gate = plan.gateFor(room.gridX, room.gridY, dir);
                if (gate != null) {
                    System.out.printf("    → %-5s GATE(%s via %s)%n",
                        dir, gate.type, gate.technique);
                }
            }
            for (Puzzle p : puzzles) {
                System.out.printf("    puzzle: %s%n", p);
            }
        }
        System.out.println("  Gates total: " + plan.edgeGates.size());
    }
}
