package com.indieniinja.world.puzzle;

import com.indieniinja.world.SeedHierarchy;
import com.indieniinja.world.WorldGraph;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Random;
import java.util.Set;

/**
 * World-level planner that assigns ability gates and puzzle chains to a
 * {@link WorldGraph} without touching any tile arrays.
 *
 * <p>Algorithm:
 * <ol>
 *   <li>BFS from START to compute depth of every room.</li>
 *   <li>Assign ability gates to eligible non-critical edges by depth threshold.</li>
 *   <li>Assign puzzles to rooms (KEY_DOOR on dead-ends, LEVER_DOOR on connectors).</li>
 *   <li>Validate — BFS simulation with progressive ability unlock.  Retry up to
 *       {@code MAX_ATTEMPTS} times; fall back to an empty plan on repeated failure.</li>
 * </ol>
 *
 * <p>Rules:
 * <ul>
 *   <li>Depth 0-1: no gates.</li>
 *   <li>Depth 2-3: DOUBLE_JUMP eligible.</li>
 *   <li>Depth 4-5: WALL_JUMP eligible.</li>
 *   <li>Depth 6+: DASH eligible.</li>
 *   <li>Never gate the only path to any room.</li>
 * </ul>
 */
public final class PuzzlePlanner {

    private static final int MAX_ATTEMPTS = 5;

    private PuzzlePlanner() {}

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Generate a {@link PuzzlePlan} for the given world graph.
     *
     * @param graph     the world graph to plan for
     * @param worldSeed base seed — sub-seeds are derived via SeedHierarchy
     * @return a validated PuzzlePlan; falls back to empty() if all attempts fail
     */
    public static PuzzlePlan plan(WorldGraph graph, long worldSeed) {
        Map<String, Integer> depths = bfsDepths(graph);

        for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            long attemptSeed = SeedHierarchy.deriveFeature(worldSeed, "puzzle_plan_" + attempt);
            PuzzlePlan candidate = buildPlan(graph, depths, attemptSeed);
            ValidationLayer.ValidationResult result = ValidationLayer.validate(graph, candidate);
            if (result.valid()) return candidate;
        }

        // Safe fallback: no gates, no puzzles
        return PuzzlePlan.empty();
    }

    // ── BFS depth computation ─────────────────────────────────────────────────

    /** BFS from START; returns roomKey → depth map for every reachable room. */
    static Map<String, Integer> bfsDepths(WorldGraph graph) {
        Map<String, Integer> depths = new HashMap<>();
        Queue<WorldGraph.RoomNode> queue = new LinkedList<>();

        WorldGraph.RoomNode start = graph.startRoom();
        String startKey = PuzzlePlan.roomKey(start.gridX, start.gridY);
        depths.put(startKey, 0);
        queue.add(start);

        while (!queue.isEmpty()) {
            WorldGraph.RoomNode cur = queue.poll();
            int d = depths.get(PuzzlePlan.roomKey(cur.gridX, cur.gridY));

            for (String dir : cur.neighborDirs()) {
                WorldGraph.RoomNode nb = graph.neighborRoom(cur.gridX, cur.gridY, dir);
                if (nb == null) continue;
                String nbKey = PuzzlePlan.roomKey(nb.gridX, nb.gridY);
                if (!depths.containsKey(nbKey)) {
                    depths.put(nbKey, d + 1);
                    queue.add(nb);
                }
            }
        }
        return depths;
    }

    // ── Plan construction ─────────────────────────────────────────────────────

    private static PuzzlePlan buildPlan(
            WorldGraph graph,
            Map<String, Integer> depths,
            long seed) {

        Random rng = new Random(seed);
        Map<String, AbilityGate>  edgeGates   = new HashMap<>();
        Map<String, List<Puzzle>> roomPuzzles = new HashMap<>();

        // ── Step 1: Assign ability gates ──────────────────────────────────────
        for (WorldGraph.RoomNode room : graph.allRooms()) {
            for (String dir : room.neighborDirs()) {
                WorldGraph.RoomNode nb = graph.neighborRoom(room.gridX, room.gridY, dir);
                if (nb == null) continue;

                int depth = depths.getOrDefault(
                    PuzzlePlan.roomKey(room.gridX, room.gridY), 0);
                AbilityGate.GateType gateType = eligibleGateType(depth);
                if (gateType == null) continue;

                // 33% chance to place a gate on this edge
                if (rng.nextInt(3) != 0) continue;

                // Never gate the only path to any room
                if (isCriticalEdge(graph, room, dir)) continue;

                AbilityGate.Technique tech = techniqueFor(gateType, rng);
                String edgeKey = edgeKey(room.gridX, room.gridY, dir);
                edgeGates.put(edgeKey, new AbilityGate(gateType, tech));
            }
        }

        // ── Step 2: Assign puzzles ────────────────────────────────────────────
        int puzzleCounter = 0;
        int echoTriggerRooms = 0;
        List<WorldGraph.RoomNode> echoCandidates = new ArrayList<>();
        for (WorldGraph.RoomNode room : graph.allRooms()) {
            int depth = depths.getOrDefault(
                PuzzlePlan.roomKey(room.gridX, room.gridY), 0);
            if (depth < 2) continue;

            if (room.type == WorldGraph.RoomType.COMBAT && depth >= 3) {
                echoCandidates.add(room);
            }

            List<Puzzle> puzzles = new ArrayList<>();

            boolean isDeadEnd = room.neighborDirs().size() == 1;
            boolean isConnector = room.neighborDirs().size() >= 3;

            if (isDeadEnd) {
                // KEY_DOOR: key in this room, door links forward (assigned at runtime)
                String id = "kd_" + puzzleCounter++;
                puzzles.add(new Puzzle(id, PuzzleType.KEY_DOOR, null, false));
            } else if (isConnector && rng.nextBoolean()) {
                // LEVER_DOOR: optional — only on 50% of connectors
                String id = "ld_" + puzzleCounter++;
                puzzles.add(new Puzzle(id, PuzzleType.LEVER_DOOR, null, false));
            } else if (room.type == WorldGraph.RoomType.COMBAT && depth >= 3
                    && rng.nextInt(6) == 0) {
                // BUTTON_SEQUENCE: rare optional challenge room (1-in-6 combat rooms)
                String id = "bs_" + puzzleCounter++;
                puzzles.add(new Puzzle(id, PuzzleType.BUTTON_SEQUENCE, null, false));
            }
            if (room.type == WorldGraph.RoomType.COMBAT && depth >= 3
                    && rng.nextInt(5) == 0) {
                String id = "et_" + puzzleCounter++;
                puzzles.add(new Puzzle(id, PuzzleType.ECHO_TRIGGER, null, false));
                echoTriggerRooms++;
            }

            if (!puzzles.isEmpty()) {
                roomPuzzles.put(PuzzlePlan.roomKey(room.gridX, room.gridY), puzzles);
            }
        }

        // Ensure every generated world has at least one authored echo trigger room.
        if (echoTriggerRooms == 0 && !echoCandidates.isEmpty()) {
            WorldGraph.RoomNode room = echoCandidates.get(rng.nextInt(echoCandidates.size()));
            String roomKey = PuzzlePlan.roomKey(room.gridX, room.gridY);
            roomPuzzles.computeIfAbsent(roomKey, ignored -> new ArrayList<>())
                .add(new Puzzle("et_" + puzzleCounter++, PuzzleType.ECHO_TRIGGER, null, false));
        }

        return new PuzzlePlan(edgeGates, roomPuzzles, depths);
    }

    // ── Gate helpers ──────────────────────────────────────────────────────────

    /** Returns the ability gate type eligible at this BFS depth, or null if none. */
    static AbilityGate.GateType eligibleGateType(int depth) {
        if (depth >= 6) return AbilityGate.GateType.DASH;
        if (depth >= 4) return AbilityGate.GateType.WALL_JUMP;
        if (depth >= 2) return AbilityGate.GateType.DOUBLE_JUMP;
        return null;
    }

    /** Choose the most appropriate physical technique for a gate type. */
    private static AbilityGate.Technique techniqueFor(
            AbilityGate.GateType type, Random rng) {
        return switch (type) {
            case DOUBLE_JUMP -> AbilityGate.Technique.RAISED_PLATFORM;
            case WALL_JUMP   -> AbilityGate.Technique.VERTICAL_SHAFT;
            case DASH        -> AbilityGate.Technique.WIDE_GAP;
            default          -> AbilityGate.Technique.RAISED_PLATFORM;
        };
    }

    /**
     * Returns true if removing this directed edge would disconnect any room
     * from the START room (ignoring all ability gates).
     *
     * Uses BFS from START with the edge temporarily removed.
     */
    static boolean isCriticalEdge(WorldGraph graph, WorldGraph.RoomNode from, String dir) {
        WorldGraph.RoomNode to = graph.neighborRoom(from.gridX, from.gridY, dir);
        if (to == null) return false;

        // BFS from START, skipping the edge from→dir
        Set<String> visited = new HashSet<>();
        Queue<WorldGraph.RoomNode> queue = new LinkedList<>();
        queue.add(graph.startRoom());
        visited.add(PuzzlePlan.roomKey(graph.startRoom().gridX, graph.startRoom().gridY));

        while (!queue.isEmpty()) {
            WorldGraph.RoomNode cur = queue.poll();
            for (String d : cur.neighborDirs()) {
                // Skip the edge under test
                if (cur.gridX == from.gridX && cur.gridY == from.gridY && d.equals(dir)) continue;

                WorldGraph.RoomNode nb = graph.neighborRoom(cur.gridX, cur.gridY, d);
                if (nb == null) continue;
                String nbKey = PuzzlePlan.roomKey(nb.gridX, nb.gridY);
                if (!visited.contains(nbKey)) {
                    visited.add(nbKey);
                    queue.add(nb);
                }
            }
        }

        // If any room became unreachable, this edge is critical
        for (WorldGraph.RoomNode r : graph.allRooms()) {
            if (!visited.contains(PuzzlePlan.roomKey(r.gridX, r.gridY))) return true;
        }
        return false;
    }

    // ── Edge key ──────────────────────────────────────────────────────────────

    static String edgeKey(int gx, int gy, String dir) {
        return gx + "," + gy + "\u2192" + dir;
    }
}
