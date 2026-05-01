package com.indieniinja.world.sections;

import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Structured validation issue emitted when authored section JSON is malformed.
 */
public record SectionTemplateValidationIssue(
        String kind,
        String file,
        String field,
        String severity,
        String message,
        String repairAction) {
    public SectionTemplateValidationIssue {
        kind = requireText(kind, "kind");
        file = requireText(file, "file");
        field = requireText(field, "field");
        severity = severity == null || severity.isBlank() ? "error" : severity.toLowerCase(Locale.ROOT);
        message = message == null || message.isBlank() ? kind : message;
        repairAction = repairAction == null || repairAction.isBlank() ? "fix_" + kind : repairAction;
    }

    public boolean isError() {
        return "error".equals(severity);
    }

    public Map<String, Object> toSnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("kind", kind);
        out.put("file", file);
        out.put("field", field);
        out.put("severity", severity);
        out.put("message", message);
        out.put("repairAction", repairAction);
        return out;
    }

    public static Comparator<SectionTemplateValidationIssue> sortOrder() {
        return Comparator.comparing(SectionTemplateValidationIssue::file)
            .thenComparing(SectionTemplateValidationIssue::field)
            .thenComparing(SectionTemplateValidationIssue::kind)
            .thenComparing(SectionTemplateValidationIssue::severity)
            .thenComparing(SectionTemplateValidationIssue::message);
    }

    private static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " must not be blank");
        }
        return value;
    }
}
