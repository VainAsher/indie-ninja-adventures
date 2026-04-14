package com.indieniinja.server;

import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.world.HubState;
import com.indieniinja.world.HubStateMachine;
import io.netty.buffer.ByteBuf;
import io.netty.channel.embedded.EmbeddedChannel;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.assertThat;

class ZoneSimulationLoopScriptedLossOrderingTest {

    @Test
    void scriptedLossBroadcastIsEmittedAndSnapshotCarriesCollapsedHubState() throws Exception {
        TestHarness harness = createHarness();
        try {
            triggerScriptedLoss(harness.zone.simulator);
            invokeSimulateTick(harness.loop);

            List<WireMessage> msgs = readOutboundMessages(harness.channel);
            assertThat(msgs).hasSize(1);
            assertThat(msgs.get(0).type()).isEqualTo(MessageType.SCRIPTED_LOSS);
            assertThat(msgs.get(0).getString("hub_id", "")).isEqualTo(harness.zone.hubId);
            assertThat(harness.zone.hubStateMachine.getState()).isEqualTo(HubState.EMPTY);

            WorldSnapshot snap = invokeBuildSnapshot(harness.loop, harness.player);
            assertThat(snap.hubState).isEqualTo(HubState.EMPTY.name());
        } finally {
            harness.executor.shutdownNow();
            harness.channel.close();
        }
    }

    @Test
    void scriptedLossBroadcastIsOneShotAcrossTicks() throws Exception {
        TestHarness harness = createHarness();
        try {
            triggerScriptedLoss(harness.zone.simulator);
            invokeSimulateTick(harness.loop);
            List<WireMessage> firstTick = readOutboundMessages(harness.channel);
            assertThat(firstTick).hasSize(1);
            assertThat(firstTick.get(0).type()).isEqualTo(MessageType.SCRIPTED_LOSS);

            invokeSimulateTick(harness.loop);
            List<WireMessage> secondTick = readOutboundMessages(harness.channel);
            assertThat(secondTick).isEmpty();
        } finally {
            harness.executor.shutdownNow();
            harness.channel.close();
        }
    }

    private static TestHarness createHarness() {
        GameSession session = new GameSession(12345L);
        ZoneInstance zone = new ZoneInstance(
            "central_hub:0:0", "central_hub", 12345L, "blob", 12, 12345L, 256f, 256f);
        zone.simulator = new GameSimulator(zone.seed, zone.hubId, LevelLayout.buildTestLayout(zone.seed));
        zone.hubStateMachine = new HubStateMachine(zone.masterHubId);
        zone.simulator.setHub(zone.hubStateMachine);
        zone.playerIds.add("p1");

        EmbeddedChannel channel = new EmbeddedChannel();
        PlayerRecord player = new PlayerRecord("p1", 0, channel);
        player.hubId = zone.hubId;
        session.players.put(player.playerId, player);

        ExecutorService executor = Executors.newSingleThreadExecutor();
        ZoneSimulationLoop loop = new ZoneSimulationLoop(
            zone,
            session,
            new AtomicBoolean(false),
            new ConcurrentHashMap<>(Map.of(zone.hubId, zone)),
            executor
        );
        return new TestHarness(loop, zone, player, channel, executor);
    }

    private static void triggerScriptedLoss(GameSimulator sim) throws Exception {
        Method trigger = GameSimulator.class.getDeclaredMethod("triggerSirenScriptedLoss");
        trigger.setAccessible(true);
        trigger.invoke(sim);
    }

    private static void invokeSimulateTick(ZoneSimulationLoop loop) throws Exception {
        Method simulate = ZoneSimulationLoop.class.getDeclaredMethod("simulateTick");
        simulate.setAccessible(true);
        simulate.invoke(loop);
    }

    private static WorldSnapshot invokeBuildSnapshot(ZoneSimulationLoop loop, PlayerRecord player)
        throws Exception {
        Method build = ZoneSimulationLoop.class.getDeclaredMethod("buildSnapshot", boolean.class, List.class);
        build.setAccessible(true);
        return (WorldSnapshot) build.invoke(loop, true, List.of(player));
    }

    private static List<WireMessage> readOutboundMessages(EmbeddedChannel channel) {
        java.util.ArrayList<WireMessage> out = new java.util.ArrayList<>();
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

    private record TestHarness(
        ZoneSimulationLoop loop,
        ZoneInstance zone,
        PlayerRecord player,
        EmbeddedChannel channel,
        ExecutorService executor
    ) {}
}
