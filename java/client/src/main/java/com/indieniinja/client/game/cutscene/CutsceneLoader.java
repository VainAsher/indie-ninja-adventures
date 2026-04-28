package com.indieniinja.client.game.cutscene;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Loads and validates cutscene definitions from {@code data/cutscenes/*.json}.
 *
 * Each file must contain a single cutscene object with an {@code id} field that
 * matches the filename (without extension).  Files are loaded in alphabetical
 * order so the result is deterministic.
 *
 * Invalid files are skipped with an ERROR log rather than crashing the loader,
 * so one bad file does not block the rest of the authored content.
 *
 * Headless-safe: returns an empty map when {@code Gdx.app == null}.
 */
public final class CutsceneLoader {

    private static final Logger log = LoggerFactory.getLogger(CutsceneLoader.class);

    private static final String CUTSCENE_DIR = "data/cutscenes";

    private CutsceneLoader() {}

    /**
     * Load all cutscene definitions from {@code data/cutscenes/}.
     * Returns a map of id → definition, sorted by id for determinism.
     */
    public static Map<String, CutsceneDefinition> loadAll() {
        if (Gdx.app == null || Gdx.files == null) return Collections.emptyMap();
        FileHandle dir = Gdx.files.internal(CUTSCENE_DIR);
        if (!dir.exists() || !dir.isDirectory()) {
            log.warn("[CutsceneLoader] directory not found: {}", CUTSCENE_DIR);
            return Collections.emptyMap();
        }
        return loadAll(dir);
    }

    /**
     * Load from an explicit {@link FileHandle} directory.
     * Exposed for testing with a local file handle.
     */
    public static Map<String, CutsceneDefinition> loadAll(FileHandle dir) {
        FileHandle[] files = dir.list(".json");
        if (files == null || files.length == 0) return Collections.emptyMap();

        // Sort alphabetically for determinism
        Arrays.sort(files, Comparator.comparing(FileHandle::name));

        Map<String, CutsceneDefinition> out = new LinkedHashMap<>();
        for (FileHandle f : files) {
            try {
                CutsceneDefinition def = loadFile(f);
                if (out.containsKey(def.id)) {
                    log.warn("[CutsceneLoader] duplicate id '{}' in {}, skipping", def.id, f.name());
                    continue;
                }
                out.put(def.id, def);
                log.debug("[CutsceneLoader] loaded '{}' ({} steps)", def.id, def.steps.size());
            } catch (CutsceneLoadException e) {
                log.error("[CutsceneLoader] skipping {} — {}", f.name(), e.getMessage());
            } catch (Exception e) {
                log.error("[CutsceneLoader] skipping {} — unexpected error: {}", f.name(), e.getMessage(), e);
            }
        }
        log.info("[CutsceneLoader] loaded {}/{} cutscenes from {}", out.size(), files.length, CUTSCENE_DIR);
        return Collections.unmodifiableMap(out);
    }

    /** Load a single cutscene file. Throws {@link CutsceneLoadException} on validation failure. */
    public static CutsceneDefinition loadFile(FileHandle f) {
        JsonValue root;
        try {
            root = new JsonReader().parse(f);
        } catch (Exception e) {
            throw new CutsceneLoadException("invalid JSON in " + f.name() + ": " + e.getMessage(), e);
        }
        Map<String, Object> map = toMap(root);
        return CutsceneDefinition.fromMap(map);
    }

    /**
     * Parse from a raw JSON string.
     * Exposed so tests can pass inline JSON without a FileHandle.
     */
    public static CutsceneDefinition loadString(String json) {
        JsonValue root;
        try {
            root = new JsonReader().parse(json);
        } catch (Exception e) {
            throw new CutsceneLoadException("invalid JSON: " + e.getMessage(), e);
        }
        return CutsceneDefinition.fromMap(toMap(root));
    }

    // ── JsonValue → Map<String, Object> bridge ────────────────────────────────

    /**
     * Recursively convert a libGDX {@link JsonValue} object/array to plain Java types.
     * This keeps CutsceneDefinition.fromMap() testable without a libGDX runtime.
     */
    static Map<String, Object> toMap(JsonValue v) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (JsonValue child = v.child; child != null; child = child.next) {
            map.put(child.name, toValue(child));
        }
        return map;
    }

    private static Object toValue(JsonValue v) {
        return switch (v.type()) {
            case object  -> toMap(v);
            case array   -> toList(v);
            case stringValue -> v.asString();
            case doubleValue, longValue -> v.isLong() ? (Object)(long) v.asLong() : v.asDouble();
            case booleanValue -> v.asBoolean();
            default -> null;
        };
    }

    private static List<Object> toList(JsonValue v) {
        List<Object> list = new ArrayList<>();
        for (JsonValue child = v.child; child != null; child = child.next) {
            list.add(toValue(child));
        }
        return list;
    }
}
