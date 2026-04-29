package com.indieniinja.world;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class RoomStructureRulesTest {

    @TempDir
    Path tempDir;

    @Test
    void loadFromJsonOverridesRoomTypeStructure() throws Exception {
        Path config = tempDir.resolve("room_structure_rules.json");
        Files.writeString(config, """
            {
              "defaultRoomType": {
                "fillMin": 1,
                "fillMax": 2,
                "lavaChance": 0.1,
                "iceChance": 0.2,
                "waterChance": 0.3,
                "decorFillChance": 0.4,
                "decorPlatformChance": 0.5,
                "decorWalkChance": 0.6,
                "perimeterDepth": 1,
                "centerClearRadiusZones": 0
              },
              "roomTypes": {
                "boss": {
                  "fillMin": 3,
                  "fillMax": 4,
                  "lavaChance": 0.35,
                  "decorFillChance": 0.18,
                  "decorPlatformChance": 0.3,
                  "decorWalkChance": 0.22,
                  "perimeterDepth": 3,
                  "centerClearRadiusZones": 2
                }
              }
            }
            """);

        RoomStructureRules rules = RoomStructureRules.load(config);
        RoomStructureRules.RoomSpec boss = rules.specFor("boss");

        assertThat(boss.fillMin()).isEqualTo(3);
        assertThat(boss.fillMax()).isEqualTo(4);
        assertThat(boss.lavaChance()).isEqualTo(0.35f);
        assertThat(boss.decorFillChance()).isEqualTo(0.18f);
        assertThat(boss.decorPlatformChance()).isEqualTo(0.3f);
        assertThat(boss.decorWalkChance()).isEqualTo(0.22f);
        assertThat(boss.perimeterDepth()).isEqualTo(3);
        assertThat(boss.centerClearRadiusZones()).isEqualTo(2);
    }

    @Test
    void missingJsonFallsBackToDefaults() {
        RoomStructureRules rules = RoomStructureRules.load(tempDir.resolve("missing.json"));

        assertThat(rules.specFor("boss").centerClearRadiusZones()).isGreaterThanOrEqualTo(1);
        assertThat(rules.specFor("unknown")).isEqualTo(rules.specFor("combat"));
    }

    @Test
    void bossPlannerKeepsConfiguredCenterArenaOpen() {
        byte[][] zones = ZonePlanner.plan(44L, "boss", Set.of("left", "right"));

        for (int y = 7; y <= 9; y++) {
            for (int x = 7; x <= 9; x++) {
                assertThat(zones[y][x])
                    .as("boss center zone %d,%d", x, y)
                    .isNotIn(ZonePlanner.FILL, ZonePlanner.LAVA, ZonePlanner.ICE, ZonePlanner.WATER, ZonePlanner.VOID);
            }
        }
    }

    @Test
    void customRulesCanDisablePerimeterThickening() {
        RoomStructureRules.RoomSpec openSpec = new RoomStructureRules.RoomSpec(
            0, 0,
            0f, 0f, 0f,
            0f, 0f, 1f,
            0,
            0
        );
        byte[][] zones = new byte[ZonePlanner.H][ZonePlanner.W];

        ZonePlanner.applyStructureRules(zones, "custom", Set.of(), java.util.List.of(), openSpec, new java.util.Random(9L));

        assertThat(zones[0][0]).isEqualTo(ZonePlanner.WALK);
        assertThat(zones[ZonePlanner.H - 1][ZonePlanner.W - 1]).isEqualTo(ZonePlanner.WALK);
    }
}
