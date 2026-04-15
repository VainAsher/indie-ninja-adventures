package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import io.netty.channel.Channel;

import java.util.concurrent.atomic.AtomicReference;

/**
 * Per-connected-player record held by the server.
 * Java equivalent of Python's network/server.py ConnectedPlayer dataclass.
 *
 * latestInput is AtomicReference so the Netty I/O thread (writer) and
 * the zone simulation thread (reader) never contend on a lock.
 */
public final class PlayerRecord {

    public final String  playerId;
    public final String  sessionId;
    public final int     slot;
    public final Channel channel;
    public final long    connectedAtMs;

    /** Written by Netty I/O thread; read by ZoneSimulationLoop. */
    public final AtomicReference<InputCommand> latestInput = new AtomicReference<>();

    // Default spawn: room centre-x, above the procedural base floor (row 126).
    // Base floor PLATFORM at row 126 → y = 126 × 32 = 4032.
    // Player height = 56 → posY = 4032 − 56 = 3976.
    // The actual spawn is overridden by ZoneSimulationLoop from LevelLayout.spawnX/Y.
    public volatile float  posX = 2048f, posY = 3976f;
    public volatile float  velX = 0f, velY = 0f;
    public volatile int    health = 5;
    public volatile int    facing = 1;     // 1=right, -1=left
    public volatile boolean isDead = false;
    public volatile String  animState = "";

    // Phase 4: which zone/hub this player is currently in
    public volatile String hubId = "central_hub";

    // Reconnect grace: slot reservation deadline (epoch ms); 0 = no reservation
    public volatile long reservedUntilMs = 0;

    /**
     * Set to true by transitionPlayerToRoom() after writing an explicit door-entry
     * spawn position into posX/Y.  ZoneSimulationLoop clears it after consuming it,
     * ensuring the sim uses the door-entry coords instead of zone.spawnX/Y.
     */
    public volatile boolean explicitSpawnSet = false;

    public PlayerRecord(String playerId, String sessionId, int slot, Channel channel) {
        this.playerId = playerId;
        this.sessionId = (sessionId == null || sessionId.isBlank()) ? "unknown" : sessionId;
        this.slot     = slot;
        this.channel  = channel;
        this.connectedAtMs = System.currentTimeMillis();
        // Neutral input until first packet arrives
        this.latestInput.set(InputCommand.neutral(0));
    }

    /** Backward-compatible constructor for existing tests/callers without session IDs. */
    public PlayerRecord(String playerId, int slot, Channel channel) {
        this(playerId, "unknown", slot, channel);
    }
}
