package com.indieniinja.world;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class WorldGraphBossExitTest {

    @Test
    void bossExitDefaultsFalse() {
        WorldGraph graph = WorldGraph.generate(42L, 8, WorldGraph.WorldShape.BLOB);
        assertThat(graph.bossExit()).isFalse();
    }

    @Test
    void withBossExitReturnsCopyWithFlagTrue() {
        WorldGraph graph = WorldGraph.generate(42L, 8, WorldGraph.WorldShape.BLOB);
        WorldGraph bossGraph = graph.withBossExit();

        assertThat(bossGraph.bossExit()).isTrue();
        assertThat(graph.bossExit()).isFalse(); // original unchanged
    }

    @Test
    void withBossExitPreservesRoomsStartAndExit() {
        WorldGraph graph = WorldGraph.generate(99L, 10, WorldGraph.WorldShape.SNAKE);
        WorldGraph bossGraph = graph.withBossExit();

        assertThat(bossGraph.size()).isEqualTo(graph.size());
        assertThat(bossGraph.startRoom().gridX).isEqualTo(graph.startRoom().gridX);
        assertThat(bossGraph.startRoom().gridY).isEqualTo(graph.startRoom().gridY);
        assertThat(bossGraph.exitRoom().gridX).isEqualTo(graph.exitRoom().gridX);
        assertThat(bossGraph.exitRoom().gridY).isEqualTo(graph.exitRoom().gridY);
    }

    @Test
    void exitRoomRetainsExitTypeInBossExitGraph() {
        // bossExit is a flag on WorldGraph, not a type change on the RoomNode —
        // consumers read bossExit() to decide the wire type at layout time.
        WorldGraph bossGraph = WorldGraph.generate(7L, 8, WorldGraph.WorldShape.BLOB).withBossExit();
        assertThat(bossGraph.exitRoom().type).isEqualTo(WorldGraph.RoomType.EXIT);
    }
}
