package com.indieniinja.world.megamap;

import com.indieniinja.world.GeneratorSchemaVersion;
import com.indieniinja.world.WorldGenerator;
import com.indieniinja.world.WorldGraph;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.zip.CRC32;

/**
 * Builds a compact stitched-map inspection snapshot from the legacy room graph.
 *
 * This does not allocate or persist a runtime megamap. It normalizes room
 * origins into one continuous coordinate space and emits enough metadata for
 * viewer overlays, golden-seed diffs, and seam inspection.
 */
public final class MegamapStitcher {
    private MegamapStitcher() {}

    public static MegamapSnapshot stitch(
            long seed,
            int requestedRooms,
            WorldGraph.WorldShape shape,
            WorldGraph graph) {
        GridBounds gridBounds = GridBounds.from(graph);
        MegamapSnapshot.Bounds bounds = gridBounds.toSnapshotBounds();
        List<MegamapSnapshot.RoomStamp> roomStamps = new ArrayList<>();
        List<MegamapSnapshot.Seam> seams = new ArrayList<>();
        MetricsAccumulator metrics = new MetricsAccumulator(bounds.widthTiles() * bounds.heightTiles());

        for (WorldGraph.RoomNode room : sortedRooms(graph)) {
            int originX = (room.gridX - gridBounds.minGridX) * WorldGraph.ROOM_W;
            int originY = (room.gridY - gridBounds.minGridY) * WorldGraph.ROOM_H;
            byte[][] tiles = WorldGenerator.generate(
                room.seed,
                WorldGraph.ROOM_W,
                WorldGraph.ROOM_H,
                new TreeSet<>(room.neighborDirs()),
                room.type.id(),
                room.biomeIndex
            );
            metrics.addRoomTiles(tiles, originX, originY);
            roomStamps.add(new MegamapSnapshot.RoomStamp(
                roomId(room),
                room.gridX,
                room.gridY,
                originX,
                originY,
                WorldGraph.ROOM_W,
                WorldGraph.ROOM_H,
                room.type.id(),
                room.biomeIndex,
                checksum(tiles)
            ));
        }

        for (WorldGraph.RoomNode room : sortedRooms(graph)) {
            for (String direction : new TreeSet<>(room.neighborDirs())) {
                WorldGraph.RoomNode neighbor = graph.neighborRoom(room.gridX, room.gridY, direction);
                if (neighbor == null || !includeSeam(room, neighbor)) {
                    continue;
                }
                seams.add(seamFor(room, neighbor, direction, gridBounds));
            }
        }

        MegamapSnapshot.Metrics outMetrics = metrics.toMetrics(roomStamps.size(), seams.size());
        return new MegamapSnapshot(
            seed,
            requestedRooms,
            shape.name(),
            "schema-" + GeneratorSchemaVersion.CURRENT + "-seed-" + seed
                + "-shape-" + shape.name() + "-rooms-" + requestedRooms,
            bounds,
            roomStamps,
            seams,
            overlayRows(graph, gridBounds),
            outMetrics,
            metrics.toAutotileSummary()
        );
    }

    private static List<WorldGraph.RoomNode> sortedRooms(WorldGraph graph) {
        return graph.allRooms().stream()
            .sorted(Comparator
                .comparingInt((WorldGraph.RoomNode room) -> room.gridY)
                .thenComparingInt(room -> room.gridX))
            .toList();
    }

    private static boolean includeSeam(WorldGraph.RoomNode room, WorldGraph.RoomNode neighbor) {
        return roomId(room).compareTo(roomId(neighbor)) < 0;
    }

    private static MegamapSnapshot.Seam seamFor(
            WorldGraph.RoomNode room,
            WorldGraph.RoomNode neighbor,
            String direction,
            GridBounds bounds) {
        int originX = (room.gridX - bounds.minGridX) * WorldGraph.ROOM_W;
        int originY = (room.gridY - bounds.minGridY) * WorldGraph.ROOM_H;
        int doorHalf = 4;
        int midX = originX + WorldGraph.ROOM_W / 2;
        int midY = originY + WorldGraph.ROOM_H / 2;
        MegamapSnapshot.BoundsTiles seamBounds = switch (direction) {
            case "up" -> new MegamapSnapshot.BoundsTiles(midX - doorHalf, originY, doorHalf * 2 + 1, 4);
            case "down" -> new MegamapSnapshot.BoundsTiles(
                midX - doorHalf,
                originY + WorldGraph.ROOM_H - 4,
                doorHalf * 2 + 1,
                4
            );
            case "left" -> new MegamapSnapshot.BoundsTiles(originX, midY - doorHalf, 4, doorHalf * 2 + 1);
            case "right" -> new MegamapSnapshot.BoundsTiles(
                originX + WorldGraph.ROOM_W - 4,
                midY - doorHalf,
                4,
                doorHalf * 2 + 1
            );
            default -> new MegamapSnapshot.BoundsTiles(originX, originY, 1, 1);
        };
        return new MegamapSnapshot.Seam(roomId(room), roomId(neighbor), direction, seamBounds, true);
    }

    private static List<String> overlayRows(WorldGraph graph, GridBounds bounds) {
        int width = bounds.maxGridX - bounds.minGridX + 1;
        int height = bounds.maxGridY - bounds.minGridY + 1;
        char[][] overlay = new char[height][width];
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                overlay[y][x] = '.';
            }
        }
        Set<String> startExit = Set.of(roomId(graph.startRoom()), roomId(graph.exitRoom()));
        for (WorldGraph.RoomNode room : graph.allRooms()) {
            int x = room.gridX - bounds.minGridX;
            int y = room.gridY - bounds.minGridY;
            overlay[y][x] = overlayChar(room, startExit.contains(roomId(room)));
        }
        List<String> rows = new ArrayList<>();
        for (char[] row : overlay) {
            rows.add(new String(row));
        }
        return rows;
    }

    private static char overlayChar(WorldGraph.RoomNode room, boolean startOrExit) {
        if (startOrExit && room.type == WorldGraph.RoomType.START) {
            return 'S';
        }
        if (startOrExit && room.type == WorldGraph.RoomType.EXIT) {
            return 'E';
        }
        return switch (room.type) {
            case BOSS -> 'B';
            case SHOP, SHOP_INTERIOR -> '$';
            case TREASURE, TREASURE_MAZE -> 'T';
            case PLATFORM, PLATFORM_ASCENT -> 'P';
            default -> '#';
        };
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

    private static boolean isSolidLike(byte tile) {
        return tile == WorldGenerator.SOLID
            || tile == WorldGenerator.ICE
            || tile == WorldGenerator.LAVA
            || tile == WorldGenerator.DOOR_LOCKED
            || tile == WorldGenerator.CLIMBABLE;
    }

    private static boolean isHazard(byte tile) {
        return tile == WorldGenerator.LAVA || tile == WorldGenerator.GAS;
    }

    private static String roomId(WorldGraph.RoomNode room) {
        return room.gridX + "," + room.gridY;
    }

    private record GridBounds(int minGridX, int minGridY, int maxGridX, int maxGridY) {
        static GridBounds from(WorldGraph graph) {
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
            return new GridBounds(minX, minY, maxX, maxY);
        }

        MegamapSnapshot.Bounds toSnapshotBounds() {
            int widthRooms = maxGridX - minGridX + 1;
            int heightRooms = maxGridY - minGridY + 1;
            return new MegamapSnapshot.Bounds(
                minGridX,
                minGridY,
                maxGridX,
                maxGridY,
                widthRooms,
                heightRooms,
                widthRooms * WorldGraph.ROOM_W,
                heightRooms * WorldGraph.ROOM_H
            );
        }
    }

    private static final class MetricsAccumulator {
        private final CRC32 stitchedCrc = new CRC32();
        private final CRC32 autotileCrc = new CRC32();
        private final int stitchedTileCount;
        private int stampedTileCount;
        private int passableTileCount;
        private int solidTileCount;
        private int platformTileCount;
        private int hazardTileCount;
        private int solidLikeTileCount;

        MetricsAccumulator(int stitchedTileCount) {
            this.stitchedTileCount = stitchedTileCount;
        }

        void addRoomTiles(byte[][] tiles, int originX, int originY) {
            for (int y = 0; y < tiles.length; y++) {
                for (int x = 0; x < tiles[y].length; x++) {
                    byte tile = tiles[y][x];
                    stampedTileCount++;
                    if (tile == WorldGenerator.AIR || tile == WorldGenerator.WATER || tile == WorldGenerator.GAS) {
                        passableTileCount++;
                    }
                    if (tile == WorldGenerator.PLATFORM) {
                        platformTileCount++;
                    }
                    if (isSolidLike(tile)) {
                        solidTileCount++;
                        solidLikeTileCount++;
                        autotileCrc.update(edgeMask(tiles, x, y));
                    }
                    if (isHazard(tile)) {
                        hazardTileCount++;
                    }
                    stitchedCrc.update((originX + x) & 0xFF);
                    stitchedCrc.update((originY + y) & 0xFF);
                    stitchedCrc.update(tile);
                }
            }
        }

        MegamapSnapshot.Metrics toMetrics(int roomCount, int seamCount) {
            return new MegamapSnapshot.Metrics(
                roomCount,
                seamCount,
                stitchedTileCount,
                stampedTileCount,
                stitchedTileCount - stampedTileCount,
                passableTileCount,
                solidTileCount,
                platformTileCount,
                hazardTileCount,
                Long.toUnsignedString(stitchedCrc.getValue(), 16)
            );
        }

        MegamapSnapshot.AutotileSummary toAutotileSummary() {
            return new MegamapSnapshot.AutotileSummary(
                "edge-mask-preview",
                solidLikeTileCount,
                Long.toUnsignedString(autotileCrc.getValue(), 16)
            );
        }

        private int edgeMask(byte[][] tiles, int x, int y) {
            int mask = 0;
            if (y > 0 && isSolidLike(tiles[y - 1][x])) {
                mask |= 1;
            }
            if (x + 1 < tiles[y].length && isSolidLike(tiles[y][x + 1])) {
                mask |= 2;
            }
            if (y + 1 < tiles.length && isSolidLike(tiles[y + 1][x])) {
                mask |= 4;
            }
            if (x > 0 && isSolidLike(tiles[y][x - 1])) {
                mask |= 8;
            }
            return mask;
        }
    }
}
