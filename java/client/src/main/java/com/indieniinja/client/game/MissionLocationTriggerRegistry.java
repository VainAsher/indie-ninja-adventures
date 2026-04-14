package com.indieniinja.client.game;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Authoritative mission location trigger map loaded from data/mission_location_triggers.json.
 *
 * Each REACH_LOCATION objective should have exactly one authored trigger entry.
 */
public final class MissionLocationTriggerRegistry {

    public record TriggerDef(
        String missionId,
        String locationId,
        int roomGridXOffset,
        int roomGridYOffset,
        float x,
        float y,
        float width,
        float height,
        boolean snapToReachableGround,
        int maxSnapRadiusTiles
    ) {}

    private final Map<String, TriggerDef> defs = new LinkedHashMap<>();

    private MissionLocationTriggerRegistry() {}

    public static MissionLocationTriggerRegistry load(FileHandle file) {
        MissionLocationTriggerRegistry reg = new MissionLocationTriggerRegistry();
        if (file == null || !file.exists()) return reg;

        JsonValue root = new JsonReader().parse(file);
        JsonValue triggers = root.get("triggers");
        if (triggers == null) return reg;

        for (JsonValue t : triggers) {
            String missionId = str(t, "mission_id", "").trim();
            String locationId = str(t, "location_id", "").trim();
            if (missionId.isEmpty() || locationId.isEmpty()) continue;

            TriggerDef def = new TriggerDef(
                missionId,
                locationId,
                t.getInt("room_grid_x_offset", 0),
                t.getInt("room_grid_y_offset", 0),
                t.getFloat("x", 0f),
                t.getFloat("y", 0f),
                t.getFloat("width", 96f),
                t.getFloat("height", 96f),
                t.getBoolean("snap_to_reachable_ground", true),
                t.getInt("max_snap_radius_tiles", 72)
            );
            reg.defs.put(key(missionId, locationId), def);
        }
        return reg;
    }

    public TriggerDef get(String missionId, String locationId) {
        return defs.get(key(missionId, locationId));
    }

    /**
     * Returns missing objective keys in "mission_id:location_id" format.
     */
    public List<String> findMissingReachObjectives(MissionManager missions) {
        List<String> missing = new ArrayList<>();
        for (String missionId : missions.getAllDefinitionIds()) {
            MissionDefinition def = missions.getDefinition(missionId);
            if (def == null) continue;
            for (MissionObjective obj : def.objectives) {
                if (obj.type != ObjectiveType.REACH_LOCATION) continue;
                String location = obj.location != null ? obj.location : "";
                if (get(missionId, location) == null) {
                    missing.add(missionId + ":" + location);
                }
            }
        }
        return missing;
    }

    public int size() { return defs.size(); }

    private static String key(String missionId, String locationId) {
        String m = missionId == null ? "" : missionId.trim().toLowerCase(Locale.ROOT);
        String l = locationId == null ? "" : locationId.trim().toLowerCase(Locale.ROOT);
        return m + "::" + l;
    }

    private static String str(JsonValue v, String key, String def) {
        JsonValue child = v.get(key);
        return (child != null && !child.isNull()) ? child.asString() : def;
    }
}
