package com.indieniinja.world.sections;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Authored pacing chunk consumed between progression graphs and room layout.
 *
 * Slice 4 only loads and exports these templates. Later layout slices will
 * place footprints, match sockets, and resolve anchors against live rooms.
 */
public record SectionTemplate(
        String id,
        String biome,
        String kind,
        Footprint footprint,
        List<String> nodeKinds,
        List<EdgeRule> edgeRules,
        List<String> requiredSockets,
        List<MutableZone> mutableZones,
        List<Anchor> anchors) {
    public SectionTemplate {
        id = requireText(id, "id");
        biome = requireText(biome, "biome");
        kind = requireText(kind, "kind");
        footprint = footprint != null ? footprint : new Footprint(1, 1);
        nodeKinds = List.copyOf(nodeKinds != null ? nodeKinds : List.of());
        edgeRules = List.copyOf(edgeRules != null ? edgeRules : List.of());
        requiredSockets = List.copyOf(requiredSockets != null ? requiredSockets : List.of());
        mutableZones = List.copyOf(mutableZones != null ? mutableZones : List.of());
        anchors = List.copyOf(anchors != null ? anchors : List.of());
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", id);
        out.put("biome", biome);
        out.put("kind", kind);
        out.put("footprint", footprint.toSnapshot());
        out.put("nodeKinds", nodeKinds);
        out.put("edgeRules", edgeRules.stream().map(EdgeRule::toSnapshot).toList());
        out.put("requiredSockets", requiredSockets);
        out.put("mutableZones", mutableZones.stream().map(MutableZone::toSnapshot).toList());
        out.put("anchors", anchors.stream().map(Anchor::toSnapshot).toList());
        return out;
    }

    public record Footprint(int gridW, int gridH) {
        public Footprint {
            gridW = Math.max(1, gridW);
            gridH = Math.max(1, gridH);
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("gridW", gridW);
            out.put("gridH", gridH);
            return out;
        }
    }

    public record EdgeRule(String from, String to) {
        public EdgeRule {
            from = requireText(from, "from");
            to = requireText(to, "to");
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("from", from);
            out.put("to", to);
            return out;
        }
    }

    public record MutableZone(int x, int y, int w, int h, String role) {
        public MutableZone {
            w = Math.max(1, w);
            h = Math.max(1, h);
            role = requireText(role, "role");
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("x", x);
            out.put("y", y);
            out.put("w", w);
            out.put("h", h);
            out.put("role", role);
            return out;
        }
    }

    public record Anchor(
            String id,
            String kind,
            String phase,
            Bounds localBounds,
            List<String> tags,
            double weight,
            String quotaGroup,
            int minDistance,
            List<String> requires,
            List<String> forbids) {
        public Anchor {
            id = requireText(id, "id");
            kind = requireText(kind, "kind");
            phase = phase == null || phase.isBlank() ? "local" : phase;
            localBounds = localBounds != null ? localBounds : new Bounds(0, 0, 1, 1);
            tags = List.copyOf(tags != null ? tags : List.of());
            weight = Math.max(0.0, weight);
            quotaGroup = quotaGroup == null || quotaGroup.isBlank() ? kind : quotaGroup;
            minDistance = Math.max(0, minDistance);
            requires = List.copyOf(requires != null ? requires : List.of());
            forbids = List.copyOf(forbids != null ? forbids : List.of());
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("id", id);
            out.put("kind", kind);
            out.put("phase", phase);
            out.put("localBounds", localBounds.toSnapshot());
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
