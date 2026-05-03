package com.indieniinja.procgen.room;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.RoomType;
import com.indieniinja.procgen.passes.TraversalGoal;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;

import static org.assertj.core.api.Assertions.assertThat;

class RoomGeneratorFullPipelineTest {

    @Test
    void dashPuzzleRoomProducesValidGeneratedRoom() {
        RoomIntent intent = new RoomIntent(
                RoomType.PUZZLE, Biome.DUNGEON, 2,
                EnumSet.of(Ability.DASH),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "trial", TraversalGoal.CROSS_GAP_WITH_DASH, true);

        GeneratedRoom room = new RoomGenerator().generate(intent, 42L);

        assertThat(room.zones).isNotNull();
        assertThat(room.tiles).isNotNull();
        assertThat(room.tiles.length).isEqualTo(GenConfig.ROOM_W);
        assertThat(room.tiles[0].length).isEqualTo(GenConfig.ROOM_H);
    }

    @Test
    void reportLogsAllTenPasses() {
        RoomIntent intent = new RoomIntent(
                RoomType.COMBAT, Biome.CAVE, 1,
                EnumSet.noneOf(Ability.class),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "", TraversalGoal.MOVEMENT_PRESSURE, true);

        GeneratedRoom room = new RoomGenerator().generate(intent, 1L);

        assertThat(room.report.passLog).hasSize(10);
    }

    @Test
    void saveRoomContainsSavePointTile() {
        RoomIntent intent = new RoomIntent(
                RoomType.SAVE, Biome.DUNGEON, 1,
                EnumSet.noneOf(Ability.class),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "", TraversalGoal.REST, true);

        GeneratedRoom room = new RoomGenerator().generate(intent, 7L);

        boolean hasSave = false;
        for (int x = 0; x < GenConfig.ROOM_W && !hasSave; x++)
            for (int y = 0; y < GenConfig.ROOM_H && !hasSave; y++)
                if (room.tiles[x][y] == com.indieniinja.procgen.model.Tile.SAVE_POINT) hasSave = true;

        assertThat(hasSave).isTrue();
    }

    @Test
    void deterministicAcrossRuns() {
        RoomIntent intent = new RoomIntent(
                RoomType.TRAVERSAL, Biome.DUNGEON, 1,
                EnumSet.noneOf(Ability.class),
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                "", TraversalGoal.HORIZONTAL_INTRO, true);

        GeneratedRoom a = new RoomGenerator().generate(intent, 99L);
        GeneratedRoom b = new RoomGenerator().generate(intent, 99L);

        for (int x = 0; x < GenConfig.ROOM_W; x++)
            for (int y = 0; y < GenConfig.ROOM_H; y++)
                assertThat(a.tiles[x][y]).isEqualTo(b.tiles[x][y]);
    }
}
