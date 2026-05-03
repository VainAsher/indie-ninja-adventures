package com.indieniinja.world.postprocess;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.world.SeedHierarchy;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.puzzle.Puzzle;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Stamps puzzle interactable tiles and entity markers onto the tile grid.
 *
 * <p>Tile changes:
 * <ul>
 *   <li>KEY_DOOR / LEVER_DOOR — stamps a 3-tile-wide {@code DOOR_LOCKED} row at
 *       the first interior bottleneck found from the gate direction.</li>
 * </ul>
 *
 * <p>Entity markers are returned as {@link RoomContent.PuzzleSpawn} records so
 *  the server can create the matching runtime entities (DoorEntity, LeverEntity,
 *  KeyPickup) when the zone initialises.
 *
 * <p>This layer runs after AbilityLayer and before EntityPlanner so that
 *  entity placement can exclude puzzle zones via {@link PlacementFilter}.
 */
public final class PuzzleLayer {

    private static final int TILE = PhysicsConstants.TILE_SIZE;   // 32
    private static final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;  // 128
    private static final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES; // 128

    private PuzzleLayer() {}

    /**
     * Apply all puzzles to the tile grid and return spawn descriptors.
     *
     * @param tiles    tile grid to mutate (already deep-copied by RoomPostProcessor)
     * @param puzzles  puzzles assigned to this room by PuzzlePlan
     * @param roomSeed per-room seed for deterministic placement
     * @return list of PuzzleSpawn descriptors for this room
     */
    public static List<RoomContent.PuzzleSpawn> apply(
            byte[][] tiles,
            List<Puzzle> puzzles,
            long roomSeed) {

        List<RoomContent.PuzzleSpawn> spawns = new ArrayList<>();
        if (puzzles == null || puzzles.isEmpty()) return spawns;

        long seed = SeedHierarchy.deriveFeature(roomSeed, "puzzle");
        Random rng = new Random(seed);

        for (Puzzle puzzle : puzzles) {
            switch (puzzle.type) {
                case KEY_DOOR    -> applyKeyDoor(tiles, puzzle, spawns, rng);
                case LEVER_DOOR  -> applyLeverDoor(tiles, puzzle, spawns, rng);
                case BUTTON_SEQUENCE -> applyButtonSequence(tiles, puzzle, spawns, rng);
                case ECHO_TRIGGER -> applyEchoTrigger(tiles, puzzle, spawns, rng);
                case ASYMMETRIC_ABILITY_LOCK -> applyAsymmetricAbilityLock(tiles, puzzle, spawns, rng);
                case SIMULTANEOUS_TIMING     -> applySimultaneousTiming(tiles, puzzle, spawns, rng);
                default -> { /* TIMED_PLATFORM: future use */ }
            }
        }
        return spawns;
    }

    // ── KEY_DOOR ──────────────────────────────────────────────────────────────

    /**
     * Stamps a DOOR_LOCKED tile block in the room's interior and records:
     * - A door entity marker at the DOOR_LOCKED position.
     * - A key pickup marker in the approach zone (picked up by player to unlock).
     */
    private static void applyKeyDoor(
            byte[][] tiles, Puzzle puzzle,
            List<RoomContent.PuzzleSpawn> spawns, Random rng) {

        int[] doorPos = findChokepoint(tiles, rng);
        if (doorPos == null) return;

        int doorRow = doorPos[0], doorCol = doorPos[1];

        // Stamp 3-tile-wide DOOR_LOCKED row
        stampDoor(tiles, doorRow, doorCol);

        float doorX = doorCol * TILE + TILE * 0.5f;
        float doorY = doorRow * TILE + TILE * 0.5f;

        // Door entity marker
        spawns.add(new RoomContent.PuzzleSpawn(
            puzzle.puzzleId, "door", doorX, doorY, puzzle.linkedPuzzleId));

        // Key pickup: place it 8-16 tiles in from the room centre on ground
        int keyCol = doorCol + (rng.nextBoolean() ? 1 : -1) * (8 + rng.nextInt(8));
        keyCol = Math.max(4, Math.min(COLS - 5, keyCol));
        int keyRow = findFloorBelow(tiles, keyCol);
        if (keyRow >= 0) {
            spawns.add(new RoomContent.PuzzleSpawn(
                "key_" + puzzle.puzzleId, "key",
                keyCol * TILE + TILE * 0.5f,
                keyRow * TILE,
                puzzle.puzzleId));
        }
    }

    // ── LEVER_DOOR ────────────────────────────────────────────────────────────

    private static void applyLeverDoor(
            byte[][] tiles, Puzzle puzzle,
            List<RoomContent.PuzzleSpawn> spawns, Random rng) {

        int[] doorPos = findChokepoint(tiles, rng);
        if (doorPos == null) return;

        int doorRow = doorPos[0], doorCol = doorPos[1];
        stampDoor(tiles, doorRow, doorCol);

        float doorX = doorCol * TILE + TILE * 0.5f;
        float doorY = doorRow * TILE + TILE * 0.5f;
        spawns.add(new RoomContent.PuzzleSpawn(
            puzzle.puzzleId, "door", doorX, doorY, "lever_" + puzzle.puzzleId));

        // Lever: on the opposite side of the door from the spawn
        int leverCol = (doorCol < COLS / 2)
            ? doorCol + 12 + rng.nextInt(8)
            : doorCol - 12 - rng.nextInt(8);
        leverCol = Math.max(4, Math.min(COLS - 5, leverCol));
        int leverRow = findFloorBelow(tiles, leverCol);
        if (leverRow >= 0) {
            spawns.add(new RoomContent.PuzzleSpawn(
                "lever_" + puzzle.puzzleId, "lever",
                leverCol * TILE + TILE * 0.5f,
                leverRow * TILE,
                puzzle.puzzleId));
        }
    }

    // ── BUTTON_SEQUENCE ───────────────────────────────────────────────────────

    private static void applyButtonSequence(
            byte[][] tiles, Puzzle puzzle,
            List<RoomContent.PuzzleSpawn> spawns, Random rng) {

        // 3 buttons spread across the room floor, a reward door near the right edge
        int numButtons = 3;
        int spacing    = (COLS - 16) / (numButtons + 1);
        for (int i = 0; i < numButtons; i++) {
            int col = 8 + (i + 1) * spacing + rng.nextInt(6) - 3;
            col = Math.max(4, Math.min(COLS - 5, col));
            int row = findFloorBelow(tiles, col);
            if (row >= 0) {
                spawns.add(new RoomContent.PuzzleSpawn(
                    "btn_" + i + "_" + puzzle.puzzleId, "button",
                    col * TILE + TILE * 0.5f,
                    row * TILE,
                    puzzle.puzzleId));
            }
        }

        // Reward door on right side
        int rewardCol = COLS - 10 - rng.nextInt(6);
        int rewardRow = findChokeRow(tiles, rewardCol);
        if (rewardRow >= 0) {
            stampDoor(tiles, rewardRow, rewardCol);
            spawns.add(new RoomContent.PuzzleSpawn(
                "reward_" + puzzle.puzzleId, "door",
                rewardCol * TILE + TILE * 0.5f,
                rewardRow * TILE + TILE * 0.5f,
                puzzle.puzzleId));
        }
    }

    // ── Tile helpers ──────────────────────────────────────────────────────────

    /**
     * Echo trigger puzzle slice:
     * - place an interact trigger marker in reachable floor space
     * - stamp a linked echo-gated door
     */
    private static void applyEchoTrigger(
            byte[][] tiles, Puzzle puzzle,
            List<RoomContent.PuzzleSpawn> spawns, Random rng) {

        int triggerCol = 12 + rng.nextInt(Math.max(1, COLS - 24));
        int triggerRow = findFloorBelow(tiles, triggerCol);
        if (triggerRow < 0) return;

        int doorCol = (triggerCol < COLS / 2)
            ? triggerCol + 14 + rng.nextInt(8)
            : triggerCol - 14 - rng.nextInt(8);
        doorCol = Math.max(4, Math.min(COLS - 5, doorCol));
        int doorRow = findChokeRow(tiles, doorCol);
        if (doorRow < 0) return;

        stampDoor(tiles, doorRow, doorCol);

        String triggerId = "echo_trigger_" + puzzle.puzzleId;
        String doorId = "echo_door_" + puzzle.puzzleId;
        spawns.add(new RoomContent.PuzzleSpawn(
            doorId, "door",
            doorCol * TILE + TILE * 0.5f,
            doorRow * TILE + TILE * 0.5f,
            triggerId));
        spawns.add(new RoomContent.PuzzleSpawn(
            triggerId, "echo_trigger",
            triggerCol * TILE + TILE * 0.5f,
            triggerRow * TILE,
            doorId));
    }

    // ── ASYMMETRIC_ABILITY_LOCK ───────────────────────────────────────────────

    /**
     * Asymmetric Ability Lock puzzle slice:
     * - place an auto-spawn echo marker (echo loops at this position indefinitely)
     * - stamp a door that only unlocks when the player jumps within echo proximity
     *
     * Spawn markers emitted:
     *   "aal_echo_<pid>"    type="aal_echo"    — GameSimulator spawns a looping echo here at room load
     *   "aal_door_<pid>"    type="door"        — DOOR_LOCKED, unlocked by GameSimulator proximity+jump check
     */
    private static void applyAsymmetricAbilityLock(
            byte[][] tiles, Puzzle puzzle,
            List<RoomContent.PuzzleSpawn> spawns, Random rng) {

        // Echo position: random floor spot on the left half
        int echoCol = 10 + rng.nextInt(Math.max(1, COLS / 2 - 12));
        int echoRow = findFloorBelow(tiles, echoCol);
        if (echoRow < 0) return;

        // Door position: to the right of echo, requires jump approach
        int doorCol = echoCol + 18 + rng.nextInt(10);
        doorCol = Math.min(COLS - 5, doorCol);
        int doorRow = findChokeRow(tiles, doorCol);
        if (doorRow < 0) return;

        stampDoor(tiles, doorRow, doorCol);

        String echoMarkerId = "aal_echo_" + puzzle.puzzleId;
        String doorId       = "aal_door_" + puzzle.puzzleId;
        spawns.add(new RoomContent.PuzzleSpawn(
            echoMarkerId, "aal_echo",
            echoCol * TILE + TILE * 0.5f,
            echoRow * TILE,
            doorId));
        spawns.add(new RoomContent.PuzzleSpawn(
            doorId, "door",
            doorCol * TILE + TILE * 0.5f,
            doorRow * TILE + TILE * 0.5f,
            echoMarkerId));
    }

    // ── SIMULTANEOUS_TIMING ───────────────────────────────────────────────────

    /**
     * Simultaneous Timing puzzle slice:
     * - place an interact trigger (player starts the echo replay)
     * - stamp a door that unlocks when player matches echo jump input 3 times
     *
     * Spawn markers emitted:
     *   "st_trigger_<pid>"  type="st_trigger"  — player interacts to start looping echo
     *   "st_door_<pid>"     type="door"        — DOOR_LOCKED, unlocked by 3 sync successes
     */
    private static void applySimultaneousTiming(
            byte[][] tiles, Puzzle puzzle,
            List<RoomContent.PuzzleSpawn> spawns, Random rng) {

        int triggerCol = 12 + rng.nextInt(Math.max(1, COLS / 2 - 14));
        int triggerRow = findFloorBelow(tiles, triggerCol);
        if (triggerRow < 0) return;

        int doorCol = COLS / 2 + 10 + rng.nextInt(Math.max(1, COLS / 2 - 20));
        doorCol = Math.min(COLS - 5, doorCol);
        int doorRow = findChokeRow(tiles, doorCol);
        if (doorRow < 0) return;

        stampDoor(tiles, doorRow, doorCol);

        String triggerId = "st_trigger_" + puzzle.puzzleId;
        String doorId    = "st_door_"    + puzzle.puzzleId;
        spawns.add(new RoomContent.PuzzleSpawn(
            triggerId, "st_trigger",
            triggerCol * TILE + TILE * 0.5f,
            triggerRow * TILE,
            doorId));
        spawns.add(new RoomContent.PuzzleSpawn(
            doorId, "door",
            doorCol * TILE + TILE * 0.5f,
            doorRow * TILE + TILE * 0.5f,
            triggerId));
    }

    /** Stamp a 3-tile-wide DOOR_LOCKED column at (doorRow, doorCol). */
    private static void stampDoor(byte[][] tiles, int doorRow, int doorCol) {
        for (int c = doorCol - 1; c <= doorCol + 1; c++) {
            if (c < 2 || c >= COLS - 2) continue;
            tiles[doorRow][c] = WorldGenerator.DOOR_LOCKED;
        }
    }

    /**
     * Find an interior chokepoint row for a door: the topmost position in the
     * interior column range that has a solid tile below and air above.
     * Returns {row, col} or null if none found.
     */
    private static int[] findChokepoint(byte[][] tiles, Random rng) {
        // Try 3 random interior columns; pick the lowest valid row (near floor)
        int bestRow = -1, bestCol = -1;
        for (int attempt = 0; attempt < 8; attempt++) {
            int col = 10 + rng.nextInt(COLS - 20);
            for (int row = ROWS - 8; row >= 6; row--) {
                byte below = tiles[row][col];
                byte above = tiles[row - 1][col];
                if (below == WorldGenerator.SOLID && above == WorldGenerator.AIR) {
                    if (row > bestRow) { bestRow = row; bestCol = col; }
                    break;
                }
            }
        }
        return bestRow >= 0 ? new int[]{bestRow, bestCol} : null;
    }

    /** Find the first solid row below the given column (floor scan). */
    private static int findFloorBelow(byte[][] tiles, int col) {
        for (int r = ROWS - 5; r >= 3; r--) {
            if (tiles[r][col] != WorldGenerator.AIR
                    && tiles[r - 1][col] == WorldGenerator.AIR) return r;
        }
        return -1;
    }

    /** Find a chokerow at a specific column for button reward door. */
    private static int findChokeRow(byte[][] tiles, int col) {
        return findFloorBelow(tiles, col);
    }
}
