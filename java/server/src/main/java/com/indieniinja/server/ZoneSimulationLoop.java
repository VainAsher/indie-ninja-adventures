package com.indieniinja.server;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.MessageType;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
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

    // ── Simulator init ────────────────────────────────────────────────────────

    /**
     * Build and attach a GameSimulator to this zone using the LevelLayout.
     * Called once before the loop starts (from ServerProtocolHandler.getOrCreateZone).
     */
    public static void initSimulator(ZoneInstance zone) {
        LevelLayout layout = LevelLayout.buildTestLayout(zone.seed);
        zone.simulator = new GameSimulator(zone.seed, zone.hubId, layout);
        log.info("[Zone {}] GameSimulator initialised (seed={})", zone.hubId, zone.seed);
    }

    @Override
    public void run() {
        // Phase B: initialise the server-side GameSimulator for this zone
        initSimulator(zone);
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
     * Phase B: drive the Java GameSimulator one tick.
     *
     * Player positions remain client-authoritative (written from INPUT messages
     * by ServerProtocolHandler into PlayerRecord.posX/Y). The simulator syncs
     * each SimPlayer's physics state from the PlayerRecord before stepping, so
     * enemies and pickups respond to accurate player positions.
     *
     * Phase C will flip players to full server-authoritative movement.
     */
    private void simulateTick() {
        GameSimulator sim = zone.simulator;
        if (sim == null) return;

        // Sync client-reported positions into the SimPlayers before each tick
        java.util.Map<Integer, InputCommand> inputs = new java.util.LinkedHashMap<>();
        for (String pid : zone.playerIds) {
            PlayerRecord pr = session.players.get(pid);
            if (pr == null) continue;

            SimPlayer sp = sim.getPlayers().get(pr.slot);
            if (sp != null) {
                // Client-authoritative: overwrite sim position from latest INPUT
                sp.physics.x   = pr.posX;
                sp.physics.y   = pr.posY;
                sp.physics.vx  = pr.velX;
                sp.physics.vy  = pr.velY;
                sp.facing      = pr.facing;
                sp.animState   = pr.animState;
                sp.isDead      = pr.isDead;
                sp.health      = pr.health;
            } else {
                // Player not yet in sim — add them
                SimPlayer newSp = new SimPlayer(pid, pr.slot, pr.posX, pr.posY);
                newSp.health    = pr.health;
                newSp.facing    = pr.facing;
                newSp.animState = pr.animState;
                sim.addPlayer(newSp);
            }

            InputCommand cmd = pr.latestInput.get();
            if (cmd != null) inputs.put(pr.slot, cmd);
        }

        sim.step(inputs);
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

    /**
     * Phase B: get snapshot from GameSimulator (enemies + pickups + platforms included).
     * Delta encoding applied on top for bandwidth efficiency.
     */
    private WorldSnapshot buildSnapshot(boolean full, List<PlayerRecord> zonePlayers) {
        GameSimulator sim = zone.simulator;

        // Full snapshot from the authoritative simulator
        WorldSnapshot snap = (sim != null)
            ? sim.getSnapshot(zone.frame.get())
            : buildFallbackSnapshot(zonePlayers);

        snap.isDelta = !full;

        if (!full) {
            // Swap full lists with delta lists computed by DeltaEncoder
            List<EnemyState>    allEnemies   = snap.enemies;
            List<PickupState>   allPickups   = snap.pickups;
            List<PlatformState> allPlatforms = snap.platformStates;

            snap.enemies        = Collections.emptyList();
            snap.pickups        = Collections.emptyList();
            snap.platformStates = Collections.emptyList();

            snap.enemiesChanged   = zone.deltaEncoder.enemiesChanged(allEnemies);
            snap.enemiesRemoved   = zone.deltaEncoder.enemiesRemoved(allEnemies);
            snap.pickupsChanged   = zone.deltaEncoder.pickupsChanged(allPickups);
            snap.pickupsRemoved   = zone.deltaEncoder.pickupsRemoved(allPickups);
            snap.platformsChanged = zone.deltaEncoder.platformsChanged(allPlatforms);
            snap.platformsRemoved = zone.deltaEncoder.platformsRemoved(allPlatforms);
        }

        return snap;
    }

    /** Fallback for the brief window before the simulator is ready (rare). */
    private WorldSnapshot buildFallbackSnapshot(List<PlayerRecord> zonePlayers) {
        WorldSnapshot snap = new WorldSnapshot();
        snap.frame  = zone.frame.get();
        snap.seed   = zone.seed;
        snap.hubId  = zone.hubId;
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
