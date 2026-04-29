package com.indieniinja.world;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Locale;
import java.util.Map;

/**
 * Data-driven room-level structure rules for zone planning.
 *
 * These rules control how many obstacle/hazard zones are placed, how remaining
 * DECOR zones resolve, how thick the zone perimeter is, and whether the room
 * keeps an open center arena.
 */
public record RoomStructureRules(RoomSpec defaultRoomType, Map<String, RoomSpec> roomTypes) {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public record RoomSpec(
        int fillMin,
        int fillMax,
        float lavaChance,
        float iceChance,
        float waterChance,
        float decorFillChance,
        float decorPlatformChance,
        float decorWalkChance,
        int perimeterDepth,
        int centerClearRadiusZones
    ) {
        public RoomSpec {
            fillMin = Math.max(0, fillMin);
            fillMax = Math.max(fillMin, fillMax);
            lavaChance = chance(lavaChance);
            iceChance = chance(iceChance);
            waterChance = chance(waterChance);
            decorFillChance = chance(decorFillChance);
            decorPlatformChance = chance(decorPlatformChance);
            decorWalkChance = chance(decorWalkChance);
            perimeterDepth = clamp(perimeterDepth, 0, Math.min(ZonePlanner.W, ZonePlanner.H) / 2);
            centerClearRadiusZones = clamp(centerClearRadiusZones, 0, Math.min(ZonePlanner.W, ZonePlanner.H) / 2);
        }
    }

    public RoomStructureRules {
        defaultRoomType = defaultRoomType != null ? defaultRoomType : combatDefaults();
        roomTypes = roomTypes != null ? Map.copyOf(roomTypes) : Map.of();
    }

    public static RoomStructureRules defaults() {
        RoomSpec fallback = combatDefaults();
        Map<String, RoomSpec> specs = new HashMap<>();
        specs.put("combat", fallback);
        specs.put("platform", new RoomSpec(8, 13, 0.10f, 0.25f, 0.15f, 0.30f, 0.50f, 0.12f, 2, 0));
        specs.put("treasure", new RoomSpec(12, 16, 0.05f, 0.15f, 0.20f, 0.45f, 0.22f, 0.15f, 2, 0));
        specs.put("boss", new RoomSpec(5, 8, 0.35f, 0.10f, 0.05f, 0.18f, 0.30f, 0.22f, 2, 1));
        specs.put("trial", new RoomSpec(7, 10, 0.25f, 0.20f, 0.10f, 0.20f, 0.55f, 0.15f, 2, 0));
        RoomSpec navigable = new RoomSpec(3, 5, 0.10f, 0.10f, 0.10f, 0.12f, 0.28f, 0.30f, 2, 0);
        specs.put("shop", navigable);
        specs.put("start", navigable);
        specs.put("exit", navigable);
        return new RoomStructureRules(fallback, specs);
    }

    public static RoomStructureRules loadDefault() {
        String override = System.getProperty("ninja.roomStructureRules", "").trim();
        if (!override.isEmpty()) {
            return load(Paths.get(override));
        }

        Path javaWorkingDirPath = Paths.get("..", "data", "room_structure_rules.json");
        if (Files.exists(javaWorkingDirPath)) {
            return load(javaWorkingDirPath);
        }

        Path repoRootPath = Paths.get("data", "room_structure_rules.json");
        if (Files.exists(repoRootPath)) {
            return load(repoRootPath);
        }

        return defaults();
    }

    public static RoomStructureRules load(Path path) {
        RoomStructureRules defaults = defaults();
        if (path == null || !Files.exists(path)) {
            return defaults;
        }
        try {
            JsonNode root = MAPPER.readTree(path.toFile());
            RoomSpec defaultSpec = mergeSpec(defaults.defaultRoomType, root.get("defaultRoomType"));
            Map<String, RoomSpec> specs = new HashMap<>(defaults.roomTypes);
            JsonNode roomTypesNode = root.get("roomTypes");
            if (roomTypesNode != null && roomTypesNode.isObject()) {
                Iterator<Map.Entry<String, JsonNode>> fields = roomTypesNode.fields();
                while (fields.hasNext()) {
                    Map.Entry<String, JsonNode> field = fields.next();
                    String key = normalize(field.getKey());
                    RoomSpec base = specs.getOrDefault(key, defaultSpec);
                    specs.put(key, mergeSpec(base, field.getValue()));
                }
            }
            return new RoomStructureRules(defaultSpec, specs);
        } catch (Exception e) {
            return defaults;
        }
    }

    public RoomSpec specFor(String roomType) {
        String key = normalize(roomType);
        return roomTypes.getOrDefault(key, roomTypes.getOrDefault("combat", defaultRoomType));
    }

    private static RoomSpec mergeSpec(RoomSpec base, JsonNode node) {
        if (node == null || !node.isObject()) {
            return base;
        }
        return new RoomSpec(
            intField(node, "fillMin", base.fillMin),
            intField(node, "fillMax", base.fillMax),
            floatField(node, "lavaChance", base.lavaChance),
            floatField(node, "iceChance", base.iceChance),
            floatField(node, "waterChance", base.waterChance),
            floatField(node, "decorFillChance", base.decorFillChance),
            floatField(node, "decorPlatformChance", base.decorPlatformChance),
            floatField(node, "decorWalkChance", base.decorWalkChance),
            intField(node, "perimeterDepth", base.perimeterDepth),
            intField(node, "centerClearRadiusZones", base.centerClearRadiusZones)
        );
    }

    private static RoomSpec combatDefaults() {
        return new RoomSpec(10, 16, 0.20f, 0.10f, 0.10f, 0.38f, 0.38f, 0.14f, 2, 0);
    }

    private static int intField(JsonNode node, String field, int fallback) {
        JsonNode value = node.get(field);
        return value != null && value.canConvertToInt() ? value.asInt() : fallback;
    }

    private static float floatField(JsonNode node, String field, float fallback) {
        JsonNode value = node.get(field);
        return value != null && value.isNumber() ? (float) value.asDouble() : fallback;
    }

    private static String normalize(String roomType) {
        return roomType == null || roomType.isBlank() ? "combat" : roomType.toLowerCase(Locale.ROOT);
    }

    private static float chance(float value) {
        return Math.max(0f, Math.min(1f, value));
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
