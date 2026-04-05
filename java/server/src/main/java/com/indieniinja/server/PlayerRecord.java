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

    // Last known player state — updated on each INPUT message, used in WORLD_STATE
    // Default spawn: 5 tiles from left wall (x=160), above the floor (floor top y=960,
    // player height=56, so posY=904 puts player bottom exactly on the floor).
    // In Y-DOWN coords (matching LevelLayout.buildTestLayout 64×32 grid).
    public volatile float  posX = 160f, posY = 904f;
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
