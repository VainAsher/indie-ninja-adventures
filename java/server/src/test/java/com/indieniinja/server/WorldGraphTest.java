package com.indieniinja.server;

import com.indieniinja.sim.LevelLayout;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.WorldGraph.RoomNode;
import com.indieniinja.world.WorldGraph.RoomType;
import com.indieniinja.world.WorldGraph.WorldShape;
import com.indieniinja.world.puzzle.PuzzlePlan;
import com.indieniinja.world.puzzle.PuzzlePlanner;
import com.indieniinja.world.puzzle.PuzzleType;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.LinkedList;
import java.util.Queue;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * WorldGraph structural tests — BFS reachability, room type invariants,
 * determinism, and PuzzlePlanner soft-lock safety.
 *
 * Covers audit gaps: WORLD-1 (BFS reachability), WORLD-2 (determinism),
 * WORLD-4 (puzzle plan no soft-lock).
 */
class WorldGraphTest {

    // ── WORLD-1: all rooms reachable from start via BFS ───────────────────────

    @Test
    void allRoomsReachableFromStart() {
        // BFS from startRoom following neighborDirs must reach every room in the
        // graph. If any room is isolated the world is unsolvable.
        WorldGraph graph = WorldGraph.generate(42L, 20, WorldShape.BLOB);

        Set<String> visited = new HashSet<>();
        Queue<RoomNode> queue = new LinkedList<>();
        RoomNode start = graph.startRoom();
        visited.add(roomKey(start));
        queue.add(start);

        while (!queue.isEmpty()) {
            RoomNode cur = queue.poll();
            for (String dir : cur.neighborDirs()) {
                RoomNode nb = graph.neighborRoom(cur.gridX, cur.gridY, dir);
                if (nb != null && visited.add(roomKey(nb))) {
                    queue.add(nb);
                }
            }
        }

        assertThat(visited).hasSize(graph.size());
    }

    // ── WORLD-2: start/exit room types are correct ────────────────────────────

    @Test
    void startAndExitRoomTypesCorrect() {
        WorldGraph graph = WorldGraph.generate(7L, 15, WorldShape.BRANCHY);

        assertThat(graph.startRoom().type).isEqualTo(RoomType.START);
        assertThat(graph.exitRoom().type).isEqualTo(RoomType.EXIT);
        // Start and exit must be distinct rooms
        assertThat(roomKey(graph.startRoom())).isNotEqualTo(roomKey(graph.exitRoom()));
    }

    // ── WORLD-3: same seed produces identical graph ───────────────────────────

    @Test
    void sameSeedException_deterministicGeneration() {
        WorldGraph g1 = WorldGraph.generate(99L, 15, WorldShape.SNAKE);
        WorldGraph g2 = WorldGraph.generate(99L, 15, WorldShape.SNAKE);

        assertThat(g1.size()).isEqualTo(g2.size());
        assertThat(g1.startRoom().gridX).isEqualTo(g2.startRoom().gridX);
        assertThat(g1.startRoom().gridY).isEqualTo(g2.startRoom().gridY);
        assertThat(g1.exitRoom().gridX).isEqualTo(g2.exitRoom().gridX);
        assertThat(g1.exitRoom().gridY).isEqualTo(g2.exitRoom().gridY);
    }

    // ── WORLD-4: PuzzlePlanner BFS covers all rooms (no soft-lock) ────────────

    @Test
    void puzzlePlanCoversAllRoomsAndStartIsDepthZero() {
        // PuzzlePlanner.bfsDepths() must reach every room — if any room is missing
        // from roomDepths, puzzles assigned there cannot be validated and the
        // player could get permanently stuck.
        WorldGraph graph = WorldGraph.generate(42L, 15, WorldShape.BLOB);
        PuzzlePlan plan = PuzzlePlanner.plan(graph, 42L);

        // Every room appears in depth map (full BFS coverage)
        assertThat(plan.roomDepths).hasSize(graph.size());

        // START room is at depth 0
        assertThat(plan.depthOf(graph.startRoom().gridX, graph.startRoom().gridY))
            .isEqualTo(0);

        // EXIT room is reachable (depth > 0)
        assertThat(plan.depthOf(graph.exitRoom().gridX, graph.exitRoom().gridY))
            .isGreaterThan(0);
    }

    // ── Helper ────────────────────────────────────────────────────────────────

    @Test
    void puzzlePlanAlwaysIncludesEchoTriggerAndMapsToInteractableNpcSpawn() {
        long seed = 4242L;
        WorldGraph graph = WorldGraph.generate(seed, 15, WorldShape.BLOB);
        PuzzlePlan plan = PuzzlePlanner.plan(graph, seed);

        long echoTriggers = plan.roomPuzzles.values().stream()
            .flatMap(List::stream)
            .filter(p -> p.type == PuzzleType.ECHO_TRIGGER)
            .count();
        assertThat(echoTriggers).isGreaterThan(0);

        LevelLayout layout = LevelLayout.buildUnifiedWorldLayoutFromPlan(graph, plan, "central_hub");
        assertThat(layout.npcSpawns)
            .anySatisfy(n -> assertThat(n.type()).startsWith("echo_trigger_"));
    }

    private static String roomKey(RoomNode r) {
        return r.gridX + "," + r.gridY;
    }
}
