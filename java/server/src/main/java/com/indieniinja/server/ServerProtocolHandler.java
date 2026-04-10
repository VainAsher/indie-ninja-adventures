package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import com.indieniinja.sim.GameMode;
import com.indieniinja.world.HubRegistry;
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
    private final ConcurrentHashMap<String, ZoneInstance> zones = new ConcurrentHashMap<>();

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
            case MessageType.TRADE_REQUEST -> handleTradeRequest(ctx, wire);
            case MessageType.CRAFT_REQUEST -> handleCraftRequest(ctx, wire);
            case MessageType.USE_ITEM      -> handleUseItem(ctx, wire);
            case MessageType.EQUIP_ITEM    -> handleEquipItem(ctx, wire);
            default -> log.debug("Unhandled message type '{}' from {}", wire.type(), ctx.channel().remoteAddress());
        }
    }

    // ── Handler: CLIENT_HELLO ─────────────────────────────────────────────────

    private void handleClientHello(ChannelHandlerContext ctx, WireMessage msg) throws Exception {
        String playerId  = msg.getString("player_id", UUID.randomUUID().toString());
        String version   = msg.getString("version", "");
        GameMode reqMode = GameMode.fromWire(msg.getString("game_mode", "arcade"));

        if (!MessageType.PROTOCOL_VERSION.equals(version)) {
            log.warn("Protocol version mismatch — client='{}' server='{}'",
                version, MessageType.PROTOCOL_VERSION);
        }

        int slot = session.claimSlot(playerId);
        if (slot < 0) {
            sendMessage(ctx.channel(), MessageType.ERROR,
                Map.of("code", "LOBBY_FULL", "message", "Server is full"));
            ctx.close();
            return;
        }

        PlayerRecord player = new PlayerRecord(playerId, slot, ctx.channel());
        session.players.put(playerId, player);
        channelToPlayer.put(ctx.channel().id().asShortText(), playerId);
        // First player's requested mode wins for the whole session
        if (slot == 0) session.gameMode = reqMode;

        log.info("Player {} joined as slot {} mode={}", playerId, slot, session.gameMode.wire);

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

        // Phase B: server-authoritative physics — the sim thread owns posX/Y/vel/health.
        // ONLY update latestInput; the sim reads it next tick and drives all state.
        // Removed Phase A client-pos writes (they caused a race where the Netty thread
        // could overwrite the door-entry spawn position set by doRoomTransition() before
        // the new zone's sim thread consumed it, causing players to spawn at the wrong
        // room-local coordinates after a room crossing.)
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

        // ── Loop 16: ability-gate check ───────────────────────────────────────
        // Look up the destination hub's required ability and verify the player has it.
        HubRegistry.HubDef destHub = HubRegistry.get(destHubId);
        if (!destHub.requiredAbility().isEmpty()) {
            ZoneInstance curZone = zones.get(player.hubId);
            if (curZone != null && curZone.simulator != null) {
                com.indieniinja.sim.SimPlayer sp = curZone.simulator.getPlayer(player.slot);
                if (sp != null && !sp.unlockedAbilities.contains(destHub.requiredAbility())) {
                    // Player lacks the required ability — send a denial notification
                    try {
                        sendMessage(ctx.channel(), MessageType.ERROR, Map.of(
                            "text", "Requires ability: " + destHub.requiredAbility(),
                            "category", "portal_denied"
                        ));
                    } catch (Exception ignored) {}
                    log.info("PORTAL_TRAVEL denied: pid={} lacks '{}' for hub '{}'",
                        pid, destHub.requiredAbility(), destHubId);
                    return;
                }
            }
        }

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

    // ── Handler: TRADE_REQUEST ────────────────────────────────────────────────

    private void handleTradeRequest(ChannelHandlerContext ctx, WireMessage msg) {
        String pid = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;
        PlayerRecord player = session.players.get(pid);
        if (player == null) return;

        String  npcId  = msg.getString("npc_id",  "");
        String  itemId = msg.getString("item_id", "");
        int     qty    = (int) msg.getLong("quantity", 1L);
        boolean isBuy  = msg.getBool("is_buy", true);

        ZoneInstance zone = zones.get(player.hubId);
        if (zone == null || zone.simulator == null) return;

        boolean ok = zone.simulator.handleTradeRequest(player.slot, npcId, itemId, qty, isBuy);
        log.debug("TRADE_REQUEST pid={} npc={} item={} qty={} buy={} → {}", pid, npcId, itemId, qty, isBuy, ok);
    }

    // ── Handler: CRAFT_REQUEST ───────────────────────────────────────────────

    private void handleCraftRequest(ChannelHandlerContext ctx, WireMessage msg) {
        String pid = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;
        PlayerRecord player = session.players.get(pid);
        if (player == null) return;
        String recipeId = msg.getString("recipe_id", "");
        ZoneInstance zone = zones.get(player.hubId);
        if (zone == null || zone.simulator == null) return;
        boolean ok = zone.simulator.handleCraftRequest(player.slot, recipeId);
        log.debug("CRAFT_REQUEST pid={} recipe={} → {}", pid, recipeId, ok);
    }

    // ── Handler: USE_ITEM ─────────────────────────────────────────────────────

    private void handleUseItem(ChannelHandlerContext ctx, WireMessage msg) {
        String pid = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;
        PlayerRecord player = session.players.get(pid);
        if (player == null) return;
        String itemId = msg.getString("item_id", "");
        ZoneInstance zone = zones.get(player.hubId);
        if (zone == null || zone.simulator == null) return;
        boolean ok = zone.simulator.handleUseItem(player.slot, itemId);
        log.debug("USE_ITEM pid={} item={} → {}", pid, itemId, ok);
    }

    // ── Handler: EQUIP_ITEM ───────────────────────────────────────────────────

    private void handleEquipItem(ChannelHandlerContext ctx, WireMessage msg) {
        String pid = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;
        PlayerRecord player = session.players.get(pid);
        if (player == null) return;
        String itemId = msg.getString("item_id", "");
        ZoneInstance zone = zones.get(player.hubId);
        if (zone == null || zone.simulator == null) return;
        boolean ok = zone.simulator.handleEquipItem(player.slot, itemId);
        log.debug("EQUIP_ITEM pid={} item={} → {}", pid, itemId, ok);
    }

    // ── Disconnect ────────────────────────────────────────────────────────────

    private void handleDisconnect(String pid, Channel channel) {
        PlayerRecord player = session.players.remove(pid);
        if (player == null) return;

        log.info("Player {} (slot {}) disconnected", pid, player.slot);

        // Release slot back to pool (player can reclaim it on reconnect)
        session.releaseSlot(pid, player.slot);

        // Remove SimPlayer from zone simulator so entity disappears from snapshots
        ZoneInstance zone = zones.get(player.hubId);
        if (zone != null) {
            zone.playerIds.remove(pid);
            zone.lastActivityMs = System.currentTimeMillis();
            if (zone.simulator != null) {
                zone.simulator.removePlayer(player.slot);
            }
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

        // Send cached full snapshot if available — client gets immediate world state
        // instead of waiting up to ~3 s for the next full-snapshot interval.
        Map<String, Object> cachedState = session.zoneStateCache.get(hub.hubId);
        if (cachedState != null) {
            try {
                byte[] encoded = WireCodec.encodeBody(MessageType.WORLD_STATE, cachedState);
                sendEncoded(channel, encoded);
                log.debug("Late-join {} received cached zone state for hub '{}'",
                    player.playerId, hub.hubId);
            } catch (Exception ex) {
                log.warn("Late-join cached state send error for {}: {}", player.playerId, ex.getMessage());
            }
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
        // Use HubRegistry to pick the correct seed offset, room count, and graph shape
        HubRegistry.HubDef hubDef  = HubRegistry.get(masterHubId);
        long zoneSeed = HubRegistry.hubSeed(session.worldSeed, masterHubId);
        int  roomCount = hubDef.roomCount();
        WorldGraph.WorldShape shape = WorldGraph.WorldShape.valueOf(hubDef.graphShape());
        WorldGraph graph = WorldGraph.generate(zoneSeed, roomCount, shape);
        WorldGraph.RoomNode startRoom = graph.startRoom();
        String key = zoneKey(masterHubId, startRoom.gridX, startRoom.gridY);

        return zones.computeIfAbsent(key, k -> {
            ZoneInstance zone = new ZoneInstance(
                key, masterHubId, zoneSeed, hubDef.graphShape(), roomCount,
                session.worldSeed, startRoom.gridX * 32f, startRoom.gridY * 32f
            );
            // Pre-set room state so initSimulator uses this room
            zone.worldGraph          = graph;
            zone.currentRoomSeed     = startRoom.seed;
            zone.currentRoomGridX    = startRoom.gridX;
            zone.currentRoomGridY    = startRoom.gridY;
            zone.currentNeighborDirs = new ArrayList<>(startRoom.neighborDirs());
            zone.currentRoomType     = startRoom.type.wire();
            zone.gameMode            = session.gameMode;
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
        HubRegistry.HubDef hubDef = HubRegistry.get(masterHubId);
        long zoneSeed = HubRegistry.hubSeed(session.worldSeed, masterHubId);
        String key = zoneKey(masterHubId, room.gridX, room.gridY);

        return zones.computeIfAbsent(key, k -> {
            ZoneInstance zone = new ZoneInstance(
                key, masterHubId, zoneSeed, hubDef.graphShape(), hubDef.roomCount(),
                session.worldSeed, room.gridX * 32f, room.gridY * 32f
            );
            zone.worldGraph          = graph;
            zone.currentRoomSeed     = room.seed;
            zone.currentRoomGridX    = room.gridX;
            zone.currentRoomGridY    = room.gridY;
            zone.currentNeighborDirs = new ArrayList<>(room.neighborDirs());
            zone.currentRoomType     = room.type.wire();
            startZoneSimLoop(zone);
            log.info("Room zone '{}' created — ({},{}) seed={}",
                key, room.gridX, room.gridY, room.seed);
            return zone;
        });
    }

    private void startZoneSimLoop(ZoneInstance zone) {
        AtomicBoolean shutdown = new AtomicBoolean(false);
        ZoneSimulationLoop loop = new ZoneSimulationLoop(zone, session, shutdown, zones, zoneExecutor);
        Future<?> future = zoneExecutor.submit(loop);
        zone.simFuture = future;
    }

    /**
     * (Door transitions replaced by ZoneSimulationLoop.checkRoomCrossings()
     *  which detects room boundary crossings automatically from player physics.)
     */

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
