package com.indieniinja.world.postprocess;

import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.puzzle.PuzzlePlan;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Verifies the seam-clearance contract: rooms at section boundaries suppress
 * enemy placement so the player is never immediately engaged when crossing a
 * section transition point (LayerProcGen effect-distance principle).
 */
class EntityPlannerSeamClearanceTest {

    private static final int TILE = PhysicsConstants.TILE_SIZE;
    private static final int COLS = PhysicsConstants.ROOM_WIDTH_TILES;
    private static final int ROWS = PhysicsConstants.ROOM_HEIGHT_TILES;

    @Test
    void enemiesArePlacedInNonSeamCombatRoom() {
        byte[][] grid  = buildWalkableGrid();
        WorldGraph.RoomNode room = combatRoom(3, 3);

        List<LevelLayout.EnemySpawn> enemies = EntityPlanner.placeEnemies(
            grid, room, PuzzlePlan.empty(), 9999L, COLS * TILE * 0.5f, ROWS * TILE * 0.8f,
            false);

        assertThat(enemies).isNotEmpty();
    }

    @Test
    void seamRoomSuppressesAllEnemies() {
        byte[][] grid  = buildWalkableGrid();
        WorldGraph.RoomNode room = combatRoom(0, 0);

        List<LevelLayout.EnemySpawn> enemies = EntityPlanner.placeEnemies(
            grid, room, PuzzlePlan.empty(), 9999L, COLS * TILE * 0.5f, ROWS * TILE * 0.8f,
            true);

        assertThat(enemies).isEmpty();
    }

    @Test
    void roomPostProcessorSeamKeysSuppressEnemies() {
        byte[][] grid = buildWalkableGrid();
        WorldGraph.RoomNode room = combatRoom(2, 5);
        String seamKey = PuzzlePlan.roomKey(2, 5);
        Set<String> seamKeys = Set.of(seamKey);

        RoomContent content = RoomPostProcessor.process(
            grid, room, PuzzlePlan.empty(), 1234L, "lantern_heights", seamKeys);

        assertThat(content.enemies).isEmpty();
    }

    @Test
    void roomPostProcessorNonSeamRoomHasEnemies() {
        byte[][] grid = buildWalkableGrid();
        WorldGraph.RoomNode room = combatRoom(2, 5);
        // Pass a seam set that does NOT include this room
        Set<String> seamKeys = Set.of(PuzzlePlan.roomKey(0, 0));

        RoomContent content = RoomPostProcessor.process(
            grid, room, PuzzlePlan.empty(), 1234L, "lantern_heights", seamKeys);

        assertThat(content.enemies).isNotEmpty();
    }

    @Test
    void backwardCompatibleOverloadBehavesIdenticallyToEmptySeamSet() {
        byte[][] grid = buildWalkableGrid();
        WorldGraph.RoomNode room = combatRoom(1, 1);

        RoomContent withEmpty = RoomPostProcessor.process(
            grid, room, PuzzlePlan.empty(), 42L, "lantern_heights", Collections.emptySet());
        RoomContent compat = RoomPostProcessor.process(
            grid, room, PuzzlePlan.empty(), 42L, "lantern_heights");

        assertThat(compat.enemies).containsExactlyElementsOf(withEmpty.enemies);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static byte[][] buildWalkableGrid() {
        byte[][] grid = new byte[ROWS][COLS];
        // Solid floor at row ROWS-3, open air above
        for (int col = 0; col < COLS; col++) {
            grid[ROWS - 3][col] = WorldGenerator.SOLID;
        }
        // Solid walls on left/right columns
        for (int row = 0; row < ROWS; row++) {
            grid[row][0] = WorldGenerator.SOLID;
            grid[row][COLS - 1] = WorldGenerator.SOLID;
        }
        return grid;
    }

    private static WorldGraph.RoomNode combatRoom(int gridX, int gridY) {
        return new WorldGraph.RoomNode(
            gridX, gridY, WorldGraph.RoomType.COMBAT, 999L, 0,
            List.of("east", "west"));
    }
}
