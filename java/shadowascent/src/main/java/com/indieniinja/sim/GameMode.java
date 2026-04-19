package com.indieniinja.sim;

/**
 * Play modes — mirrors Python game/play_mode.py PlayMode enum.
 *
 * ARCADE   — infinite procedural dungeon; score + depth tracking; rooms scale per depth
 * CAMPAIGN — story-driven mission progression; hub worlds; ability gates
 * SANDBOX  — freeform play; all abilities unlocked; start with currency; no save pressure
 */
public enum GameMode {
    ARCADE("arcade"),
    CAMPAIGN("campaign"),
    SANDBOX("sandbox");

    public final String wire;  // string sent over the network

    GameMode(String wire) { this.wire = wire; }

    public static GameMode fromWire(String s) {
        if (s == null) return ARCADE;
        return switch (s) {
            case "campaign" -> CAMPAIGN;
            case "sandbox"  -> SANDBOX;
            default         -> ARCADE;
        };
    }
}
