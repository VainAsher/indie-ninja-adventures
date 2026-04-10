package com.indieniinja.server;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.indieniinja.world.WorldGraph;
import com.indieniinja.world.WorldGraph.RoomNode;
import com.indieniinja.world.WorldGraph.RoomType;
import com.indieniinja.world.WorldGraph.WorldShape;
import com.zaxxer.hikari.HikariDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.*;
import java.util.*;

/**
 * PostgreSQL persistence for {@link WorldGraph} (WORLD-3).
 *
 * Schema (applied via {@link #ensureSchema()}):
 * <pre>
 *   CREATE TABLE IF NOT EXISTS world_graph (
 *     hub_id  TEXT        NOT NULL,
 *     seed    BIGINT      NOT NULL,
 *     shape   TEXT        NOT NULL,
 *     rooms   JSONB       NOT NULL,
 *     PRIMARY KEY (hub_id)
 *   );
 * </pre>
 *
 * The {@code rooms} JSONB column stores a list of room descriptors, each with:
 *   gridX, gridY, type, seed, biomeIndex, neighborDirs (string array)
 *
 * On hub creation {@link #save} persists the graph; on reconnect {@link #load}
 * reconstructs it so returning players see the same world layout every session.
 */
public final class WorldGraphRepository {

    private static final Logger log = LoggerFactory.getLogger(WorldGraphRepository.class);
    private static final ObjectMapper JSON = new ObjectMapper();

    private final HikariDataSource ds;

    public WorldGraphRepository(HikariDataSource dataSource) {
        this.ds = dataSource;
    }

    // ── Schema ────────────────────────────────────────────────────────────────

    /**
     * Create the {@code world_graph} table if it does not already exist.
     * Safe to call at server startup.
     */
    public void ensureSchema() {
        String ddl = """
                CREATE TABLE IF NOT EXISTS world_graph (
                    hub_id  TEXT    NOT NULL,
                    seed    BIGINT  NOT NULL,
                    shape   TEXT    NOT NULL,
                    rooms   JSONB   NOT NULL,
                    PRIMARY KEY (hub_id)
                )
                """;
        try (Connection conn = ds.getConnection();
             Statement st = conn.createStatement()) {
            st.execute(ddl);
            log.info("world_graph table ready");
        } catch (SQLException e) {
            log.error("Failed to create world_graph table", e);
            throw new RuntimeException("DB schema init failed", e);
        }
    }

    // ── Save ──────────────────────────────────────────────────────────────────

    /**
     * Persist a world graph for the given hub.
     * Uses an UPSERT so re-generating the same hub_id overwrites the old graph.
     *
     * @param hubId unique hub identifier (e.g. zone UUID or "hub_default")
     * @param seed  world seed used to generate the graph
     * @param shape world shape style
     * @param graph the generated {@link WorldGraph}
     */
    public void save(String hubId, long seed, WorldShape shape, WorldGraph graph) {
        String sql = """
                INSERT INTO world_graph (hub_id, seed, shape, rooms)
                VALUES (?, ?, ?, ?::jsonb)
                ON CONFLICT (hub_id) DO UPDATE
                    SET seed  = EXCLUDED.seed,
                        shape = EXCLUDED.shape,
                        rooms = EXCLUDED.rooms
                """;
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, hubId);
            ps.setLong(2, seed);
            ps.setString(3, shape.name());
            ps.setString(4, serializeRooms(graph));
            ps.executeUpdate();
            log.info("Saved world_graph hub={} rooms={}", hubId, graph.size());
        } catch (Exception e) {
            log.error("Failed to save world_graph hub={}", hubId, e);
            throw new RuntimeException("DB save failed for hub " + hubId, e);
        }
    }

    // ── Load ──────────────────────────────────────────────────────────────────

    /**
     * Load a previously persisted world graph.
     *
     * @param hubId the hub identifier
     * @return the reconstructed {@link WorldGraph}, or {@code null} if not found
     */
    public WorldGraph load(String hubId) {
        String sql = "SELECT seed, shape, rooms FROM world_graph WHERE hub_id = ?";
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, hubId);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) return null;
                long seed = rs.getLong("seed");
                WorldShape shape = WorldShape.valueOf(rs.getString("shape"));
                String roomsJson = rs.getString("rooms");
                return deserializeGraph(seed, shape, roomsJson);
            }
        } catch (Exception e) {
            log.error("Failed to load world_graph hub={}", hubId, e);
            return null;
        }
    }

    // ── Serialization ─────────────────────────────────────────────────────────

    private static String serializeRooms(WorldGraph graph) throws Exception {
        List<Map<String, Object>> list = new ArrayList<>();
        for (RoomNode room : graph.allRooms()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("gridX",       room.gridX);
            m.put("gridY",       room.gridY);
            m.put("type",        room.type.name());
            m.put("seed",        room.seed);
            m.put("biomeIndex",  room.biomeIndex);
            m.put("neighborDirs", new ArrayList<>(room.neighborDirs()));
            list.add(m);
        }
        return JSON.writeValueAsString(list);
    }

    /** Reconstruct a {@link WorldGraph} from serialized JSONB without re-running generation. */
    private static WorldGraph deserializeGraph(long worldSeed, WorldShape shape,
                                                String roomsJson) throws Exception {
        List<Map<String, Object>> list = JSON.readValue(
                roomsJson, new TypeReference<>() {});

        Map<Long, RoomNode> rooms = new LinkedHashMap<>();
        for (Map<String, Object> m : list) {
            int gx           = (int) m.get("gridX");
            int gy           = (int) m.get("gridY");
            RoomType type    = RoomType.valueOf((String) m.get("type"));
            long roomSeed    = ((Number) m.get("seed")).longValue();
            int biomeIndex   = (int) m.get("biomeIndex");
            @SuppressWarnings("unchecked")
            List<String> dirs = (List<String>) m.get("neighborDirs");

            RoomNode node = new RoomNode(gx, gy, type, roomSeed, biomeIndex, dirs);
            rooms.put(roomKey(gx, gy), node);
        }

        // Find start and exit rooms
        RoomNode startRoom = rooms.values().stream()
                .filter(r -> r.type == RoomType.START).findFirst()
                .orElseThrow(() -> new IllegalStateException("No START room in DB"));
        RoomNode exitRoom = rooms.values().stream()
                .filter(r -> r.type == RoomType.EXIT).findFirst()
                .orElseThrow(() -> new IllegalStateException("No EXIT room in DB"));

        return WorldGraph.fromRooms(rooms, startRoom, exitRoom);
    }

    private static long roomKey(int x, int y) {
        return (long)(x + 50000) * 100000L + (y + 50000);
    }
}
