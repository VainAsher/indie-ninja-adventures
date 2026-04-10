package com.indieniinja.server;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Regression tests for networking desync detection (NET-2/NET-4).
 *
 * Covers:
 *  NET-2a: WorldSnapshot.schemaVersion is always SCHEMA_VERSION
 *  NET-2b: frameHash changes when enemy positions change
 *  NET-2c: frameHash is stable when nothing changes
 *  NET-2d: frameHash differs for different player positions
 *  NET-2e: ZoneStateCache round-trips a snapshot map through msgpack encode/decode
 *  NET-2f: ZoneStateCache.get() returns null when pool is null (disabled cache)
 *  NET-2g: Full snapshot delivery — toMap() includes schema_version and frame_hash
 *  NET-2h: Desync simulation — two snapshots with different enemies produce different hashes
 */
class NetworkingDesyncTest {

    // ── NET-2a: schemaVersion is always stamped ───────────────────────────────

    @Test
    void snapshotSchemaVersionIsStamped() {
        WorldSnapshot snap = new WorldSnapshot();
        assertThat(snap.schemaVersion).isEqualTo(WorldSnapshot.SCHEMA_VERSION);
        assertThat(WorldSnapshot.SCHEMA_VERSION).isEqualTo(1);
    }

    @Test
    void toMapIncludesSchemaVersion() {
        WorldSnapshot snap = new WorldSnapshot();
        Map<String, Object> m = snap.toMap();
        assertThat(m).containsKey("schema_version");
        assertThat(((Number) m.get("schema_version")).intValue())
            .isEqualTo(WorldSnapshot.SCHEMA_VERSION);
    }

    // ── NET-2b: frameHash changes when enemy positions change ─────────────────

    @Test
    void frameHashChangesWhenEnemyMoves() {
        WorldSnapshot a = snapshotWithEnemy("e1", 100f, 200f, 10);
        WorldSnapshot b = snapshotWithEnemy("e1", 101f, 200f, 10);  // x moved

        long hashA = ZoneSimulationLoop.computeFrameHash(a);
        long hashB = ZoneSimulationLoop.computeFrameHash(b);

        assertThat(hashA).isNotEqualTo(hashB);
    }

    // ── NET-2c: frameHash is stable when nothing changes ─────────────────────

    @Test
    void frameHashIsStableForUnchangedState() {
        WorldSnapshot snap = snapshotWithEnemy("e1", 100f, 200f, 10);

        long hash1 = ZoneSimulationLoop.computeFrameHash(snap);
        long hash2 = ZoneSimulationLoop.computeFrameHash(snap);

        assertThat(hash1).isEqualTo(hash2);
    }

    // ── NET-2d: frameHash differs for different player positions ──────────────

    @Test
    void frameHashChangesWhenPlayerMoves() {
        WorldSnapshot a = new WorldSnapshot();
        a.players = List.of(makePlayer("p1", 50f, 100f, 100));

        WorldSnapshot b = new WorldSnapshot();
        b.players = List.of(makePlayer("p1", 50f, 150f, 100));  // y moved

        assertThat(ZoneSimulationLoop.computeFrameHash(a))
            .isNotEqualTo(ZoneSimulationLoop.computeFrameHash(b));
    }

    // ── NET-2e: ZoneStateCache round-trips a snapshot map ────────────────────

    @Test
    void zoneCacheRoundTripsSnapshotMap() throws IOException {
        WorldSnapshot snap = snapshotWithEnemy("e1", 300f, 400f, 5);
        snap.frameHash = ZoneSimulationLoop.computeFrameHash(snap);
        Map<String, Object> original = snap.toMap();

        byte[] encoded = ZoneStateCache.encodeMap(original);
        Map<String, Object> decoded = ZoneStateCache.decodeMap(encoded);

        assertThat(decoded).containsKey("frame_hash");
        assertThat(decoded).containsKey("schema_version");
        // Verify frame_hash survived the round-trip
        assertThat(((Number) decoded.get("frame_hash")).longValue())
            .isEqualTo(((Number) original.get("frame_hash")).longValue());
    }

    // ── NET-2f: null-pool cache is a no-op ────────────────────────────────────

    @Test
    void nullPoolCacheReturnsNullOnGet() {
        ZoneStateCache cache = new ZoneStateCache(null);
        assertThat(cache.get("any_hub")).isNull();
    }

    @Test
    void nullPoolCachePutIsNoop() {
        ZoneStateCache cache = new ZoneStateCache(null);
        WorldSnapshot snap = new WorldSnapshot();
        // Should not throw
        cache.put("any_hub", snap.toMap());
    }

    // ── NET-2g: full snapshot toMap() includes frame_hash key ─────────────────

    @Test
    void toMapIncludesFrameHash() {
        WorldSnapshot snap = snapshotWithEnemy("e1", 10f, 20f, 8);
        snap.frameHash = ZoneSimulationLoop.computeFrameHash(snap);
        Map<String, Object> m = snap.toMap();

        assertThat(m).containsKey("frame_hash");
        assertThat(((Number) m.get("frame_hash")).longValue()).isEqualTo(snap.frameHash);
    }

    // ── NET-2h: desync simulation ─────────────────────────────────────────────

    @Test
    void differentEnemySetProducesDifferentHash() {
        WorldSnapshot serverSnap = new WorldSnapshot();
        serverSnap.enemies = List.of(
            makeEnemy("e1", 100f, 200f, 10),
            makeEnemy("e2", 300f, 400f,  5)
        );

        // "Client" has stale state — e2 is dead (missing from its list)
        WorldSnapshot clientSnap = new WorldSnapshot();
        clientSnap.enemies = List.of(makeEnemy("e1", 100f, 200f, 10));

        long serverHash = ZoneSimulationLoop.computeFrameHash(serverSnap);
        long clientHash = ZoneSimulationLoop.computeFrameHash(clientSnap);

        assertThat(serverHash).as("desync: client missing e2 must differ from server hash")
            .isNotEqualTo(clientHash);
    }

    @Test
    void sameStateSameHash() {
        EnemyState e = makeEnemy("e1", 123f, 456f, 7);

        WorldSnapshot s1 = new WorldSnapshot();
        s1.enemies = List.of(e);

        WorldSnapshot s2 = new WorldSnapshot();
        s2.enemies = List.of(e);

        assertThat(ZoneSimulationLoop.computeFrameHash(s1))
            .isEqualTo(ZoneSimulationLoop.computeFrameHash(s2));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static WorldSnapshot snapshotWithEnemy(String id, float x, float y, int hp) {
        WorldSnapshot snap = new WorldSnapshot();
        snap.enemies = List.of(makeEnemy(id, x, y, hp));
        return snap;
    }

    private static EnemyState makeEnemy(String id, float x, float y, int hp) {
        EnemyState e = new EnemyState();
        e.enemyId     = id;
        e.x           = x;
        e.y           = y;
        e.hp          = hp;
        e.aiState     = "idle";
        e.facingRight = true;
        return e;
    }

    private static PlayerState makePlayer(String id, float x, float y, int health) {
        PlayerState p = new PlayerState();
        p.playerId = id;
        p.posX     = x;
        p.posY     = y;
        p.health   = health;
        return p;
    }

    @SuppressWarnings("unused")
    private static PickupState makePickup(String id, float x, float y, boolean alive) {
        PickupState p = new PickupState();
        p.pickupId = id;
        p.x        = x;
        p.y        = y;
        p.alive    = alive;
        return p;
    }
}
