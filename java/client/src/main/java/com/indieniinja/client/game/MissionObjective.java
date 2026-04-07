package com.indieniinja.client.game;

/**
 * Single mission objective — Java port of Python MissionObjective dataclass.
 *
 * Not all fields are used by every objective type; unused fields are null/0.
 */
public final class MissionObjective {

    public final ObjectiveType type;
    public final String        description;

    // Type-specific fields (mirror Python dataclass fields)
    public final int    target;    // KILL_ALL_ENEMIES, ACTIVATE_SWITCHES
    public final String item;      // COLLECT_ITEMS
    public final int    count;     // COLLECT_ITEMS
    public final String location;  // REACH_LOCATION
    public final String boss;      // DEFEAT_BOSS
    public final float  timeLimit; // TIME_CHALLENGE (seconds, 0 = no limit)

    public MissionObjective(ObjectiveType type, String description,
                            int target, String item, int count,
                            String location, String boss, float timeLimit) {
        this.type        = type;
        this.description = description;
        this.target      = target;
        this.item        = item;
        this.count       = count;
        this.location    = location;
        this.boss        = boss;
        this.timeLimit   = timeLimit;
    }
}
