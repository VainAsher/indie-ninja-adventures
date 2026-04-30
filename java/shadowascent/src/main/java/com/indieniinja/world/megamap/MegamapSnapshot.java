package com.indieniinja.world.megamap;

import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Compact continuous-map export for deterministic worldgen inspection.
 *
 * The snapshot records stitched room origins, seam metadata, overlay rows, and
 * metrics without replacing live server room placement.
 */
public record MegamapSnapshot(
        long worldSeed,
        int requestedRooms,
        String shape,
        String goldenSeedKey,
        Bounds bounds,
        List<RoomStamp> rooms,
        List<Seam> seams,
        List<String> overlayRows,
        Metrics metrics,
        AutotileSummary autotileSummary) {
    public MegamapSnapshot {
        shape = requireText(shape, "shape");
        goldenSeedKey = requireText(goldenSeedKey, "goldenSeedKey");
        bounds = bounds != null ? bounds : Bounds.empty();
        rooms = List.copyOf(rooms != null ? rooms : List.of());
        seams = List.copyOf(seams != null ? seams : List.of());
        overlayRows = List.copyOf(overlayRows != null ? overlayRows : List.of());
        metrics = metrics != null ? metrics : Metrics.empty();
        autotileSummary = autotileSummary != null ? autotileSummary : AutotileSummary.empty();
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("worldSeed", worldSeed);
        out.put("requestedRooms", requestedRooms);
        out.put("shape", shape);
        out.put("goldenSeedKey", goldenSeedKey);
        out.put("bounds", bounds.toSnapshot());
        out.put("roomCount", rooms.size());
        out.put("seamCount", seams.size());
        out.put("rooms", rooms.stream()
            .sorted(Comparator
                .comparingInt(RoomStamp::originY)
                .thenComparingInt(RoomStamp::originX)
                .thenComparing(RoomStamp::id))
            .map(RoomStamp::toSnapshot)
            .toList());
        out.put("seams", seams.stream()
            .sorted(Comparator
                .comparing(Seam::fromRoomId)
                .thenComparing(Seam::toRoomId)
                .thenComparing(Seam::direction))
            .map(Seam::toSnapshot)
            .toList());
        out.put("overlayRows", overlayRows);
        out.put("metrics", metrics.toSnapshot());
        out.put("autotileSummary", autotileSummary.toSnapshot());
        return out;
    }

    public record Bounds(
            int minGridX,
            int minGridY,
            int maxGridX,
            int maxGridY,
            int widthRooms,
            int heightRooms,
            int widthTiles,
            int heightTiles) {
        public Bounds {
            widthRooms = Math.max(0, widthRooms);
            heightRooms = Math.max(0, heightRooms);
            widthTiles = Math.max(0, widthTiles);
            heightTiles = Math.max(0, heightTiles);
        }

        static Bounds empty() {
            return new Bounds(0, 0, 0, 0, 0, 0, 0, 0);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("minGridX", minGridX);
            out.put("minGridY", minGridY);
            out.put("maxGridX", maxGridX);
            out.put("maxGridY", maxGridY);
            out.put("widthRooms", widthRooms);
            out.put("heightRooms", heightRooms);
            out.put("widthTiles", widthTiles);
            out.put("heightTiles", heightTiles);
            return out;
        }
    }

    public record RoomStamp(
            String id,
            int gridX,
            int gridY,
            int originX,
            int originY,
            int w,
            int h,
            String type,
            int biomeIndex,
            String tileChecksum) {
        public RoomStamp {
            id = requireText(id, "id");
            type = requireText(type, "type");
            tileChecksum = requireText(tileChecksum, "tileChecksum");
            w = Math.max(1, w);
            h = Math.max(1, h);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("id", id);
            out.put("gridX", gridX);
            out.put("gridY", gridY);
            out.put("originX", originX);
            out.put("originY", originY);
            out.put("w", w);
            out.put("h", h);
            out.put("type", type);
            out.put("biomeIndex", biomeIndex);
            out.put("tileChecksum", tileChecksum);
            return out;
        }
    }

    public record Seam(
            String fromRoomId,
            String toRoomId,
            String direction,
            BoundsTiles bounds,
            boolean passable) {
        public Seam {
            fromRoomId = requireText(fromRoomId, "fromRoomId");
            toRoomId = requireText(toRoomId, "toRoomId");
            direction = requireText(direction, "direction");
            bounds = bounds != null ? bounds : new BoundsTiles(0, 0, 1, 1);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("fromRoomId", fromRoomId);
            out.put("toRoomId", toRoomId);
            out.put("direction", direction);
            out.put("bounds", bounds.toSnapshot());
            out.put("passable", passable);
            return out;
        }
    }

    public record BoundsTiles(int x, int y, int w, int h) {
        public BoundsTiles {
            w = Math.max(1, w);
            h = Math.max(1, h);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("x", x);
            out.put("y", y);
            out.put("w", w);
            out.put("h", h);
            return out;
        }
    }

    public record Metrics(
            int roomCount,
            int seamCount,
            int stitchedTileCount,
            int stampedTileCount,
            int emptyTileCount,
            int passableTileCount,
            int solidTileCount,
            int platformTileCount,
            int hazardTileCount,
            String stitchedTileChecksum) {
        public Metrics {
            roomCount = Math.max(0, roomCount);
            seamCount = Math.max(0, seamCount);
            stitchedTileCount = Math.max(0, stitchedTileCount);
            stampedTileCount = Math.max(0, stampedTileCount);
            emptyTileCount = Math.max(0, emptyTileCount);
            passableTileCount = Math.max(0, passableTileCount);
            solidTileCount = Math.max(0, solidTileCount);
            platformTileCount = Math.max(0, platformTileCount);
            hazardTileCount = Math.max(0, hazardTileCount);
            stitchedTileChecksum = stitchedTileChecksum == null ? "0" : stitchedTileChecksum;
        }

        static Metrics empty() {
            return new Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0, "0");
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("roomCount", roomCount);
            out.put("seamCount", seamCount);
            out.put("stitchedTileCount", stitchedTileCount);
            out.put("stampedTileCount", stampedTileCount);
            out.put("emptyTileCount", emptyTileCount);
            out.put("passableTileCount", passableTileCount);
            out.put("solidTileCount", solidTileCount);
            out.put("platformTileCount", platformTileCount);
            out.put("hazardTileCount", hazardTileCount);
            out.put("stitchedTileChecksum", stitchedTileChecksum);
            return out;
        }
    }

    public record AutotileSummary(
            String mode,
            int solidLikeTileCount,
            String solidEdgeMaskChecksum) {
        public AutotileSummary {
            mode = mode == null || mode.isBlank() ? "edge-mask-preview" : mode;
            solidLikeTileCount = Math.max(0, solidLikeTileCount);
            solidEdgeMaskChecksum = solidEdgeMaskChecksum == null ? "0" : solidEdgeMaskChecksum;
        }

        static AutotileSummary empty() {
            return new AutotileSummary("edge-mask-preview", 0, "0");
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("mode", mode);
            out.put("solidLikeTileCount", solidLikeTileCount);
            out.put("solidEdgeMaskChecksum", solidEdgeMaskChecksum);
            return out;
        }
    }

    private static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " must not be blank");
        }
        return value;
    }
}
