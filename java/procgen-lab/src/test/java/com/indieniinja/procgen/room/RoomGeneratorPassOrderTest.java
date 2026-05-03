package com.indieniinja.procgen.room;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.RoomType;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;

import static org.assertj.core.api.Assertions.assertThat;

class RoomGeneratorPassOrderTest {

    @Test
    void generatesPuzzleRoomWithCorrectDimensions() {
        RoomIntent intent = new RoomIntent(
                RoomType.PUZZLE, Biome.DUNGEON, 2,
                EnumSet.of(Ability.DASH),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "trial", "cross_gap_with_dash", true);

        GeneratedRoom room = new RoomGenerator().generate(intent, 42L);

        assertThat(room.zones).isNotNull();
        assertThat(room.tiles).isNotNull();
        assertThat(room.zones.length).isEqualTo(GenConfig.ZONE_W);
        assertThat(room.zones[0].length).isEqualTo(GenConfig.ZONE_H);
        assertThat(room.tiles.length).isEqualTo(GenConfig.ROOM_W);
        assertThat(room.tiles[0].length).isEqualTo(GenConfig.ROOM_H);
    }

    @Test
    void reportLogsAllSixPasses() {
        RoomIntent intent = new RoomIntent(
                RoomType.COMBAT, Biome.CAVE, 1,
                EnumSet.noneOf(Ability.class),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "", "movement_pressure", true);

        GeneratedRoom room = new RoomGenerator().generate(intent, 1L);

        assertThat(room.report.passLog).hasSizeGreaterThanOrEqualTo(6);
    }

    @Test
    void deterministicAcrossRuns() {
        RoomIntent intent = new RoomIntent(
                RoomType.TRAVERSAL, Biome.DUNGEON, 1,
                EnumSet.noneOf(Ability.class),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "", "horizontal_intro", true);

        GeneratedRoom a = new RoomGenerator().generate(intent, 99L);
        GeneratedRoom b = new RoomGenerator().generate(intent, 99L);

        for (int x = 0; x < GenConfig.ROOM_W; x++)
            for (int y = 0; y < GenConfig.ROOM_H; y++)
                assertThat(a.tiles[x][y])
                        .as("tile [%d][%d]", x, y)
                        .isEqualTo(b.tiles[x][y]);
    }
}
