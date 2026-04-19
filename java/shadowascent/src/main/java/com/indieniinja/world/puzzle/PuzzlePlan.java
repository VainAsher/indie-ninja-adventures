package com.indieniinja.world.puzzle;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Immutable result of {@link PuzzlePlanner}.
 *
 * Encodes all world-level decisions about ability gates and puzzle chains
 * without touching any tile arrays.  Produced once per WorldGraph and
 * cached on the ZoneInstance for the lifetime of the hub.
 *
 * <p>Edge gate keys use the format {@code "gx,gy→dir"}, e.g.
 * {@code "3,2→right"} means the passage from room (3,2) heading right
 * is gated.
 */
public final class PuzzlePlan {

    /** Ability gate per directed room edge: key = {@code "gx,gy→dir"}. */
    public final Map<String, AbilityGate> edgeGates;

    /** Puzzles keyed by room node id string {@code "gx,gy"}. */
    public final Map<String, List<Puzzle>> roomPuzzles;

    /** BFS depth of each room from START, keyed by {@code "gx,gy"}. */
    public final Map<String, Integer> roomDepths;

    public PuzzlePlan(
            Map<String, AbilityGate>   edgeGates,
            Map<String, List<Puzzle>>  roomPuzzles,
            Map<String, Integer>       roomDepths) {
        this.edgeGates   = Collections.unmodifiableMap(edgeGates);
        this.roomPuzzles = Collections.unmodifiableMap(roomPuzzles);
        this.roomDepths  = Collections.unmodifiableMap(roomDepths);
    }

    /** Returns null if there is no gate on this edge. */
    public AbilityGate gateFor(int gx, int gy, String dir) {
        return edgeGates.get(gx + "," + gy + "\u2192" + dir);
    }

    /** Returns an empty list if this room has no assigned puzzles. */
    public List<Puzzle> puzzlesFor(String roomKey) {
        return roomPuzzles.getOrDefault(roomKey, List.of());
    }

    /** Returns -1 if the room is unknown. */
    public int depthOf(String roomKey) {
        return roomDepths.getOrDefault(roomKey, -1);
    }

    /** Returns -1 if the room is unknown. */
    public int depthOf(int gx, int gy) {
        return depthOf(gx + "," + gy);
    }

    /** Canonical room key for a given grid position. */
    public static String roomKey(int gx, int gy) {
        return gx + "," + gy;
    }

    // ── Empty plan (safe fallback / Phase-1 skeleton) ─────────────────────────

    /** Returns an empty plan that produces no gates and no puzzles. */
    public static PuzzlePlan empty() {
        return new PuzzlePlan(Map.of(), Map.of(), Map.of());
    }
}
