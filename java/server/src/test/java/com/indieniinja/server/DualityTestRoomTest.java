package com.indieniinja.server;

import com.indieniinja.world.TmxRoomLoader;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.nio.file.Paths;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNoException;

/**
 * Validates the duality_test.tmx room file (P1-03A / GDD §3.3 test-room slice).
 *
 * The room provides a controlled environment for playtesting stance-driven
 * movement, noise/awareness, teleport variants, and Echo Art types.
 */
class DualityTestRoomTest {

    // Gradle test working directory is java/server; assets live in java/assets/
    private static final Path ROOM_PATH =
        Paths.get("..", "assets", "rooms", "templates", "duality_test.tmx");

    @Test
    void dualityTestRoomLoadsWithoutError() {
        assertThatNoException()
            .as("duality_test.tmx must parse without throwing")
            .isThrownBy(() -> TmxRoomLoader.load(ROOM_PATH));
    }

    @Test
    void dualityTestRoomIs128x128() throws Exception {
        byte[][] grid = TmxRoomLoader.load(ROOM_PATH);
        assertThat(grid.length).isEqualTo(128);
        assertThat(grid[0].length).isEqualTo(128);
    }

    @Test
    void dualityTestRoomHasSolidFloorRow() throws Exception {
        byte[][] grid = TmxRoomLoader.load(ROOM_PATH);
        // Row 112 should be fully solid (tile 1)
        for (int c = 0; c < 128; c++) {
            assertThat(grid[112][c])
                .as("Floor row 112, col %d should be solid", c)
                .isEqualTo((byte) 1);
        }
    }

    @Test
    void dualityTestRoomHasClimbableWall() throws Exception {
        byte[][] grid = TmxRoomLoader.load(ROOM_PATH);
        // Climbable wall (tile 8) at col 88, rows 82-112
        int climbCount = 0;
        for (int r = 0; r < 128; r++) {
            if (grid[r][88] == 8) climbCount++;
        }
        assertThat(climbCount)
            .as("Shadow-path climbable wall (col 88) should have at least 20 tiles")
            .isGreaterThanOrEqualTo(20);
    }

    @Test
    void dualityTestRoomHasOneWayPlatforms() throws Exception {
        byte[][] grid = TmxRoomLoader.load(ROOM_PATH);
        // Count platform tiles (tile 2)
        int platformCount = 0;
        for (int r = 0; r < 128; r++) {
            for (int c = 0; c < 128; c++) {
                if (grid[r][c] == 2) platformCount++;
            }
        }
        assertThat(platformCount)
            .as("Room should have one-way platforms for traversal testing")
            .isGreaterThanOrEqualTo(50);
    }

    @Test
    void dualityTestRoomHasSolidOuterWalls() throws Exception {
        byte[][] grid = TmxRoomLoader.load(ROOM_PATH);
        for (int i = 0; i < 128; i++) {
            assertThat(grid[0][i]).as("Top wall col %d", i).isEqualTo((byte) 1);
            assertThat(grid[127][i]).as("Bottom wall col %d", i).isEqualTo((byte) 1);
            assertThat(grid[i][0]).as("Left wall row %d", i).isEqualTo((byte) 1);
            assertThat(grid[i][127]).as("Right wall row %d", i).isEqualTo((byte) 1);
        }
    }
}
