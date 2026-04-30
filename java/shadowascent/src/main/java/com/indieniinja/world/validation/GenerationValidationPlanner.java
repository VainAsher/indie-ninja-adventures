package com.indieniinja.world.validation;

import com.indieniinja.world.contracts.SocketAnchorPlan;
import com.indieniinja.world.layout.HybridLayoutPlan;
import com.indieniinja.world.progression.ProgressionValidationResult;
import com.indieniinja.world.progression.ProgressionValidator;
import com.indieniinja.world.progression.WorldProgressionGraph;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Validates the layered metadata stack and emits bounded repair recommendations.
 *
 * This slice does not mutate layout or tiles. It makes validation outcomes and
 * likely repair tier visible to tooling and later runtime integration work.
 */
public final class GenerationValidationPlanner {
    private GenerationValidationPlanner() {}

    public static GenerationValidationReport validate(
            WorldProgressionGraph graph,
            HybridLayoutPlan layout,
            SocketAnchorPlan socketAnchorPlan) {
        List<GenerationValidationReport.Issue> issues = new ArrayList<>();
        List<GenerationValidationReport.RepairAction> repairs = new ArrayList<>();

        ProgressionValidationResult progression = ProgressionValidator.validate(graph);
        if (!progression.valid()) {
            for (String nodeId : progression.blockedNodeIds()) {
                issues.add(new GenerationValidationReport.Issue(
                    "blocked_progression_node",
                    nodeId,
                    "error",
                    "required progression node is not reachable"
                ));
                repairs.add(new GenerationValidationReport.RepairAction(
                    "regenerate",
                    "regenerate_progression_branch",
                    nodeId,
                    "node requirements are not satisfied by reachable grants"
                ));
            }
        }

        Set<String> contractKeys = new HashSet<>();
        for (SocketAnchorPlan.ConnectionContract contract : socketAnchorPlan.connectionContracts()) {
            contractKeys.add(contract.fromNodeId() + "->" + contract.toNodeId());
            if ("needs_transition".equals(contract.status())) {
                repairs.add(new GenerationValidationReport.RepairAction(
                    "patch",
                    "insert_transition_room",
                    contract.fromNodeId() + "->" + contract.toNodeId(),
                    "socket bands or traversal tags do not directly match"
                ));
            }
        }

        for (HybridLayoutPlan.Connection connection : layout.connections()) {
            String key = connection.fromNodeId() + "->" + connection.toNodeId();
            if (!contractKeys.contains(key)) {
                issues.add(new GenerationValidationReport.Issue(
                    "missing_connection_contract",
                    key,
                    "error",
                    "layout connection has no socket contract"
                ));
                repairs.add(new GenerationValidationReport.RepairAction(
                    "replace",
                    "replace_section_template",
                    key,
                    "choose compatible section templates with required sockets"
                ));
            }
        }

        int reachableCriticalAnchors = 0;
        for (SocketAnchorPlan.ResolvedAnchor anchor : socketAnchorPlan.resolvedAnchors()) {
            boolean critical = anchor.tags().contains("critical")
                || anchor.kind().contains("key")
                || anchor.kind().contains("door")
                || anchor.kind().contains("boss");
            if (!critical) {
                continue;
            }
            if (progression.reachableNodeIds().contains(anchor.nodeId())) {
                reachableCriticalAnchors++;
            } else {
                issues.add(new GenerationValidationReport.Issue(
                    "unreachable_critical_anchor",
                    anchor.nodeId() + "::" + anchor.anchorId(),
                    "error",
                    "critical anchor belongs to an unreachable progression node"
                ));
                repairs.add(new GenerationValidationReport.RepairAction(
                    "regenerate",
                    "regenerate_enclosing_section",
                    anchor.nodeId(),
                    "critical anchor is outside reachable progression"
                ));
            }
        }

        boolean valid = progression.valid() && issues.isEmpty();
        return new GenerationValidationReport(
            valid,
            progression.valid(),
            reachableCriticalAnchors,
            issues,
            repairs
        );
    }
}
