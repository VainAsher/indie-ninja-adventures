package com.indieniinja.content;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public record EnemyDefinition(
    String id,
    String displayName,
    int width,
    int height,
    int physicsHeight,
    int baseHp,
    int damage,
    float speed,
    float detectionRange,
    float attackRange,
    float attackWindupSeconds,
    float fleeHpThreshold,
    int knockoutDurationTicks,
    int xpReward,
    String animationKey,
    String aiProfile,
    int spawnWeight,
    List<String> biomeAffinity,
    Set<String> tags
) {
    public static EnemyDefinition fromJson(JsonNode node) {
        List<String> biomes = new ArrayList<>();
        if (node.has("biomeAffinity")) {
            node.get("biomeAffinity").forEach(n -> biomes.add(n.asText()));
        }
        Set<String> tags = new HashSet<>();
        if (node.has("tags")) {
            node.get("tags").forEach(n -> tags.add(n.asText()));
        }
        return new EnemyDefinition(
            node.get("id").asText(),
            node.get("displayName").asText(),
            node.get("width").asInt(),
            node.get("height").asInt(),
            node.get("physicsHeight").asInt(),
            node.get("baseHp").asInt(),
            node.get("damage").asInt(),
            (float) node.get("speed").asDouble(),
            (float) node.get("detectionRange").asDouble(),
            (float) node.get("attackRange").asDouble(),
            node.has("attackWindupSeconds") ? (float) node.get("attackWindupSeconds").asDouble() : 0.5f,
            node.has("fleeHpThreshold")     ? (float) node.get("fleeHpThreshold").asDouble()     : 0.0f,
            node.has("knockoutDurationTicks")? node.get("knockoutDurationTicks").asInt()          : 120,
            node.has("xpReward")            ? node.get("xpReward").asInt()                       : 0,
            node.get("animationKey").asText(),
            node.get("aiProfile").asText(),
            node.has("spawnWeight")         ? node.get("spawnWeight").asInt()                    : 5,
            biomes,
            tags
        );
    }
}
