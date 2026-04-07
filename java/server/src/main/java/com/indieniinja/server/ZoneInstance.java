package com.indieniinja.server;

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
    public final float  spawnX;
    public final float  spawnY;

    /** Monotonically increasing frame counter for this zone. */
    public final AtomicLong frame = new AtomicLong(0);

    /** Players currently in this zone (player IDs). */
    public final Set<String> playerIds = new HashSet<>();

    /** Delta encoder — one per zone, only touched by the sim thread. */
    public final DeltaEncoder deltaEncoder = new DeltaEncoder();

    /** Broadcast counter — reset every FULL_SNAPSHOT_INTERVAL broadcasts. */
    public int fullSnapCountdown = 0;

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
}
