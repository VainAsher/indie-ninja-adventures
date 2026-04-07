package com.indieniinja.server;

import com.indieniinja.sim.GameMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Server-wide session state — players, lobby, game-started flag.
 * Java equivalent of Python's network/server.py GameSession.
 *
 * All mutable fields that cross thread boundaries use ConcurrentHashMap
 * or AtomicInteger/AtomicBoolean for thread safety without explicit locking.
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

    private final AtomicInteger nextSlot = new AtomicInteger(0);

    /** Reconnect grace period in seconds. */
    public static final int RECONNECT_GRACE_SECONDS = 30;

    public GameSession(long worldSeed) {
        this.worldSeed   = worldSeed;
        this.globalFrame = 0;
    }

    /**
     * Assign the next available slot number.
     * Returns -1 if the session is full (MAX_PLAYERS reached).
     */
    public int claimSlot() {
        int slot = nextSlot.getAndIncrement();
        return slot < MAX_PLAYERS ? slot : -1;
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
