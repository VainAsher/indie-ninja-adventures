package com.indieniinja.server;

import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import com.indieniinja.sim.SimPickup;
import com.indieniinja.world.HubState;
import com.indieniinja.world.HubStateMachine;
import com.indieniinja.world.WorldGraph;
import io.netty.buffer.ByteBuf;
import io.netty.channel.embedded.EmbeddedChannel;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.LinkedHashMap;
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

    @Test
    void missionPickupSeedRequestSpawnsPersistentQuestPickups() throws Exception {
        TestHarness harness = createHarness();
        try {
            harness.zone.playerIds.clear(); // Avoid pickup collection while validating persistence.
            long before = countPickupType(harness.zone.simulator, "ancient_tablet");

            harness.zone.pendingMissionPickupSeeds.add(new ZoneInstance.PendingMissionPickupSeed(
                "req-mission-seed-1",
                "mission_alpha",
                harness.player.playerId,
                harness.player.slot,
                Map.of("ancient_tablet", 2, "coin", 9, "weapon_sword", 5)
            ));

            invokeSimulateTick(harness.loop);

            long after = countPickupType(harness.zone.simulator, "ancient_tablet");
            assertThat(after).isGreaterThanOrEqualTo(before + 2);
            assertThat(harness.zone.simulator.getPickups().stream()
                .filter(p -> "ancient_tablet".equals(p.pickupType))
                .allMatch(p -> p.persistent))
                .isTrue();
            assertThat(harness.zone.simulator.getPickups().stream()
                .filter(p -> "ancient_tablet".equals(p.pickupType))
                .allMatch(p -> p.missionOwnerSlot == harness.player.slot))
                .isTrue();

            for (int i = 0; i < 5000; i++) {
                harness.zone.simulator.step(Map.of());
            }

            long aliveAfterTicks = harness.zone.simulator.getPickups().stream()
                .filter(p -> "ancient_tablet".equals(p.pickupType) && p.alive)
                .count();
            assertThat(aliveAfterTicks).isGreaterThanOrEqualTo(before + 2);
        } finally {
            harness.executor.shutdownNow();
            harness.channel.close();
        }
    }

    @Test
    void missionPickupSeededForPlayerCannotBeConsumedByOtherPlayer() throws Exception {
        MultiHarness harness = createMultiHarness();
        try {
            harness.zone.pendingMissionPickupSeeds.add(new ZoneInstance.PendingMissionPickupSeed(
                "req-owner-scope-1",
                "mission_scope",
                harness.player1.playerId,
                harness.player1.slot,
                Map.of("ancient_tablet", 1)
            ));
            invokeSimulateTick(harness.loop);

            com.indieniinja.sim.SimPickup scopedPickup = harness.zone.simulator.getPickups().stream()
                .filter(p -> "ancient_tablet".equals(p.pickupType) && p.missionOwnerSlot == harness.player1.slot)
                .findFirst()
                .orElseThrow();

            SimPlayer owner = harness.zone.simulator.getPlayer(harness.player1.slot);
            SimPlayer nonOwner = harness.zone.simulator.getPlayer(harness.player2.slot);
            assertThat(owner).isNotNull();
            assertThat(nonOwner).isNotNull();

            int ownerBefore = owner.inventory.countItem("ancient_tablet");
            int nonOwnerBefore = nonOwner.inventory.countItem("ancient_tablet");

            owner.physics.x = scopedPickup.x + 280f;
            owner.physics.y = scopedPickup.y + 280f;
            nonOwner.physics.x = scopedPickup.x;
            nonOwner.physics.y = scopedPickup.y;
            invokeSimulateTick(harness.loop);

            assertThat(harness.zone.simulator.getPickups().stream()
                .anyMatch(p -> p.pickupId.equals(scopedPickup.pickupId) && p.alive))
                .isTrue();
            assertThat(nonOwner.inventory.countItem("ancient_tablet")).isEqualTo(nonOwnerBefore);

            owner.physics.x = scopedPickup.x;
            owner.physics.y = scopedPickup.y;
            nonOwner.physics.x = scopedPickup.x + 280f;
            nonOwner.physics.y = scopedPickup.y + 280f;
            invokeSimulateTick(harness.loop);

            assertThat(harness.zone.simulator.getPickups().stream()
                .noneMatch(p -> p.pickupId.equals(scopedPickup.pickupId) && p.alive))
                .isTrue();
            assertThat(owner.inventory.countItem("ancient_tablet")).isEqualTo(ownerBefore + 1);
        } finally {
            harness.executor.shutdownNow();
            harness.channel1.close();
            harness.channel2.close();
            harness.outsiderChannel.close();
        }
    }

    @Test
    void duplicateMissionPickupSeedRequestIdIsIgnored() throws Exception {
        TestHarness harness = createHarness();
        try {
            harness.zone.playerIds.clear();
            long before = countPickupType(harness.zone.simulator, "map_shard");

            ZoneInstance.PendingMissionPickupSeed request = new ZoneInstance.PendingMissionPickupSeed(
                "req-dup-42",
                "mission_beta",
                harness.player.playerId,
                harness.player.slot,
                Map.of("map_shard", 1)
            );
            harness.zone.pendingMissionPickupSeeds.add(request);
            harness.zone.pendingMissionPickupSeeds.add(request);

            invokeSimulateTick(harness.loop);

            long after = countPickupType(harness.zone.simulator, "map_shard");
            assertThat(after - before).isEqualTo(1L);
        } finally {
            harness.executor.shutdownNow();
            harness.channel.close();
        }
    }

    @Test
    void missionScopedPickupSeedAndCollectionForceNextFullSnapshot() throws Exception {
        TestHarness harness = createHarness();
        try {
            harness.zone.forceNextFullSnapshot.set(false);
            invokeSimulateTick(harness.loop); // establish mission pickup baseline hash
            assertThat(harness.zone.forceNextFullSnapshot.get()).isFalse();

            SimPlayer owner = harness.zone.simulator.getPlayer(harness.player.slot);
            assertThat(owner).isNotNull();
            owner.physics.x = harness.zone.spawnX - 1200f;
            owner.physics.y = harness.zone.spawnY - 1200f;

            harness.zone.pendingMissionPickupSeeds.add(new ZoneInstance.PendingMissionPickupSeed(
                "req-sync-force-1",
                "mission_sync",
                harness.player.playerId,
                harness.player.slot,
                Map.of("ancient_tablet", 1)
            ));

            invokeSimulateTick(harness.loop);
            assertThat(harness.zone.forceNextFullSnapshot.get()).isTrue();

            harness.zone.forceNextFullSnapshot.set(false);
            SimPickup seeded = harness.zone.simulator.getPickups().stream()
                .filter(p -> "ancient_tablet".equals(p.pickupType) && p.missionOwnerSlot == harness.player.slot)
                .findFirst()
                .orElseThrow();

            owner.physics.x = seeded.x;
            owner.physics.y = seeded.y;
            invokeSimulateTick(harness.loop);

            assertThat(harness.zone.forceNextFullSnapshot.get()).isTrue();
        } finally {
            harness.executor.shutdownNow();
            harness.channel.close();
        }
    }

    @Test
    void updateCurrentRoomUsesLowestActiveSlotAnchor() throws Exception {
        GameSession session = new GameSession(32345L);
        ZoneInstance zone = new ZoneInstance(
            "central_hub:0:0", "central_hub", 32345L, "blob", 12, 32345L, 128f, 128f);
        zone.simulator = new GameSimulator(zone.seed, zone.hubId, LevelLayout.buildTestLayout(zone.seed));
        zone.worldGraph = buildTwoRoomHorizontalGraph();
        zone.megamapMinGridX = 0;
        zone.megamapMinGridY = 0;
        zone.currentRoomGridX = 0;
        zone.currentRoomGridY = 0;
        zone.currentRoomSeed = zone.worldGraph.roomAt(0, 0).seed;
        zone.currentRoomType = zone.worldGraph.roomAt(0, 0).type.wire();
        zone.currentNeighborDirs = List.copyOf(zone.worldGraph.roomAt(0, 0).neighborDirs());

        EmbeddedChannel channel1 = new EmbeddedChannel();
        EmbeddedChannel channel2 = new EmbeddedChannel();
        PlayerRecord p1 = new PlayerRecord("p1", 1, channel1);
        PlayerRecord p2 = new PlayerRecord("p2", 0, channel2);
        p1.hubId = zone.hubId;
        p2.hubId = zone.hubId;
        session.players.put(p1.playerId, p1);
        session.players.put(p2.playerId, p2);

        // Concurrent set iteration is intentionally non-deterministic. Slot ordering must be authoritative.
        zone.playerIds.add("p1");
        zone.playerIds.add("p2");

        SimPlayer simP1 = new SimPlayer("p1", 1, 128f, 128f);
        SimPlayer simP2 = new SimPlayer("p2", 0, roomPx() + 128f, 128f);
        zone.simulator.addPlayer(simP1);
        zone.simulator.addPlayer(simP2);

        ExecutorService executor = Executors.newSingleThreadExecutor();
        ZoneSimulationLoop loop = new ZoneSimulationLoop(
            zone,
            session,
            new AtomicBoolean(false),
            new ConcurrentHashMap<>(Map.of(zone.hubId, zone)),
            executor
        );
        try {
            PlayerRecord anchor = invokeSelectRoomAnchorPlayer(loop);
            assertThat(anchor).isNotNull();
            assertThat(anchor.playerId).isEqualTo("p2");
            assertThat(anchor.slot).isEqualTo(0);

            invokeUpdateCurrentRoom(loop);

            assertThat(zone.currentRoomGridX).isEqualTo(1);
            assertThat(zone.currentRoomGridY).isEqualTo(0);
            assertThat(zone.currentRoomSeed).isEqualTo(zone.worldGraph.roomAt(1, 0).seed);
            assertThat(zone.currentRoomType).isEqualTo(zone.worldGraph.roomAt(1, 0).type.wire());
            assertThat(zone.currentNeighborDirs)
                .containsExactlyInAnyOrderElementsOf(zone.worldGraph.roomAt(1, 0).neighborDirs());
        } finally {
            executor.shutdownNow();
            channel1.close();
            channel2.close();
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

    private static long countPickupType(GameSimulator sim, String pickupType) {
        return sim.getPickups().stream()
            .filter(p -> pickupType.equals(p.pickupType))
            .count();
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

    private static void invokeUpdateCurrentRoom(ZoneSimulationLoop loop) throws Exception {
        Method update = ZoneSimulationLoop.class.getDeclaredMethod("updateCurrentRoom");
        update.setAccessible(true);
        update.invoke(loop);
    }

    private static PlayerRecord invokeSelectRoomAnchorPlayer(ZoneSimulationLoop loop) throws Exception {
        Method select = ZoneSimulationLoop.class.getDeclaredMethod("selectRoomAnchorPlayer");
        select.setAccessible(true);
        return (PlayerRecord) select.invoke(loop);
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

    private static WorldGraph buildTwoRoomHorizontalGraph() {
        WorldGraph.RoomNode start = new WorldGraph.RoomNode(
            0, 0, WorldGraph.RoomType.START, 1001L, 0, List.of("right")
        );
        WorldGraph.RoomNode exit = new WorldGraph.RoomNode(
            1, 0, WorldGraph.RoomType.EXIT, 1002L, 0, List.of("left")
        );
        Map<Long, WorldGraph.RoomNode> rooms = new LinkedHashMap<>();
        rooms.put(worldKey(0, 0), start);
        rooms.put(worldKey(1, 0), exit);
        return WorldGraph.fromRooms(rooms, start, exit);
    }

    private static long worldKey(int x, int y) {
        return (long) (x + 50000) * 100000L + (y + 50000);
    }

    private static int roomPx() {
        return com.indieniinja.physics.PhysicsConstants.ROOM_WIDTH_TILES
            * com.indieniinja.physics.PhysicsConstants.TILE_SIZE;
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
