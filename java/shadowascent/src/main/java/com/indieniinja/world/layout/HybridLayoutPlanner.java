package com.indieniinja.world.layout;

import com.indieniinja.world.SeedHierarchy;
import com.indieniinja.world.progression.WorldProgressionGraph;
import com.indieniinja.world.sections.SectionTemplate;
import com.indieniinja.world.sections.SectionTemplateLibrary;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Places authored section footprints into deterministic macro grid space.
 *
 * The current algorithm is intentionally conservative: it keeps the critical
 * path in readable left-to-right order and places optional branches in a lower
 * row. Later slices can replace the placement strategy without changing the
 * exported plan contract.
 */
public final class HybridLayoutPlanner {
    private static final int GRID_ROW_WIDTH = 14;
    private static final int SECTION_GAP = 1;

    private HybridLayoutPlanner() {}

    public static HybridLayoutPlan plan(
            long worldSeed,
            WorldProgressionGraph progressionGraph,
            SectionTemplateLibrary sectionTemplates) {
        if (progressionGraph == null || sectionTemplates == null || sectionTemplates.templates().isEmpty()) {
            return new HybridLayoutPlan(worldSeed, HybridLayoutPlan.Bounds.empty(), List.of(), List.of());
        }

        Map<String, WorldProgressionGraph.ProgressionNode> nodesById = progressionGraph.nodesById();
        List<WorldProgressionGraph.ProgressionNode> ordered = orderedNodes(progressionGraph);
        List<HybridLayoutPlan.SectionAssignment> assignments = new ArrayList<>();
        Map<String, HybridLayoutPlan.SectionAssignment> byNodeId = new LinkedHashMap<>();

        Cursor cursor = new Cursor();
        for (WorldProgressionGraph.ProgressionNode node : ordered) {
            Optional<SectionTemplate> selected = selectTemplate(worldSeed, node, sectionTemplates);
            if (selected.isEmpty()) {
                continue;
            }

            SectionTemplate template = selected.get();
            cursor.advanceFor(template.footprint(), node.optional());
            HybridLayoutPlan.SectionAssignment assignment = new HybridLayoutPlan.SectionAssignment(
                node.id(),
                template.id(),
                node.biome(),
                template.kind(),
                partitionId(node, nodesById),
                cursor.x,
                cursor.y,
                template.footprint().gridW(),
                template.footprint().gridH(),
                node.optional()
            );
            assignments.add(assignment);
            byNodeId.put(node.id(), assignment);
            cursor.consume(template.footprint());
        }

        List<HybridLayoutPlan.Connection> connections = connections(progressionGraph, byNodeId.keySet());
        return new HybridLayoutPlan(worldSeed, bounds(assignments), assignments, connections);
    }

    private static List<WorldProgressionGraph.ProgressionNode> orderedNodes(WorldProgressionGraph graph) {
        List<WorldProgressionGraph.ProgressionNode> ordered = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (WorldProgressionGraph.ProgressionNode node : graph.criticalPath()) {
            if (node.kind() != WorldProgressionGraph.NodeKind.CENTRAL_HUB && seen.add(node.id())) {
                ordered.add(node);
            }
        }
        graph.allNodes().stream()
            .filter(node -> node.kind() != WorldProgressionGraph.NodeKind.CENTRAL_HUB)
            .filter(node -> seen.add(node.id()))
            .sorted(Comparator.comparing(WorldProgressionGraph.ProgressionNode::id))
            .forEach(ordered::add);
        return ordered;
    }

    private static Optional<SectionTemplate> selectTemplate(
            long worldSeed,
            WorldProgressionGraph.ProgressionNode node,
            SectionTemplateLibrary library) {
        String kind = sectionKind(node);
        long selectionSeed = SeedHierarchy.deriveSeed(worldSeed, "section_layout:" + node.id());
        Optional<SectionTemplate> exact = library.select(node.biome(), kind, selectionSeed);
        if (exact.isPresent()) {
            return exact;
        }

        List<SectionTemplate> sameKind = library.templates().stream()
            .filter(template -> template.kind().equals(kind))
            .sorted(Comparator.comparing(SectionTemplate::id))
            .toList();
        if (!sameKind.isEmpty()) {
            return Optional.of(sameKind.get(Math.floorMod(selectionSeed, sameKind.size())));
        }

        List<SectionTemplate> fallback = library.templates().stream()
            .sorted(Comparator.comparing(SectionTemplate::id))
            .toList();
        if (fallback.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(fallback.get(Math.floorMod(selectionSeed, fallback.size())));
    }

    private static String sectionKind(WorldProgressionGraph.ProgressionNode node) {
        if (node.kind() == WorldProgressionGraph.NodeKind.REGION_HUB) {
            return "shop_save_loop";
        }
        if (node.tags().contains("ability_trial")) {
            return "key_trial";
        }
        if (node.tags().contains("boss")) {
            return "boss_approach";
        }
        if (node.tags().contains("lock_gate")) {
            return "lock_gate";
        }
        if (node.tags().contains("treasure")) {
            return "treasure";
        }
        if (node.tags().contains("entry")) {
            return "region_entrance";
        }
        return "connector";
    }

    private static String partitionId(
            WorldProgressionGraph.ProgressionNode node,
            Map<String, WorldProgressionGraph.ProgressionNode> nodesById) {
        if (node.kind() == WorldProgressionGraph.NodeKind.REGION_HUB) {
            return node.id();
        }
        String best = "";
        for (String id : nodesById.keySet()) {
            if (id.endsWith("_region_1") || id.endsWith("_region_2")
                    || id.endsWith("_region_3") || id.endsWith("_region_4")) {
                String prefix = id.substring(0, id.indexOf("_region_"));
                if (node.id().startsWith(prefix) && (best.isBlank() || id.compareTo(best) < 0)) {
                    best = id;
                }
            }
        }
        return best.isBlank() ? "global" : best;
    }

    private static List<HybridLayoutPlan.Connection> connections(
            WorldProgressionGraph graph,
            Set<String> assignedNodeIds) {
        Map<String, HybridLayoutPlan.Connection> unique = new HashMap<>();
        for (WorldProgressionGraph.ProgressionNode node : graph.allNodes()) {
            if (!assignedNodeIds.contains(node.id())) {
                continue;
            }
            for (String child : node.children()) {
                if (!assignedNodeIds.contains(child)) {
                    continue;
                }
                HybridLayoutPlan.Connection connection = new HybridLayoutPlan.Connection(
                    node.id(), child, "progression_edge");
                unique.put(node.id() + "->" + child, connection);
            }
        }
        return unique.values().stream()
            .sorted(Comparator
                .comparing(HybridLayoutPlan.Connection::fromNodeId)
                .thenComparing(HybridLayoutPlan.Connection::toNodeId))
            .toList();
    }

    private static HybridLayoutPlan.Bounds bounds(List<HybridLayoutPlan.SectionAssignment> assignments) {
        if (assignments.isEmpty()) {
            return HybridLayoutPlan.Bounds.empty();
        }
        int minX = Integer.MAX_VALUE;
        int minY = Integer.MAX_VALUE;
        int maxX = Integer.MIN_VALUE;
        int maxY = Integer.MIN_VALUE;
        for (HybridLayoutPlan.SectionAssignment assignment : assignments) {
            minX = Math.min(minX, assignment.x());
            minY = Math.min(minY, assignment.y());
            maxX = Math.max(maxX, assignment.x() + assignment.w());
            maxY = Math.max(maxY, assignment.y() + assignment.h());
        }
        return new HybridLayoutPlan.Bounds(minX, minY, maxX, maxY);
    }

    private static final class Cursor {
        private int x;
        private int y;
        private int rowHeight = 1;
        private boolean optionalRowStarted;

        private void advanceFor(SectionTemplate.Footprint footprint, boolean optional) {
            if (optional && !optionalRowStarted) {
                x = 0;
                y += rowHeight + SECTION_GAP;
                rowHeight = 1;
                optionalRowStarted = true;
            }
            if (x > 0 && x + footprint.gridW() > GRID_ROW_WIDTH) {
                x = 0;
                y += rowHeight + SECTION_GAP;
                rowHeight = 1;
            }
        }

        private void consume(SectionTemplate.Footprint footprint) {
            x += footprint.gridW() + SECTION_GAP;
            rowHeight = Math.max(rowHeight, footprint.gridH());
        }
    }
}
