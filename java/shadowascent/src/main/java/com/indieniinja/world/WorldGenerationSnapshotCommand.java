package com.indieniinja.world;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.indieniinja.world.progression.WorldProgressionGenerator;
import com.indieniinja.world.sections.SectionTemplateLibrary;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.zip.CRC32;

/**
 * Deterministic world-generation snapshot exporter.
 *
 * This is intentionally graph-centric in the first layered-generator slice.
 * Later slices can append section, anchor, validation, and megamap blocks while
 * preserving the same command entry point.
 */
public final class WorldGenerationSnapshotCommand {
    private static final ObjectMapper MAPPER = new ObjectMapper()
        .enable(SerializationFeature.INDENT_OUTPUT)
        .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, false);

    private static final List<String> SEED_STREAMS = List.of(
        "world_graph",
        "world_graph::back_edges",
        "room_synthesis::<roomId>",
        "zone_patch::<roomId>",
        "autotile::<roomId>"
    );

    private WorldGenerationSnapshotCommand() {}

    public static void main(String[] args) throws Exception {
        Options options = Options.parse(args);
        writeSnapshot(options.seed(), options.rooms(), options.shape(), options.out());
    }

    static void writeSnapshot(long seed, int rooms, WorldGraph.WorldShape shape, Path out) throws IOException {
        WorldGraph graph = WorldGraph.generate(seed, rooms, shape);
        Map<String, Object> snapshot = snapshot(seed, rooms, shape, graph);

        Path parent = out.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        MAPPER.writeValue(out.toFile(), snapshot);
    }

    private static Map<String, Object> snapshot(
            long seed, int requestedRooms, WorldGraph.WorldShape shape, WorldGraph graph) {
        Bounds bounds = Bounds.from(graph);
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("generatorSchemaVersion", GeneratorSchemaVersion.CURRENT);
        root.put("worldSeed", seed);
        root.put("shape", shape.name());
        root.put("roomCountRequested", requestedRooms);
        root.put("roomCountActual", graph.size());
        root.put("roomWidthTiles", WorldGraph.ROOM_W);
        root.put("roomHeightTiles", WorldGraph.ROOM_H);
        root.put("seedStreams", SEED_STREAMS);
        root.put("bounds", bounds.toJson());
        root.put("startRoomId", roomId(graph.startRoom()));
        root.put("exitRoomId", roomId(graph.exitRoom()));
        root.put("progressionGraph", WorldProgressionGenerator.generate(seed).toSnapshot());
        root.put("sectionTemplates", SectionTemplateLibrary.loadDefault().summarySnapshot());
        root.put("rooms", rooms(graph));
        return root;
    }

    private static List<Map<String, Object>> rooms(WorldGraph graph) {
        return graph.allRooms().stream()
            .sorted(Comparator
                .comparingInt((WorldGraph.RoomNode room) -> room.gridY)
                .thenComparingInt(room -> room.gridX))
            .map(WorldGenerationSnapshotCommand::room)
            .toList();
    }

    private static Map<String, Object> room(WorldGraph.RoomNode room) {
        Set<String> dirs = new TreeSet<>(room.neighborDirs());
        byte[][] tiles = WorldGenerator.generate(
            room.seed,
            WorldGraph.ROOM_W,
            WorldGraph.ROOM_H,
            dirs,
            room.type.id(),
            room.biomeIndex
        );

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", roomId(room));
        out.put("gridX", room.gridX);
        out.put("gridY", room.gridY);
        out.put("type", room.type.id());
        out.put("seed", room.seed);
        out.put("biomeIndex", room.biomeIndex);
        out.put("neighborDirs", new ArrayList<>(dirs));
        out.put("tileChecksum", checksum(tiles));
        return out;
    }

    private static String checksum(byte[][] tiles) {
        CRC32 crc = new CRC32();
        for (byte[] row : tiles) {
            for (byte tile : row) {
                crc.update(tile);
            }
        }
        return Long.toUnsignedString(crc.getValue(), 16);
    }

    private static String roomId(WorldGraph.RoomNode room) {
        return room.gridX + "," + room.gridY;
    }

    private record Bounds(int minGridX, int minGridY, int maxGridX, int maxGridY) {
        static Bounds from(WorldGraph graph) {
            int minX = Integer.MAX_VALUE;
            int minY = Integer.MAX_VALUE;
            int maxX = Integer.MIN_VALUE;
            int maxY = Integer.MIN_VALUE;
            for (WorldGraph.RoomNode room : graph.allRooms()) {
                minX = Math.min(minX, room.gridX);
                minY = Math.min(minY, room.gridY);
                maxX = Math.max(maxX, room.gridX);
                maxY = Math.max(maxY, room.gridY);
            }
            return new Bounds(minX, minY, maxX, maxY);
        }

        Map<String, Object> toJson() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("minGridX", minGridX);
            out.put("minGridY", minGridY);
            out.put("maxGridX", maxGridX);
            out.put("maxGridY", maxGridY);
            out.put("widthRooms", maxGridX - minGridX + 1);
            out.put("heightRooms", maxGridY - minGridY + 1);
            return out;
        }
    }

    private record Options(long seed, int rooms, WorldGraph.WorldShape shape, Path out) {
        static Options parse(String[] args) {
            long seed = 1L;
            int rooms = 20;
            WorldGraph.WorldShape shape = WorldGraph.WorldShape.BLOB;
            Path out = Paths.get("build", "worldgen-snapshots", "snapshot.json");

            for (int i = 0; i < args.length; i++) {
                String arg = args[i];
                String value = i + 1 < args.length ? args[i + 1] : "";
                switch (arg) {
                    case "--seed" -> {
                        seed = Long.parseLong(required(arg, value));
                        i++;
                    }
                    case "--rooms" -> {
                        rooms = Integer.parseInt(required(arg, value));
                        i++;
                    }
                    case "--shape" -> {
                        shape = WorldGraph.WorldShape.valueOf(required(arg, value).toUpperCase());
                        i++;
                    }
                    case "--out", "--export-json" -> {
                        out = Paths.get(required(arg, value));
                        i++;
                    }
                    case "--help", "-h" -> throw new IllegalArgumentException(usage());
                    default -> throw new IllegalArgumentException("Unknown argument: " + arg + "\n" + usage());
                }
            }
            if (rooms < 1) {
                throw new IllegalArgumentException("--rooms must be >= 1");
            }
            return new Options(seed, rooms, shape, out);
        }

        private static String required(String arg, String value) {
            if (value == null || value.isBlank() || value.startsWith("--")) {
                throw new IllegalArgumentException(arg + " requires a value\n" + usage());
            }
            return value;
        }

        private static String usage() {
            return "Usage: WorldGenerationSnapshotCommand --seed <long> --rooms <int> "
                + "--shape <BLOB|BRANCHY|SNAKE|SPIRAL|TREE|GRID> --out <snapshot.json>";
        }
    }
}
