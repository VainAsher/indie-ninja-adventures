package com.indieniinja.world;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Loads a Tiled .tmx room template into the engine's byte[][] tile grid.
 *
 * TMX tile GID → engine byte value mapping (direct, one-to-one):
 *   GID 0 = AIR      (0) — no tile placed in Tiled
 *   GID 1 = SOLID    (1)
 *   GID 2 = PLATFORM (2) — one-way platform
 *   GID 3 = ICE      (3) — low-friction solid
 *   GID 4 = WATER    (4) — passable liquid
 *   GID 5 = LAVA     (5) — contact damage
 *   GID 6 = DOOR_LOCKED (6)
 *   GID 7 = GAS      (7)
 *   GID 8 = CLIMBABLE (8)
 *
 * Templates must be 128×128 tiles and use CSV encoding.
 * Only the first layer named "terrain" (or the first layer if no name match) is loaded.
 * Missing files return null — callers fall back to procedural generation.
 */
public final class TmxRoomLoader {

    /** Root path for room templates, resolved relative to the working directory. */
    private static final Path TEMPLATE_ROOT = Paths.get("assets", "rooms", "templates");
    private static final RoomTemplateCatalog TEMPLATE_CATALOG = RoomTemplateCatalog.loadDefault();

    private TmxRoomLoader() {}

    /**
     * Load a template for a room type by id (e.g. "boss", "shop", "start", "exit").
     * Returns null if no template file is found — caller should generate procedurally.
     */
    public static byte[][] loadTemplate(String roomTypeId) {
        return loadTemplate(roomTypeId, 0L);
    }

    /**
     * Load a deterministic template variant for a room type and room seed.
     */
    public static byte[][] loadTemplate(String roomTypeId, long roomSeed) {
        return loadTemplate(roomTypeId, roomSeed, TEMPLATE_ROOT, TEMPLATE_CATALOG);
    }

    static byte[][] loadTemplate(String roomTypeId, long roomSeed, Path templateRoot, RoomTemplateCatalog catalog) {
        Path path = catalog.selectTemplate(roomTypeId, roomSeed, templateRoot).orElse(null);
        if (path == null || !Files.exists(path)) return null;
        try {
            return load(path);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * Parse a .tmx file and return its terrain layer as a byte[][] grid.
     *
     * @throws Exception on XML parse error or malformed tile data
     */
    public static byte[][] load(Path tmxPath) throws Exception {
        Document doc;
        try (InputStream in = Files.newInputStream(tmxPath)) {
            doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(in);
        }
        Element map = doc.getDocumentElement();
        int width  = Integer.parseInt(map.getAttribute("width"));
        int height = Integer.parseInt(map.getAttribute("height"));

        // Find the terrain layer — prefer the one named "terrain", fall back to first.
        NodeList layerNodes = map.getElementsByTagName("layer");
        Element targetLayer = null;
        for (int i = 0; i < layerNodes.getLength(); i++) {
            Element layer = (Element) layerNodes.item(i);
            if ("terrain".equalsIgnoreCase(layer.getAttribute("name"))) {
                targetLayer = layer;
                break;
            }
            if (targetLayer == null) targetLayer = layer;
        }
        if (targetLayer == null) throw new IllegalArgumentException("No layer found in " + tmxPath);

        NodeList dataNodes = targetLayer.getElementsByTagName("data");
        if (dataNodes.getLength() == 0) throw new IllegalArgumentException("No data element in " + tmxPath);
        Element data = (Element) dataNodes.item(0);

        String encoding = data.getAttribute("encoding");
        if (!encoding.isEmpty() && !"csv".equals(encoding)) {
            throw new UnsupportedOperationException(
                "TmxRoomLoader only supports CSV encoding; found: " + encoding + " in " + tmxPath);
        }

        return parseCsv(data.getTextContent().trim(), width, height);
    }

    private static byte[][] parseCsv(String csv, int width, int height) {
        byte[][] grid = new byte[height][width];
        String[] tokens = csv.split("[,\n\r]+");
        int idx = 0;
        for (int r = 0; r < height; r++) {
            for (int c = 0; c < width; c++) {
                if (idx >= tokens.length) break;
                String t = tokens[idx++].trim();
                if (t.isEmpty()) { c--; continue; }
                int gid = Integer.parseInt(t);
                grid[r][c] = (byte) gid;
            }
        }
        return grid;
    }
}
