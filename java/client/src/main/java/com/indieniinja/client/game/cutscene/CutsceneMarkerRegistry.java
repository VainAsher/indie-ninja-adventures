package com.indieniinja.client.game.cutscene;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

public final class CutsceneMarkerRegistry {
    private static final Logger log = LoggerFactory.getLogger(CutsceneMarkerRegistry.class);
    private static final String MARKERS_PATH = "data/cutscenes/markers.json";

    private final Map<String, CutsceneMarker> markers;

    private CutsceneMarkerRegistry(Map<String, CutsceneMarker> markers) {
        this.markers = Collections.unmodifiableMap(new LinkedHashMap<>(markers));
    }

    public static CutsceneMarkerRegistry empty() {
        return new CutsceneMarkerRegistry(Map.of());
    }

    public static CutsceneMarkerRegistry load() {
        if (Gdx.app == null || Gdx.files == null) return empty();
        FileHandle file = Gdx.files.internal(MARKERS_PATH);
        if (!file.exists()) {
            log.warn("[CutsceneMarkerRegistry] markers file not found: {}", MARKERS_PATH);
            return empty();
        }
        try {
            return fromJson(new JsonReader().parse(file));
        } catch (Exception e) {
            log.error("[CutsceneMarkerRegistry] failed to load {}: {}", MARKERS_PATH, e.getMessage(), e);
            return empty();
        }
    }

    public static CutsceneMarkerRegistry loadString(String json) {
        try {
            return fromJson(new JsonReader().parse(json));
        } catch (Exception e) {
            throw new CutsceneLoadException("invalid markers JSON: " + e.getMessage(), e);
        }
    }

    public Optional<CutsceneMarker> resolve(String id) {
        if (id == null || id.isBlank()) return Optional.empty();
        return Optional.ofNullable(markers.get(id));
    }

    public Map<String, CutsceneMarker> markers() {
        return markers;
    }

    private static CutsceneMarkerRegistry fromJson(JsonValue root) {
        JsonValue markerArray = root;
        if (root.type() == JsonValue.ValueType.object && root.has("markers")) {
            markerArray = root.get("markers");
        }
        if (markerArray == null || markerArray.type() != JsonValue.ValueType.array) {
            throw new CutsceneLoadException("markers root must be an array or object with 'markers' array");
        }

        Map<String, CutsceneMarker> out = new LinkedHashMap<>();
        for (JsonValue child = markerArray.child; child != null; child = child.next) {
            if (child.type() != JsonValue.ValueType.object) continue;
            String id = child.getString("id", "");
            if (id.isBlank()) continue;
            float x = child.getFloat("x", 0f);
            float y = child.getFloat("y", 0f);
            out.put(id, new CutsceneMarker(id, x, y));
        }
        return new CutsceneMarkerRegistry(out);
    }
}
