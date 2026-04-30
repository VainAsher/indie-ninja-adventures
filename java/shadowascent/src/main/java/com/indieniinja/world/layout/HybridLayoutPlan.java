package com.indieniinja.world.layout;

import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Deterministic section-footprint layout above legacy room generation.
 *
 * This slice emits inspectable grid placement metadata only. Runtime room
 * generation still uses the legacy WorldGraph path until later slices consume
 * these assignments for room instantiation.
 */
public record HybridLayoutPlan(
        long worldSeed,
        Bounds bounds,
        List<SectionAssignment> assignments,
        List<Connection> connections) {
    public HybridLayoutPlan {
        bounds = bounds != null ? bounds : Bounds.empty();
        assignments = List.copyOf(assignments != null ? assignments : List.of());
        connections = List.copyOf(connections != null ? connections : List.of());
    }

    public Optional<SectionAssignment> assignmentByNodeId(String nodeId) {
        return assignments.stream()
            .filter(assignment -> assignment.nodeId().equals(nodeId))
            .findFirst();
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("worldSeed", worldSeed);
        out.put("bounds", bounds.toSnapshot());
        out.put("assignmentCount", assignments.size());
        out.put("connectionCount", connections.size());
        out.put("assignments", assignments.stream()
            .sorted(Comparator
                .comparingInt(SectionAssignment::y)
                .thenComparingInt(SectionAssignment::x)
                .thenComparing(SectionAssignment::nodeId))
            .map(SectionAssignment::toSnapshot)
            .toList());
        out.put("connections", connections.stream()
            .sorted(Comparator
                .comparing(Connection::fromNodeId)
                .thenComparing(Connection::toNodeId))
            .map(Connection::toSnapshot)
            .toList());
        return out;
    }

    public record SectionAssignment(
            String nodeId,
            String templateId,
            String biome,
            String kind,
            String partitionId,
            int x,
            int y,
            int w,
            int h,
            boolean optional) {
        public SectionAssignment {
            nodeId = requireText(nodeId, "nodeId");
            templateId = requireText(templateId, "templateId");
            biome = requireText(biome, "biome");
            kind = requireText(kind, "kind");
            partitionId = requireText(partitionId, "partitionId");
            w = Math.max(1, w);
            h = Math.max(1, h);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("nodeId", nodeId);
            out.put("templateId", templateId);
            out.put("biome", biome);
            out.put("kind", kind);
            out.put("partitionId", partitionId);
            out.put("x", x);
            out.put("y", y);
            out.put("w", w);
            out.put("h", h);
            out.put("optional", optional);
            return out;
        }
    }

    public record Connection(String fromNodeId, String toNodeId, String policy) {
        public Connection {
            fromNodeId = requireText(fromNodeId, "fromNodeId");
            toNodeId = requireText(toNodeId, "toNodeId");
            policy = policy == null || policy.isBlank() ? "direct_grid" : policy;
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("fromNodeId", fromNodeId);
            out.put("toNodeId", toNodeId);
            out.put("policy", policy);
            return out;
        }
    }

    public record Bounds(int minX, int minY, int maxX, int maxY) {
        static Bounds empty() {
            return new Bounds(0, 0, 0, 0);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("minX", minX);
            out.put("minY", minY);
            out.put("maxX", maxX);
            out.put("maxY", maxY);
            out.put("width", Math.max(0, maxX - minX));
            out.put("height", Math.max(0, maxY - minY));
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
