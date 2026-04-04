package com.indieniinja.server;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.MessageType;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WorldSnapshot;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.Channel;
import java.util.concurrent.locks.LockSupport;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 60 Hz zone simulation loop — runs on a dedicated platform thread.
 *
 * Java equivalent of Python's network/server.py _zone_simulation_loop coroutine.
 *
 * Key design decisions:
 *  - LockSupport.parkNanos for sub-millisecond sleep precision (avoids
 *    Thread.sleep(16) quantization on Windows which has ~15ms minimum)
 *  - AtomicReference<InputCommand> on PlayerRecord — Netty I/O thread writes,
 *    this loop reads — zero lock on the hot path
 *  - Encode snapshot once, write to all zone members (zero-copy multicast)
 *  - Broadcast every 3rd tick (20 Hz) matching Python server behaviour
 *  - Full snapshot every FULL_SNAPSHOT_INTERVAL broadcasts (~3 seconds)
 */
public final class ZoneSimulationLoop implements Runnable {

    private static final Logger log = LoggerFactory.getLogger(ZoneSimulationLoop.class);

    static final long TICK_NS              = 1_000_000_000L / 60;  // 16,666,666 ns
    static final int  BROADCAST_EVERY      = 3;    // 20 Hz — matches Python
    static final int  FULL_SNAPSHOT_EVERY  = 60;   // 3 s full snapshot

    /** Idle zone reaper: tear down zone after this many ms without any player. */
    static final long IDLE_TTL_MS = 120_000L;  // 120 s — matches Python

    private final ZoneInstance   zone;
    private final GameSession    session;
    private final AtomicBoolean  shutdown;

    public ZoneSimulationLoop(ZoneInstance zone, GameSession session, AtomicBoolean shutdown) {
        this.zone     = zone;
        this.session  = session;
        this.shutdown = shutdown;
    }

    @Override
    public void run() {
        log.info("[Zone {}] simulation loop started", zone.hubId);
        long nextTickNs   = System.nanoTime();
        int  broadcastCtr = 0;

        while (!shutdown.get()) {
            long now = System.nanoTime();

            if (now < nextTickNs) {
                // Sleep until next tick — use parkNanos for precision
                long sleepNs = nextTickNs - now;
                if (sleepNs > 1_000_000L) {
                    // More than 1ms to go — sleep most of it
                    LockSupport.parkNanos(sleepNs - 500_000L);
                }
                // Spin the last ~0.5ms for precision
                while (System.nanoTime() < nextTickNs) {
                    Thread.onSpinWait();
                }
            }

            nextTickNs += TICK_NS;

            // ── Simulate one tick ─────────────────────────────────────────────
            simulateTick();
            zone.frame.incrementAndGet();

            // ── Broadcast ─────────────────────────────────────────────────────
            if (++broadcastCtr >= BROADCAST_EVERY) {
                broadcastCtr = 0;
                boolean fullSnap = (++zone.fullSnapCountdown >= FULL_SNAPSHOT_EVERY);
                if (fullSnap) {
                    zone.fullSnapCountdown = 0;
                    zone.deltaEncoder.reset();
                }
                broadcastWorldState(fullSnap);
            }

            // ── Idle zone reaping ─────────────────────────────────────────────
            if (zone.isEmpty()) {
                long idleMs = System.currentTimeMillis() - zone.lastActivityMs;
                if (idleMs > IDLE_TTL_MS) {
                    log.info("[Zone {}] idle for {}s — shutting down", zone.hubId, idleMs / 1000);
                    break;
                }
            }
        }

        log.info("[Zone {}] simulation loop stopped", zone.hubId);
    }

    // ── Simulation tick ───────────────────────────────────────────────────────

    /**
     * Placeholder for the real game simulation step.
     *
     * Phase A: The Java server proxies inputs to/from Python-side simulation.
     * Phase B: This will call JavaGameSimulator.step(inputs, FIXED_DT).
     *
     * For now, applies player inputs to the PlayerRecord position fields so that
     * WORLD_STATE reflects the client-reported positions (matching Python Phase 1/2.5 behaviour).
     */
    private void simulateTick() {
        for (String pid : zone.playerIds) {
            PlayerRecord player = session.players.get(pid);
            if (player == null) continue;

            InputCommand input = player.latestInput.get();
            if (input == null) continue;

            // Phase A: client-authoritative — positions come from INPUT messages.
            // No server-side physics in Phase A; PhysicsSystem will drive this in Phase B.
        }
    }

    // ── Broadcast ─────────────────────────────────────────────────────────────

    private void broadcastWorldState(boolean fullSnapshot) {
        List<PlayerRecord> zonePlayers = playersInZone();
        if (zonePlayers.isEmpty()) return;

        WorldSnapshot snap = buildSnapshot(fullSnapshot, zonePlayers);
        Map<String, Object> payload = snap.toMap();

        byte[] encoded;
        try {
            encoded = WireCodec.encodeBody(MessageType.WORLD_STATE, payload);
        } catch (Exception ex) {
            log.error("[Zone {}] snapshot encode error: {}", zone.hubId, ex.getMessage());
            return;
        }

        // Write once-encoded bytes to all zone members — zero re-encoding
        for (PlayerRecord p : zonePlayers) {
            Channel ch = p.channel;
            if (ch.isActive()) {
                ByteBuf buf = Unpooled.wrappedBuffer(encoded);
                // LengthFieldPrepender in the Netty pipeline adds the 4-byte header
                ch.writeAndFlush(buf).addListener(f -> {
                    if (!f.isSuccess()) {
                        log.warn("[Zone {}] write failed for player {}: {}",
                            zone.hubId, p.playerId, f.cause().getMessage());
                    }
                });
            }
        }
    }

    private WorldSnapshot buildSnapshot(boolean full, List<PlayerRecord> zonePlayers) {
        WorldSnapshot snap = new WorldSnapshot();
        snap.frame  = zone.frame.get();
        snap.seed   = zone.seed;
        snap.hubId  = zone.hubId;
        snap.isDelta = !full;

        // Players always sent in full (never delta'd)
        for (PlayerRecord pr : zonePlayers) {
            PlayerState ps = new PlayerState();
            ps.playerId  = pr.playerId;
            ps.slot      = pr.slot;
            ps.posX      = pr.posX;
            ps.posY      = pr.posY;
            ps.velX      = pr.velX;
            ps.velY      = pr.velY;
            ps.health    = pr.health;
            ps.facing    = pr.facing;
            ps.isDead    = pr.isDead;
            ps.animState = pr.animState;
            snap.players.add(ps);
        }

        // Phase A: no server-side entities yet — send empty lists
        // Phase B: populate from JavaGameSimulator.getEnemyStates(), etc.
        List<EnemyState>    enemies   = Collections.emptyList();
        List<PickupState>   pickups   = Collections.emptyList();
        List<PlatformState> platforms = Collections.emptyList();

        if (full) {
            snap.enemies        = enemies;
            snap.pickups        = pickups;
            snap.platformStates = platforms;
        } else {
            snap.enemiesChanged   = zone.deltaEncoder.enemiesChanged(enemies);
            snap.enemiesRemoved   = zone.deltaEncoder.enemiesRemoved(enemies);
            snap.pickupsChanged   = zone.deltaEncoder.pickupsChanged(pickups);
            snap.pickupsRemoved   = zone.deltaEncoder.pickupsRemoved(pickups);
            snap.platformsChanged = zone.deltaEncoder.platformsChanged(platforms);
            snap.platformsRemoved = zone.deltaEncoder.platformsRemoved(platforms);
        }

        return snap;
    }

    private List<PlayerRecord> playersInZone() {
        List<PlayerRecord> result = new ArrayList<>(zone.playerIds.size());
        for (String pid : zone.playerIds) {
            PlayerRecord pr = session.players.get(pid);
            if (pr != null) result.add(pr);
        }
        return result;
    }
}
