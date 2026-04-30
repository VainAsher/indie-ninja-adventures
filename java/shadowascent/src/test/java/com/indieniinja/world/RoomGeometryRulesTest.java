package com.indieniinja.world;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class RoomGeometryRulesTest {

    @TempDir
    Path tempDir;

    @Test
    void defaultRulesEnforceTwoTileFloorWhenNoDownNeighbor() {
        byte[][] zones = emptyZones();

        byte[][] grid = RoomGenerator.generate(zones, Set.of(), 101L, "combat", 4);

        for (int c = 0; c < 128; c++) {
            assertThat(grid[126][c]).as("floor row 126 col %d", c).isEqualTo(WorldGenerator.SOLID);
            assertThat(grid[127][c]).as("floor row 127 col %d", c).isEqualTo(WorldGenerator.SOLID);
        }
    }

    @Test
    void defaultRulesLeaveDownDoorCorridorOpenThroughFloor() {
        byte[][] zones = emptyZones();

        byte[][] grid = RoomGenerator.generate(zones, Set.of("down"), 102L, "combat", 4);

        for (int r = 126; r < 128; r++) {
            for (int c = 59; c <= 69; c++) {
                assertThat(grid[r][c])
                    .as("down door corridor row %d col %d", r, c)
                    .isEqualTo(WorldGenerator.AIR);
            }
        }
    }

    @Test
    void connectedDownEdgeKeepsFloorOutsideDoorCorridor() {
        byte[][] zones = emptyZones();

        byte[][] grid = RoomGenerator.generate(zones, Set.of("down"), 1777562291895L, "combat", 4);

        for (int r = 126; r < 128; r++) {
            for (int c = 0; c < 128; c++) {
                if (c >= 59 && c <= 69) {
                    continue;
                }
                assertThat(grid[r][c])
                    .as("down-connected floor shell row %d col %d", r, c)
                    .isEqualTo(WorldGenerator.SOLID);
            }
        }
    }

    @Test
    void loadFromJsonOverridesDefaults() throws Exception {
        Path config = tempDir.resolve("room_geometry_rules.json");
        Files.writeString(config, """
            {
              "edgeWallThickness": 2,
              "floorThickness": 3,
              "doorHalfSpan": 6,
              "horizontalDoorDepth": 5,
              "verticalDoorDepth": 4
            }
            """);

        RoomGeometryRules rules = RoomGeometryRules.load(config);

        assertThat(rules.edgeWallThickness()).isEqualTo(2);
        assertThat(rules.floorThickness()).isEqualTo(3);
        assertThat(rules.doorHalfSpan()).isEqualTo(6);
        assertThat(rules.horizontalDoorDepth()).isEqualTo(5);
        assertThat(rules.verticalDoorDepth()).isEqualTo(4);
    }

    @Test
    void missingJsonFallsBackToDefaults() {
        RoomGeometryRules rules = RoomGeometryRules.load(tempDir.resolve("missing.json"));

        assertThat(rules).isEqualTo(RoomGeometryRules.defaults());
    }

    @Test
    void enforcerNormalizesAuthoredTemplateShellBeforeDoorCarving() {
        byte[][] grid = new byte[128][128];
        for (int c = 0; c < 128; c++) {
            grid[127][c] = WorldGenerator.SOLID;
        }

        RoomGeometryEnforcer.enforce(grid, Set.of("right"), RoomGeometryRules.defaults());

        for (int c = 0; c < 128; c++) {
            assertThat(grid[126][c]).as("normalized floor row 126 col %d", c).isEqualTo(WorldGenerator.SOLID);
            assertThat(grid[127][c]).as("normalized floor row 127 col %d", c).isEqualTo(WorldGenerator.SOLID);
        }
        for (int r = 59; r <= 69; r++) {
            for (int c = 124; c < 128; c++) {
                assertThat(grid[r][c]).as("right door corridor row %d col %d", r, c).isEqualTo(WorldGenerator.AIR);
            }
        }
    }

    private static byte[][] emptyZones() {
        byte[][] zones = new byte[ZonePlanner.H][ZonePlanner.W];
        for (int r = 0; r < ZonePlanner.H; r++) {
            for (int c = 0; c < ZonePlanner.W; c++) {
                zones[r][c] = ZonePlanner.VOID;
            }
        }
        return zones;
    }
}
