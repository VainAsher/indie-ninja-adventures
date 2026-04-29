package com.indieniinja.world.progression;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * Solvability validator for macro progression graphs.
 */
public final class ProgressionValidator {
    private ProgressionValidator() {}

    public static ProgressionValidationResult validate(WorldProgressionGraph graph) {
        Map<String, WorldProgressionGraph.ProgressionNode> nodes = graph.nodesById();
        Set<String> reachable = new LinkedHashSet<>();
        Set<String> grants = new LinkedHashSet<>();
        reachable.add(graph.centralHub().id());
        grants.addAll(graph.centralHub().grants());

        boolean changed;
        do {
            changed = false;
            for (WorldProgressionGraph.ProgressionNode node : nodes.values()) {
                if (!reachable.contains(node.id())) {
                    continue;
                }
                for (String childId : node.children()) {
                    WorldProgressionGraph.ProgressionNode child = nodes.get(childId);
                    if (child == null || reachable.contains(childId)) {
                        continue;
                    }
                    if (grants.containsAll(child.requires())) {
                        reachable.add(childId);
                        grants.addAll(child.grants());
                        changed = true;
                    }
                }
            }
        } while (changed);

        ArrayList<String> blocked = new ArrayList<>();
        for (WorldProgressionGraph.ProgressionNode node : graph.allNodes()) {
            if (!reachable.contains(node.id()) && !node.optional()) {
                blocked.add(node.id());
            }
        }

        boolean valid = blocked.isEmpty();
        String message = valid ? "valid" : "blocked required nodes: " + blocked;
        return new ProgressionValidationResult(valid, message, reachable, grants, blocked);
    }
}
