package com.indieniinja.client.game;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Static mission template loaded from data/missions.json.
 *
 * Java port of Python game/mission_registry.py MissionDefinition dataclass.
 * Immutable once constructed; loaded once at startup by MissionManager.
 */
public final class MissionDefinition {

    public final String               missionId;
    public final String               missionName;
    public final String               description;
    public final String               region;
    public final int                  difficulty;
    public final int                  roomCount;
    public final String               shape;
    public final List<MissionObjective> objectives;
    public final List<String>         requiredAbilities;
    public final List<String>         unlockAbilities;
    public final int                  rewardCurrency;
    public final List<String>         enemyTypes;
    public final float                timeLimit;   // seconds, 0 = none
    public final int                  act;         // min act when available
    /** Authored campaign node this mission maps to (optional, informational). */
    public final String               progressionNodeId;
    /** Mission IDs that must be COMPLETED before this mission is available. */
    public final List<String>         requires;
    /** When true, the exit room of the generated world is typed as a boss room. */
    public final boolean              guaranteedBossExit;

    public MissionDefinition(String missionId, String missionName, String description,
                             String region, int difficulty, int roomCount, String shape,
                             List<MissionObjective> objectives,
                             List<String> requiredAbilities, List<String> unlockAbilities,
                             int rewardCurrency, List<String> enemyTypes,
                             float timeLimit, int act,
                             String progressionNodeId, List<String> requires,
                             boolean guaranteedBossExit) {
        this.missionId          = missionId;
        this.missionName        = missionName;
        this.description        = description;
        this.region             = region;
        this.difficulty         = difficulty;
        this.roomCount          = roomCount;
        this.shape              = shape;
        this.objectives         = objectives;
        this.requiredAbilities  = requiredAbilities;
        this.unlockAbilities    = unlockAbilities;
        this.rewardCurrency     = rewardCurrency;
        this.enemyTypes         = enemyTypes;
        this.timeLimit          = timeLimit;
        this.act                = act;
        this.progressionNodeId  = progressionNodeId != null ? progressionNodeId : "";
        this.requires           = requires != null ? requires : new ArrayList<>();
        this.guaranteedBossExit = guaranteedBossExit;
    }

    // ── JSON loading ─────────────────────────────────────────────────────────

    /**
     * Load all mission definitions from data/missions.json.
     * Returns a map of missionId → MissionDefinition.
     *
     * @param file libGDX FileHandle pointing to missions.json
     */
    public static Map<String, MissionDefinition> loadAll(FileHandle file) {
        Map<String, MissionDefinition> out = new HashMap<>();
        if (!file.exists()) return out;

        JsonValue root = new JsonReader().parse(file);
        JsonValue missionsArr = root.get("missions");
        if (missionsArr == null) return out;

        for (JsonValue m : missionsArr) {
            MissionDefinition def = parse(m);
            out.put(def.missionId, def);
        }
        return out;
    }

    private static MissionDefinition parse(JsonValue m) {
        String id          = str(m, "mission_id",   "unknown");
        String name        = str(m, "mission_name", id);
        String desc        = str(m, "description",  "");
        String region      = str(m, "region",       "forest");
        int    difficulty  = m.getInt("difficulty", 1);
        int    roomCount   = m.getInt("room_count",  8);
        String shape       = str(m, "shape",        "blob");
        int    act         = m.getInt("act", 0);

        // Objectives
        List<MissionObjective> objectives = new ArrayList<>();
        JsonValue objArr = m.get("objectives");
        if (objArr != null) {
            for (JsonValue o : objArr) {
                ObjectiveType type  = ObjectiveType.fromWire(str(o, "type", "kill_all_enemies"));
                String oDesc        = str(o, "description", "");
                int    target       = o.getInt("target", 0);
                String item         = str(o, "item",     null);
                int    count        = o.getInt("count",  0);
                String location     = str(o, "location", null);
                String boss         = str(o, "boss",     null);
                float  timeLimitObj = o.getFloat("time_limit", 0f);
                objectives.add(new MissionObjective(type, oDesc, target, item, count,
                                                    location, boss, timeLimitObj));
            }
        }

        // String arrays
        List<String> reqAbilities    = strList(m, "required_abilities");
        List<String> unlockAbilities = strList(m, "unlock_abilities");
        List<String> enemyTypes      = strList(m, "enemy_types");

        // Rewards
        int rewardCurrency = 0;
        JsonValue rewards = m.get("rewards");
        if (rewards != null) rewardCurrency = rewards.getInt("currency", 0);

        float timeLimit = m.getFloat("time_limit", 0f);
        String progressionNodeId = str(m, "progression_node_id", null);
        List<String> requires    = strList(m, "requires");
        boolean guaranteedBossExit = m.getBoolean("guaranteed_boss_exit", false);

        return new MissionDefinition(id, name, desc, region, difficulty, roomCount, shape,
                                     objectives, reqAbilities, unlockAbilities,
                                     rewardCurrency, enemyTypes, timeLimit, act,
                                     progressionNodeId, requires, guaranteedBossExit);
    }

    private static String str(JsonValue v, String key, String def) {
        JsonValue child = v.get(key);
        return (child != null && !child.isNull()) ? child.asString() : def;
    }

    private static List<String> strList(JsonValue v, String key) {
        List<String> out = new ArrayList<>();
        JsonValue arr = v.get(key);
        if (arr == null) return out;
        for (JsonValue item : arr) if (!item.isNull()) out.add(item.asString());
        return out;
    }
}
