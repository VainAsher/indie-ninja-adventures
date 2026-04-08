package com.indieniinja.world.postprocess;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.puzzle.AbilityGate;

import java.util.Random;

/**
 * Reshapes room tile geometry at ability-gated edges.
 *
 * Each technique produces a physical constraint that requires the target ability
 * to pass.  Tile distances are derived from PhysicsConstants so gate geometry
 * automatically tracks any physics tuning.
 *
 * <pre>
 * RAISED_PLATFORM — platform elevated 10 tiles above floor, beyond single-jump reach.
 *   Single jump height: JUMP_POWER² / (2 × GRAVITY) = 14.5² / 0.8 ≈ 263 px ≈ 8.2 tiles
 *   Double jump clears ≈ 16.4 tiles; gate target = 10 tiles (reachable with double jump).
 *
 * WIDE_GAP — horizontal gap too wide for a normal jump alone.
 *   Max horizontal reach (no dash): MAX_RUN_SPEED × jump_duration ≈ 8 × 24 ≈ 6 tiles
 *   Dash adds DASH_SPEED × DASH_DURATION × TICK = 16 × 10 ≈ 5 tiles extra.
 *   Gate gap = 8-10 tiles (only crossable with dash).
 *
 * VERTICAL_SHAFT — narrow vertical shaft that requires wall-jump to ascend.
 *   Shaft width = 3-4 tiles (narrow enough for wall-jump, too wide to clear in one jump).
 *   Shaft height = 12-16 tiles.
 * </pre>
 *
 * Only modifies tiles in the passage zone for the gate direction; never
 * touches door openings at the room boundary.
 */
public final class AbilityLayer {

    private static final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;  // 128
    private static final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES; // 128

    // Physics-derived gate geometry constants
    // Single jump height ≈ JUMP_POWER² / (2 * GRAVITY) ≈ 263 px ≈ 8.2 tiles
    private static final int GATE_PLATFORM_RISE = 10; // above floor: requires double jump
    private static final int GATE_GAP_MIN = 8;         // tiles — wider than unaided jump
    private static final int GATE_GAP_MAX = 10;
    private static final int SHAFT_WIDTH_MIN = 3;
    private static final int SHAFT_WIDTH_MAX = 4;
    private static final int SHAFT_HEIGHT_MIN = 12;
    private static final int SHAFT_HEIGHT_MAX = 16;

    private AbilityLayer() {}

    /**
     * Apply the gate's physical constraint to the tile grid.
     *
     * @param grid  tile grid to mutate (in-place; already deep-copied by RoomPostProcessor)
     * @param gate  gate descriptor from PuzzlePlan
     * @param dir   direction the gate is placed in ("up","down","left","right")
     * @param seed  per-gate seed for deterministic jitter
     */
    public static void apply(byte[][] grid, AbilityGate gate, String dir, long seed) {
        switch (gate.technique) {
            case RAISED_PLATFORM -> applyRaisedPlatform(grid, dir, seed);
            case WIDE_GAP        -> applyWideGap(grid, dir, seed);
            case VERTICAL_SHAFT  -> applyVerticalShaft(grid, dir, seed);
        }
    }

    // ── RAISED_PLATFORM ───────────────────────────────────────────────────────

    /**
     * Clear the column directly above the door passage and place a platform
     * 10 tiles above the floor — requires double jump to reach.
     *
     * Applied in the inner 8 columns on the gate side so the geometry reads
     * as a wall with a high platform, not a random floating tile.
     */
    private static void applyRaisedPlatform(byte[][] grid, String dir, long seed) {
        Random rng  = new Random(seed);
        int floorR  = ROWS - 5;          // topmost solid floor row
        int targetR = floorR - GATE_PLATFORM_RISE - rng.nextInt(2);  // 10-11 tiles up
        targetR = Math.max(4, targetR);

        // Gate column: depends on direction
        int gateCol = switch (dir) {
            case "left"  -> 6 + rng.nextInt(4);          // near left door
            case "right" -> COLS - 10 + rng.nextInt(4);  // near right door
            default      -> COLS / 2 + rng.nextInt(10) - 5; // centre for up/down
        };
        gateCol = Math.max(4, Math.min(COLS - 5, gateCol));

        // Raise the platform: clear column above floor up to targetR, place platform
        for (int r = floorR - 1; r > targetR; r--) {
            if (grid[r][gateCol] != WorldGenerator.SOLID) continue; // only erase solid blocks
            grid[r][gateCol] = WorldGenerator.AIR;
        }
        // Stamp a 3-tile-wide platform at the target height
        for (int c = gateCol - 1; c <= gateCol + 1; c++) {
            if (c < 2 || c >= COLS - 2) continue;
            grid[targetR][c] = WorldGenerator.PLATFORM;
            // Clear tiles above the platform so the player can land
            for (int r = targetR - 1; r >= targetR - 3 && r >= 2; r--) {
                if (grid[r][c] == WorldGenerator.SOLID) grid[r][c] = WorldGenerator.AIR;
            }
        }
    }

    // ── WIDE_GAP ─────────────────────────────────────────────────────────────

    /**
     * Widen an existing gap (or carve a new one) in the floor/platform layer
     * so it cannot be crossed without a dash.
     *
     * The gap is placed in the travel corridor 8-10 tiles from the approach wall.
     */
    private static void applyWideGap(byte[][] grid, String dir, long seed) {
        Random rng = new Random(seed);
        int gapW = GATE_GAP_MIN + rng.nextInt(GATE_GAP_MAX - GATE_GAP_MIN + 1); // 8-10

        int gapStartCol;
        if ("left".equals(dir)) {
            gapStartCol = 8 + rng.nextInt(4);
        } else if ("right".equals(dir)) {
            gapStartCol = COLS - 14 - rng.nextInt(4);
        } else {
            gapStartCol = COLS / 2 - gapW / 2 + rng.nextInt(5) - 2;
        }
        gapStartCol = Math.max(4, Math.min(COLS - 4 - gapW, gapStartCol));

        int floorR = ROWS - 5;  // topmost floor row

        // Carve a gap through the floor row (4 tiles deep into floor)
        for (int c = gapStartCol; c < gapStartCol + gapW; c++) {
            if (c < 2 || c >= COLS - 2) continue;
            for (int r = floorR; r < floorR + 4; r++) {
                grid[r][c] = WorldGenerator.AIR;  // open the pit
            }
            // Also clear any platform above the gap
            for (int r = floorR - 1; r >= floorR - 3 && r >= 2; r--) {
                if (grid[r][c] == WorldGenerator.PLATFORM) grid[r][c] = WorldGenerator.AIR;
            }
        }
    }

    // ── VERTICAL_SHAFT ────────────────────────────────────────────────────────

    /**
     * Carve a narrow vertical shaft that can only be ascended with wall-jump.
     *
     * Width = 3-4 tiles (wall jump bounce distance = ~2-3 tiles lateral).
     * Height = 12-16 tiles.
     */
    private static void applyVerticalShaft(byte[][] grid, String dir, long seed) {
        Random rng     = new Random(seed);
        int shaftW     = SHAFT_WIDTH_MIN + rng.nextInt(SHAFT_WIDTH_MAX - SHAFT_WIDTH_MIN + 1);
        int shaftH     = SHAFT_HEIGHT_MIN + rng.nextInt(SHAFT_HEIGHT_MAX - SHAFT_HEIGHT_MIN + 1);

        int centreCol = switch (dir) {
            case "left"  -> 10 + rng.nextInt(6);
            case "right" -> COLS - 16 + rng.nextInt(6);
            default      -> COLS / 2 + rng.nextInt(8) - 4;
        };
        centreCol = Math.max(4, Math.min(COLS - 4, centreCol));

        int floorR = ROWS - 5;
        int topR   = floorR - shaftH;
        topR = Math.max(3, topR);

        int leftCol  = centreCol - shaftW / 2;
        int rightCol = leftCol + shaftW - 1;
        leftCol  = Math.max(2, leftCol);
        rightCol = Math.min(COLS - 3, rightCol);

        // Ensure solid walls on both sides of shaft, air inside
        for (int r = topR; r <= floorR; r++) {
            // Left wall solid
            if (leftCol - 1 >= 2)  grid[r][leftCol - 1] = WorldGenerator.SOLID;
            // Right wall solid
            if (rightCol + 1 < COLS - 2) grid[r][rightCol + 1] = WorldGenerator.SOLID;
            // Interior = air
            for (int c = leftCol; c <= rightCol; c++) {
                if (r == floorR) continue;  // leave floor intact
                grid[r][c] = WorldGenerator.AIR;
            }
        }

        // Place a small landing platform at the top of the shaft
        for (int c = leftCol; c <= rightCol; c++) {
            grid[topR][c] = WorldGenerator.PLATFORM;
        }
    }
}
