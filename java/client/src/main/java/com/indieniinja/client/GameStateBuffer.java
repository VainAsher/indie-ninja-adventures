package com.indieniinja.client;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.WorldSnapshot;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Thread-safe buffer between the NetworkClientThread (writer) and
 * the libGDX render thread (reader).
 *
 * The NetworkClientThread receives WorldSnapshot messages (full + delta).
 * This buffer merges them into one canonical "current world state" that the
 * render thread reads every frame via poll().
 *
 * Design: single AtomicReference<WorldSnapshot> for lock-free read on the
 * render hot path. Delta merging happens on the network thread (write path).
 */
public final class GameStateBuffer {

    private final AtomicReference<WorldSnapshot> current = new AtomicReference<>(new WorldSnapshot());

    // Delta state tracked on the network thread — enemies/pickups by ID
    private final Map<String, EnemyState>    enemyById    = new HashMap<>();
    private final Map<String, PickupState>   pickupById   = new HashMap<>();
    private final Map<String, PlatformState> platformById = new HashMap<>();

    private volatile long lastFrameReceived = -1;
    private volatile boolean connected      = false;

    // ── Network thread writes ─────────────────────────────────────────────────

    /**
     * Called by NetworkClientThread when a WORLD_STATE message arrives.
     * Merges delta into the canonical state and publishes the new snapshot.
     */
    public void update(WorldSnapshot snap) {
        lastFrameReceived = snap.frame;
        connected = true;

        if (snap.isDelta) {
            applyDelta(snap);
        } else {
            // Full snapshot — rebuild maps from scratch
            enemyById.clear();
            pickupById.clear();
            platformById.clear();
            for (EnemyState    e : snap.enemies)        enemyById.put(e.enemyId, e);
            for (PickupState   p : snap.pickups)        pickupById.put(p.pickupId, p);
            for (PlatformState p : snap.platformStates) platformById.put(p.platformId, p);
            current.set(snap);
        }
    }

    private void applyDelta(WorldSnapshot delta) {
        // Apply changes
        for (EnemyState    e : delta.enemiesChanged)   enemyById.put(e.enemyId, e);
        for (PickupState   p : delta.pickupsChanged)   pickupById.put(p.pickupId, p);
        for (PlatformState p : delta.platformsChanged) platformById.put(p.platformId, p);

        // Apply removals
        for (String id : delta.enemiesRemoved)   enemyById.remove(id);
        for (String id : delta.pickupsRemoved)   pickupById.remove(id);
        for (String id : delta.platformsRemoved) platformById.remove(id);

        // Build a merged full snapshot for the render thread
        WorldSnapshot merged = new WorldSnapshot();
        merged.frame  = delta.frame;
        merged.seed   = delta.seed;
        merged.hubId  = delta.hubId;
        merged.isDelta = false;  // render thread always sees a full view
        merged.players.addAll(delta.players);
        merged.enemies.addAll(enemyById.values());
        merged.pickups.addAll(pickupById.values());
        merged.platformStates.addAll(platformById.values());
        current.set(merged);
    }

    public void markDisconnected() {
        connected = false;
    }

    // ── Render thread reads ───────────────────────────────────────────────────

    /** Latest merged snapshot — safe to call from any thread. */
    public WorldSnapshot poll() {
        return current.get();
    }

    public boolean isConnected()        { return connected; }
    public long    getLastFrame()       { return lastFrameReceived; }
}
