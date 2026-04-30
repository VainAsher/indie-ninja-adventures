package com.indieniinja.world.sections;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * Loads authored section templates from JSON files.
 *
 * Files live under {@code data/worldgen/sections/}. Invalid files are skipped so
 * designers can iterate without breaking legacy room generation.
 */
public final class SectionTemplateLibrary {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final List<SectionTemplate> templates;

    private SectionTemplateLibrary(List<SectionTemplate> templates) {
        this.templates = List.copyOf(templates != null ? templates : List.of());
    }

    public static SectionTemplateLibrary empty() {
        return new SectionTemplateLibrary(List.of());
    }

    public static SectionTemplateLibrary loadDefault() {
        String override = System.getProperty("ninja.sectionTemplateRoot", "").trim();
        if (!override.isEmpty()) {
            return load(Paths.get(override));
        }

        for (Path candidate : List.of(
            Paths.get("data", "worldgen", "sections"),
            Paths.get("..", "data", "worldgen", "sections"),
            Paths.get("..", "..", "data", "worldgen", "sections"))) {
            if (Files.isDirectory(candidate)) {
                return load(candidate);
            }
        }

        return empty();
    }

    public static SectionTemplateLibrary load(Path root) {
        if (root == null || !Files.isDirectory(root)) {
            return empty();
        }

        List<SectionTemplate> loaded = new ArrayList<>();
        try (Stream<Path> stream = Files.walk(root)) {
            stream
                .filter(Files::isRegularFile)
                .filter(path -> path.getFileName().toString().endsWith(".json"))
                .sorted(Comparator.comparing(path -> root.relativize(path).toString()))
                .forEach(path -> parse(path).ifPresent(loaded::add));
        } catch (IOException ignored) {
            return empty();
        }

        loaded.sort(Comparator.comparing(SectionTemplate::id));
        return new SectionTemplateLibrary(loaded);
    }

    public List<SectionTemplate> templates() {
        return templates;
    }

    public Optional<SectionTemplate> select(String biome, String kind, long seed) {
        List<SectionTemplate> candidates = templates.stream()
            .filter(template -> normalize(template.biome()).equals(normalize(biome)))
            .filter(template -> normalize(template.kind()).equals(normalize(kind)))
            .sorted(Comparator.comparing(SectionTemplate::id))
            .toList();
        if (candidates.isEmpty()) {
            return Optional.empty();
        }
        int index = Math.floorMod(seed, candidates.size());
        return Optional.of(candidates.get(index));
    }

    public List<Map<String, Object>> toSnapshot() {
        return templates.stream()
            .sorted(Comparator.comparing(SectionTemplate::id))
            .map(SectionTemplate::toSnapshot)
            .toList();
    }

    private static Optional<SectionTemplate> parse(Path path) {
        try {
            JsonNode root = MAPPER.readTree(path.toFile());
            return Optional.of(new SectionTemplate(
                text(root, "id"),
                text(root, "biome"),
                text(root, "kind"),
                footprint(root.get("footprint")),
                strings(root.get("nodeKinds")),
                edgeRules(root.get("edgeRules")),
                strings(root.get("requiredSockets")),
                mutableZones(root.get("mutableZones")),
                anchors(root.get("anchors"))
            ));
        } catch (Exception ignored) {
            return Optional.empty();
        }
    }

    private static SectionTemplate.Footprint footprint(JsonNode node) {
        if (node == null || !node.isObject()) {
            return new SectionTemplate.Footprint(1, 1);
        }
        return new SectionTemplate.Footprint(intField(node, "gridW", 1), intField(node, "gridH", 1));
    }

    private static List<SectionTemplate.EdgeRule> edgeRules(JsonNode node) {
        List<SectionTemplate.EdgeRule> out = new ArrayList<>();
        if (node == null || !node.isArray()) {
            return out;
        }
        for (JsonNode item : node) {
            try {
                out.add(new SectionTemplate.EdgeRule(text(item, "from"), text(item, "to")));
            } catch (IllegalArgumentException ignored) {
                // Skip malformed edge entries inside an otherwise valid template.
            }
        }
        return out;
    }

    private static List<SectionTemplate.MutableZone> mutableZones(JsonNode node) {
        List<SectionTemplate.MutableZone> out = new ArrayList<>();
        if (node == null || !node.isArray()) {
            return out;
        }
        for (JsonNode item : node) {
            try {
                out.add(new SectionTemplate.MutableZone(
                    intField(item, "x", 0),
                    intField(item, "y", 0),
                    intField(item, "w", 1),
                    intField(item, "h", 1),
                    text(item, "role")
                ));
            } catch (IllegalArgumentException ignored) {
                // Skip malformed mutable zone entries.
            }
        }
        return out;
    }

    private static List<SectionTemplate.Anchor> anchors(JsonNode node) {
        List<SectionTemplate.Anchor> out = new ArrayList<>();
        if (node == null || !node.isArray()) {
            return out;
        }
        for (JsonNode item : node) {
            try {
                out.add(new SectionTemplate.Anchor(
                    text(item, "id"),
                    text(item, "kind"),
                    optionalText(item, "phase", "local"),
                    bounds(item.get("localBounds")),
                    strings(item.get("tags")),
                    doubleField(item, "weight", 1.0),
                    optionalText(item, "quotaGroup", text(item, "kind")),
                    intField(item, "minDistance", 0),
                    strings(item.get("requires")),
                    strings(item.get("forbids"))
                ));
            } catch (IllegalArgumentException ignored) {
                // Skip malformed anchor entries.
            }
        }
        return out;
    }

    private static SectionTemplate.Bounds bounds(JsonNode node) {
        if (node == null || !node.isObject()) {
            return new SectionTemplate.Bounds(0, 0, 1, 1);
        }
        return new SectionTemplate.Bounds(
            intField(node, "x", 0),
            intField(node, "y", 0),
            intField(node, "w", 1),
            intField(node, "h", 1)
        );
    }

    private static List<String> strings(JsonNode node) {
        List<String> out = new ArrayList<>();
        if (node == null || !node.isArray()) {
            return out;
        }
        for (JsonNode item : node) {
            if (item.isTextual() && !item.asText().isBlank()) {
                out.add(item.asText());
            }
        }
        return out;
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node != null ? node.get(field) : null;
        if (value == null || !value.isTextual() || value.asText().isBlank()) {
            throw new IllegalArgumentException(field + " must be text");
        }
        return value.asText();
    }

    private static String optionalText(JsonNode node, String field, String fallback) {
        JsonNode value = node != null ? node.get(field) : null;
        return value != null && value.isTextual() && !value.asText().isBlank() ? value.asText() : fallback;
    }

    private static int intField(JsonNode node, String field, int fallback) {
        JsonNode value = node != null ? node.get(field) : null;
        return value != null && value.canConvertToInt() ? value.asInt() : fallback;
    }

    private static double doubleField(JsonNode node, String field, double fallback) {
        JsonNode value = node != null ? node.get(field) : null;
        return value != null && value.isNumber() ? value.asDouble() : fallback;
    }

    private static String normalize(String value) {
        return value == null || value.isBlank() ? "" : value.toLowerCase(Locale.ROOT);
    }

    public Map<String, Object> summarySnapshot() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("templateCount", templates.size());
        out.put("templates", toSnapshot());
        return out;
    }
}
