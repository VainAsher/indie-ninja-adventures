package com.indieniinja.client.game;

/**
 * Mission objective kinds — Java port of Python ObjectiveType enum.
 */
public enum ObjectiveType {
    KILL_ALL_ENEMIES,
    COLLECT_ITEMS,
    ACTIVATE_SWITCHES,
    REACH_LOCATION,
    TIME_CHALLENGE,
    DEFEAT_BOSS,
    TALK_TO_NPC;

    public static ObjectiveType fromWire(String s) {
        if (s == null) return KILL_ALL_ENEMIES;
        return switch (s.toLowerCase()) {
            case "kill_all_enemies"  -> KILL_ALL_ENEMIES;
            case "collect_items"     -> COLLECT_ITEMS;
            case "activate_switches" -> ACTIVATE_SWITCHES;
            case "reach_location"    -> REACH_LOCATION;
            case "time_challenge"    -> TIME_CHALLENGE;
            case "defeat_boss"       -> DEFEAT_BOSS;
            case "talk_to_npc"       -> TALK_TO_NPC;
            default                  -> KILL_ALL_ENEMIES;
        };
    }
}
