package com.indieniinja.server;

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

    public final String hubId;
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

    public ZoneInstance(
            String hubId, long seed, String shape, int rooms,
            long worldSeed, float spawnX, float spawnY) {
        this.hubId     = hubId;
        this.seed      = seed;
        this.shape     = shape;
        this.rooms     = rooms;
        this.worldSeed = worldSeed;
        this.spawnX    = spawnX;
        this.spawnY    = spawnY;
    }

    public boolean isEmpty() {
        return playerIds.isEmpty();
    }
}
