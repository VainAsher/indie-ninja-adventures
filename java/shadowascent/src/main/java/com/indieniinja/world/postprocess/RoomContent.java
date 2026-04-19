package com.indieniinja.world.postprocess;

import com.indieniinja.sim.FallingPlatform;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimMovingPlatform;

import java.util.List;

/**
 * Intermediate artifact produced by {@link RoomPostProcessor} for a single room.
 *
 * Contains the (possibly geometry-reshaped) tile grid plus all entity spawn
 * descriptors determined by the post-processing pipeline.  Consumed by
 * {@link LevelLayout#buildFromRoomContent} to produce the final immutable
 * layout used at runtime.
 *
 * All lists are unmodifiable after construction.
 */
public final class RoomContent {

    /** Tile grid — may have been reshaped by AbilityLayer. byte[rows][cols]. */
    public final byte[][] tiles;

    public final List<LevelLayout.EnemySpawn>  enemies;
    public final List<LevelLayout.PickupSpawn> pickups;
    public final List<LevelLayout.NPCSpawn>    npcs;
    /** null if this is not a boss room. */
    public final LevelLayout.BossSpawn         bossSpawn;
    public final List<PuzzleSpawn>             puzzles;
    public final List<LevelLayout.PortalSpawn> portals;
    public final List<FallingPlatform>         fallingPlatforms;
    public final List<SimMovingPlatform>       movingPlatforms;

    /** Recommended player spawn position in room-local pixels. */
    public final float spawnX;
    public final float spawnY;

    public RoomContent(
            byte[][]                      tiles,
            List<LevelLayout.EnemySpawn>  enemies,
            List<LevelLayout.PickupSpawn> pickups,
            List<LevelLayout.NPCSpawn>    npcs,
            LevelLayout.BossSpawn         bossSpawn,
            List<PuzzleSpawn>             puzzles,
            List<LevelLayout.PortalSpawn> portals,
            List<FallingPlatform>         fallingPlatforms,
            List<SimMovingPlatform>       movingPlatforms,
            float spawnX, float spawnY) {
        this.tiles            = tiles;
        this.enemies          = List.copyOf(enemies);
        this.pickups          = List.copyOf(pickups);
        this.npcs             = List.copyOf(npcs);
        this.bossSpawn        = bossSpawn;
        this.puzzles          = List.copyOf(puzzles);
        this.portals          = portals != null ? List.copyOf(portals) : List.of();
        this.fallingPlatforms = fallingPlatforms != null ? List.copyOf(fallingPlatforms) : List.of();
        this.movingPlatforms  = movingPlatforms  != null ? List.copyOf(movingPlatforms)  : List.of();
        this.spawnX           = spawnX;
        this.spawnY           = spawnY;
    }

    // ── Inner record ──────────────────────────────────────────────────────────

    /**
     * Spawn descriptor for a puzzle interactable (lever, door, button).
     *
     * @param puzzleId      stable deterministic ID for this puzzle element
     * @param puzzleType    "lever", "door", "button", "key"
     * @param x             world-pixel X centre
     * @param y             world-pixel Y (top of tile)
     * @param linkedPuzzleId id of the paired puzzle element (e.g., door linked to lever)
     */
    public record PuzzleSpawn(
        String puzzleId,
        String puzzleType,
        float  x,
        float  y,
        String linkedPuzzleId
    ) {}
}
