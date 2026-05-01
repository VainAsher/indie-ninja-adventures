package com.indieniinja.world.progression;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Loads an authored WorldProgressionGraph from data/worldgen/progressions/{campaignId}.json.
 *
 * Falls back to empty if the file is not found, allowing callers to use the procedural
 * generator as a fallback. Mirrors the path-search pattern from SectionTemplateLibrary.
 */
public final class AuthoredProgressionLoader {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private AuthoredProgressionLoader() {}

    public static Optional<WorldProgressionGraph> load(String campaignId, long worldSeed) {
        if (campaignId == null || campaignId.isBlank()) {
            return Optional.empty();
        }
        Path file = resolveFile(campaignId);
        if (file == null) {
            return Optional.empty();
        }
        try {
            JsonNode root = MAPPER.readTree(file.toFile());
            return Optional.of(parse(root, worldSeed));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    private static Path resolveFile(String campaignId) {
        String override = System.getProperty("ninja.progressionRoot", "").trim();
        String filename = campaignId + ".json";

        if (!override.isEmpty()) {
            Path p = Paths.get(override).resolve(filename);
            return Files.isRegularFile(p) ? p : null;
        }

        for (Path base : List.of(
                Paths.get("data", "worldgen", "progressions"),
                Paths.get("..", "data", "worldgen", "progressions"),
                Paths.get("..", "..", "data", "worldgen", "progressions"))) {
            Path candidate = base.resolve(filename);
            if (Files.isRegularFile(candidate)) {
                return candidate;
            }
        }
        return null;
    }

    private static WorldProgressionGraph parse(JsonNode root, long worldSeed) {
        JsonNode hubNode = root.get("centralHub");
        WorldProgressionGraph.ProgressionNode centralHub = parseNode(hubNode);

        List<WorldProgressionGraph.ProgressionNode> worldNodes = new ArrayList<>();
        worldNodes.add(centralHub);

        List<WorldProgressionGraph.ProgressionNode> dungeonNodes = new ArrayList<>();
        JsonNode nodesArray = root.get("nodes");
        if (nodesArray != null && nodesArray.isArray()) {
            for (JsonNode n : nodesArray) {
                dungeonNodes.add(parseNode(n));
            }
        }

        // Build id→node map for critical path resolution
        Map<String, WorldProgressionGraph.ProgressionNode> byId = new LinkedHashMap<>();
        byId.put(centralHub.id(), centralHub);
        dungeonNodes.forEach(n -> byId.put(n.id(), n));

        List<WorldProgressionGraph.ProgressionNode> criticalPath = new ArrayList<>();
        JsonNode cpArray = root.get("criticalPath");
        if (cpArray != null && cpArray.isArray()) {
            for (JsonNode idNode : cpArray) {
                WorldProgressionGraph.ProgressionNode n = byId.get(idNode.asText());
                if (n != null) {
                    criticalPath.add(n);
                }
            }
        }

        return new WorldProgressionGraph(
                worldSeed,
                centralHub,
                worldNodes,
                List.of(),
                dungeonNodes,
                criticalPath,
                "authored");
    }

    private static WorldProgressionGraph.ProgressionNode parseNode(JsonNode n) {
        String id = n.path("id").asText();
        String kindStr = n.path("kind").asText("dungeon");
        WorldProgressionGraph.NodeKind kind = parseKind(kindStr);
        String biome = n.path("biome").asText("forest");
        String difficultyBand = n.path("difficultyBand").asText("low");
        boolean optional = n.path("optional").asBoolean(false);

        List<String> requires = stringList(n.get("requires"));
        List<String> grants = stringList(n.get("grants"));
        List<String> children = stringList(n.get("children"));
        List<String> tags = stringList(n.get("tags"));

        return new WorldProgressionGraph.ProgressionNode(
                id, kind, biome, requires, grants, children, tags, difficultyBand, optional);
    }

    private static WorldProgressionGraph.NodeKind parseKind(String kind) {
        return switch (kind.toLowerCase()) {
            case "central_hub" -> WorldProgressionGraph.NodeKind.CENTRAL_HUB;
            case "region_hub"  -> WorldProgressionGraph.NodeKind.REGION_HUB;
            default            -> WorldProgressionGraph.NodeKind.DUNGEON;
        };
    }

    private static List<String> stringList(JsonNode node) {
        List<String> out = new ArrayList<>();
        if (node != null && node.isArray()) {
            node.forEach(e -> out.add(e.asText()));
        }
        return out;
    }
}
