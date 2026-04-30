package com.indieniinja.world.validation;

import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Deterministic validation and bounded repair metadata for layered worldgen.
 */
public record GenerationValidationReport(
        boolean valid,
        boolean progressionValid,
        int reachableCriticalAnchorCount,
        List<Issue> issues,
        List<RepairAction> repairActions) {
    public GenerationValidationReport {
        issues = List.copyOf(issues != null ? issues : List.of());
        repairActions = List.copyOf(repairActions != null ? repairActions : List.of());
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("valid", valid);
        out.put("progressionValid", progressionValid);
        out.put("reachableCriticalAnchorCount", reachableCriticalAnchorCount);
        out.put("issueCount", issues.size());
        out.put("repairActionCount", repairActions.size());
        out.put("issues", issues.stream()
            .sorted(Comparator
                .comparing(Issue::kind)
                .thenComparing(Issue::scopeId)
                .thenComparing(Issue::message))
            .map(Issue::toSnapshot)
            .toList());
        out.put("repairActions", repairActions.stream()
            .sorted(Comparator
                .comparing(RepairAction::scopeId)
                .thenComparing(RepairAction::tier)
                .thenComparing(RepairAction::action))
            .map(RepairAction::toSnapshot)
            .toList());
        return out;
    }

    public record Issue(String kind, String scopeId, String severity, String message) {
        public Issue {
            kind = requireText(kind, "kind");
            scopeId = requireText(scopeId, "scopeId");
            severity = severity == null || severity.isBlank() ? "error" : severity;
            message = message == null || message.isBlank() ? kind : message;
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("kind", kind);
            out.put("scopeId", scopeId);
            out.put("severity", severity);
            out.put("message", message);
            return out;
        }
    }

    public record RepairAction(String tier, String action, String scopeId, String reason) {
        public RepairAction {
            tier = requireText(tier, "tier");
            action = requireText(action, "action");
            scopeId = requireText(scopeId, "scopeId");
            reason = reason == null || reason.isBlank() ? action : reason;
        }

        Map<String, Object> toSnapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("tier", tier);
            out.put("action", action);
            out.put("scopeId", scopeId);
            out.put("reason", reason);
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
