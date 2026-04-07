package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import com.indieniinja.world.WorldGraph;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.SimpleChannelInboundHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Netty channel handler — routes incoming messages to session/zone logic.
 *
 * Java equivalent of Python's network/server.py _handle_client() coroutine
 * and the per-message handlers (handle_input, handle_entity_event, etc.).
 *
 * One instance shared across all channels (@ChannelHandler.Sharable).
 * Thread-safety: all mutable state uses ConcurrentHashMap or volatile.
 */
@io.netty.channel.ChannelHandler.Sharable
public final class ServerProtocolHandler extends SimpleChannelInboundHandler<ByteBuf> {

    private static final Logger log = LoggerFactory.getLogger(ServerProtocolHandler.class);

    static final String SERVER_VERSION = "2.0.0";

    /** Zone idle TTL before sim thread is stopped (120 s). */
    private static final long ZONE_IDLE_TTL_MS = 120_000L;

    /** Rooms per hub world — matches ZoneSimulationLoop.DEFAULT_ROOMS. */
    private static final int DEFAULT_ROOMS = 12;

    private final GameSession session;

    /** Active zones keyed by hubId. */
    private final Map<String, ZoneInstance> zones = new ConcurrentHashMap<>();

    /** Zone simulation executor — one thread per zone. */
    private final ExecutorService zoneExecutor =
            Executors.newCachedThreadPool(r -> {
                Thread t = new Thread(r, "ninja-zone-sim");
                t.setDaemon(true);
                return t;
            });

    /** Map channelId → playerId for disconnect lookup. */
    private final Map<String, String> channelToPlayer = new ConcurrentHashMap<>();

    public ServerProtocolHandler(GameSession session) {
        this.session = session;
    }

    // ── Connection lifecycle ──────────────────────────────────────────────────

    @Override
    public void channelActive(ChannelHandlerContext ctx) {
        log.info("Client connected: {}", ctx.channel().remoteAddress());
    }

    @Override
    public void channelInactive(ChannelHandlerContext ctx) {
        String pid = channelToPlayer.remove(ctx.channel().id().asShortText());
        if (pid != null) handleDisconnect(pid, ctx.channel());
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
        log.warn("Channel error ({}): {}", ctx.channel().remoteAddress(), cause.getMessage());
        ctx.close();
    }

    // ── Message routing ───────────────────────────────────────────────────────

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, ByteBuf msg) throws Exception {
        byte[] bytes = new byte[msg.readableBytes()];
        msg.readBytes(bytes);

        WireMessage wire;
        try {
            wire = WireCodec.decodeBody(bytes);
        } catch (Exception ex) {
            log.warn("Malformed message from {}: {}", ctx.channel().remoteAddress(), ex.getMessage());
            return;
        }

        switch (wire.type()) {
            case MessageType.CLIENT_HELLO  -> handleClientHello(ctx, wire);
            case MessageType.INPUT         -> handleInput(ctx, wire);
            case MessageType.ENTITY_EVENT  -> handleEntityEvent(ctx, wire);
            case MessageType.PORTAL_TRAVEL -> handlePortalTravel(ctx, wire);
            default -> log.debug("Unhandled message type '{}' from {}", wire.type(), ctx.channel().remoteAddress());
        }
    }

    // ── Handler: CLIENT_HELLO ─────────────────────────────────────────────────

    private void handleClientHello(ChannelHandlerContext ctx, WireMessage msg) throws Exception {
        String playerId = msg.getString("player_id", UUID.randomUUID().toString());
        String version  = msg.getString("version", "");

        if (!MessageType.PROTOCOL_VERSION.equals(version)) {
            log.warn("Protocol version mismatch — client='{}' server='{}'",
                version, MessageType.PROTOCOL_VERSION);
        }

        int slot = session.claimSlot();
        if (slot < 0) {
            sendMessage(ctx.channel(), MessageType.ERROR,
                Map.of("code", "LOBBY_FULL", "message", "Server is full"));
            ctx.close();
            return;
        }

        PlayerRecord player = new PlayerRecord(playerId, slot, ctx.channel());
        session.players.put(playerId, player);
        channelToPlayer.put(ctx.channel().id().asShortText(), playerId);

        log.info("Player {} joined as slot {}", playerId, slot);

        // SERVER_HELLO
        sendMessage(ctx.channel(), MessageType.SERVER_HELLO, Map.of(
            "player_id",   playerId,
            "slot",        slot,
            "frame",       0,
            "seed",        session.worldSeed,
            "max_players", GameSession.MAX_PLAYERS
        ));

        // LOBBY_UPDATE → all
        broadcastAll(MessageType.LOBBY_UPDATE, Map.of(
            "connected", session.players.size(),
            "max",       GameSession.MAX_PLAYERS,
            "players",   session.lobbyPlayerList()
        ));

        // PLAYER_JOIN → all
        broadcastAll(MessageType.PLAYER_JOIN, Map.of(
            "player_id", playerId,
            "slot",      slot
        ));

        // Start game: immediately on first player (solo/dev), or when full lobby
        if (session.gameStarted.get()) {
            bootstrapLateJoiner(ctx.channel(), player);
        } else {
            startGame();  // start as soon as any player joins
        }
    }

    // ── Handler: INPUT ────────────────────────────────────────────────────────

    @SuppressWarnings("unchecked")
    private void handleInput(ChannelHandlerContext ctx, WireMessage msg) {
        String pid = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;

        PlayerRecord player = session.players.get(pid);
        if (player == null) return;

        Map<String, Object> payload = msg.payload();

        // Update client-reported position/velocity (client-authoritative in Phase A)
        Object posObj = payload.get("pos");
        Object velObj = payload.get("vel");
        if (posObj instanceof List<?> pos && pos.size() == 2) {
            player.posX = ((Number) pos.get(0)).floatValue();
            player.posY = ((Number) pos.get(1)).floatValue();
        }
        if (velObj instanceof List<?> vel && vel.size() == 2) {
            player.velX = ((Number) vel.get(0)).floatValue();
            player.velY = ((Number) vel.get(1)).floatValue();
        }
        Object healthObj = payload.get("health");
        if (healthObj instanceof Number n) player.health = n.intValue();
        Object facingObj = payload.get("facing");
        if (facingObj instanceof Number n) player.facing = n.intValue();
        Object animObj = payload.get("anim_state");
        if (animObj instanceof String s) player.animState = s;

        // Store latest input for simulation
        player.latestInput.set(InputCommand.fromMap(payload));
    }

    // ── Handler: ENTITY_EVENT (Phase 2.5 relay) ───────────────────────────────

    private void handleEntityEvent(ChannelHandlerContext ctx, WireMessage msg) {
        // Relay to all other clients in the same zone
        String pid  = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;

        PlayerRecord sender = session.players.get(pid);
        if (sender == null) return;

        Map<String, Object> payload = msg.payload();
        try {
            byte[] encoded = WireCodec.encodeBody(MessageType.ENTITY_EVENT, payload);
            for (PlayerRecord pr : session.connectedPlayers()) {
                if (!pr.playerId.equals(pid) && pr.hubId.equals(sender.hubId)) {
                    sendEncoded(pr.channel, encoded);
                }
            }
        } catch (Exception ex) {
            log.warn("entity_event relay error: {}", ex.getMessage());
        }
    }

    // ── Handler: PORTAL_TRAVEL ────────────────────────────────────────────────

    private void handlePortalTravel(ChannelHandlerContext ctx, WireMessage msg) {
        String pid = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;

        PlayerRecord player = session.players.get(pid);
        if (player == null) return;

        String destHubId = msg.getString("destination_id", "central_hub");

        // Remove from current zone
        ZoneInstance oldZone = zones.get(player.hubId);
        if (oldZone != null) {
            oldZone.playerIds.remove(pid);
            oldZone.lastActivityMs = System.currentTimeMillis();
            broadcastZone(oldZone, MessageType.ZONE_PRESENCE, Map.of(
                "player_id", pid, "slot", player.slot,
                "hub_id", oldZone.hubId, "action", "departed"
            ));
        }

        // Get or create destination zone (start room of that hub)
        ZoneInstance newZone = getOrCreateStartZone(destHubId);
        player.hubId = newZone.hubId;
        newZone.playerIds.add(pid);

        // Send WORLD_TRANSITION to this player
        try {
            sendMessage(ctx.channel(), MessageType.WORLD_TRANSITION, Map.of(
                "hub_id",     newZone.hubId,
                "seed",       newZone.seed,
                "shape",      newZone.shape,
                "rooms",      newZone.rooms,
                "world_seed", newZone.worldSeed,
                "spawn_x",    newZone.spawnX,
                "spawn_y",    newZone.spawnY
            ));
        } catch (Exception ex) {
            log.error("WORLD_TRANSITION send error: {}", ex.getMessage());
        }

        broadcastZone(newZone, MessageType.ZONE_PRESENCE, Map.of(
            "player_id", pid, "slot", player.slot,
            "hub_id", destHubId, "action", "arrived"
        ));
    }

    // ── Disconnect ────────────────────────────────────────────────────────────

    private void handleDisconnect(String pid, Channel channel) {
        PlayerRecord player = session.players.remove(pid);
        if (player == null) return;

        log.info("Player {} (slot {}) disconnected", pid, player.slot);

        // Remove from zone
        ZoneInstance zone = zones.get(player.hubId);
        if (zone != null) {
            zone.playerIds.remove(pid);
            zone.lastActivityMs = System.currentTimeMillis();
        }

        // Broadcast leave to all remaining players
        broadcastAll(MessageType.PLAYER_LEAVE, Map.of("player_id", pid, "slot", player.slot));
        broadcastAll(MessageType.LOBBY_UPDATE, Map.of(
            "connected", session.players.size(),
            "max",       GameSession.MAX_PLAYERS,
            "players",   session.lobbyPlayerList()
        ));
    }

    // ── Game start ────────────────────────────────────────────────────────────

    private void startGame() {
        if (!session.gameStarted.compareAndSet(false, true)) return; // already started

        log.info("Game starting — seed={}", session.worldSeed);
        ZoneInstance hub = getOrCreateStartZone("central_hub");

        Map<String, Object> startPayload = Map.of(
            "seed",       session.worldSeed,
            "shape",      hub.shape,
            "rooms",      hub.rooms,
            "hub_id",     hub.hubId,
            "world_seed", hub.worldSeed
        );

        for (PlayerRecord pr : session.connectedPlayers()) {
            pr.hubId = hub.hubId;   // zone key, not just "central_hub"
            hub.playerIds.add(pr.playerId);
            try {
                sendMessage(pr.channel, MessageType.GAME_START, startPayload);
            } catch (Exception ex) {
                log.error("GAME_START send error for {}: {}", pr.playerId, ex.getMessage());
            }
        }
    }

    private void bootstrapLateJoiner(Channel channel, PlayerRecord player) {
        ZoneInstance hub = getOrCreateStartZone("central_hub");
        player.hubId = hub.hubId;
        hub.playerIds.add(player.playerId);

        Map<String, Object> startPayload = Map.of(
            "seed",       session.worldSeed,
            "shape",      hub.shape,
            "rooms",      hub.rooms,
            "hub_id",     hub.hubId,
            "world_seed", hub.worldSeed
        );
        try {
            sendMessage(channel, MessageType.GAME_START, startPayload);
        } catch (Exception ex) {
            log.error("Late-join GAME_START error: {}", ex.getMessage());
        }
    }

    // ── Zone management ───────────────────────────────────────────────────────

    /** Zone key format: "masterHubId:gridX:gridY" */
    private static String zoneKey(String masterHubId, int gx, int gy) {
        return masterHubId + ":" + gx + ":" + gy;
    }

    /**
     * Get or create the start-room zone for a hub.  Pre-generates the
     * WorldGraph so we know the start room's grid coordinates before the
     * sim thread starts, enabling per-room zone keying.
     */
    private ZoneInstance getOrCreateStartZone(String masterHubId) {
        long zoneSeed = session.worldSeed ^ masterHubId.hashCode();
        WorldGraph graph = WorldGraph.generate(zoneSeed, DEFAULT_ROOMS, WorldGraph.WorldShape.BLOB);
        WorldGraph.RoomNode startRoom = graph.startRoom();
        String key = zoneKey(masterHubId, startRoom.gridX, startRoom.gridY);

        return zones.computeIfAbsent(key, k -> {
            ZoneInstance zone = new ZoneInstance(
                key, masterHubId, zoneSeed, "standard", DEFAULT_ROOMS,
                session.worldSeed, startRoom.gridX * 32f, startRoom.gridY * 32f
            );
            // Pre-set room state so initSimulator uses this room
            zone.worldGraph          = graph;
            zone.currentRoomSeed     = startRoom.seed;
            zone.currentRoomGridX    = startRoom.gridX;
            zone.currentRoomGridY    = startRoom.gridY;
            zone.currentNeighborDirs = new ArrayList<>(startRoom.neighborDirs());
            startZoneSimLoop(zone);
            log.info("Hub zone '{}' created — start room ({},{}) seed={}",
                key, startRoom.gridX, startRoom.gridY, startRoom.seed);
            return zone;
        });
    }

    /**
     * Get or create a zone for a specific room within a hub's WorldGraph.
     * Called when a player transitions through a door.
     */
    private ZoneInstance getOrCreateRoomZone(String masterHubId, WorldGraph graph,
            WorldGraph.RoomNode room) {
        long zoneSeed = session.worldSeed ^ masterHubId.hashCode();
        String key = zoneKey(masterHubId, room.gridX, room.gridY);

        return zones.computeIfAbsent(key, k -> {
            ZoneInstance zone = new ZoneInstance(
                key, masterHubId, zoneSeed, "standard", DEFAULT_ROOMS,
                session.worldSeed, room.gridX * 32f, room.gridY * 32f
            );
            zone.worldGraph          = graph;
            zone.currentRoomSeed     = room.seed;
            zone.currentRoomGridX    = room.gridX;
            zone.currentRoomGridY    = room.gridY;
            zone.currentNeighborDirs = new ArrayList<>(room.neighborDirs());
            startZoneSimLoop(zone);
            log.info("Room zone '{}' created — ({},{}) seed={}",
                key, room.gridX, room.gridY, room.seed);
            return zone;
        });
    }

    private void startZoneSimLoop(ZoneInstance zone) {
        AtomicBoolean shutdown = new AtomicBoolean(false);
        ZoneSimulationLoop loop = new ZoneSimulationLoop(
            zone, session, shutdown,
            (pid, dir) -> transitionPlayerToRoom(pid, dir)
        );
        Future<?> future = zoneExecutor.submit(loop);
        zone.simFuture = future;
    }

    /**
     * Move a player from their current zone to the adjacent room zone in
     * the given direction.  Called from the sim thread via the transition
     * callback — zone.playerIds has already had the player removed.
     */
    private void transitionPlayerToRoom(String pid, String direction) {
        PlayerRecord pr = session.players.get(pid);
        if (pr == null) return;

        ZoneInstance fromZone = zones.get(pr.hubId);
        if (fromZone == null || fromZone.worldGraph == null) {
            log.warn("Transition: no zone or worldGraph for player {}", pid);
            return;
        }

        WorldGraph.RoomNode nextRoom = fromZone.worldGraph.neighborRoom(
            fromZone.currentRoomGridX, fromZone.currentRoomGridY, direction);
        if (nextRoom == null) {
            log.warn("Transition: no neighbor in '{}' from ({},{})",
                direction, fromZone.currentRoomGridX, fromZone.currentRoomGridY);
            return;
        }

        ZoneInstance toZone = getOrCreateRoomZone(fromZone.masterHubId,
            fromZone.worldGraph, nextRoom);

        // Set spawn position at the entry door of the new room (opposite side)
        float[] spawn = entrySpawn(direction);
        pr.posX  = spawn[0];
        pr.posY  = spawn[1];
        pr.velX  = 0;
        pr.velY  = 0;
        pr.hubId = toZone.hubId;
        toZone.playerIds.add(pid);
        toZone.lastActivityMs = System.currentTimeMillis();

        log.info("Player {} transitioned {} → room ({},{}) zone '{}'",
            pid, direction, nextRoom.gridX, nextRoom.gridY, toZone.hubId);
    }

    /**
     * Spawn position when entering a room through the opposite door.
     * direction = the direction the player exited the previous room.
     */
    private static float[] entrySpawn(String direction) {
        final float TILE   = com.indieniinja.physics.PhysicsConstants.TILE_SIZE;
        final float COLS   = com.indieniinja.physics.PhysicsConstants.ROOM_WIDTH_TILES;
        final float ROWS   = com.indieniinja.physics.PhysicsConstants.ROOM_HEIGHT_TILES;
        final float midX   = (COLS / 2f) * TILE;
        final float midY   = (ROWS / 2f) * TILE;
        return switch (direction) {
            // exited up → enter new room near its bottom door
            case "up"    -> new float[]{midX, (ROWS - 6) * TILE};
            // exited down → enter new room near its top door
            case "down"  -> new float[]{midX, 4 * TILE};
            // exited left → enter new room near its right door
            case "left"  -> new float[]{(COLS - 4) * TILE, midY};
            // exited right → enter new room near its left door
            case "right" -> new float[]{4 * TILE, midY};
            default      -> new float[]{midX, (ROWS - 6) * TILE};
        };
    }

    // ── Wire helpers ──────────────────────────────────────────────────────────

    private static void sendMessage(Channel ch, String type, Map<String, Object> payload)
            throws Exception {
        byte[] body = WireCodec.encodeBody(type, payload);
        sendEncoded(ch, body);
    }

    private static void sendEncoded(Channel ch, byte[] encoded) {
        if (ch.isActive()) {
            ch.writeAndFlush(Unpooled.wrappedBuffer(encoded));
        }
    }

    private void broadcastAll(String type, Map<String, Object> payload) {
        try {
            byte[] encoded = WireCodec.encodeBody(type, payload);
            for (PlayerRecord pr : session.connectedPlayers()) {
                sendEncoded(pr.channel, encoded);
            }
        } catch (Exception ex) {
            log.error("broadcast error ({}): {}", type, ex.getMessage());
        }
    }

    private void broadcastZone(ZoneInstance zone, String type, Map<String, Object> payload) {
        try {
            byte[] encoded = WireCodec.encodeBody(type, payload);
            for (String pid : zone.playerIds) {
                PlayerRecord pr = session.players.get(pid);
                if (pr != null) sendEncoded(pr.channel, encoded);
            }
        } catch (Exception ex) {
            log.error("zone broadcast error ({}): {}", type, ex.getMessage());
        }
    }
}
