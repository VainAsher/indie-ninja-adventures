package com.indieniinja.server;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.WorldRoomDescriptor;
import com.indieniinja.network.WorldSnapshot;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Regression tests for the full-snapshot / delta broadcast schedule
 * and {@link WorldSnapshot} serialisation contract (audit gaps NET-6/NET-7,
 * and the "Full snapshot on tick FULL_SNAPSHOT_EVERY" item).
 *
 * These tests do NOT spin up a ZoneSimulationLoop thread. They verify:
 * <ol>
 *   <li>The {@link ZoneInstance#fullSnapCountdown} sentinel ensures the very
 *       first broadcast is always a full snapshot.</li>
 *   <li>After {@code FULL_SNAPSHOT_EVERY} delta broadcasts the counter reaches
 *       the threshold and a full snapshot is triggered.</li>
 *   <li>{@link WorldSnapshot#toMap()} honours {@code isDelta}: world-rooms,
 *       shop states, portals are present on full snaps and absent on deltas.</li>
 *   <li>{@link WorldSnapshot#fromMap()} round-trips all fields including
 *       {@code schemaVersion} and {@code frameHash}.</li>
 *   <li>Delta field structure: changed/removed lists populated on delta;
 *       full lists populated on full snap.</li>
 * </ol>
 */
class SnapshotBroadcastScheduleTest {

    // ── Broadcast schedule ────────────────────────────────────────────────────

    /**
     * ZoneInstance.fullSnapCountdown is pre-set to FULL_SNAPSHOT_EVERY so that
     * the FIRST broadcast is always a full snapshot, giving the client room layout,
     * shop states, and portal data on join.
     */
    @Test
    void zoneInstanceFullSnapCountdownStartsAtFullSnapshotEvery() {
        ZoneInstance zone = new ZoneInstance(
            "test_hub", "test_hub", 42L, "BLOB", 12, 42L, 100f, 200f);
        assertThat(zone.fullSnapCountdown)
            .as("first broadcast must be a full snapshot")
            .isEqualTo(ZoneSimulationLoop.FULL_SNAPSHOT_EVERY);
    }

    /**
     * Simulate the broadcast-counter logic from ZoneSimulationLoop.run():
     *   if (++zone.fullSnapCountdown >= FULL_SNAPSHOT_EVERY) → full snap, reset to 0
     *
     * After exactly FULL_SNAPSHOT_EVERY increments from 0, the condition fires.
     */
    @Test
    void broadcastCounterFiresFullSnapAfterInterval() {
        ZoneInstance zone = new ZoneInstance(
            "test_hub", "test_hub", 42L, "BLOB", 12, 42L, 100f, 200f);

        // Simulate the first broadcast (fullSnapCountdown starts at FULL_SNAPSHOT_EVERY)
        boolean firstIsFull = zone.fullSnapCountdown >= ZoneSimulationLoop.FULL_SNAPSHOT_EVERY;
        assertThat(firstIsFull).as("first broadcast must be full").isTrue();

        // Reset as the loop does
        zone.fullSnapCountdown = 0;

        // Tick through FULL_SNAPSHOT_EVERY - 1 deltas
        for (int i = 0; i < ZoneSimulationLoop.FULL_SNAPSHOT_EVERY - 1; i++) {
            boolean isFull = (++zone.fullSnapCountdown >= ZoneSimulationLoop.FULL_SNAPSHOT_EVERY);
            assertThat(isFull)
                .as("broadcast %d must be a delta (not yet at threshold)", i + 1)
                .isFalse();
        }

        // One more increment must trigger full snap
        boolean triggersFull = (++zone.fullSnapCountdown >= ZoneSimulationLoop.FULL_SNAPSHOT_EVERY);
        assertThat(triggersFull)
            .as("broadcast at FULL_SNAPSHOT_EVERY must be a full snapshot")
            .isTrue();
    }

    // ── isDelta=false (full snapshot) field contract ──────────────────────────

    @Test
    void fullSnapshotHasIsDeltaFalseInMap() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = false;
        Map<String, Object> m = snap.toMap();
        assertThat(m.get("is_delta")).isEqualTo(false);
    }

    @Test
    void fullSnapshotIncludesEnemiesListNotDeltaFields() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = false;
        snap.enemies = List.of(makeEnemy("e1"));
        Map<String, Object> m = snap.toMap();

        assertThat(m).containsKey("enemies");
        assertThat(m).doesNotContainKey("enemies_changed");
        assertThat(m).doesNotContainKey("enemies_removed");
    }

    @Test
    void fullSnapshotIncludesWorldRooms() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = false;
        WorldRoomDescriptor room = new WorldRoomDescriptor();
        room.gridX = 1;
        room.gridY = 2;
        room.seed  = 999L;
        room.roomType = "combat";
        snap.worldRooms = List.of(room);

        Map<String, Object> m = snap.toMap();
        @SuppressWarnings("unchecked")
        List<Object> worldRooms = (List<Object>) m.get("world_rooms");
        assertThat(worldRooms).hasSize(1);
    }

    // ── isDelta=true (delta snapshot) field contract ─────────────────────────

    @Test
    void deltaSnapshotHasIsDeltaTrueInMap() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = true;
        Map<String, Object> m = snap.toMap();
        assertThat(m.get("is_delta")).isEqualTo(true);
    }

    @Test
    void deltaSnapshotIncludesDeltaFieldsNotFullEnemiesList() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = true;
        snap.enemiesChanged = List.of(makeEnemy("e1"));
        snap.enemiesRemoved = List.of("e2");
        Map<String, Object> m = snap.toMap();

        assertThat(m).containsKey("enemies_changed");
        assertThat(m).containsKey("enemies_removed");
        assertThat(m).doesNotContainKey("enemies");
    }

    @Test
    void deltaSnapshotHasEmptyWorldRooms() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = true;
        // Even if worldRooms is non-empty, delta must send empty list
        WorldRoomDescriptor room = new WorldRoomDescriptor();
        room.gridX = 0; room.gridY = 0; room.seed = 1L; room.roomType = "start";
        snap.worldRooms = List.of(room);

        Map<String, Object> m = snap.toMap();
        @SuppressWarnings("unchecked")
        List<Object> worldRooms = (List<Object>) m.get("world_rooms");
        assertThat(worldRooms).isEmpty();
    }

    // ── fromMap round-trip ────────────────────────────────────────────────────

    @Test
    void fromMapRoundTripPreservesSchemaVersionAndFrameHash() {
        WorldSnapshot original = new WorldSnapshot();
        original.schemaVersion = WorldSnapshot.SCHEMA_VERSION;
        original.frameHash     = 0xDEADBEEFL;
        original.frame         = 42L;
        original.seed          = 99L;
        original.isDelta       = false;

        Map<String, Object> map = original.toMap();
        WorldSnapshot restored = WorldSnapshot.fromMap(map);

        assertThat(restored.schemaVersion).isEqualTo(WorldSnapshot.SCHEMA_VERSION);
        assertThat(restored.frameHash).isEqualTo(0xDEADBEEFL);
        assertThat(restored.frame).isEqualTo(42L);
        assertThat(restored.seed).isEqualTo(99L);
        assertThat(restored.isDelta).isFalse();
    }

    @Test
    void fromMapDefaultsSchemaVersionWhenAbsent() {
        // Simulates receiving an old snapshot from a pre-v0.10.82 server
        Map<String, Object> legacyMap = new java.util.LinkedHashMap<>();
        legacyMap.put("frame", 1L);
        legacyMap.put("seed", 0L);
        legacyMap.put("is_delta", false);
        // No schema_version key
        WorldSnapshot snap = WorldSnapshot.fromMap(legacyMap);
        assertThat(snap.schemaVersion).isEqualTo(WorldSnapshot.SCHEMA_VERSION);
    }

    @Test
    void fromMapDefaultsFrameHashWhenAbsent() {
        Map<String, Object> legacyMap = new java.util.LinkedHashMap<>();
        legacyMap.put("frame", 1L);
        legacyMap.put("seed", 0L);
        legacyMap.put("is_delta", false);
        WorldSnapshot snap = WorldSnapshot.fromMap(legacyMap);
        assertThat(snap.frameHash).isEqualTo(0L);
    }

    @Test
    void toMapFromMapRoundTripForDeltaFields() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = true;
        snap.enemiesChanged = List.of(makeEnemy("e1"));
        snap.enemiesRemoved = List.of("e2", "e3");
        snap.pickupsRemoved = List.of("p1");

        WorldSnapshot restored = WorldSnapshot.fromMap(snap.toMap());

        assertThat(restored.isDelta).isTrue();
        assertThat(restored.enemiesChanged).hasSize(1);
        assertThat(restored.enemiesRemoved).containsExactlyInAnyOrder("e2", "e3");
        assertThat(restored.pickupsRemoved).containsExactly("p1");
    }

    // ── ZoneStateCache encode/decode with schedule fields ─────────────────────

    @Test
    void zoneCachePreservesSchemaVersionAndFrameHash() throws Exception {
        WorldSnapshot snap = new WorldSnapshot();
        snap.frameHash     = 12345678L;
        snap.schemaVersion = WorldSnapshot.SCHEMA_VERSION;

        byte[] encoded = ZoneStateCache.encodeMap(snap.toMap());
        Map<String, Object> decoded = ZoneStateCache.decodeMap(encoded);

        assertThat(((Number) decoded.get("frame_hash")).longValue()).isEqualTo(12345678L);
        assertThat(((Number) decoded.get("schema_version")).intValue())
            .isEqualTo(WorldSnapshot.SCHEMA_VERSION);
    }

    // ── Pickup delta round-trip ───────────────────────────────────────────────

    @Test
    void fromMapRoundTripPickupChangedAndRemoved() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.isDelta = true;
        PickupState p = new PickupState();
        p.pickupId   = "pk1";
        p.x          = 10f;
        p.y          = 20f;
        p.pickupType = "health";
        p.alive      = true;
        snap.pickupsChanged = List.of(p);
        snap.pickupsRemoved = List.of("pk2");

        WorldSnapshot restored = WorldSnapshot.fromMap(snap.toMap());
        assertThat(restored.pickupsChanged).hasSize(1);
        assertThat(restored.pickupsChanged.get(0).pickupId).isEqualTo("pk1");
        assertThat(restored.pickupsRemoved).containsExactly("pk2");
    }

    // ── Helper ────────────────────────────────────────────────────────────────

    private static EnemyState makeEnemy(String id) {
        EnemyState e = new EnemyState();
        e.enemyId     = id;
        e.x           = 0f;
        e.y           = 0f;
        e.hp          = 10;
        e.aiState     = "idle";
        e.facingRight = true;
        return e;
    }
}
