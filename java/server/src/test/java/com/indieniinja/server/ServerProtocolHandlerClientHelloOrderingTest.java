package com.indieniinja.server;

import com.indieniinja.network.MessageType;
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

class ServerProtocolHandlerClientHelloOrderingTest {

    @Test
    void duplicateClientHelloOnSameChannelIsIdempotent() throws Exception {
        GameSession session = new GameSession(20260423L);
        session.gameStarted.set(true);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel channel = new EmbeddedChannel(handler);
        try {
            prepareCentralStartZone(handler, session);

            invokeClientHello(handler, channel, "p1", "session-a");
            PlayerRecord first = session.players.get("p1");
            assertThat(first).isNotNull();
            assertThat(first.slot).isEqualTo(0);

            invokeClientHello(handler, channel, "p1", "session-a-dup");
            PlayerRecord second = session.players.get("p1");
            assertThat(second).isNotNull();
            assertThat(second.slot).isEqualTo(0);
            assertThat(session.players).hasSize(1);

            int slotP2 = session.claimSlot("p2");
            assertThat(slotP2).isEqualTo(1);
        } finally {
            channel.close();
        }
    }

    @Test
    void overlappingClientHelloFromDifferentChannelReclaimsSameSlot() throws Exception {
        GameSession session = new GameSession(20260424L);
        session.gameStarted.set(true);
        ServerProtocolHandler handler = new ServerProtocolHandler(session);
        EmbeddedChannel oldChannel = new EmbeddedChannel(handler);
        EmbeddedChannel newChannel = new EmbeddedChannel(handler);
        try {
            prepareCentralStartZone(handler, session);

            invokeClientHello(handler, oldChannel, "p1", "session-old");
            PlayerRecord initial = session.players.get("p1");
            assertThat(initial).isNotNull();
            assertThat(initial.slot).isEqualTo(0);

            invokeClientHello(handler, newChannel, "p1", "session-new");
            PlayerRecord replaced = session.players.get("p1");
            assertThat(replaced).isNotNull();
            assertThat(replaced.slot).isEqualTo(0);
            assertThat(replaced.channel.id().asShortText()).isEqualTo(newChannel.id().asShortText());

            @SuppressWarnings("unchecked")
            Map<String, String> channelToPlayer =
                (Map<String, String>) getField(handler, "channelToPlayer");
            assertThat(channelToPlayer).containsEntry(newChannel.id().asShortText(), "p1");
            assertThat(channelToPlayer).hasSize(1);

            int slotP2 = session.claimSlot("p2");
            assertThat(slotP2).isEqualTo(1);
        } finally {
            oldChannel.close();
            newChannel.close();
        }
    }

    private static void invokeClientHello(
        ServerProtocolHandler handler,
        EmbeddedChannel channel,
        String playerId,
        String sessionId
    ) throws Exception {
        Method handleClientHello = ServerProtocolHandler.class.getDeclaredMethod(
            "handleClientHello",
            ChannelHandlerContext.class,
            WireMessage.class
        );
        handleClientHello.setAccessible(true);
        ChannelHandlerContext ctx = channel.pipeline().context(handler);
        WireMessage hello = new WireMessage("client_hello", Map.of(
            "player_id", playerId,
            "session_id", sessionId,
            "version", MessageType.PROTOCOL_VERSION,
            "game_mode", "arcade"
        ));
        handleClientHello.invoke(handler, ctx, hello);
    }

    private static void prepareCentralStartZone(ServerProtocolHandler handler, GameSession session)
        throws Exception {
        HubRegistry.HubDef hubDef = HubRegistry.get("central_hub");
        long zoneSeed = HubRegistry.hubSeed(session.worldSeed, "central_hub");
        WorldGraph graph = WorldGraph.generate(
            zoneSeed,
            hubDef.roomCount(),
            WorldGraph.WorldShape.valueOf(hubDef.graphShape())
        );
        WorldGraph.RoomNode start = graph.startRoom();
        String zoneKey = "central_hub:" + start.gridX + ":" + start.gridY;
        ZoneInstance zone = new ZoneInstance(
            zoneKey,
            "central_hub",
            zoneSeed,
            hubDef.graphShape(),
            hubDef.roomCount(),
            session.worldSeed,
            start.gridX * 32f,
            start.gridY * 32f
        );
        zone.worldGraph = graph;

        @SuppressWarnings("unchecked")
        ConcurrentHashMap<String, ZoneInstance> zones =
            (ConcurrentHashMap<String, ZoneInstance>) getField(handler, "zones");
        zones.put(zoneKey, zone);
    }

    private static Object getField(Object target, String fieldName) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(target);
    }
}
