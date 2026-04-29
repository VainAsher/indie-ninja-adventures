package com.indieniinja.world;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.indieniinja.physics.PhysicsConstants;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Data-driven structural rules for generated and authored room geometry.
 *
 * The defaults preserve the current 128x128 room contract while making wall,
 * floor, and door dimensions explicit instead of scattering magic numbers
 * through room generation and validation.
 */
public record RoomGeometryRules(
        int roomWidthTiles,
        int roomHeightTiles,
        int edgeWallThickness,
        int floorThickness,
        int doorHalfSpan,
        int horizontalDoorDepth,
        int verticalDoorDepth
) {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static RoomGeometryRules defaults() {
        int tpz = PhysicsConstants.TILES_PER_ZONE;
        return new RoomGeometryRules(
            PhysicsConstants.ROOM_WIDTH_TILES,
            PhysicsConstants.ROOM_HEIGHT_TILES,
            1,
            2,
            tpz / 2 + 1,
            4,
            2
        );
    }

    public RoomGeometryRules {
        roomWidthTiles = Math.max(8, roomWidthTiles);
        roomHeightTiles = Math.max(8, roomHeightTiles);
        edgeWallThickness = clamp(edgeWallThickness, 1, Math.min(roomWidthTiles, roomHeightTiles) / 4);
        floorThickness = clamp(floorThickness, 1, roomHeightTiles / 4);
        doorHalfSpan = clamp(doorHalfSpan, 1, Math.min(roomWidthTiles, roomHeightTiles) / 2 - 1);
        horizontalDoorDepth = clamp(horizontalDoorDepth, 1, roomWidthTiles / 4);
        verticalDoorDepth = clamp(verticalDoorDepth, 1, roomHeightTiles / 4);
    }

    public static RoomGeometryRules loadDefault() {
        String override = System.getProperty("ninja.roomGeometryRules", "").trim();
        if (!override.isEmpty()) {
            return load(Paths.get(override));
        }

        Path javaWorkingDirPath = Paths.get("..", "data", "room_geometry_rules.json");
        if (Files.exists(javaWorkingDirPath)) {
            return load(javaWorkingDirPath);
        }

        Path repoRootPath = Paths.get("data", "room_geometry_rules.json");
        if (Files.exists(repoRootPath)) {
            return load(repoRootPath);
        }

        return defaults();
    }

    public static RoomGeometryRules load(Path path) {
        if (path == null || !Files.exists(path)) {
            return defaults();
        }
        try {
            JsonNode node = MAPPER.readTree(path.toFile());
            RoomGeometryRules d = defaults();
            return new RoomGeometryRules(
                intField(node, "roomWidthTiles", d.roomWidthTiles),
                intField(node, "roomHeightTiles", d.roomHeightTiles),
                intField(node, "edgeWallThickness", d.edgeWallThickness),
                intField(node, "floorThickness", d.floorThickness),
                intField(node, "doorHalfSpan", d.doorHalfSpan),
                intField(node, "horizontalDoorDepth", d.horizontalDoorDepth),
                intField(node, "verticalDoorDepth", d.verticalDoorDepth)
            );
        } catch (Exception e) {
            return defaults();
        }
    }

    private static int intField(JsonNode node, String field, int fallback) {
        JsonNode value = node != null ? node.get(field) : null;
        return value != null && value.canConvertToInt() ? value.asInt() : fallback;
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
