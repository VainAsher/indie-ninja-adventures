package com.indieniinja.sim;

import com.indieniinja.procgen.dungeon.DungeonPlan;
import com.indieniinja.procgen.dungeon.DungeonPlanner;
import com.indieniinja.procgen.dungeon.RoomNode;
import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.RoomType;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.room.GeneratedRoom;
import com.indieniinja.procgen.room.RoomGenerator;
import com.indieniinja.world.WorldGenerator;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class LevelLayoutProcgenTest {

    @Test
    void solidTilesHaveTileRects() {
        GeneratedRoom room = room();
        LevelLayout layout = LevelLayout.fromProcgenRoom(room, 42L);

        int solidCount = 0;
        for (int x = 0; x < GenConfig.ROOM_W; x++)
            for (int y = 0; y < GenConfig.ROOM_H; y++)
                if (room.tiles[x][y] == Tile.SOLID) solidCount++;

        // SpatialHash must contain at least as many rects as SOLID tiles
        int hashCount = layout.spatialHash
            .candidates(0, 0, GenConfig.ROOM_W * 32f, GenConfig.ROOM_H * 32f)
            .size();
        assertThat(hashCount).isGreaterThanOrEqualTo(solidCount);
    }

    @Test
    void tilePositionsUse32pxScale() {
        GeneratedRoom room = room();
        LevelLayout layout = LevelLayout.fromProcgenRoom(room, 42L);

        List<com.indieniinja.physics.TileRect> rects = layout.spatialHash
            .candidates(0, 0, GenConfig.ROOM_W * 32f, GenConfig.ROOM_H * 32f);

        assertThat(rects).isNotEmpty();
        for (com.indieniinja.physics.TileRect rect : rects) {
            assertThat(rect.x() % 32).as("x %% 32 must be 0").isEqualTo(0f);
            assertThat(rect.y() % 32).as("y %% 32 must be 0").isEqualTo(0f);
            assertThat(rect.w()).as("tile width must be 32").isEqualTo(32f);
            assertThat(rect.h()).as("tile height must be 32").isEqualTo(32f);
        }
    }

    @Test
    void waterTileUsesLiveWaterConstant() {
        GeneratedRoom room = room();

        // Find an interior AIR tile and force it to WATER for this test.
        int wx = -1, wy = -1;
        outer:
        for (int x = 10; x < GenConfig.ROOM_W - 10; x++) {
            for (int y = 10; y < GenConfig.ROOM_H - 10; y++) {
                if (room.tiles[x][y] == Tile.AIR) { wx = x; wy = y; break outer; }
            }
        }
        assertThat(wx).as("need an interior AIR tile to inject WATER").isGreaterThan(0);
        room.tiles[wx][wy] = Tile.WATER; // == WorldGenerator.WATER == 4 after realignment

        LevelLayout layout = LevelLayout.fromProcgenRoom(room, 42L);

        final float px = wx * 32f, py = wy * 32f;
        boolean found = layout.spatialHash
            .candidates(px, py, 32f, 32f)
            .stream()
            .anyMatch(r -> r.x() == px && r.y() == py
                       && r.tileType() == WorldGenerator.WATER);
        assertThat(found)
            .as("WATER tile at (%d,%d) must produce TileRect with tileType=WATER(%d)",
                wx, wy, WorldGenerator.WATER)
            .isTrue();
    }

    @Test
    void bossRoomProducesBossSpawn() {
        DungeonPlan plan = new DungeonPlanner().plan(
            new DungeonIntent("d1", "Boss Dungeon", Biome.DUNGEON, "main",
                Ability.DASH, 8, 1, true, true, true));

        RoomNode bossNode = plan.roomGraph.nodes().stream()
            .filter(n -> n.intent.type == RoomType.BOSS)
            .findFirst()
            .orElse(null);
        assertThat(bossNode).as("dungeon must contain a BOSS room").isNotNull();

        GeneratedRoom room = new RoomGenerator().generate(bossNode.intent, 99L);
        LevelLayout layout = LevelLayout.fromProcgenRoom(room, 99L);

        assertThat(layout.bossSpawn).as("BOSS room must produce a BossSpawn").isNotNull();
        assertThat(layout.bossSpawn.bossTypeWire()).isEqualTo("shadow_warden");
    }

    // -------------------------------------------------------------------------

    private static GeneratedRoom room() {
        DungeonPlan plan = new DungeonPlanner().plan(
            new DungeonIntent("d1", "Test Dungeon", Biome.DUNGEON, "main",
                Ability.DASH, 8, 1, true, true, true));
        RoomNode start = plan.roomGraph.start();
        return new RoomGenerator().generate(start.intent, 42L);
    }
}
