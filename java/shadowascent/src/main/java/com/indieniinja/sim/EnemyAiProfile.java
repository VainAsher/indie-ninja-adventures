package com.indieniinja.sim;

public enum EnemyAiProfile {
    STANDARD,   // goblin, skeleton — patrol/chase/attack/flee
    AERIAL,     // bat — airborne patrol, dive attack
    RANGED;     // archer — maintain distance, projectile attack

    public static EnemyAiProfile of(String key) {
        return switch (key == null ? "" : key.toLowerCase(java.util.Locale.ROOT)) {
            case "aerial" -> AERIAL;
            case "ranged" -> RANGED;
            default       -> STANDARD;
        };
    }
}
