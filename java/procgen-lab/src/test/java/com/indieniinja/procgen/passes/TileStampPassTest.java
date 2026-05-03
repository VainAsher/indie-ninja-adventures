package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.RoomType;
import com.indieniinja.procgen.model.ZoneCell;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;

class TileStampPassTest {

    @Test
    void outputIsExactly128x128() {
        ZoneCell[][] zones = new SolidFillPass().apply();
        byte[][] tiles = new TileStampPass().apply(zones);
        assertThat(tiles.length).isEqualTo(GenConfig.ROOM_W);
        assertThat(tiles[0].length).isEqualTo(GenConfig.ROOM_H);
    }

    @Test
    void allTileIdsAreLegal() {
        ZoneCell[][] zones = buildZones();
        byte[][] tiles = new TileStampPass().apply(zones);
        for (int x = 0; x < GenConfig.ROOM_W; x++) {
            for (int y = 0; y < GenConfig.ROOM_H; y++) {
                assertThat(tiles[x][y])
                        .as("tile [%d][%d]", x, y)
                        .isBetween((byte) 0, (byte) 12);
            }
        }
    }

    @Test
    void airZonesStampAllAir() {
        ZoneCell[][] zones = new SolidFillPass().apply();
        RoomIntent intent = intent(TraversalGoal.HORIZONTAL_INTRO);
        new CarvePass().apply(zones, intent, new Random(1L));
        byte[][] tiles = new TileStampPass().apply(zones);

        // Zone (8, 8) is deep interior — carve should have opened it on horizontal intent
        // Verify that a known-air zone expands to all-zero tiles
        for (int x = 0; x < GenConfig.ZONE_W; x++) {
            for (int y = 0; y < GenConfig.ZONE_H; y++) {
                if (zones[x][y].base == com.indieniinja.procgen.model.ZoneBase.AIR) {
                    int ox = x * GenConfig.ZONE_SIZE;
                    int oy = y * GenConfig.ZONE_SIZE;
                    for (int sx = 0; sx < GenConfig.ZONE_SIZE; sx++) {
                        for (int sy = 0; sy < GenConfig.ZONE_SIZE; sy++) {
                            assertThat(tiles[ox + sx][oy + sy])
                                    .as("air tile at zone[%d][%d] stamp[%d][%d]", x, y, sx, sy)
                                    .isEqualTo((byte) 0);
                        }
                    }
                    return; // one verified air zone is sufficient
                }
            }
        }
    }

    @Test
    void fullPassPipelineProducesCorrectDimensions() {
        RoomIntent intent = intent(TraversalGoal.CROSS_GAP_WITH_DASH);
        ZoneCell[][] zones = new SolidFillPass().apply();
        new CarvePass().apply(zones, intent, new Random(7L));
        new DoorPass().apply(zones, intent.connections);
        new SurfaceClassificationPass().apply(zones);
        new FillVariantPass().apply(zones, intent, new Random(7L));
        byte[][] tiles = new TileStampPass().apply(zones);
        assertThat(tiles.length).isEqualTo(128);
        assertThat(tiles[0].length).isEqualTo(128);
    }

    // -------------------------------------------------------------------------

    private static ZoneCell[][] buildZones() {
        ZoneCell[][] z = new SolidFillPass().apply();
        new CarvePass().apply(z, intent(TraversalGoal.HORIZONTAL_INTRO), new Random(1L));
        return z;
    }

    private static RoomIntent intent(String goal) {
        return new RoomIntent(RoomType.PUZZLE, Biome.DUNGEON, 1,
                EnumSet.of(Ability.DASH), EnumSet.noneOf(Direction.class),
                "", goal, true);
    }
}
