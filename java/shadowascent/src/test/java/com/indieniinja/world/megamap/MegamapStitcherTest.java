package com.indieniinja.world.megamap;

import com.indieniinja.world.WorldGraph;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class MegamapStitcherTest {
    @Test
    void stitchedMegamapIsDeterministicForSameGraph() {
        WorldGraph graph = WorldGraph.generate(12345L, 12, WorldGraph.WorldShape.BLOB);

        MegamapSnapshot first = MegamapStitcher.stitch(12345L, 12, WorldGraph.WorldShape.BLOB, graph);
        MegamapSnapshot second = MegamapStitcher.stitch(12345L, 12, WorldGraph.WorldShape.BLOB, graph);

        assertThat(first.toSnapshot()).isEqualTo(second.toSnapshot());
        assertThat(first.goldenSeedKey()).isEqualTo("schema-10-seed-12345-shape-BLOB-rooms-12");
    }

    @Test
    void stitchedMegamapExportsRoomOriginsSeamsAndMetrics() {
        WorldGraph graph = WorldGraph.generate(777L, 10, WorldGraph.WorldShape.BRANCHY);

        MegamapSnapshot snapshot = MegamapStitcher.stitch(777L, 10, WorldGraph.WorldShape.BRANCHY, graph);

        assertThat(snapshot.bounds().widthTiles()).isGreaterThanOrEqualTo(WorldGraph.ROOM_W);
        assertThat(snapshot.bounds().heightTiles()).isGreaterThanOrEqualTo(WorldGraph.ROOM_H);
        assertThat(snapshot.rooms()).hasSize(graph.size());
        assertThat(snapshot.rooms())
            .allSatisfy(room -> {
                assertThat(room.originX()).isGreaterThanOrEqualTo(0);
                assertThat(room.originY()).isGreaterThanOrEqualTo(0);
                assertThat(room.w()).isEqualTo(WorldGraph.ROOM_W);
                assertThat(room.h()).isEqualTo(WorldGraph.ROOM_H);
                assertThat(room.tileChecksum()).isNotBlank();
            });
        assertThat(snapshot.seams()).isNotEmpty();
        assertThat(snapshot.seams()).allSatisfy(seam -> {
            assertThat(seam.fromRoomId()).isNotEqualTo(seam.toRoomId());
            assertThat(seam.bounds().w()).isGreaterThanOrEqualTo(1);
            assertThat(seam.bounds().h()).isGreaterThanOrEqualTo(1);
        });
        assertThat(snapshot.metrics().roomCount()).isEqualTo(graph.size());
        assertThat(snapshot.metrics().stitchedTileCount())
            .isEqualTo(snapshot.bounds().widthTiles() * snapshot.bounds().heightTiles());
        assertThat(snapshot.metrics().passableTileCount()).isGreaterThan(0);
        assertThat(snapshot.metrics().solidTileCount()).isGreaterThan(0);
        assertThat(snapshot.overlayRows()).isNotEmpty();
    }
}
