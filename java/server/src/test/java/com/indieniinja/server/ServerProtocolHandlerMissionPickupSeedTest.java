package com.indieniinja.server;

import com.indieniinja.network.WireMessage;
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

    private static Object getField(Object target, String fieldName) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(target);
    }
}
