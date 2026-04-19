package com.indieniinja.content;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;

public record RoomTypeDefinition(
    String id,
    String displayName,
    int enemyDensity,
    boolean hasPortal,
    boolean hasPuzzle,
    boolean hasShop,
    int lootTier,
    /** 0=open/clean, 1=moderate, 2=dense, 3=maze-like */
    int terrainDensity,
    List<String> allowedBiomes,
    List<String> spawnableEnemyTags,
    List<String> environmentHazards,
    int minRoomWidth,
    int minRoomHeight,
    boolean requiresTemplate,
    String templateHint
) {
    public static RoomTypeDefinition fromJson(JsonNode node) {
        List<String> biomes = new ArrayList<>();
        if (node.has("allowedBiomes")) {
            node.get("allowedBiomes").forEach(n -> biomes.add(n.asText()));
        }
        List<String> enemyTags = new ArrayList<>();
        if (node.has("spawnableEnemyTags")) {
            node.get("spawnableEnemyTags").forEach(n -> enemyTags.add(n.asText()));
        }
        List<String> hazards = new ArrayList<>();
        if (node.has("environmentHazards")) {
            node.get("environmentHazards").forEach(n -> hazards.add(n.asText()));
        }
        int minW = 32, minH = 32;
        if (node.has("minRoomSize")) {
            minW = node.get("minRoomSize").get(0).asInt();
            minH = node.get("minRoomSize").get(1).asInt();
        }
        return new RoomTypeDefinition(
            node.get("id").asText(),
            node.get("displayName").asText(),
            node.has("enemyDensity")    ? node.get("enemyDensity").asInt()         : 0,
            node.has("hasPortal")       ? node.get("hasPortal").asBoolean()       : false,
            node.has("hasPuzzle")       ? node.get("hasPuzzle").asBoolean()       : false,
            node.has("hasShop")         ? node.get("hasShop").asBoolean()         : false,
            node.has("lootTier")        ? node.get("lootTier").asInt()            : 0,
            node.has("terrainDensity")  ? node.get("terrainDensity").asInt()      : 1,
            biomes,
            enemyTags,
            hazards,
            minW,
            minH,
            node.has("requiresTemplate") ? node.get("requiresTemplate").asBoolean() : false,
            node.has("templateHint")     ? node.get("templateHint").asText()         : null
        );
    }
}
