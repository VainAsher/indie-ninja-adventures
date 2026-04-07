package com.indieniinja.client;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.WorldSnapshot;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
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
    /** Set by NetworkClientThread on WORLD_TRANSITION; consumed once by GameScreen. */
    private final AtomicBoolean pendingZoneTransition = new AtomicBoolean(false);

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
        merged.frame        = delta.frame;
        merged.seed         = delta.seed;
        merged.hubId        = delta.hubId;
        merged.roomType     = delta.roomType;       // carry room metadata from delta
        merged.neighborDirs = delta.neighborDirs;   // ← was defaulting to [] causing tile flicker
        merged.roomGridX    = delta.roomGridX;
        merged.roomGridY    = delta.roomGridY;
        merged.isDelta = false;  // render thread always sees a full view
        merged.players.addAll(delta.players);
        merged.enemies.addAll(enemyById.values());
        merged.pickups.addAll(pickupById.values());
        merged.platformStates.addAll(platformById.values());
        // Shurikens and NPCs are always sent on every wire packet (not delta-encoded).
        merged.shurikens.addAll(delta.shurikens);
        merged.npcs.addAll(delta.npcs);
        // Bosses, portals, worldRooms, shopStates are full-snapshot-only; carry forward
        // from the previous merged state so they don't vanish on delta frames.
        WorldSnapshot prev = current.get();
        if (prev != null) {
            if (delta.bosses.isEmpty())      merged.bosses.addAll(prev.bosses);
            else                             merged.bosses.addAll(delta.bosses);
            if (delta.portals.isEmpty())     merged.portals.addAll(prev.portals);
            else                             merged.portals.addAll(delta.portals);
            if (delta.shopStates.isEmpty())  merged.shopStates.addAll(prev.shopStates);
            else                             merged.shopStates.addAll(delta.shopStates);
            if (delta.worldRooms.isEmpty())  merged.worldRooms.addAll(prev.worldRooms);
            else                             merged.worldRooms.addAll(delta.worldRooms);
        }
        merged.gameMode    = delta.gameMode;
        merged.arcadeScore = delta.arcadeScore;
        merged.arcadeDepth = delta.arcadeDepth;
        merged.arcadeRooms = delta.arcadeRooms;
        current.set(merged);
    }

    /**
     * Called by NetworkClientThread when a WORLD_TRANSITION message arrives.
     * Clears all delta state so the next full snapshot is treated as a fresh zone.
     * GameScreen calls pollZoneTransition() to detect this and reset its tile/megamap state.
     */
    public void resetForZoneTransition() {
        enemyById.clear();
        pickupById.clear();
        platformById.clear();
        current.set(new WorldSnapshot());   // blank state — no stale entities from old zone
        pendingZoneTransition.set(true);
    }

    /** Returns true (and clears the flag) if a zone transition arrived since last check. */
    public boolean pollZoneTransition() {
        return pendingZoneTransition.getAndSet(false);
    }

    public void markConnected()    { connected = true; }
    public void markDisconnected() { connected = false; }

    // ── Render thread reads ───────────────────────────────────────────────────

    /** Latest merged snapshot — safe to call from any thread. */
    public WorldSnapshot poll() {
        return current.get();
    }

    public boolean isConnected()        { return connected; }
    public long    getLastFrame()       { return lastFrameReceived; }
}
