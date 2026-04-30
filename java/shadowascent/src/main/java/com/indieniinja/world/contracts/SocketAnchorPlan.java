package com.indieniinja.world.contracts;

import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Inspectable socket and anchor metadata resolved from section layout.
 *
 * This is a planning/export layer only. Runtime room joins still flow through
 * the legacy room graph until later slices consume these contracts.
 */
public record SocketAnchorPlan(
        long worldSeed,
        List<ConnectionContract> connectionContracts,
        List<ResolvedAnchor> resolvedAnchors) {
    public SocketAnchorPlan {
        connectionContracts = List.copyOf(connectionContracts != null ? connectionContracts : List.of());
        resolvedAnchors = List.copyOf(resolvedAnchors != null ? resolvedAnchors : List.of());
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("worldSeed", worldSeed);
        out.put("connectionContractCount", connectionContracts.size());
        out.put("resolvedAnchorCount", resolvedAnchors.size());
        out.put("connectionContracts", connectionContracts.stream()
            .sorted(Comparator
                .comparing(ConnectionContract::fromNodeId)
                .thenComparing(ConnectionContract::toNodeId))
            .map(ConnectionContract::toSnapshot)
            .toList());
        out.put("resolvedAnchors", resolvedAnchors.stream()
            .sorted(Comparator
                .comparing(ResolvedAnchor::nodeId)
                .thenComparing(ResolvedAnchor::anchorId))
            .map(ResolvedAnchor::toSnapshot)
            .toList());
        return out;
    }

    public record ConnectionContract(
            String fromNodeId,
            String toNodeId,
            SocketContract fromSocket,
            SocketContract toSocket,
            String status,
            String policy) {
        public ConnectionContract {
            fromNodeId = requireText(fromNodeId, "fromNodeId");
            toNodeId = requireText(toNodeId, "toNodeId");
            fromSocket = fromSocket != null ? fromSocket : SocketContract.missing("missing_from");
            toSocket = toSocket != null ? toSocket : SocketContract.missing("missing_to");
            status = status == null || status.isBlank() ? "needs_transition" : status;
            policy = policy == null || policy.isBlank() ? "progression_edge" : policy;
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("fromNodeId", fromNodeId);
            out.put("toNodeId", toNodeId);
            out.put("fromSocket", fromSocket.toSnapshot());
            out.put("toSocket", toSocket.toSnapshot());
            out.put("status", status);
            out.put("policy", policy);
            return out;
        }
    }

    public record SocketContract(
            String id,
            String side,
            String band,
            List<String> traversalTags,
            int width,
            int clearanceW,
            int clearanceH) {
        public SocketContract {
            id = requireText(id, "id");
            side = side == null || side.isBlank() ? "unknown" : side;
            band = band == null || band.isBlank() ? "mid" : band;
            traversalTags = List.copyOf(traversalTags != null ? traversalTags : List.of());
            width = Math.max(1, width);
            clearanceW = Math.max(width, clearanceW);
            clearanceH = Math.max(1, clearanceH);
        }

        static SocketContract missing(String id) {
            return new SocketContract(id, "unknown", "mid", List.of("transition"), 1, 1, 1);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("id", id);
            out.put("side", side);
            out.put("band", band);
            out.put("traversalTags", traversalTags);
            out.put("width", width);
            out.put("clearance", Map.of("w", clearanceW, "h", clearanceH));
            return out;
        }
    }

    public record ResolvedAnchor(
            String nodeId,
            String templateId,
            String anchorId,
            String kind,
            String phase,
            Bounds localBounds,
            Bounds worldBounds,
            List<String> tags,
            double weight,
            String quotaGroup,
            int minDistance,
            List<String> requires,
            List<String> forbids) {
        public ResolvedAnchor {
            nodeId = requireText(nodeId, "nodeId");
            templateId = requireText(templateId, "templateId");
            anchorId = requireText(anchorId, "anchorId");
            kind = requireText(kind, "kind");
            phase = phase == null || phase.isBlank() ? "local" : phase;
            localBounds = localBounds != null ? localBounds : new Bounds(0, 0, 1, 1);
            worldBounds = worldBounds != null ? worldBounds : localBounds;
            tags = List.copyOf(tags != null ? tags : List.of());
            weight = Math.max(0.0, weight);
            quotaGroup = quotaGroup == null || quotaGroup.isBlank() ? kind : quotaGroup;
            minDistance = Math.max(0, minDistance);
            requires = List.copyOf(requires != null ? requires : List.of());
            forbids = List.copyOf(forbids != null ? forbids : List.of());
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("nodeId", nodeId);
            out.put("templateId", templateId);
            out.put("anchorId", anchorId);
            out.put("kind", kind);
            out.put("phase", phase);
            out.put("localBounds", localBounds.toSnapshot());
            out.put("worldBounds", worldBounds.toSnapshot());
            out.put("tags", tags);
            out.put("weight", weight);
            out.put("quotaGroup", quotaGroup);
            out.put("minDistance", minDistance);
            out.put("requires", requires);
            out.put("forbids", forbids);
            return out;
        }
    }

    public record Bounds(int x, int y, int w, int h) {
        public Bounds {
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

    private static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " must not be blank");
        }
        return value;
    }
}
