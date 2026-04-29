package com.indieniinja.world;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.Set;

/**
 * Loads designer-authored 8x8 TMX zone patches and selects them by role.
 *
 * Entries are mixed with the built-in {@link ZoneTemplateLibrary} pool through
 * per-role fallback weights. Missing or malformed patch files are ignored so
 * procedural generation can keep using the legacy template pool.
 */
public final class ZonePatchTemplateLibrary {
    private static final int PATCH_SIZE = 8;
    private static final int MAX_GID = 8;
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Map<String, RoleTemplates> roles;

    private ZonePatchTemplateLibrary(Map<String, RoleTemplates> roles) {
        this.roles = roles != null ? Map.copyOf(roles) : Map.of();
    }

    public static ZonePatchTemplateLibrary empty() {
        return new ZonePatchTemplateLibrary(Map.of());
    }

    public static ZonePatchTemplateLibrary loadDefault() {
        String catalogOverride = System.getProperty("ninja.zoneTemplateCatalog", "").trim();
        String rootOverride = System.getProperty("ninja.zoneTemplateRoot", "").trim();

        Path root = !rootOverride.isEmpty()
            ? Paths.get(rootOverride)
            : Paths.get("assets", "rooms", "zone_templates");

        if (!catalogOverride.isEmpty()) {
            return load(Paths.get(catalogOverride), root);
        }

        Path javaWorkingDirPath = Paths.get("..", "data", "zone_template_catalog.json");
        if (Files.exists(javaWorkingDirPath)) {
            return load(javaWorkingDirPath, root);
        }

        Path repoRootPath = Paths.get("data", "zone_template_catalog.json");
        if (Files.exists(repoRootPath)) {
            return load(repoRootPath, root);
        }

        return empty();
    }

    public static ZonePatchTemplateLibrary load(Path catalogPath, Path templateRoot) {
        if (catalogPath == null || templateRoot == null || !Files.exists(catalogPath)) {
            return empty();
        }

        try {
            JsonNode root = MAPPER.readTree(catalogPath.toFile());
            JsonNode rolesNode = root.get("roles");
            if (rolesNode == null || !rolesNode.isObject()) {
                return empty();
            }

            Map<String, RoleTemplates> loaded = new HashMap<>();
            Iterator<Map.Entry<String, JsonNode>> fields = rolesNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                RoleTemplates roleTemplates = parseRole(field.getValue(), templateRoot);
                if (!roleTemplates.templates().isEmpty() || roleTemplates.fallbackWeight() > 0) {
                    loaded.put(normalize(field.getKey()), roleTemplates);
                }
            }
            return new ZonePatchTemplateLibrary(loaded);
        } catch (Exception e) {
            return empty();
        }
    }

    public Optional<byte[][]> pick(byte role, int biomeIndex, Random rng) {
        RoleTemplates roleTemplates = roles.get(roleKey(role));
        if (roleTemplates == null) {
            return Optional.empty();
        }

        List<Entry> candidates = roleTemplates.templates().stream()
            .filter(entry -> entry.appliesTo(biomeIndex))
            .toList();
        int total = roleTemplates.fallbackWeight();
        for (Entry entry : candidates) {
            total += entry.weight();
        }
        if (total <= 0) {
            return Optional.empty();
        }

        int roll = rng.nextInt(total);
        if (roll < roleTemplates.fallbackWeight()) {
            return Optional.empty();
        }

        roll -= roleTemplates.fallbackWeight();
        for (Entry entry : candidates) {
            roll -= entry.weight();
            if (roll < 0) {
                return Optional.of(copy(entry.patch()));
            }
        }
        return Optional.empty();
    }

    private static RoleTemplates parseRole(JsonNode node, Path templateRoot) {
        int fallbackWeight = Math.max(0, intField(node, "fallbackWeight", 0));
        JsonNode templatesNode = node.get("templates");
        if (templatesNode == null || !templatesNode.isArray()) {
            return new RoleTemplates(fallbackWeight, List.of());
        }

        List<Entry> entries = new ArrayList<>();
        for (JsonNode item : templatesNode) {
            JsonNode fileNode = item.get("file");
            if (fileNode == null || !fileNode.isTextual()) {
                continue;
            }

            String file = fileNode.asText("").trim();
            if (file.isBlank()) {
                continue;
            }

            Path resolved = templateRoot.resolve(file).normalize();
            if (!resolved.startsWith(templateRoot.normalize()) || !Files.exists(resolved)) {
                continue;
            }

            try {
                byte[][] patch = loadPatch(resolved);
                int weight = Math.max(1, intField(item, "weight", 1));
                Set<Integer> biomeIndexes = parseBiomeIndexes(item.get("biomeIndexes"));
                entries.add(new Entry(file, weight, biomeIndexes, patch));
            } catch (Exception ignored) {
                // Invalid authored patches should not break world generation.
            }
        }
        return new RoleTemplates(fallbackWeight, entries);
    }

    private static byte[][] loadPatch(Path tmxPath) throws Exception {
        Document doc;
        try (InputStream in = Files.newInputStream(tmxPath)) {
            doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(in);
        }

        Element map = doc.getDocumentElement();
        int width = Integer.parseInt(map.getAttribute("width"));
        int height = Integer.parseInt(map.getAttribute("height"));
        if (width != PATCH_SIZE || height != PATCH_SIZE) {
            throw new IllegalArgumentException("Zone patch must be 8x8: " + tmxPath);
        }

        Element targetLayer = terrainLayer(map);
        if (targetLayer == null) {
            throw new IllegalArgumentException("No layer found in " + tmxPath);
        }

        NodeList dataNodes = targetLayer.getElementsByTagName("data");
        if (dataNodes.getLength() == 0) {
            throw new IllegalArgumentException("No data element in " + tmxPath);
        }
        Element data = (Element) dataNodes.item(0);
        String encoding = data.getAttribute("encoding");
        if (!encoding.isEmpty() && !"csv".equals(encoding)) {
            throw new UnsupportedOperationException("Zone patches only support CSV encoding: " + tmxPath);
        }

        return parseCsv(data.getTextContent().trim(), width, height, tmxPath);
    }

    private static Element terrainLayer(Element map) {
        NodeList layerNodes = map.getElementsByTagName("layer");
        Element targetLayer = null;
        for (int i = 0; i < layerNodes.getLength(); i++) {
            Element layer = (Element) layerNodes.item(i);
            if ("terrain".equalsIgnoreCase(layer.getAttribute("name"))) {
                return layer;
            }
            if (targetLayer == null) {
                targetLayer = layer;
            }
        }
        return targetLayer;
    }

    private static byte[][] parseCsv(String csv, int width, int height, Path tmxPath) {
        byte[][] grid = new byte[height][width];
        String[] tokens = csv.split("[,\n\r]+");
        int idx = 0;
        for (int r = 0; r < height; r++) {
            for (int c = 0; c < width; c++) {
                while (idx < tokens.length && tokens[idx].trim().isEmpty()) {
                    idx++;
                }
                if (idx >= tokens.length) {
                    throw new IllegalArgumentException("Not enough tile data in " + tmxPath);
                }
                int gid = Integer.parseInt(tokens[idx++].trim());
                if (gid < 0 || gid > MAX_GID) {
                    throw new IllegalArgumentException("Unsupported tile gid " + gid + " in " + tmxPath);
                }
                grid[r][c] = (byte) gid;
            }
        }
        return grid;
    }

    private static Set<Integer> parseBiomeIndexes(JsonNode node) {
        if (node == null || !node.isArray()) {
            return Set.of();
        }
        Set<Integer> indexes = new HashSet<>();
        for (JsonNode item : node) {
            if (item.canConvertToInt()) {
                indexes.add(item.asInt());
            }
        }
        return Set.copyOf(indexes);
    }

    private static int intField(JsonNode node, String field, int fallback) {
        if (node == null) {
            return fallback;
        }
        JsonNode value = node.get(field);
        return value != null && value.canConvertToInt() ? value.asInt() : fallback;
    }

    private static String roleKey(byte role) {
        if (role == ZonePlanner.FILL) {
            return "fill";
        }
        if (role == ZonePlanner.PLAT) {
            return "plat";
        }
        if (role == ZonePlanner.LAVA) {
            return "lava";
        }
        if (role == ZonePlanner.ICE) {
            return "ice";
        }
        if (role == ZonePlanner.WATER) {
            return "water";
        }
        return "";
    }

    private static String normalize(String id) {
        return id == null || id.isBlank() ? "" : id.toLowerCase(Locale.ROOT);
    }

    private static byte[][] copy(byte[][] source) {
        byte[][] copy = new byte[source.length][];
        for (int r = 0; r < source.length; r++) {
            copy[r] = source[r].clone();
        }
        return copy;
    }

    private record RoleTemplates(int fallbackWeight, List<Entry> templates) {
        private RoleTemplates {
            fallbackWeight = Math.max(0, fallbackWeight);
            templates = templates != null ? List.copyOf(templates) : List.of();
        }
    }

    private record Entry(String file, int weight, Set<Integer> biomeIndexes, byte[][] patch) {
        private Entry {
            file = file == null ? "" : file.trim();
            weight = Math.max(1, weight);
            biomeIndexes = biomeIndexes != null ? Set.copyOf(biomeIndexes) : Set.of();
            patch = copy(patch);
        }

        private boolean appliesTo(int biomeIndex) {
            return biomeIndexes.isEmpty() || biomeIndexes.contains(biomeIndex);
        }
    }
}
