package com.indieniinja.server;

import com.indieniinja.sim.GameMode;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.world.WorldGraph;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicLong;

/**
 * One active instanced zone on the server.
 *
 * Java equivalent of Python's network/server.py _ZoneInstance dataclass.
 * Each zone runs its own ZoneSimulationLoop thread at 60 Hz.
 * Multiple zones can be live simultaneously — one per hub that has players.
 */
public final class ZoneInstance {

    /** Zone lookup key — includes grid coords: "hubId:gridX:gridY". */
    public final String hubId;
    /** Original hub name without grid suffix (e.g. "central_hub"). */
    public final String masterHubId;
    public final long   seed;
    public final String shape;
    public final int    rooms;
    public final long   worldSeed;
    /** Authoritative player spawn position, set from LevelLayout after room generation. */
    public volatile float  spawnX;
    public volatile float  spawnY;

    /** Monotonically increasing frame counter for this zone. */
    public final AtomicLong frame = new AtomicLong(0);

    /** Players currently in this zone (player IDs). */
    public final Set<String> playerIds = new HashSet<>();

    /** Delta encoder — one per zone, only touched by the sim thread. */
    public final DeltaEncoder deltaEncoder = new DeltaEncoder();

    /** Broadcast counter — reset every FULL_SNAPSHOT_INTERVAL broadcasts.
     *  Pre-set to FULL_SNAPSHOT_EVERY so the very first broadcast is always a full snapshot,
     *  ensuring the client gets shop states, world rooms, and all full-snap fields immediately. */
    public int fullSnapCountdown = ZoneSimulationLoop.FULL_SNAPSHOT_EVERY;

    /** Handle to the running sim loop task (for cancellation on zone teardown). */
    public volatile Future<?> simFuture;

    /** Epoch ms of last player departure — used for idle TTL reaping. */
    public volatile long lastActivityMs = System.currentTimeMillis();

    /**
     * Java authoritative game simulator for this zone.
     * Null before the zone is started; assigned in ZoneSimulationLoop.
     * Phase B: fully populated with enemies, pickups, platforms from LevelLayout.
     */
    public volatile GameSimulator simulator;

    /**
     * Multi-room world graph generated from this zone's master seed.
     * Assigned in ZoneSimulationLoop.initSimulator once at startup.
     */
    public volatile WorldGraph worldGraph;

    /** Seed for the current room (start room at boot; changes on room transition). */
    public volatile long  currentRoomSeed = 0;
    /** Grid coordinates of the current room in the WorldGraph. */
    public volatile int   currentRoomGridX = 0;
    public volatile int   currentRoomGridY = 0;
    /** Neighbor directions for the current room (doors that exist). */
    public volatile java.util.List<String> currentNeighborDirs = java.util.List.of();
    /** Room type for the current room (wire string: combat/start/exit/shop/etc.). */
    public volatile String currentRoomType = "combat";

    /** Game mode for this zone — set when the zone is first created. */
    public volatile GameMode gameMode = GameMode.ARCADE;
    /** Arcade: current depth (increments when players clear the exit room). */
    public volatile int arcadeDepth = 0;
    /** Arcade: room count for current depth level. */
    public volatile int arcadeRooms = 10;

    public ZoneInstance(
            String hubId, String masterHubId, long seed, String shape, int rooms,
            long worldSeed, float spawnX, float spawnY) {
        this.hubId        = hubId;
        this.masterHubId  = masterHubId;
        this.seed         = seed;
        this.shape        = shape;
        this.rooms        = rooms;
        this.worldSeed    = worldSeed;
        this.spawnX       = spawnX;
        this.spawnY       = spawnY;
    }

    public boolean isEmpty() {
        return playerIds.isEmpty();
    }

    /**
     * Room transition queued by ZoneSimulationLoop.checkRoomCrossings().
     * Processed by ZoneSimulationLoop.processPendingTransitions() after each tick
     * so the player is safely moved to the new room's ZoneInstance.
     *
     * newX/Y are already adjusted to room-local coordinates in the new room.
     */
    public record PendingRoomTransition(
        String playerId, int newGridX, int newGridY, float newX, float newY) {}

    /** Transitions queued by the sim thread; drained each tick before broadcast. */
    public final java.util.concurrent.ConcurrentLinkedQueue<PendingRoomTransition>
        pendingRoomTransitions = new java.util.concurrent.ConcurrentLinkedQueue<>();
}
