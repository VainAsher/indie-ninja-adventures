package com.indieniinja.server;

import com.indieniinja.network.WireMessage;
import com.indieniinja.world.HubRegistry;
import com.indieniinja.world.WorldGraph;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.embedded.EmbeddedChannel;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
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

    private static Object getField(Object target, String fieldName) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(target);
    }
}
