package com.indieniinja.server;

import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import com.indieniinja.world.HubState;
import com.indieniinja.world.HubStateMachine;
import io.netty.buffer.ByteBuf;
import io.netty.channel.embedded.EmbeddedChannel;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
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
    void immediateBossDefeatQueueAdvancesHubStateInSameTick() throws Exception {
        TestHarness harness = createHarness();
        try {
            assertThat(harness.zone.hubStateMachine.getState()).isEqualTo(HubState.FULL);
            seedPendingBossDefeat(harness.zone.simulator, "boss_immediate");

            invokeSimulateTick(harness.loop);

            assertThat(harness.zone.hubStateMachine.getState()).isEqualTo(HubState.CORRUPTED);
            assertThat(harness.zone.simulator.drainPendingBossDefeatIds()).isEmpty();
        } finally {
            harness.executor.shutdownNow();
            harness.channel.close();
        }
    }

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

    @Test
    void scriptedLossBroadcastsToAllZoneMembersAndDrainsSnapshotYinYang() throws Exception {
        MultiHarness harness = createMultiHarness();
        try {
            triggerScriptedLoss(harness.zone.simulator);
            invokeSimulateTick(harness.loop);

            List<WireMessage> p1Msgs = readOutboundMessages(harness.channel1);
            List<WireMessage> p2Msgs = readOutboundMessages(harness.channel2);
            List<WireMessage> outsiderMsgs = readOutboundMessages(harness.outsiderChannel);

            assertThat(p1Msgs).hasSize(1);
            assertThat(p1Msgs.get(0).type()).isEqualTo(MessageType.SCRIPTED_LOSS);
            assertThat(p2Msgs).hasSize(1);
            assertThat(p2Msgs.get(0).type()).isEqualTo(MessageType.SCRIPTED_LOSS);
            assertThat(outsiderMsgs).isEmpty();

            WorldSnapshot snap = invokeBuildSnapshot(
                harness.loop,
                List.of(harness.player1, harness.player2)
            );
            assertThat(snap.hubState).isEqualTo(HubState.EMPTY.name());
            assertThat(snap.players).hasSize(2);
            assertThat(snap.players)
                .allSatisfy(ps -> {
                    assertThat(ps.yinValue).isLessThan(0.1f);
                    assertThat(ps.yangValue).isLessThan(0.1f);
                });
        } finally {
            harness.executor.shutdownNow();
            harness.channel1.close();
            harness.channel2.close();
            harness.outsiderChannel.close();
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

    private static MultiHarness createMultiHarness() {
        GameSession session = new GameSession(22345L);
        ZoneInstance zone = new ZoneInstance(
            "central_hub:1:0", "central_hub", 22345L, "blob", 12, 22345L, 256f, 256f);
        zone.simulator = new GameSimulator(zone.seed, zone.hubId, LevelLayout.buildTestLayout(zone.seed));
        zone.hubStateMachine = new HubStateMachine(zone.masterHubId);
        zone.simulator.setHub(zone.hubStateMachine);

        SimPlayer sp1 = new SimPlayer("p1", 0, 256f, 256f);
        sp1.yinYang.yin = 0.9f;
        sp1.yinYang.yang = 0.7f;
        zone.simulator.addPlayer(sp1);
        SimPlayer sp2 = new SimPlayer("p2", 1, 320f, 256f);
        sp2.yinYang.yin = 0.8f;
        sp2.yinYang.yang = 0.6f;
        zone.simulator.addPlayer(sp2);

        EmbeddedChannel channel1 = new EmbeddedChannel();
        EmbeddedChannel channel2 = new EmbeddedChannel();
        EmbeddedChannel outsiderChannel = new EmbeddedChannel();
        PlayerRecord player1 = new PlayerRecord("p1", 0, channel1);
        player1.hubId = zone.hubId;
        PlayerRecord player2 = new PlayerRecord("p2", 1, channel2);
        player2.hubId = zone.hubId;
        PlayerRecord outsider = new PlayerRecord("p3", 2, outsiderChannel);
        outsider.hubId = "some_other_hub";

        zone.playerIds.add("p1");
        zone.playerIds.add("p2");
        session.players.put(player1.playerId, player1);
        session.players.put(player2.playerId, player2);
        session.players.put(outsider.playerId, outsider);

        ExecutorService executor = Executors.newSingleThreadExecutor();
        ZoneSimulationLoop loop = new ZoneSimulationLoop(
            zone,
            session,
            new AtomicBoolean(false),
            new ConcurrentHashMap<>(Map.of(zone.hubId, zone)),
            executor
        );
        return new MultiHarness(
            loop,
            zone,
            player1,
            player2,
            outsider,
            channel1,
            channel2,
            outsiderChannel,
            executor
        );
    }

    private static void triggerScriptedLoss(GameSimulator sim) throws Exception {
        Method trigger = GameSimulator.class.getDeclaredMethod("triggerSirenScriptedLoss");
        trigger.setAccessible(true);
        trigger.invoke(sim);
    }

    @SuppressWarnings("unchecked")
    private static void seedPendingBossDefeat(GameSimulator sim, String bossId) throws Exception {
        Field f = GameSimulator.class.getDeclaredField("pendingBossDefeatIds");
        f.setAccessible(true);
        ((List<String>) f.get(sim)).add(bossId);
    }

    private static void invokeSimulateTick(ZoneSimulationLoop loop) throws Exception {
        Method simulate = ZoneSimulationLoop.class.getDeclaredMethod("simulateTick");
        simulate.setAccessible(true);
        simulate.invoke(loop);
    }

    private static WorldSnapshot invokeBuildSnapshot(ZoneSimulationLoop loop, PlayerRecord player)
        throws Exception {
        return invokeBuildSnapshot(loop, List.of(player));
    }

    private static WorldSnapshot invokeBuildSnapshot(ZoneSimulationLoop loop, List<PlayerRecord> players)
        throws Exception {
        Method build = ZoneSimulationLoop.class.getDeclaredMethod("buildSnapshot", boolean.class, List.class);
        build.setAccessible(true);
        return (WorldSnapshot) build.invoke(loop, true, players);
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

    private record MultiHarness(
        ZoneSimulationLoop loop,
        ZoneInstance zone,
        PlayerRecord player1,
        PlayerRecord player2,
        PlayerRecord outsider,
        EmbeddedChannel channel1,
        EmbeddedChannel channel2,
        EmbeddedChannel outsiderChannel,
        ExecutorService executor
    ) {}
}
