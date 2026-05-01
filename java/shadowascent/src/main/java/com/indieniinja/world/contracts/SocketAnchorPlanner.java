package com.indieniinja.world.contracts;

import com.indieniinja.world.layout.HybridLayoutPlan;
import com.indieniinja.world.sections.SectionTemplate;
import com.indieniinja.world.sections.SectionTemplateLibrary;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Resolves section socket requirements and anchor candidates into world-space
 * metadata that later validation and stitching slices can consume.
 */
public final class SocketAnchorPlanner {
    private static final int SECTION_GRID_TILE_SIZE = 64;
    private static final Set<String> VALID_SIDES = Set.of("north", "south", "east", "west");
    private static final Set<String> VALID_BANDS = Set.of("low", "mid", "high");
    private static final Set<String> TRANSITION_STRATEGY_TAGS = Set.of(
        "transition", "bridge", "ladder", "portal", "door", "climb", "vault", "shaft");

    private SocketAnchorPlanner() {}

    public static SocketAnchorPlan plan(
            long worldSeed,
            HybridLayoutPlan layout,
            SectionTemplateLibrary templates) {
        if (layout == null || templates == null || layout.assignments().isEmpty()) {
            return new SocketAnchorPlan(worldSeed, List.of(), List.of());
        }
        SocketPolicy socketPolicy = SocketPolicy.fromSystemProperties();

        Map<String, SectionTemplate> templatesById = templates.templates().stream()
            .collect(Collectors.toMap(SectionTemplate::id, template -> template, (first, ignored) -> first));

        List<SocketAnchorPlan.ConnectionContract> contracts = new ArrayList<>();
        for (HybridLayoutPlan.Connection connection : layout.connections()) {
            Optional<HybridLayoutPlan.SectionAssignment> from = layout.assignmentByNodeId(connection.fromNodeId());
            Optional<HybridLayoutPlan.SectionAssignment> to = layout.assignmentByNodeId(connection.toNodeId());
            if (from.isEmpty() || to.isEmpty()) {
                continue;
            }

            SectionTemplate fromTemplate = templatesById.get(from.get().templateId());
            SectionTemplate toTemplate = templatesById.get(to.get().templateId());
            String direction = direction(from.get(), to.get());
            SocketAnchorPlan.SocketContract fromSocket = chooseSocket(
                fromTemplate,
                socket -> socket.side().equals(direction),
                socketPolicy
            );
            SocketAnchorPlan.SocketContract toSocket = chooseSocket(
                toTemplate,
                socket -> socket.side().equals(opposite(direction)),
                socketPolicy
            );
            boolean isCompatible = compatible(fromSocket, toSocket);
            boolean mandatory = !from.get().optional() && !to.get().optional();
            String policy = (mandatory ? "mandatory_" : "optional_") + connection.policy();
            contracts.add(new SocketAnchorPlan.ConnectionContract(
                connection.fromNodeId(),
                connection.toNodeId(),
                fromSocket,
                toSocket,
                isCompatible ? "matched" : "needs_transition",
                policy,
                mandatory,
                isCompatible ? "direct" : deriveTransitionStrategy(fromSocket, toSocket)
            ));
        }

        List<SocketAnchorPlan.ResolvedAnchor> anchors = new ArrayList<>();
        for (HybridLayoutPlan.SectionAssignment assignment : layout.assignments()) {
            SectionTemplate template = templatesById.get(assignment.templateId());
            if (template == null) {
                continue;
            }
            int originX = assignment.x() * SECTION_GRID_TILE_SIZE;
            int originY = assignment.y() * SECTION_GRID_TILE_SIZE;
            for (SectionTemplate.Anchor anchor : template.anchors()) {
                SocketAnchorPlan.Bounds local = bounds(anchor.localBounds());
                SocketAnchorPlan.Bounds world = new SocketAnchorPlan.Bounds(
                    originX + local.x(),
                    originY + local.y(),
                    local.w(),
                    local.h()
                );
                anchors.add(new SocketAnchorPlan.ResolvedAnchor(
                    assignment.nodeId(),
                    assignment.templateId(),
                    anchor.id(),
                    anchor.kind(),
                    anchor.phase(),
                    local,
                    world,
                    anchor.tags(),
                    anchor.weight(),
                    anchor.quotaGroup(),
                    anchor.minDistance(),
                    anchor.requires(),
                    anchor.forbids()
                ));
            }
        }

        anchors.sort(Comparator
            .comparing(SocketAnchorPlan.ResolvedAnchor::nodeId)
            .thenComparing(SocketAnchorPlan.ResolvedAnchor::anchorId));
        return new SocketAnchorPlan(worldSeed, contracts, anchors);
    }

    private static SocketAnchorPlan.SocketContract chooseSocket(
            SectionTemplate template,
            Predicate<SocketAnchorPlan.SocketContract> preferred,
            SocketPolicy policy) {
        if (template == null || template.requiredSockets().isEmpty()) {
            return SocketAnchorPlan.SocketContract.missing("missing");
        }
        List<SocketAnchorPlan.SocketContract> sockets = template.requiredSockets().stream()
            .map(id -> parseSocket(id, policy))
            .toList();
        return sockets.stream()
            .filter(preferred)
            .findFirst()
            .orElse(sockets.get(0));
    }

    private static SocketAnchorPlan.SocketContract parseSocket(String id, SocketPolicy policy) {
        String[] parts = id == null ? new String[0] : id.split("_");
        String side = parts.length > 0 && !parts[0].isBlank() ? parts[0] : "unknown";
        String band = parts.length > 1 && !parts[1].isBlank() ? parts[1] : "mid";
        List<String> tags = parts.length > 2
            ? Arrays.stream(parts).skip(2).filter(part -> !part.isBlank()).toList()
            : List.of("walk");
        if (policy.strictGrammar()
                && (!VALID_SIDES.contains(side) || !VALID_BANDS.contains(band))) {
            return SocketAnchorPlan.SocketContract.missing(id != null ? id : "missing");
        }
        int width = tags.contains("jump") ? 3 : 4;
        int clearanceH = band.equals("low") ? 4 : 6;
        return new SocketAnchorPlan.SocketContract(id, side, band, tags, width, width, clearanceH);
    }

    private static boolean compatible(
            SocketAnchorPlan.SocketContract from,
            SocketAnchorPlan.SocketContract to) {
        if (from.side().equals("unknown") || to.side().equals("unknown")) {
            return false;
        }
        return from.traversalTags().stream().anyMatch(to.traversalTags()::contains)
            && Math.abs(bandValue(from.band()) - bandValue(to.band())) <= 1;
    }

    private static int bandValue(String band) {
        return switch (band) {
            case "low" -> 0;
            case "high" -> 2;
            default -> 1;
        };
    }

    private static String direction(
            HybridLayoutPlan.SectionAssignment from,
            HybridLayoutPlan.SectionAssignment to) {
        int fromCenterX = from.x() * 2 + from.w();
        int toCenterX = to.x() * 2 + to.w();
        int fromCenterY = from.y() * 2 + from.h();
        int toCenterY = to.y() * 2 + to.h();
        int dx = toCenterX - fromCenterX;
        int dy = toCenterY - fromCenterY;
        if (Math.abs(dx) >= Math.abs(dy)) {
            return dx >= 0 ? "east" : "west";
        }
        return dy >= 0 ? "south" : "north";
    }

    private static String opposite(String side) {
        return switch (side) {
            case "north" -> "south";
            case "south" -> "north";
            case "east" -> "west";
            case "west" -> "east";
            default -> "unknown";
        };
    }

    private static SocketAnchorPlan.Bounds bounds(SectionTemplate.Bounds bounds) {
        return new SocketAnchorPlan.Bounds(bounds.x(), bounds.y(), bounds.w(), bounds.h());
    }

    private static String deriveTransitionStrategy(
            SocketAnchorPlan.SocketContract from,
            SocketAnchorPlan.SocketContract to) {
        Set<String> tags = new LinkedHashSet<>();
        from.traversalTags().stream()
            .filter(TRANSITION_STRATEGY_TAGS::contains)
            .sorted()
            .forEach(tags::add);
        to.traversalTags().stream()
            .filter(TRANSITION_STRATEGY_TAGS::contains)
            .sorted()
            .forEach(tags::add);
        if (tags.isEmpty()) {
            return "none";
        }
        return String.join("+", tags);
    }

    private record SocketPolicy(boolean strictGrammar) {
        private static SocketPolicy fromSystemProperties() {
            return new SocketPolicy(Boolean.parseBoolean(
                System.getProperty("ninja.socketContractStrict", "false")));
        }
    }
}
