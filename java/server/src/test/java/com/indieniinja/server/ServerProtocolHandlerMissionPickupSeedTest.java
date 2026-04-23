package com.indieniinja.server;

import com.indieniinja.network.WireMessage;
import com.indieniinja.network.WireCodec;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import com.indieniinja.world.HubRegistry;
import com.indieniinja.world.WorldGraph;
import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.embedded.EmbeddedChannel;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import static org.assertj.core.api.Assertions.assertThat;

class ServerProtocolHandlerMissionPickupSeedTest {

    @Test
    void missionPickupSeedEntityEventQueuesOnZoneAndSkipsRelay() throws Exception {
        GameSession session = new GameSession(314159L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        EmbeddedChannel otherChannel = new EmbeddedChannel();
        try {
            ZoneInstance zone = new ZoneInstance(
                "central_hub:0:0", "central_hub", 314159L, "blob", 12, 314159L, 256f, 256f);

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = zone.hubId;
            PlayerRecord other = new PlayerRecord("p2", 1, otherChannel);
            other.hubId = zone.hubId;
            session.players.put(sender.playerId, sender);
            session.players.put(other.playerId, other);

            zone.playerIds.add(sender.playerId);
            zone.playerIds.add(other.playerId);

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            channelToPlayer.put(senderChannel.id().asShortText(), sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zone.hubId, zone);

            WireMessage msg = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups",
                "request_id", "req-123",
                "mission_id", "demo_mission",
                "item_counts", Map.of("relic", 2, "coin", 99)
            ));

            Method handleEntityEvent = ServerProtocolHandler.class.getDeclaredMethod(
                "handleEntityEvent", ChannelHandlerContext.class, WireMessage.class);
            handleEntityEvent.setAccessible(true);
            ChannelHandlerContext senderCtx = senderChannel.pipeline().context(handler);
            handleEntityEvent.invoke(handler, senderCtx, msg);

            ZoneInstance.PendingMissionPickupSeed queued = zone.pendingMissionPickupSeeds.poll();
            assertThat(queued).isNotNull();
            assertThat(queued.requestId()).isEqualTo("req-123");
            assertThat(queued.missionId()).isEqualTo("demo_mission");
            assertThat(queued.playerId()).isEqualTo(sender.playerId);
            assertThat(queued.playerSlot()).isEqualTo(sender.slot);
            assertThat(queued.itemCounts()).containsEntry("relic", 2);
            assertThat(queued.itemCounts()).doesNotContainKey("coin");
            assertThat((Object) otherChannel.readOutbound()).isNull();
        } finally {
            senderChannel.close();
            otherChannel.close();
        }
    }

    @Test
    void bootstrapLateJoinerMarksZoneForImmediateFullSnapshot() throws Exception {
        GameSession session = new GameSession(271828L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel channel = new EmbeddedChannel(handler);
        try {
            HubRegistry.HubDef hubDef = HubRegistry.get("central_hub");
            long zoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
            WorldGraph graph = WorldGraph.generate(
                zoneSeed,
                hubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(hubDef.graphShape())
            );
            WorldGraph.RoomNode startRoom = graph.startRoom();
            String zoneKey = "central_hub:" + startRoom.gridX + ":" + startRoom.gridY;
            ZoneInstance zone = new ZoneInstance(
                zoneKey,
                "central_hub",
                zoneSeed,
                hubDef.graphShape(),
                hubDef.roomCount(),
                session.worldSeed,
                startRoom.gridX * 32f,
                startRoom.gridY * 32f
            );
            zone.worldGraph = graph;

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zoneKey, zone);

            PlayerRecord lateJoiner = new PlayerRecord("late-player", "session-xyz", 0, channel);
            assertThat(zone.forceNextFullSnapshot.get()).isFalse();

            Method bootstrapLateJoiner = ServerProtocolHandler.class.getDeclaredMethod(
                "bootstrapLateJoiner",
                io.netty.channel.Channel.class,
                PlayerRecord.class
            );
            bootstrapLateJoiner.setAccessible(true);
            bootstrapLateJoiner.invoke(handler, channel, lateJoiner);

            assertThat(lateJoiner.hubId).isEqualTo(zone.hubId);
            assertThat(zone.playerIds).contains(lateJoiner.playerId);
            assertThat(zone.forceNextFullSnapshot.get()).isTrue();
        } finally {
            channel.close();
        }
    }

    @Test
    void bootstrapLateJoinerQueuesMissionPickupReseedWhenContractExists() throws Exception {
        GameSession session = new GameSession(314159L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            HubRegistry.HubDef hubDef = HubRegistry.get("central_hub");
            long zoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
            WorldGraph graph = WorldGraph.generate(
                zoneSeed,
                hubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(hubDef.graphShape())
            );
            WorldGraph.RoomNode startRoom = graph.startRoom();
            String zoneKey = "central_hub:" + startRoom.gridX + ":" + startRoom.gridY;
            ZoneInstance zone = new ZoneInstance(
                zoneKey,
                "central_hub",
                zoneSeed,
                hubDef.graphShape(),
                hubDef.roomCount(),
                session.worldSeed,
                startRoom.gridX * 32f,
                startRoom.gridY * 32f
            );
            zone.worldGraph = graph;

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = zone.hubId;
            session.players.put(sender.playerId, sender);
            zone.playerIds.add(sender.playerId);

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            channelToPlayer.put(senderChannel.id().asShortText(), sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zone.hubId, zone);

            WireMessage msg = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups",
                "request_id", "req-contract-1",
                "mission_id", "demo_mission",
                "item_counts", Map.of("relic", 2)
            ));

            Method handleEntityEvent = ServerProtocolHandler.class.getDeclaredMethod(
                "handleEntityEvent", ChannelHandlerContext.class, WireMessage.class);
            handleEntityEvent.setAccessible(true);
            ChannelHandlerContext senderCtx = senderChannel.pipeline().context(handler);
            handleEntityEvent.invoke(handler, senderCtx, msg);

            ZoneInstance.PendingMissionPickupSeed initial = zone.pendingMissionPickupSeeds.poll();
            assertThat(initial).isNotNull();
            assertThat(initial.requestId()).isEqualTo("req-contract-1");
            assertThat(zone.pendingMissionPickupSeeds).isEmpty();

            Method bootstrapLateJoiner = ServerProtocolHandler.class.getDeclaredMethod(
                "bootstrapLateJoiner",
                io.netty.channel.Channel.class,
                PlayerRecord.class
            );
            bootstrapLateJoiner.setAccessible(true);
            bootstrapLateJoiner.invoke(handler, senderChannel, sender);

            ZoneInstance.PendingMissionPickupSeed reseed = zone.pendingMissionPickupSeeds.poll();
            assertThat(reseed).isNotNull();
            assertThat(reseed.requestId()).startsWith("reseed-");
            assertThat(reseed.missionId()).isEqualTo("demo_mission");
            assertThat(reseed.playerId()).isEqualTo(sender.playerId);
            assertThat(reseed.playerSlot()).isEqualTo(sender.slot);
            assertThat(reseed.itemCounts()).containsEntry("relic", 2);
            assertThat(zone.forceNextFullSnapshot.get()).isTrue();
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void missionPickupSeedClearEventPreventsLateJoinReseed() throws Exception {
        GameSession session = new GameSession(161803L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            HubRegistry.HubDef hubDef = HubRegistry.get("central_hub");
            long zoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
            WorldGraph graph = WorldGraph.generate(
                zoneSeed,
                hubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(hubDef.graphShape())
            );
            WorldGraph.RoomNode startRoom = graph.startRoom();
            String zoneKey = "central_hub:" + startRoom.gridX + ":" + startRoom.gridY;
            ZoneInstance zone = new ZoneInstance(
                zoneKey,
                "central_hub",
                zoneSeed,
                hubDef.graphShape(),
                hubDef.roomCount(),
                session.worldSeed,
                startRoom.gridX * 32f,
                startRoom.gridY * 32f
            );
            zone.worldGraph = graph;

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = zone.hubId;
            session.players.put(sender.playerId, sender);
            zone.playerIds.add(sender.playerId);

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            channelToPlayer.put(senderChannel.id().asShortText(), sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zone.hubId, zone);

            Method handleEntityEvent = ServerProtocolHandler.class.getDeclaredMethod(
                "handleEntityEvent", ChannelHandlerContext.class, WireMessage.class);
            handleEntityEvent.setAccessible(true);
            ChannelHandlerContext senderCtx = senderChannel.pipeline().context(handler);

            WireMessage seedMsg = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups",
                "request_id", "req-contract-2",
                "mission_id", "demo_mission",
                "item_counts", Map.of("relic", 2)
            ));
            handleEntityEvent.invoke(handler, senderCtx, seedMsg);
            ZoneInstance.PendingMissionPickupSeed initial = zone.pendingMissionPickupSeeds.poll();
            assertThat(initial).isNotNull();
            assertThat(initial.requestId()).isEqualTo("req-contract-2");

            WireMessage clearMsg = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups_clear",
                "mission_id", "demo_mission",
                "reason", "mission_complete"
            ));
            handleEntityEvent.invoke(handler, senderCtx, clearMsg);
            assertThat(zone.pendingMissionPickupSeeds).isEmpty();

            Method bootstrapLateJoiner = ServerProtocolHandler.class.getDeclaredMethod(
                "bootstrapLateJoiner",
                io.netty.channel.Channel.class,
                PlayerRecord.class
            );
            bootstrapLateJoiner.setAccessible(true);
            bootstrapLateJoiner.invoke(handler, senderChannel, sender);

            assertThat(zone.pendingMissionPickupSeeds.poll()).isNull();
            assertThat(zone.forceNextFullSnapshot.get()).isTrue();
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void missionSwitchAToBRejoinReseedsMissionBContract() throws Exception {
        GameSession session = new GameSession(123456L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            HubRegistry.HubDef hubDef = HubRegistry.get("central_hub");
            long zoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
            WorldGraph graph = WorldGraph.generate(
                zoneSeed,
                hubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(hubDef.graphShape())
            );
            WorldGraph.RoomNode startRoom = graph.startRoom();
            String zoneKey = "central_hub:" + startRoom.gridX + ":" + startRoom.gridY;
            ZoneInstance zone = new ZoneInstance(
                zoneKey,
                "central_hub",
                zoneSeed,
                hubDef.graphShape(),
                hubDef.roomCount(),
                session.worldSeed,
                startRoom.gridX * 32f,
                startRoom.gridY * 32f
            );
            zone.worldGraph = graph;

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = zone.hubId;
            session.players.put(sender.playerId, sender);
            zone.playerIds.add(sender.playerId);

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            channelToPlayer.put(senderChannel.id().asShortText(), sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zone.hubId, zone);

            Method handleEntityEvent = ServerProtocolHandler.class.getDeclaredMethod(
                "handleEntityEvent", ChannelHandlerContext.class, WireMessage.class);
            handleEntityEvent.setAccessible(true);
            ChannelHandlerContext senderCtx = senderChannel.pipeline().context(handler);

            WireMessage seedMissionA = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups",
                "request_id", "req-switch-a",
                "mission_id", "mission_a",
                "item_counts", Map.of("relic", 2)
            ));
            handleEntityEvent.invoke(handler, senderCtx, seedMissionA);
            ZoneInstance.PendingMissionPickupSeed missionASeed = zone.pendingMissionPickupSeeds.poll();
            assertThat(missionASeed).isNotNull();
            assertThat(missionASeed.missionId()).isEqualTo("mission_a");

            WireMessage seedMissionB = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups",
                "request_id", "req-switch-b",
                "mission_id", "mission_b",
                "item_counts", Map.of("key_mission_b", 1)
            ));
            handleEntityEvent.invoke(handler, senderCtx, seedMissionB);
            ZoneInstance.PendingMissionPickupSeed missionBSeed = zone.pendingMissionPickupSeeds.poll();
            assertThat(missionBSeed).isNotNull();
            assertThat(missionBSeed.missionId()).isEqualTo("mission_b");
            assertThat(missionBSeed.itemCounts()).containsEntry("key_mission_b", 1);

            // Simulate a late stale clear from mission A arriving after mission B started.
            WireMessage lateClearMissionA = new WireMessage("entity_event", Map.of(
                "event", "mission_seed_pickups_clear",
                "mission_id", "mission_a",
                "reason", "mission_switch_start"
            ));
            handleEntityEvent.invoke(handler, senderCtx, lateClearMissionA);
            assertThat(zone.pendingMissionPickupSeeds).isEmpty();

            Method bootstrapLateJoiner = ServerProtocolHandler.class.getDeclaredMethod(
                "bootstrapLateJoiner",
                io.netty.channel.Channel.class,
                PlayerRecord.class
            );
            bootstrapLateJoiner.setAccessible(true);
            bootstrapLateJoiner.invoke(handler, senderChannel, sender);

            ZoneInstance.PendingMissionPickupSeed reseed = zone.pendingMissionPickupSeeds.poll();
            assertThat(reseed).isNotNull();
            assertThat(reseed.requestId()).startsWith("reseed-");
            assertThat(reseed.missionId()).isEqualTo("mission_b");
            assertThat(reseed.itemCounts()).containsEntry("key_mission_b", 1);
            assertThat(reseed.itemCounts()).doesNotContainKey("relic");
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void missionReturnTravelClearsContractsAndSkipsDestinationReseed() throws Exception {
        GameSession session = new GameSession(20260423L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            HubRegistry.HubDef missionHubDef = HubRegistry.get("forest_hub");
            long missionZoneSeed = HubRegistry.hubSeed(session.worldSeed, "forest_hub");
            WorldGraph missionGraph = WorldGraph.generate(
                missionZoneSeed,
                missionHubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(missionHubDef.graphShape())
            );
            WorldGraph.RoomNode missionStart = missionGraph.startRoom();
            String missionZoneKey = "forest_hub:" + missionStart.gridX + ":" + missionStart.gridY;
            ZoneInstance missionZone = new ZoneInstance(
                missionZoneKey,
                "forest_hub",
                missionZoneSeed,
                missionHubDef.graphShape(),
                missionHubDef.roomCount(),
                session.worldSeed,
                missionStart.gridX * 32f,
                missionStart.gridY * 32f
            );
            missionZone.worldGraph = missionGraph;

            HubRegistry.HubDef centralHubDef = HubRegistry.get("central_hub");
            long centralZoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
            WorldGraph centralGraph = WorldGraph.generate(
                centralZoneSeed,
                centralHubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(centralHubDef.graphShape())
            );
            WorldGraph.RoomNode centralStart = centralGraph.startRoom();
            String centralZoneKey = "central_hub:" + centralStart.gridX + ":" + centralStart.gridY;
            ZoneInstance centralZone = new ZoneInstance(
                centralZoneKey,
                "central_hub",
                centralZoneSeed,
                centralHubDef.graphShape(),
                centralHubDef.roomCount(),
                session.worldSeed,
                centralStart.gridX * 32f,
                centralStart.gridY * 32f
            );
            centralZone.worldGraph = centralGraph;

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = missionZone.hubId;
            session.players.put(sender.playerId, sender);
            missionZone.playerIds.add(sender.playerId);
            missionZone.simulator = new GameSimulator(
                missionZone.seed,
                missionZone.hubId,
                LevelLayout.buildTestLayout(missionZone.seed)
            );
            missionZone.simulator.addPlayer(new SimPlayer(
                sender.playerId,
                sender.slot,
                missionZone.spawnX,
                missionZone.spawnY
            ));
            assertThat(missionZone.simulator.getPlayer(sender.slot)).isNotNull();

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            channelToPlayer.put(senderChannel.id().asShortText(), sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(missionZone.hubId, missionZone);
            zones.put(centralZone.hubId, centralZone);

            Method rememberContract = ServerProtocolHandler.class.getDeclaredMethod(
                "rememberMissionPickupSeedContract",
                String.class,
                String.class,
                String.class,
                Map.class
            );
            rememberContract.setAccessible(true);
            rememberContract.invoke(handler, sender.playerId, missionZone.hubId, "mission_a", Map.of("relic", 2));
            rememberContract.invoke(handler, sender.playerId, centralZone.hubId, "mission_stale", Map.of("key_old", 1));

            @SuppressWarnings("unchecked")
            Map<String, Object> contracts =
                (Map<String, Object>) getField(handler, "missionPickupSeedContractsByPlayerZone");
            assertThat(contracts.keySet()).containsExactlyInAnyOrder(
                sender.playerId + "|" + missionZone.hubId,
                sender.playerId + "|" + centralZone.hubId
            );

            Method handlePortalTravel = ServerProtocolHandler.class.getDeclaredMethod(
                "handlePortalTravel",
                ChannelHandlerContext.class,
                WireMessage.class
            );
            handlePortalTravel.setAccessible(true);
            ChannelHandlerContext senderCtx = senderChannel.pipeline().context(handler);
            WireMessage portalTravel = new WireMessage("portal_travel", Map.of(
                "destination_id", "central_hub",
                "transition_type", "mission_return"
            ));
            handlePortalTravel.invoke(handler, senderCtx, portalTravel);

            assertThat(sender.hubId).isEqualTo(centralZone.hubId);
            assertThat(missionZone.playerIds).doesNotContain(sender.playerId);
            assertThat(centralZone.playerIds).contains(sender.playerId);
            assertThat(missionZone.simulator.getPlayer(sender.slot)).isNull();
            assertThat(contracts).isEmpty();
            assertThat(centralZone.pendingMissionPickupSeeds.poll()).isNull();
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void portalTravelArrivedPresenceUsesDestinationZoneKey() throws Exception {
        GameSession session = new GameSession(20260424L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            HubRegistry.HubDef missionHubDef = HubRegistry.get("forest_hub");
            long missionZoneSeed = HubRegistry.hubSeed(session.worldSeed, "forest_hub");
            WorldGraph missionGraph = WorldGraph.generate(
                missionZoneSeed,
                missionHubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(missionHubDef.graphShape())
            );
            WorldGraph.RoomNode missionStart = missionGraph.startRoom();
            String missionZoneKey = "forest_hub:" + missionStart.gridX + ":" + missionStart.gridY;
            ZoneInstance missionZone = new ZoneInstance(
                missionZoneKey,
                "forest_hub",
                missionZoneSeed,
                missionHubDef.graphShape(),
                missionHubDef.roomCount(),
                session.worldSeed,
                missionStart.gridX * 32f,
                missionStart.gridY * 32f
            );
            missionZone.worldGraph = missionGraph;

            HubRegistry.HubDef centralHubDef = HubRegistry.get("central_hub");
            long centralZoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
            WorldGraph centralGraph = WorldGraph.generate(
                centralZoneSeed,
                centralHubDef.roomCount(),
                WorldGraph.WorldShape.valueOf(centralHubDef.graphShape())
            );
            WorldGraph.RoomNode centralStart = centralGraph.startRoom();
            String centralZoneKey = "central_hub:" + centralStart.gridX + ":" + centralStart.gridY;
            ZoneInstance centralZone = new ZoneInstance(
                centralZoneKey,
                "central_hub",
                centralZoneSeed,
                centralHubDef.graphShape(),
                centralHubDef.roomCount(),
                session.worldSeed,
                centralStart.gridX * 32f,
                centralStart.gridY * 32f
            );
            centralZone.worldGraph = centralGraph;

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = missionZone.hubId;
            session.players.put(sender.playerId, sender);
            missionZone.playerIds.add(sender.playerId);

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            channelToPlayer.put(senderChannel.id().asShortText(), sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(missionZone.hubId, missionZone);
            zones.put(centralZone.hubId, centralZone);

            Method handlePortalTravel = ServerProtocolHandler.class.getDeclaredMethod(
                "handlePortalTravel",
                ChannelHandlerContext.class,
                WireMessage.class
            );
            handlePortalTravel.setAccessible(true);
            ChannelHandlerContext senderCtx = senderChannel.pipeline().context(handler);
            WireMessage portalTravel = new WireMessage("portal_travel", Map.of(
                "destination_id", "central_hub",
                "transition_type", "inter_hub"
            ));
            handlePortalTravel.invoke(handler, senderCtx, portalTravel);

            List<WireMessage> outbound = readOutboundMessages(senderChannel);
            WireMessage arrivedPresence = outbound.stream()
                .filter(m -> "zone_presence".equals(m.type()))
                .filter(m -> "arrived".equals(m.getString("action", "")))
                .findFirst()
                .orElse(null);
            assertThat(arrivedPresence).isNotNull();
            assertThat(arrivedPresence.getString("hub_id", "")).isEqualTo(centralZone.hubId);
            assertThat(arrivedPresence.getString("master_hub_id", "")).isEqualTo("central_hub");
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void disconnectKeepsCurrentHubContractAndClearsStaleContractsForPlayer() throws Exception {
        GameSession session = new GameSession(424242L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            ZoneInstance zone = new ZoneInstance(
                "central_hub:0:0", "central_hub", 424242L, "blob", 12, 424242L, 256f, 256f);

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = zone.hubId;
            session.players.put(sender.playerId, sender);
            zone.playerIds.add(sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zone.hubId, zone);

            Method rememberContract = ServerProtocolHandler.class.getDeclaredMethod(
                "rememberMissionPickupSeedContract",
                String.class,
                String.class,
                String.class,
                Map.class
            );
            rememberContract.setAccessible(true);
            rememberContract.invoke(handler, sender.playerId, zone.hubId, "demo_mission", Map.of("relic", 2));
            rememberContract.invoke(handler, sender.playerId, "mission_hub:9:9", "demo_mission", Map.of("relic", 1));

            @SuppressWarnings("unchecked")
            Map<String, Object> contracts =
                (Map<String, Object>) getField(handler, "missionPickupSeedContractsByPlayerZone");
            assertThat(contracts.keySet()).containsExactlyInAnyOrder(
                sender.playerId + "|" + zone.hubId,
                sender.playerId + "|mission_hub:9:9"
            );

            Method handleDisconnect = ServerProtocolHandler.class.getDeclaredMethod(
                "handleDisconnect", String.class, io.netty.channel.Channel.class);
            handleDisconnect.setAccessible(true);
            handleDisconnect.invoke(handler, sender.playerId, senderChannel);

            assertThat(contracts.keySet()).containsExactly(sender.playerId + "|" + zone.hubId);
            assertThat(zone.playerIds).doesNotContain(sender.playerId);
            assertThat(session.players).doesNotContainKey(sender.playerId);
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void disconnectKeepsCurrentHubContractAvailableForRejoinReseed() throws Exception {
        GameSession session = new GameSession(515151L);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel senderChannel = new EmbeddedChannel(handler);
        try {
            ZoneInstance zone = new ZoneInstance(
                "central_hub:0:0", "central_hub", 515151L, "blob", 12, 515151L, 256f, 256f);

            PlayerRecord sender = new PlayerRecord("p1", 0, senderChannel);
            sender.hubId = zone.hubId;
            session.players.put(sender.playerId, sender);
            zone.playerIds.add(sender.playerId);

            @SuppressWarnings("unchecked")
            ConcurrentHashMap<String, ZoneInstance> zones =
                (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
            zones.put(zone.hubId, zone);

            Method rememberContract = ServerProtocolHandler.class.getDeclaredMethod(
                "rememberMissionPickupSeedContract",
                String.class,
                String.class,
                String.class,
                Map.class
            );
            rememberContract.setAccessible(true);
            rememberContract.invoke(handler, sender.playerId, zone.hubId, "demo_mission", Map.of("relic", 2));

            Method handleDisconnect = ServerProtocolHandler.class.getDeclaredMethod(
                "handleDisconnect", String.class, io.netty.channel.Channel.class);
            handleDisconnect.setAccessible(true);
            handleDisconnect.invoke(handler, sender.playerId, senderChannel);

            PlayerRecord rejoin = new PlayerRecord("p1", "session-rejoin", 0, senderChannel);
            rejoin.hubId = zone.hubId;
            Method queueReseed = ServerProtocolHandler.class.getDeclaredMethod(
                "queueMissionPickupReseedForPlayerIfPresent",
                PlayerRecord.class,
                ZoneInstance.class
            );
            queueReseed.setAccessible(true);
            queueReseed.invoke(handler, rejoin, zone);

            ZoneInstance.PendingMissionPickupSeed reseed = zone.pendingMissionPickupSeeds.poll();
            assertThat(reseed).isNotNull();
            assertThat(reseed.requestId()).startsWith("reseed-");
            assertThat(reseed.missionId()).isEqualTo("demo_mission");
            assertThat(reseed.playerId()).isEqualTo("p1");
            assertThat(reseed.playerSlot()).isEqualTo(0);
            assertThat(reseed.itemCounts()).containsEntry("relic", 2);
        } finally {
            senderChannel.close();
        }
    }

    @Test
    void normalizePortalTransitionTypeAcceptsCaseAndWhitespaceVariants() throws Exception {
        Method normalizePortalTransitionType = ServerProtocolHandler.class.getDeclaredMethod(
            "normalizePortalTransitionType",
            String.class
        );
        normalizePortalTransitionType.setAccessible(true);

        assertThat((String) normalizePortalTransitionType.invoke(null, "mission_return"))
            .isEqualTo("mission_return");
        assertThat((String) normalizePortalTransitionType.invoke(null, " MISSION_RETURN "))
            .isEqualTo("mission_return");
        assertThat((String) normalizePortalTransitionType.invoke(null, "inter_hub"))
            .isEqualTo("inter_hub");
        assertThat((String) normalizePortalTransitionType.invoke(null, "something_else"))
            .isEqualTo("inter_hub");
        assertThat((String) normalizePortalTransitionType.invoke(null, new Object[] { null }))
            .isEqualTo("inter_hub");
    }

    @Test
    void normalizeSessionIdTrimsAndClampsLength() throws Exception {
        Method normalizeSessionId = ServerProtocolHandler.class.getDeclaredMethod(
            "normalizeSessionId",
            String.class
        );
        normalizeSessionId.setAccessible(true);

        String longSessionId = "x".repeat(256);
        assertThat((String) normalizeSessionId.invoke(null, "  session-123  "))
            .isEqualTo("session-123");
        assertThat((String) normalizeSessionId.invoke(null, "   "))
            .isEqualTo("missing");
        assertThat((String) normalizeSessionId.invoke(null, new Object[] { null }))
            .isEqualTo("missing");
        assertThat(((String) normalizeSessionId.invoke(null, longSessionId)).length())
            .isEqualTo(128);
    }

    private static Object getField(Object target, String fieldName) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(target);
    }

    private static List<WireMessage> readOutboundMessages(EmbeddedChannel channel) {
        ArrayList<WireMessage> out = new ArrayList<>();
        for (;;) {
            Object msg = channel.readOutbound();
            if (!(msg instanceof ByteBuf buf)) break;
            try {
                byte[] body = new byte[buf.readableBytes()];
                buf.readBytes(body);
                out.add(WireCodec.decodeBody(body));
            } catch (java.io.IOException io) {
                throw new RuntimeException("Failed to decode outbound wire message", io);
            } finally {
                buf.release();
            }
        }
        return out;
    }
}
