package com.indieniinja.server;

import com.indieniinja.sim.GameMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Server-wide session state — players, lobby, game-started flag.
 *
 * Slot management uses a recyclable TreeSet so disconnected slots are returned
 * to the pool and reused by reconnecting players (or new joiners).
 * Player IDs are remembered so a reconnecting client reclaims their exact slot.
 */
public final class GameSession {

    public static final int MAX_PLAYERS = 4;

    public final long   worldSeed;
    public final long   globalFrame;

    /** Game mode for this session — set from the first CLIENT_HELLO. */
    public volatile GameMode gameMode = GameMode.ARCADE;

    /** Connected players, keyed by playerId. Thread-safe map. */
    public final Map<String, PlayerRecord> players = new ConcurrentHashMap<>();

    /** True once GAME_START has been broadcast. */
    public final AtomicBoolean gameStarted = new AtomicBoolean(false);

    /** Reconnect grace period in seconds. */
    public static final int RECONNECT_GRACE_SECONDS = 30;

    /** Available slot numbers (0–MAX_PLAYERS-1). Guarded by itself. */
    private final TreeSet<Integer> freeSlots = new TreeSet<>();

    /**
     * Slot reserved for a disconnected player's playerId.
     * Allows the same client to reconnect and reclaim their slot within the grace period.
     */
    private final Map<String, Integer> reservedSlots = new ConcurrentHashMap<>();

    public GameSession(long worldSeed) {
        this.worldSeed   = worldSeed;
        this.globalFrame = 0;
        for (int i = 0; i < MAX_PLAYERS; i++) freeSlots.add(i);
    }

    /**
     * Claim a slot for the given playerId.
     * If the player previously held a slot (reserved), return that slot.
     * Otherwise return the lowest free slot, or -1 if full.
     */
    public synchronized int claimSlot(String playerId) {
        // Reconnecting player? Give them back their old slot.
        Integer reserved = reservedSlots.remove(playerId);
        if (reserved != null) {
            freeSlots.remove(reserved);
            return reserved;
        }
        if (freeSlots.isEmpty()) return -1;
        int slot = freeSlots.first();
        freeSlots.remove(slot);
        return slot;
    }

    /**
     * Release a slot back to the pool.
     * Remembers the association so the same player can reclaim it on reconnect.
     */
    public synchronized void releaseSlot(String playerId, int slot) {
        reservedSlots.put(playerId, slot);
        freeSlots.add(slot);
    }

    /** Snapshot of currently connected players for broadcast. */
    public List<PlayerRecord> connectedPlayers() {
        return new ArrayList<>(players.values());
    }

    /** Lobby payload for LOBBY_UPDATE message. */
    public List<Map<String, Object>> lobbyPlayerList() {
        List<Map<String, Object>> list = new ArrayList<>();
        for (PlayerRecord p : players.values()) {
            list.add(Map.of("player_id", p.playerId, "slot", p.slot));
        }
        return list;
    }
}
