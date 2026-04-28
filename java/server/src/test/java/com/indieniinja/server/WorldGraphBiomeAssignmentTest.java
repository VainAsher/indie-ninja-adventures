package com.indieniinja.server;

import com.indieniinja.network.WorldRoomDescriptor;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.WorldGraph.RoomNode;
import com.indieniinja.world.WorldGraph.WorldShape;
import org.junit.jupiter.api.Test;

import java.util.Collection;
import java.util.Map;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S5 — Verifies that biomeIndex flows correctly from WorldGraph through the
 * wire protocol and that the WorldSnapshot additive field round-trips safely.
 */
class WorldGraphBiomeAssignmentTest {

    // ── WorldGraph biome assignment ───────────────────────────────────────────

    @Test
    void everyRoomHasValidBiomeIndex() {
        WorldGraph graph = WorldGraph.generate(12345L, 20, WorldShape.BLOB);
        // WorldGraph's depth-zone mapping produces indices in [0,5); full blob-set ceiling is 12.
        for (RoomNode room : graph.allRooms()) {
            assertTrue(room.biomeIndex >= 0 && room.biomeIndex < 12,
                "room at (" + room.gridX + "," + room.gridY + ") has out-of-range biomeIndex: " + room.biomeIndex);
        }
    }

    @Test
    void startRoomBiomeIndexIsDeterministic() {
        WorldGraph g1 = WorldGraph.generate(99L, 15, WorldShape.BLOB);
        WorldGraph g2 = WorldGraph.generate(99L, 15, WorldShape.BLOB);
        assertEquals(g1.startRoom().biomeIndex, g2.startRoom().biomeIndex,
            "same seed should produce same startRoom biomeIndex");
    }

    @Test
    void differentSeedsCanProduceDifferentBiomes() {
        // With many seeds, not all start-room biomes should be identical
        java.util.Set<Integer> seen = new java.util.HashSet<>();
        for (long seed = 1; seed <= 20; seed++) {
            seen.add(WorldGraph.generate(seed, 10, WorldShape.BLOB).startRoom().biomeIndex);
        }
        assertTrue(seen.size() > 1, "expected biome variety across seeds, only got: " + seen);
    }

    @Test
    void deeperRoomsCanHaveDifferentBiomeThanStart() {
        WorldGraph graph = WorldGraph.generate(42L, 30, WorldShape.SNAKE);
        int startBiome = graph.startRoom().biomeIndex;
        boolean foundDifferent = graph.allRooms().stream()
            .anyMatch(r -> r.biomeIndex != startBiome);
        assertTrue(foundDifferent, "expected at least one room with a different biome than start");
    }

    // ── WorldRoomDescriptor round-trip ────────────────────────────────────────

    @Test
    void worldRoomDescriptorRoundTripsWithBiomeIndex() {
        WorldGraph graph = WorldGraph.generate(7L, 10, WorldShape.BLOB);
        for (RoomNode room : graph.allRooms()) {
            WorldRoomDescriptor d = new WorldRoomDescriptor();
            d.gridX      = room.gridX;
            d.gridY      = room.gridY;
            d.seed       = room.seed;
            d.roomType   = room.type.wire();
            d.biomeIndex = room.biomeIndex;
            d.neighborDirs.addAll(room.neighborDirs());

            Map<String, Object> map = d.toMap();
            WorldRoomDescriptor restored = WorldRoomDescriptor.fromMap(map);

            assertEquals(d.biomeIndex, restored.biomeIndex,
                "biomeIndex should survive toMap/fromMap round-trip");
        }
    }

    // ── WorldSnapshot additive field (S5 protocol) ────────────────────────────

    @Test
    void worldSnapshotBiomeIndexRoundTrips() {
        WorldSnapshot snap = new WorldSnapshot();
        snap.biomeIndex = 3;
        Map<String, Object> map = snap.toMap();
        WorldSnapshot restored = WorldSnapshot.fromMap(map);
        assertEquals(3, restored.biomeIndex, "biomeIndex should survive WorldSnapshot toMap/fromMap");
    }

    @Test
    void worldSnapshotBiomeIndexDefaultsToZeroWhenAbsent() {
        // Simulate an old-server snapshot that omits biome_index
        Map<String, Object> oldMap = new java.util.HashMap<>();
        oldMap.put("frame", 0L);
        oldMap.put("seed",  0L);
        oldMap.put("is_delta", false);
        oldMap.put("schema_version", WorldSnapshot.SCHEMA_VERSION);
        oldMap.put("players", java.util.List.of());
        WorldSnapshot restored = WorldSnapshot.fromMap(oldMap);
        assertEquals(0, restored.biomeIndex,
            "missing biome_index from old server should default to 0");
    }
}
