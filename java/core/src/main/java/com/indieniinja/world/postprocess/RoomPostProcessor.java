package com.indieniinja.world.postprocess;

import com.indieniinja.sim.FallingPlatform;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimMovingPlatform;
import com.indieniinja.world.SeedHierarchy;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.puzzle.AbilityGate;
import com.indieniinja.world.puzzle.PuzzlePlan;

import java.util.Arrays;
import java.util.List;

/**
 * Orchestrates the post-processing passes applied to a tile grid after
 * {@link com.indieniinja.world.RoomGenerator} produces raw geometry.
 *
 * <p>Pass order (enforced here):
 * <ol>
 *   <li>AbilityLayer  — reshape geometry at gated edges (Phase 3)</li>
 *   <li>PuzzleLayer   — stamp DOOR_LOCKED tiles + puzzle entity markers (Phase 4)</li>
 *   <li>EntityPlanner — place enemies, pickups, NPCs, boss (Phase 2 ← current)</li>
 * </ol>
 *
 * <p>The grid is deep-copied before processing so the caller's array is never
 * mutated.  Returns an immutable {@link RoomContent} consumed by
 * {@link LevelLayout#buildFromRoomContent}.
 */
public final class RoomPostProcessor {

    private RoomPostProcessor() {}

    /**
     * Run all post-processing passes and produce a {@link RoomContent}.
     *
     * @param grid      raw tile grid from RoomGenerator (not mutated)
     * @param room      room descriptor from WorldGraph
     * @param plan      puzzle plan for this hub (use PuzzlePlan.empty() until Phase 3)
     * @param roomSeed  per-room seed for deterministic sub-seed derivation
     * @param masterHubId hub id for portal destination lookup
     */
    public static RoomContent process(
            byte[][]           grid,
            WorldGraph.RoomNode room,
            PuzzlePlan          plan,
            long                roomSeed,
            String              masterHubId) {

        // Deep-copy — never mutate caller's tile array
        byte[][] tiles = deepCopy(grid);

        // ── Pass 1: AbilityLayer — reshape geometry at gated edges ───────────
        for (String dir : room.neighborDirs()) {
            AbilityGate gate = plan.gateFor(room.gridX, room.gridY, dir);
            if (gate != null) {
                long gateSeed = SeedHierarchy.deriveFeature(roomSeed, "gate_" + dir);
                AbilityLayer.apply(tiles, gate, dir, gateSeed);
            }
        }

        // ── Pass 2: PuzzleLayer — stamp DOOR_LOCKED tiles + puzzle markers ───
        String roomKey = PuzzlePlan.roomKey(room.gridX, room.gridY);
        List<RoomContent.PuzzleSpawn> puzzleSpawns =
            PuzzleLayer.apply(tiles, plan.puzzlesFor(roomKey), roomSeed);

        // ── Pass 3: Compute spawn point ───────────────────────────────────────
        float[] spawn = EntityPlanner.computeSpawn(tiles);
        float spawnX = spawn[0], spawnY = spawn[1];

        // ── Pass 4: Entity placement ──────────────────────────────────────────
        List<LevelLayout.EnemySpawn> enemies = EntityPlanner.placeEnemies(
            tiles, room, plan, roomSeed, spawnX, spawnY);

        List<LevelLayout.PickupSpawn> pickups = EntityPlanner.placePickups(
            tiles, room, enemies, roomSeed, spawnX, spawnY);

        List<LevelLayout.NPCSpawn> npcs = EntityPlanner.placeNpcs(
            tiles, room, enemies, pickups, roomSeed);

        LevelLayout.BossSpawn boss = EntityPlanner.placeBoss(tiles, room, roomSeed);

        List<LevelLayout.PortalSpawn> portals = EntityPlanner.placePortals(
            tiles, room, roomSeed, masterHubId);

        List<SimMovingPlatform>  moving  = EntityPlanner.placeMovingPlatforms(room, roomSeed);
        List<FallingPlatform>    falling = EntityPlanner.placeFallingPlatforms(room, roomSeed);

        return new RoomContent(
            tiles, enemies, pickups, npcs, boss,
            puzzleSpawns, portals, falling, moving,
            spawnX, spawnY
        );
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static byte[][] deepCopy(byte[][] src) {
        byte[][] copy = new byte[src.length][];
        for (int r = 0; r < src.length; r++) copy[r] = Arrays.copyOf(src[r], src[r].length);
        return copy;
    }
}
