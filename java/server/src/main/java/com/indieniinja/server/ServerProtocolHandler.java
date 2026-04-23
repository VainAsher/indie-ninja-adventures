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
import java.util.concurrent.atomic.AtomicLong;

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
    private static final String PORTAL_TRANSITION_INTER_HUB = "inter_hub";
    private static final String PORTAL_TRANSITION_MISSION_RETURN = "mission_return";
    private static final String ENTITY_EVENT_MISSION_SEED_PICKUPS = "mission_seed_pickups";
    private static final String ENTITY_EVENT_MISSION_SEED_PICKUPS_CLEAR = "mission_seed_pickups_clear";
    private static final int MISSION_SEED_MAX_ITEM_TYPES = 24;
    private static final int MISSION_SEED_MAX_PER_ITEM = 16;
    private static final int MISSION_SEED_MAX_TOTAL = 64;

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
    /** Latest mission pickup seed contract keyed by player+zone for late-join/rejoin reconcile. */
    private final Map<String, MissionPickupSeedContract> missionPickupSeedContractsByPlayerZone =
        new ConcurrentHashMap<>();
    private final AtomicLong missionPickupReseedSeq = new AtomicLong(0L);

    public ServerProtocolHandler(GameSession session) {
        this.session = session;
    }

    private record MissionPickupSeedContract(
        String missionId,
        java.util.Map<String, Integer> itemCounts
    ) {}

    // ── Connection lifecycle ──────────────────────────────────────────────────

    @Override
    public void channelActive(ChannelHandlerContext ctx) {
        log.info("Client connected: remote={} channel={}",
            ctx.channel().remoteAddress(), ctx.channel().id().asShortText());
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
        String sessionId = normalizeSessionId(msg.getString("session_id", ""));
        String version   = msg.getString("version", "");
        GameMode reqMode = GameMode.fromWire(msg.getString("game_mode", "arcade"));

        if (!MessageType.PROTOCOL_VERSION.equals(version)) {
            log.warn("Protocol version mismatch — player={} session={} client='{}' server='{}'",
                playerId, sessionId, version, MessageType.PROTOCOL_VERSION);
        }

        int slot = session.claimSlot(playerId);
        if (slot < 0) {
            sendMessage(ctx.channel(), MessageType.ERROR,
                Map.of("code", "LOBBY_FULL", "message", "Server is full"));
            ctx.close();
            return;
        }

        PlayerRecord player = new PlayerRecord(playerId, sessionId, slot, ctx.channel());
        session.players.put(playerId, player);
        channelToPlayer.put(ctx.channel().id().asShortText(), playerId);
        // First player's requested mode wins for the whole session
        if (slot == 0) session.gameMode = reqMode;

        log.info("Player joined: player={} session={} slot={} mode={} remote={}",
            playerId, sessionId, slot, session.gameMode.wire, ctx.channel().remoteAddress());

        // SERVER_HELLO
        sendMessage(ctx.channel(), MessageType.SERVER_HELLO, Map.of(
            "player_id",   playerId,
            "session_id",  sessionId,
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
            "session_id", sessionId,
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
        // Relay to all other clients in the same zone (except control events).
        String pid  = channelToPlayer.get(ctx.channel().id().asShortText());
        if (pid == null) return;

        PlayerRecord sender = session.players.get(pid);
        if (sender == null) return;

        Map<String, Object> payload = msg.payload();
        if (isMissionPickupSeedEvent(payload)) {
            queueMissionPickupSeedRequest(sender, payload);
            return;
        }
        if (isMissionPickupSeedClearEvent(payload)) {
            clearMissionPickupSeedContract(sender, payload);
            return;
        }
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
        String transitionType = normalizePortalTransitionType(msg.getString(
            "transition_type",
            PORTAL_TRANSITION_INTER_HUB
        ));
        boolean missionReturn = PORTAL_TRANSITION_MISSION_RETURN.equals(transitionType);
        ZoneInstance oldZone = zones.get(player.hubId);
        String originHubId = oldZone != null ? oldZone.masterHubId : player.hubId;

        // ── Loop 16: ability-gate check ───────────────────────────────────────
        // Look up the destination hub's required ability and verify the player has it.
        HubRegistry.HubDef destHub = HubRegistry.get(destHubId);
        if (!destHub.requiredAbility().isEmpty()) {
            if (oldZone != null && oldZone.simulator != null) {
                com.indieniinja.sim.SimPlayer sp = oldZone.simulator.getPlayer(player.slot);
                if (sp != null && !sp.unlockedAbilities.contains(destHub.requiredAbility())) {
                    // Player lacks the required ability — send a denial notification
                    try {
                        sendMessage(ctx.channel(), MessageType.ERROR, Map.of(
                            "text", "Requires ability: " + destHub.requiredAbility(),
                            "category", "portal_denied"
                        ));
                    } catch (Exception ignored) {}
                    log.info(
                        "[Server][Playtest][Portal] portal denied type={} player_id={} session_id={} origin_hub_id={} destination_hub_id={} required_ability={}",
                        transitionType, pid, player.sessionId, originHubId, destHubId, destHub.requiredAbility()
                    );
                    return;
                }
            }
        }

        // Remove from current zone
        if (oldZone != null) {
            oldZone.playerIds.remove(pid);
            oldZone.lastActivityMs = System.currentTimeMillis();
            forgetMissionPickupSeedContract(pid, oldZone.hubId);
            broadcastZone(oldZone, MessageType.ZONE_PRESENCE, Map.of(
                "player_id", pid, "slot", player.slot,
                "hub_id", oldZone.hubId, "action", "departed"
            ));
        }
        if (missionReturn) {
            int clearedContracts = forgetMissionPickupSeedContractsForPlayer(pid);
            if (clearedContracts > 0) {
                log.info(
                    "[Mission][Net] mission_return cleared {} mission pickup seed contract(s) player={} session={} slot={}",
                    clearedContracts, pid, player.sessionId, player.slot
                );
            }
        }

        // Get or create destination zone (start room of that hub)
        ZoneInstance newZone = getOrCreateStartZone(destHubId);
        String destinationSpawnRoomId = newZone.hubId;
        player.hubId = newZone.hubId;
        newZone.playerIds.add(pid);
        if (!missionReturn) {
            queueMissionPickupReseedForPlayerIfPresent(player, newZone);
        }
        log.info(
            "[Server][Playtest][Portal] portal travel type={} player_id={} session_id={} origin_hub_id={} destination_hub_id={} destination_spawn_room_id={}",
            transitionType, pid, player.sessionId, originHubId, destHubId, destinationSpawnRoomId
        );

        // Send WORLD_TRANSITION to this player
        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("hub_id", newZone.hubId);
            payload.put("seed", newZone.seed);
            payload.put("shape", newZone.shape);
            payload.put("rooms", newZone.rooms);
            payload.put("world_seed", newZone.worldSeed);
            payload.put("spawn_x", newZone.spawnX);
            payload.put("spawn_y", newZone.spawnY);
            payload.put("transition_type", transitionType);
            payload.put("origin_hub_id", originHubId);
            payload.put("destination_hub_id", destHubId);
            payload.put("destination_spawn_room_id", destinationSpawnRoomId);
            sendMessage(ctx.channel(), MessageType.WORLD_TRANSITION, payload);
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

        long connectedMs = Math.max(0L, System.currentTimeMillis() - player.connectedAtMs);
        log.info("Player disconnected: player={} session={} slot={} connected_ms={}",
            pid, player.sessionId, player.slot, connectedMs);

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
        int clearedMissionContracts = forgetMissionPickupSeedContractsForPlayerExceptHub(
            pid,
            player.hubId
        );
        if (clearedMissionContracts > 0) {
            log.info(
                "[Mission][Net] cleared {} stale mission pickup seed contract(s) on disconnect player={} session={} slot={} kept_hub={}",
                clearedMissionContracts, pid, player.sessionId, player.slot, player.hubId
            );
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
        // Late joiners may receive a cached full snapshot that is slightly stale.
        // Force the next live zone broadcast to be a full snapshot so state
        // (especially pickups) converges immediately on authoritative data.
        hub.forceNextFullSnapshot.set(true);
        queueMissionPickupReseedForPlayerIfPresent(player, hub);

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

    private static boolean isMissionPickupSeedEvent(Map<String, Object> payload) {
        if (payload == null) return false;
        Object event = payload.get("event");
        return event != null && ENTITY_EVENT_MISSION_SEED_PICKUPS.equals(event.toString());
    }

    private static boolean isMissionPickupSeedClearEvent(Map<String, Object> payload) {
        if (payload == null) return false;
        Object event = payload.get("event");
        return event != null && ENTITY_EVENT_MISSION_SEED_PICKUPS_CLEAR.equals(event.toString());
    }

    private void queueMissionPickupSeedRequest(PlayerRecord sender, Map<String, Object> payload) {
        ZoneInstance zone = zones.get(sender.hubId);
        if (zone == null) return;

        String requestId = normalizeRequestId(payload.get("request_id"));
        if (requestId.isBlank()) {
            log.warn("[Mission][Net] dropped pickup seed event with empty request_id player={} hub={}",
                sender.playerId, sender.hubId);
            return;
        }

        String missionId = normalizeMissionId(payload.get("mission_id"));
        Map<String, Integer> itemCounts = sanitizeMissionItemCounts(payload.get("item_counts"));
        if (itemCounts.isEmpty()) {
            log.info("[Mission][Net] dropped pickup seed request_id={} mission={} player={} (no valid objective items)",
                requestId, missionId, sender.playerId);
            return;
        }

        zone.pendingMissionPickupSeeds.add(new ZoneInstance.PendingMissionPickupSeed(
            requestId,
            missionId,
            sender.playerId,
            sender.slot,
            java.util.Collections.unmodifiableMap(new LinkedHashMap<>(itemCounts))
        ));
        rememberMissionPickupSeedContract(sender.playerId, sender.hubId, missionId, itemCounts);
        log.info("[Mission][Net] queued pickup seed request_id={} mission={} player={} slot={} items={} hub={}",
            requestId, missionId, sender.playerId, sender.slot, itemCounts, sender.hubId);
    }

    private void rememberMissionPickupSeedContract(
        String playerId,
        String zoneId,
        String missionId,
        Map<String, Integer> itemCounts
    ) {
        if (playerId == null || playerId.isBlank()) return;
        if (zoneId == null || zoneId.isBlank()) return;
        if (itemCounts == null || itemCounts.isEmpty()) return;
        missionPickupSeedContractsByPlayerZone.put(
            missionPickupSeedContractKey(playerId, zoneId),
            new MissionPickupSeedContract(
                missionId == null ? "" : missionId,
                java.util.Collections.unmodifiableMap(new LinkedHashMap<>(itemCounts))
            )
        );
    }

    private void forgetMissionPickupSeedContract(String playerId, String zoneId) {
        if (playerId == null || playerId.isBlank()) return;
        if (zoneId == null || zoneId.isBlank()) return;
        missionPickupSeedContractsByPlayerZone.remove(missionPickupSeedContractKey(playerId, zoneId));
    }

    private int forgetMissionPickupSeedContractsForPlayerExceptHub(String playerId, String keepZoneId) {
        if (playerId == null || playerId.isBlank()) return 0;
        String keepKey = (keepZoneId == null || keepZoneId.isBlank())
            ? ""
            : missionPickupSeedContractKey(playerId, keepZoneId);
        String keyPrefix = playerId + "|";
        int removed = 0;
        for (String key : missionPickupSeedContractsByPlayerZone.keySet()) {
            if (!key.startsWith(keyPrefix)) continue;
            if (!keepKey.isEmpty() && keepKey.equals(key)) continue;
            if (missionPickupSeedContractsByPlayerZone.remove(key) != null) {
                removed++;
            }
        }
        return removed;
    }

    private int forgetMissionPickupSeedContractsForPlayer(String playerId) {
        return forgetMissionPickupSeedContractsForPlayerExceptHub(playerId, null);
    }

    private void clearMissionPickupSeedContract(PlayerRecord sender, Map<String, Object> payload) {
        if (sender == null) return;
        String missionId = normalizeMissionId(payload == null ? null : payload.get("mission_id"));
        String contractKey = missionPickupSeedContractKey(sender.playerId, sender.hubId);
        MissionPickupSeedContract existing = missionPickupSeedContractsByPlayerZone.get(contractKey);
        if (existing == null) return;
        String existingMissionId = normalizeMissionId(existing.missionId());
        if (!missionId.isBlank() && !missionId.equals(existingMissionId)) {
            log.info(
                "[Mission][Net] ignored mission pickup seed clear due to mission mismatch requested={} existing={} player={} slot={} hub={}",
                missionId, existingMissionId, sender.playerId, sender.slot, sender.hubId
            );
            return;
        }
        missionPickupSeedContractsByPlayerZone.remove(contractKey);
        log.info(
            "[Mission][Net] cleared mission pickup seed contract mission={} player={} slot={} hub={}",
            missionId, sender.playerId, sender.slot, sender.hubId
        );
    }

    private void queueMissionPickupReseedForPlayerIfPresent(PlayerRecord player, ZoneInstance zone) {
        if (player == null || zone == null) return;
        MissionPickupSeedContract contract = missionPickupSeedContractsByPlayerZone.get(
            missionPickupSeedContractKey(player.playerId, zone.hubId)
        );
        if (contract == null || contract.itemCounts() == null || contract.itemCounts().isEmpty()) return;

        String requestId = "reseed-" + missionPickupReseedSeq.incrementAndGet();
        zone.pendingMissionPickupSeeds.add(new ZoneInstance.PendingMissionPickupSeed(
            requestId,
            contract.missionId(),
            player.playerId,
            player.slot,
            contract.itemCounts()
        ));
        zone.forceNextFullSnapshot.set(true);
        log.info(
            "[Mission][Net] queued late-join pickup reconcile request_id={} mission={} player={} slot={} items={} hub={}",
            requestId, contract.missionId(), player.playerId, player.slot, contract.itemCounts(), zone.hubId
        );
    }

    private static String missionPickupSeedContractKey(String playerId, String zoneId) {
        return playerId + "|" + zoneId;
    }

    private static String normalizeRequestId(Object raw) {
        if (!(raw instanceof String s)) return "";
        String trimmed = s.trim();
        if (trimmed.isEmpty()) return "";
        return trimmed.length() <= 128 ? trimmed : trimmed.substring(0, 128);
    }

    private static String normalizeMissionId(Object raw) {
        if (!(raw instanceof String s)) return "";
        return s.trim().toLowerCase(java.util.Locale.ROOT);
    }

    private static Map<String, Integer> sanitizeMissionItemCounts(Object raw) {
        if (!(raw instanceof Map<?, ?> source)) return Map.of();

        LinkedHashMap<String, Integer> clean = new LinkedHashMap<>();
        int total = 0;

        for (Map.Entry<?, ?> entry : source.entrySet()) {
            if (clean.size() >= MISSION_SEED_MAX_ITEM_TYPES || total >= MISSION_SEED_MAX_TOTAL) break;

            String itemId = normalizeMissionItemId(entry.getKey());
            if (itemId.isBlank() || "coin".equals(itemId)) continue;

            int count = parsePositiveInt(entry.getValue());
            if (count <= 0) continue;
            count = Math.min(count, MISSION_SEED_MAX_PER_ITEM);

            int allowed = Math.min(count, MISSION_SEED_MAX_TOTAL - total);
            if (allowed <= 0) break;

            clean.merge(itemId, allowed, Integer::sum);
            total += allowed;
        }
        return clean;
    }

    private static String normalizeMissionItemId(Object raw) {
        if (raw == null) return "";
        return raw.toString().trim().toLowerCase(java.util.Locale.ROOT);
    }

    private static int parsePositiveInt(Object raw) {
        if (raw instanceof Number n) return Math.max(0, n.intValue());
        if (raw instanceof String s) {
            try {
                return Math.max(0, Integer.parseInt(s.trim()));
            } catch (NumberFormatException ignored) {
                return 0;
            }
        }
        return 0;
    }

    private static String normalizePortalTransitionType(String raw) {
        if (PORTAL_TRANSITION_MISSION_RETURN.equals(raw)) return PORTAL_TRANSITION_MISSION_RETURN;
        return PORTAL_TRANSITION_INTER_HUB;
    }

    private static String normalizeSessionId(String raw) {
        if (raw == null) return "missing";
        String s = raw.trim();
        return s.isEmpty() ? "missing" : s;
    }
}
