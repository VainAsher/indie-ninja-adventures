package com.indieniinja.world;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * Selects authored TMX room templates from explicit weighted data or filename
 * conventions.
 */
public record RoomTemplateCatalog(Map<String, List<Entry>> roomTypes) {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public record Entry(String file, int weight) {
        public Entry {
            file = file == null ? "" : file.trim();
            weight = Math.max(1, weight);
        }
    }

    public RoomTemplateCatalog {
        roomTypes = roomTypes != null ? copy(roomTypes) : Map.of();
    }

    public static RoomTemplateCatalog empty() {
        return new RoomTemplateCatalog(Map.of());
    }

    public static RoomTemplateCatalog loadDefault() {
        String override = System.getProperty("ninja.roomTemplateCatalog", "").trim();
        if (!override.isEmpty()) {
            return load(Paths.get(override));
        }

        Path javaWorkingDirPath = Paths.get("..", "data", "room_template_catalog.json");
        if (Files.exists(javaWorkingDirPath)) {
            return load(javaWorkingDirPath);
        }

        Path repoRootPath = Paths.get("data", "room_template_catalog.json");
        if (Files.exists(repoRootPath)) {
            return load(repoRootPath);
        }

        return empty();
    }

    public static RoomTemplateCatalog load(Path path) {
        if (path == null || !Files.exists(path)) {
            return empty();
        }
        try {
            JsonNode root = MAPPER.readTree(path.toFile());
            JsonNode roomTypesNode = root.get("roomTypes");
            if (roomTypesNode == null || !roomTypesNode.isObject()) {
                return empty();
            }

            Map<String, List<Entry>> templates = new HashMap<>();
            Iterator<Map.Entry<String, JsonNode>> fields = roomTypesNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                List<Entry> entries = parseEntries(field.getValue());
                if (!entries.isEmpty()) {
                    templates.put(normalize(field.getKey()), entries);
                }
            }
            return new RoomTemplateCatalog(templates);
        } catch (Exception e) {
            return empty();
        }
    }

    public Optional<Path> selectTemplate(String roomTypeId, long roomSeed, Path templateRoot) {
        if (templateRoot == null) {
            return Optional.empty();
        }

        String key = normalize(roomTypeId);
        List<Entry> explicit = roomTypes.getOrDefault(key, List.of());
        List<Entry> existingExplicit = explicit.stream()
            .filter(entry -> !entry.file().isBlank())
            .filter(entry -> Files.exists(templateRoot.resolve(entry.file())))
            .toList();
        if (!existingExplicit.isEmpty()) {
            return Optional.of(templateRoot.resolve(weightedPick(existingExplicit, roomSeed).file()));
        }

        List<Path> discovered = discoverConventionTemplates(key, templateRoot);
        if (discovered.isEmpty()) {
            return Optional.empty();
        }
        int index = Math.floorMod(roomSeed, discovered.size());
        return Optional.of(discovered.get(index));
    }

    private static List<Entry> parseEntries(JsonNode node) {
        List<Entry> entries = new ArrayList<>();
        if (node == null || !node.isArray()) {
            return entries;
        }
        for (JsonNode item : node) {
            JsonNode fileNode = item.get("file");
            if (fileNode == null || !fileNode.isTextual()) {
                continue;
            }
            int weight = intField(item, "weight", 1);
            entries.add(new Entry(fileNode.asText(), weight));
        }
        return entries;
    }

    private static Entry weightedPick(List<Entry> entries, long seed) {
        int total = entries.stream().mapToInt(Entry::weight).sum();
        int roll = Math.floorMod(seed, total);
        for (Entry entry : entries) {
            roll -= entry.weight();
            if (roll < 0) {
                return entry;
            }
        }
        return entries.get(entries.size() - 1);
    }

    private static List<Path> discoverConventionTemplates(String roomTypeId, Path templateRoot) {
        List<Path> paths = new ArrayList<>();
        Path exact = templateRoot.resolve(roomTypeId + ".tmx");
        if (Files.exists(exact)) {
            paths.add(exact);
        }

        if (Files.isDirectory(templateRoot)) {
            try (var stream = Files.list(templateRoot)) {
                stream
                    .filter(Files::isRegularFile)
                    .filter(path -> {
                        String name = path.getFileName().toString();
                        return name.startsWith(roomTypeId + "_") && name.endsWith(".tmx")
                            || name.startsWith(roomTypeId + "-") && name.endsWith(".tmx");
                    })
                    .sorted(Comparator.comparing(path -> path.getFileName().toString()))
                    .forEach(paths::add);
            } catch (IOException ignored) {
                return paths;
            }
        }
        return paths;
    }

    private static int intField(JsonNode node, String field, int fallback) {
        JsonNode value = node.get(field);
        return value != null && value.canConvertToInt() ? value.asInt() : fallback;
    }

    private static String normalize(String id) {
        return id == null || id.isBlank() ? "" : id.toLowerCase(Locale.ROOT);
    }

    private static Map<String, List<Entry>> copy(Map<String, List<Entry>> input) {
        Map<String, List<Entry>> copied = new HashMap<>();
        input.forEach((key, value) -> copied.put(normalize(key), List.copyOf(value)));
        return Map.copyOf(copied);
    }
}
