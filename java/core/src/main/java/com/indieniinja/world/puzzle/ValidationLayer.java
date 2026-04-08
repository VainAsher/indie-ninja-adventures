package com.indieniinja.world.puzzle;

import com.indieniinja.world.WorldGraph;

import java.util.HashSet;
import java.util.LinkedList;
import java.util.Queue;
import java.util.Set;

/**
 * BFS-based progression validator.
 *
 * Simulates a player traversing the WorldGraph with an incrementally unlocked
 * ability set (abilities unlock based on BFS depth from START).  Verifies:
 * <ul>
 *   <li>Every room is reachable with the abilities available at that depth.</li>
 *   <li>The EXIT room is reachable.</li>
 *   <li>No critical path is blocked behind a gate requiring an ability the
 *       player cannot yet have.</li>
 * </ul>
 *
 * Called by {@link PuzzlePlanner} after each attempt; if validation fails the
 * planner retries with a different seed.
 */
public final class ValidationLayer {

    private ValidationLayer() {}

    // ── Result type ───────────────────────────────────────────────────────────

    /**
     * @param valid         true if the plan is softlock-free
     * @param failureReason human-readable description, or null if valid
     */
    public record ValidationResult(boolean valid, String failureReason) {
        static ValidationResult ok()                    { return new ValidationResult(true,  null); }
        static ValidationResult fail(String reason)    { return new ValidationResult(false, reason); }
    }

    // ── Validation ────────────────────────────────────────────────────────────

    /**
     * Validate that the given plan does not softlock the world graph.
     */
    public static ValidationResult validate(WorldGraph graph, PuzzlePlan plan) {
        Set<String>               abilities = new HashSet<>();
        Set<String>               visited   = new HashSet<>();
        Queue<WorldGraph.RoomNode> queue     = new LinkedList<>();

        WorldGraph.RoomNode start = graph.startRoom();
        visited.add(PuzzlePlan.roomKey(start.gridX, start.gridY));
        queue.add(start);

        while (!queue.isEmpty()) {
            WorldGraph.RoomNode cur = queue.poll();
            int depth = plan.depthOf(cur.gridX, cur.gridY);

            // Unlock abilities that become available at or before this depth
            abilities.addAll(abilitiesAvailableAt(depth));

            for (String dir : cur.neighborDirs()) {
                WorldGraph.RoomNode nb = graph.neighborRoom(cur.gridX, cur.gridY, dir);
                if (nb == null) continue;
                String nbKey = PuzzlePlan.roomKey(nb.gridX, nb.gridY);
                if (visited.contains(nbKey)) continue;

                AbilityGate gate = plan.gateFor(cur.gridX, cur.gridY, dir);
                if (gate != null && !abilities.contains(gate.requiredAbilityString())) {
                    // Gated and player doesn't have the ability yet.
                    // Check if this is the only route to any still-unreachable room.
                    if (isOnlyCriticalPath(graph, cur, dir, visited, plan, abilities)) {
                        return ValidationResult.fail(
                            "SOFTLOCK: " + PuzzlePlan.roomKey(cur.gridX, cur.gridY)
                            + " → " + dir + " requires " + gate.type.abilityString
                            + " but no alternative route exists");
                    }
                    continue;  // gated for now — skip
                }

                visited.add(nbKey);
                queue.add(nb);
            }
        }

        // EXIT must be reachable
        WorldGraph.RoomNode exit = graph.exitRoom();
        if (!visited.contains(PuzzlePlan.roomKey(exit.gridX, exit.gridY))) {
            return ValidationResult.fail("SOFTLOCK: EXIT room unreachable");
        }

        return ValidationResult.ok();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Abilities the player has available at or before the given BFS depth.
     * Mirrors the unlock thresholds in PuzzlePlanner.
     */
    static Set<String> abilitiesAvailableAt(int depth) {
        Set<String> a = new HashSet<>(4);
        if (depth >= 2) a.add(AbilityGate.GateType.DOUBLE_JUMP.abilityString);
        if (depth >= 4) a.add(AbilityGate.GateType.WALL_JUMP.abilityString);
        if (depth >= 6) a.add(AbilityGate.GateType.DASH.abilityString);
        return a;
    }

    /**
     * Returns true if the edge (from→dir) is the only remaining way to reach
     * any unvisited room — meaning blocking it would create a softlock.
     *
     * BFS from 'from' room's current reachable set (visited), skipping this
     * edge and any currently-gated edges.  If any unvisited room can no longer
     * be reached via an ungated path, the edge is critical.
     */
    private static boolean isOnlyCriticalPath(
            WorldGraph graph,
            WorldGraph.RoomNode from, String blockedDir,
            Set<String> alreadyVisited,
            PuzzlePlan plan, Set<String> abilities) {

        // BFS from all currently-visited rooms, skipping the blocked edge
        Set<String>               reachable = new HashSet<>(alreadyVisited);
        Queue<WorldGraph.RoomNode> queue     = new LinkedList<>();
        for (WorldGraph.RoomNode r : graph.allRooms()) {
            if (alreadyVisited.contains(PuzzlePlan.roomKey(r.gridX, r.gridY))) queue.add(r);
        }

        while (!queue.isEmpty()) {
            WorldGraph.RoomNode cur = queue.poll();
            for (String dir : cur.neighborDirs()) {
                if (cur.gridX == from.gridX && cur.gridY == from.gridY
                        && dir.equals(blockedDir)) continue;  // skip blocked edge

                WorldGraph.RoomNode nb = graph.neighborRoom(cur.gridX, cur.gridY, dir);
                if (nb == null) continue;
                String nbKey = PuzzlePlan.roomKey(nb.gridX, nb.gridY);
                if (reachable.contains(nbKey)) continue;

                AbilityGate gate = plan.gateFor(cur.gridX, cur.gridY, dir);
                if (gate != null && !abilities.contains(gate.requiredAbilityString())) continue;

                reachable.add(nbKey);
                queue.add(nb);
            }
        }

        // If any room is still unreachable, this edge was the only path to it
        for (WorldGraph.RoomNode r : graph.allRooms()) {
            if (!reachable.contains(PuzzlePlan.roomKey(r.gridX, r.gridY))) return true;
        }
        return false;
    }
}
