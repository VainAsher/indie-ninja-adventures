package com.indieniinja.world.progression;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Deterministic macro progression graph above the legacy room graph.
 *
 * This layer describes world/region/dungeon beats, grants, and requirements.
 * It does not place rooms yet; later section/layout slices consume this graph.
 */
public final class WorldProgressionGraph {
    public enum NodeKind {
        CENTRAL_HUB,
        REGION_HUB,
        DUNGEON
    }

    private final long worldSeed;
    private final ProgressionNode centralHub;
    private final List<ProgressionNode> worldNodes;
    private final List<RegionHub> regionHubs;
    private final List<ProgressionNode> dungeonNodes;
    private final List<ProgressionNode> criticalPath;

    public WorldProgressionGraph(
            long worldSeed,
            ProgressionNode centralHub,
            List<ProgressionNode> worldNodes,
            List<RegionHub> regionHubs,
            List<ProgressionNode> dungeonNodes,
            List<ProgressionNode> criticalPath) {
        this.worldSeed = worldSeed;
        this.centralHub = Objects.requireNonNull(centralHub, "centralHub");
        this.worldNodes = List.copyOf(worldNodes);
        this.regionHubs = List.copyOf(regionHubs);
        this.dungeonNodes = List.copyOf(dungeonNodes);
        this.criticalPath = List.copyOf(criticalPath);
    }

    public long worldSeed() {
        return worldSeed;
    }

    public ProgressionNode centralHub() {
        return centralHub;
    }

    public List<ProgressionNode> worldNodes() {
        return worldNodes;
    }

    public List<RegionHub> regionHubs() {
        return regionHubs;
    }

    public List<ProgressionNode> dungeonNodes() {
        return dungeonNodes;
    }

    public List<ProgressionNode> criticalPath() {
        return criticalPath;
    }

    public List<ProgressionNode> allNodes() {
        List<ProgressionNode> nodes = new ArrayList<>(worldNodes.size() + dungeonNodes.size());
        nodes.addAll(worldNodes);
        nodes.addAll(dungeonNodes);
        return nodes;
    }

    public Map<String, ProgressionNode> nodesById() {
        Map<String, ProgressionNode> out = new LinkedHashMap<>();
        allNodes().stream()
            .sorted(Comparator.comparing(ProgressionNode::id))
            .forEach(node -> out.put(node.id(), node));
        return out;
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("worldSeed", worldSeed);
        out.put("centralHubId", centralHub.id());
        out.put("nodes", allNodes().stream().map(ProgressionNode::toSnapshot).toList());
        out.put("worldNodes", worldNodes.stream().map(ProgressionNode::toSnapshot).toList());
        out.put("regionHubs", regionHubs.stream().map(RegionHub::toSnapshot).toList());
        out.put("dungeonNodes", dungeonNodes.stream().map(ProgressionNode::toSnapshot).toList());
        out.put("criticalPath", criticalPath.stream().map(ProgressionNode::id).toList());
        return out;
    }

    public record ProgressionNode(
            String id,
            NodeKind kind,
            String biome,
            List<String> requires,
            List<String> grants,
            List<String> children,
            List<String> tags,
            String difficultyBand,
            boolean optional) {
        public ProgressionNode {
            id = requireText(id, "id");
            biome = requireText(biome, "biome");
            requires = List.copyOf(requires != null ? requires : List.of());
            grants = List.copyOf(grants != null ? grants : List.of());
            children = List.copyOf(children != null ? children : List.of());
            tags = List.copyOf(tags != null ? tags : List.of());
            difficultyBand = difficultyBand == null || difficultyBand.isBlank() ? "low" : difficultyBand;
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("id", id);
            out.put("kind", kind.name().toLowerCase());
            out.put("biome", biome);
            out.put("requires", requires);
            out.put("grants", grants);
            out.put("children", children);
            out.put("tags", tags);
            out.put("difficultyBand", difficultyBand);
            out.put("optional", optional);
            return out;
        }
    }

    public record RegionHub(
            String id,
            String entryNodeId,
            List<PortalRule> portalNodes,
            List<ShortcutRule> shortcutRules,
            List<String> services,
            String themeProfile) {
        public RegionHub {
            id = requireText(id, "id");
            entryNodeId = requireText(entryNodeId, "entryNodeId");
            portalNodes = List.copyOf(portalNodes != null ? portalNodes : List.of());
            shortcutRules = List.copyOf(shortcutRules != null ? shortcutRules : List.of());
            services = List.copyOf(services != null ? services : List.of());
            themeProfile = requireText(themeProfile, "themeProfile");
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("id", id);
            out.put("entryNodeId", entryNodeId);
            out.put("portalNodes", portalNodes.stream().map(PortalRule::toSnapshot).toList());
            out.put("shortcutRules", shortcutRules.stream().map(ShortcutRule::toSnapshot).toList());
            out.put("services", services);
            out.put("themeProfile", themeProfile);
            return out;
        }
    }

    public record PortalRule(String target, List<String> requires) {
        public PortalRule {
            target = requireText(target, "target");
            requires = List.copyOf(requires != null ? requires : List.of());
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("target", target);
            out.put("requires", requires);
            return out;
        }
    }

    public record ShortcutRule(String unlockOnGrant, String from, String to) {
        public ShortcutRule {
            unlockOnGrant = requireText(unlockOnGrant, "unlockOnGrant");
            from = requireText(from, "from");
            to = requireText(to, "to");
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("unlockOnGrant", unlockOnGrant);
            out.put("from", from);
            out.put("to", to);
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
