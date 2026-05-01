package com.indieniinja.world.sections;

import com.fasterxml.jackson.databind.JsonNode;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Strict authoring contract checks for section template JSON files.
 */
public final class SectionTemplateValidator {
    private static final Set<String> NAV_EXEMPT_KINDS = Set.of("hub_home", "boss_approach");
    private static final Pattern SOCKET_PATTERN =
        Pattern.compile("^[a-z]+_[a-z]+_[a-z]+(?:_[a-z0-9]+)*$");

    private SectionTemplateValidator() {}

    public static List<SectionTemplateValidationIssue> validate(Path file, JsonNode root) {
        String fileLabel = normalizePath(file);
        List<SectionTemplateValidationIssue> issues = new ArrayList<>();
        if (root == null || !root.isObject()) {
            issues.add(issue(
                "invalid_json_root",
                fileLabel,
                "$",
                "template JSON must be an object",
                "replace file content with a JSON object containing section fields"));
            return sort(issues);
        }

        requireText(root, "id", fileLabel, issues);
        requireText(root, "biome", fileLabel, issues);
        String kind = requireText(root, "kind", fileLabel, issues);
        boolean navigationRequired = requiresNavigation(kind);
        boolean footprintRequired = requiresFootprint(kind);

        if (footprintRequired) {
            validateFootprint(root.get("footprint"), fileLabel, issues);
        }
        if (navigationRequired) {
            validateNodeKinds(root.get("nodeKinds"), fileLabel, issues);
            validateEdgeRules(root.get("edgeRules"), fileLabel, issues);
            validateRequiredSockets(root.get("requiredSockets"), fileLabel, issues);
        }
        validateAnchors(root.get("anchors"), fileLabel, issues);

        return sort(issues);
    }

    private static boolean requiresNavigation(String kind) {
        return !NAV_EXEMPT_KINDS.contains(normalize(kind));
    }

    private static boolean requiresFootprint(String kind) {
        return !NAV_EXEMPT_KINDS.contains(normalize(kind));
    }

    private static void validateFootprint(
            JsonNode footprint, String file, List<SectionTemplateValidationIssue> issues) {
        if (footprint == null || !footprint.isObject()) {
            issues.add(issue(
                "missing_required_field",
                file,
                "footprint",
                "required field `footprint` is missing or not an object",
                "add `footprint` with positive `gridW` and `gridH` values"));
            return;
        }
        requirePositiveInt(footprint, "footprint.gridW", file, issues);
        requirePositiveInt(footprint, "footprint.gridH", file, issues);
    }

    private static void validateNodeKinds(
            JsonNode nodeKinds, String file, List<SectionTemplateValidationIssue> issues) {
        if (!requireNonEmptyArray(nodeKinds, file, "nodeKinds", issues)) {
            return;
        }
        for (int i = 0; i < nodeKinds.size(); i++) {
            JsonNode item = nodeKinds.get(i);
            if (item == null || !item.isTextual() || item.asText().isBlank()) {
                issues.add(issue(
                    "invalid_field_type",
                    file,
                    "nodeKinds[" + i + "]",
                    "nodeKinds entries must be non-blank strings",
                    "replace this entry with a non-blank node kind string"));
            }
        }
    }

    private static void validateEdgeRules(
            JsonNode edgeRules, String file, List<SectionTemplateValidationIssue> issues) {
        if (!requireNonEmptyArray(edgeRules, file, "edgeRules", issues)) {
            return;
        }
        for (int i = 0; i < edgeRules.size(); i++) {
            JsonNode rule = edgeRules.get(i);
            if (rule == null || !rule.isObject()) {
                issues.add(issue(
                    "invalid_field_type",
                    file,
                    "edgeRules[" + i + "]",
                    "edge rule must be an object with `from` and `to`",
                    "replace with `{ \"from\": \"<node>\", \"to\": \"<node>\" }`"));
                continue;
            }
            requireText(rule, "from", file, "edgeRules[" + i + "].from", issues);
            requireText(rule, "to", file, "edgeRules[" + i + "].to", issues);
        }
    }

    private static void validateRequiredSockets(
            JsonNode sockets, String file, List<SectionTemplateValidationIssue> issues) {
        if (!requireNonEmptyArray(sockets, file, "requiredSockets", issues)) {
            return;
        }
        for (int i = 0; i < sockets.size(); i++) {
            JsonNode entry = sockets.get(i);
            if (entry == null || !entry.isTextual() || entry.asText().isBlank()) {
                issues.add(issue(
                    "invalid_field_type",
                    file,
                    "requiredSockets[" + i + "]",
                    "required socket entries must be non-blank strings",
                    "replace this entry with a socket token like `west_low_walk`"));
                continue;
            }
            String token = entry.asText();
            if (!SOCKET_PATTERN.matcher(token).matches()) {
                issues.add(issue(
                    "invalid_socket_id",
                    file,
                    "requiredSockets[" + i + "]",
                    "socket id `" + token + "` does not match `side_band_traversal[_modifier...]`",
                    "rename socket id to underscore-delimited tokens like `west_low_walk`"));
            }
        }
    }

    private static void validateAnchors(
            JsonNode anchors, String file, List<SectionTemplateValidationIssue> issues) {
        if (!requireNonEmptyArray(anchors, file, "anchors", issues)) {
            return;
        }
        for (int i = 0; i < anchors.size(); i++) {
            JsonNode anchor = anchors.get(i);
            if (anchor == null || !anchor.isObject()) {
                issues.add(issue(
                    "invalid_field_type",
                    file,
                    "anchors[" + i + "]",
                    "anchor must be an object",
                    "replace with an object containing at least `id` and `kind`"));
                continue;
            }
            requireText(anchor, "id", file, "anchors[" + i + "].id", issues);
            requireText(anchor, "kind", file, "anchors[" + i + "].kind", issues);
        }
    }

    private static boolean requireNonEmptyArray(
            JsonNode node,
            String file,
            String field,
            List<SectionTemplateValidationIssue> issues) {
        if (node == null) {
            issues.add(issue(
                "missing_required_field",
                file,
                field,
                "required field `" + field + "` is missing",
                "add `" + field + "` with at least one entry"));
            return false;
        }
        if (!node.isArray()) {
            issues.add(issue(
                "invalid_field_type",
                file,
                field,
                "field `" + field + "` must be an array",
                "replace `" + field + "` with a JSON array"));
            return false;
        }
        if (node.isEmpty()) {
            issues.add(issue(
                "empty_required_array",
                file,
                field,
                "field `" + field + "` must include at least one entry",
                "add at least one valid entry to `" + field + "`"));
            return false;
        }
        return true;
    }

    private static String requireText(
            JsonNode node, String field, String file, List<SectionTemplateValidationIssue> issues) {
        return requireText(node, field, file, field, issues);
    }

    private static String requireText(
            JsonNode node,
            String field,
            String file,
            String path,
            List<SectionTemplateValidationIssue> issues) {
        JsonNode value = node != null ? node.get(field) : null;
        if (value == null) {
            issues.add(issue(
                "missing_required_field",
                file,
                path,
                "required field `" + path + "` is missing",
                "add field `" + path + "` with a non-blank string value"));
            return "";
        }
        if (!value.isTextual() || value.asText().isBlank()) {
            issues.add(issue(
                "invalid_field_type",
                file,
                path,
                "field `" + path + "` must be a non-blank string",
                "replace `" + path + "` with a non-blank string value"));
            return "";
        }
        return value.asText();
    }

    private static void requirePositiveInt(
            JsonNode node,
            String path,
            String file,
            List<SectionTemplateValidationIssue> issues) {
        String field = path.substring(path.lastIndexOf('.') + 1);
        JsonNode value = node != null ? node.get(field) : null;
        if (value == null || !value.canConvertToInt() || value.asInt() < 1) {
            issues.add(issue(
                "invalid_field_type",
                file,
                path,
                "field `" + path + "` must be an integer >= 1",
                "set `" + path + "` to a positive integer"));
        }
    }

    private static SectionTemplateValidationIssue issue(
            String kind, String file, String field, String message, String repairAction) {
        return new SectionTemplateValidationIssue(kind, file, field, "error", message, repairAction);
    }

    private static List<SectionTemplateValidationIssue> sort(List<SectionTemplateValidationIssue> issues) {
        issues.sort(SectionTemplateValidationIssue.sortOrder());
        return List.copyOf(issues);
    }

    private static String normalize(String value) {
        return value == null || value.isBlank() ? "" : value.toLowerCase(Locale.ROOT);
    }

    private static String normalizePath(Path file) {
        if (file == null) {
            return "<unknown>";
        }
        return file.toString().replace('\\', '/');
    }
}
