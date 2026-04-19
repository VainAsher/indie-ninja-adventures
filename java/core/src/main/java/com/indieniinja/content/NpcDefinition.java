package com.indieniinja.content;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public record NpcDefinition(
    String id,
    String displayName,
    int width,
    int height,
    String animationKey,
    String dialogueTreeId,
    boolean isQuestGiver,
    boolean isShop,
    boolean isBoss,
    int bossPhases,
    List<String> bossAnimationKeys,
    Map<String, Boolean> hubPresenceByState
) {
    public static NpcDefinition fromJson(JsonNode node) {
        List<String> bossKeys = new ArrayList<>();
        if (node.has("bossAnimationKeys")) {
            node.get("bossAnimationKeys").forEach(n -> bossKeys.add(n.asText()));
        }
        Map<String, Boolean> hubPresence = new HashMap<>();
        if (node.has("hubPresenceByState")) {
            node.get("hubPresenceByState").fields().forEachRemaining(e ->
                hubPresence.put(e.getKey(), e.getValue().asBoolean()));
        }
        return new NpcDefinition(
            node.get("id").asText(),
            node.get("displayName").asText(),
            node.get("width").asInt(),
            node.get("height").asInt(),
            node.get("animationKey").asText(),
            node.has("dialogueTreeId") ? node.get("dialogueTreeId").asText() : null,
            node.has("isQuestGiver")   ? node.get("isQuestGiver").asBoolean() : false,
            node.has("isShop")         ? node.get("isShop").asBoolean()        : false,
            node.has("isBoss")         ? node.get("isBoss").asBoolean()        : false,
            node.has("bossPhases")     ? node.get("bossPhases").asInt()        : 1,
            bossKeys,
            hubPresence
        );
    }
}
