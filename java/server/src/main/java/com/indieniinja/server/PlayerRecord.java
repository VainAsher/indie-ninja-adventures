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
    public final int     slot;
    public final Channel channel;

    /** Written by Netty I/O thread; read by ZoneSimulationLoop. */
    public final AtomicReference<InputCommand> latestInput = new AtomicReference<>();

    // Default spawn: 5 tiles from left wall (x=160), above the procedural floor.
    // Procedural 128×128 grid: floor top = row 124 → y = 124 × 32 = 3968.
    // Player height = 56 → posY = 3968 − 56 = 3912.
    public volatile float  posX = 160f, posY = 3912f;
    public volatile float  velX = 0f, velY = 0f;
    public volatile int    health = 5;
    public volatile int    facing = 1;     // 1=right, -1=left
    public volatile boolean isDead = false;
    public volatile String  animState = "";

    // Phase 4: which zone/hub this player is currently in
    public volatile String hubId = "central_hub";

    // Reconnect grace: slot reservation deadline (epoch ms); 0 = no reservation
    public volatile long reservedUntilMs = 0;

    public PlayerRecord(String playerId, int slot, Channel channel) {
        this.playerId = playerId;
        this.slot     = slot;
        this.channel  = channel;
        // Neutral input until first packet arrives
        this.latestInput.set(InputCommand.neutral(0));
    }
}
