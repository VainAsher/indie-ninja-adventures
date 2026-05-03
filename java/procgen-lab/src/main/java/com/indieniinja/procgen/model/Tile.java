package com.indieniinja.procgen.model;

public final class Tile {
    // Shared with live WorldGenerator — values must stay in sync with that class.
    public static final byte AIR          = 0;
    public static final byte SOLID        = 1;
    public static final byte PLATFORM     = 2;
    public static final byte ICE          = 3;   // reserved — not generated yet
    public static final byte WATER        = 4;
    public static final byte LAVA         = 5;
    public static final byte LOCKED_DOOR  = 6;   // aligns with WorldGenerator.DOOR_LOCKED
    public static final byte GAS          = 7;   // reserved — not generated yet
    public static final byte CLIMBABLE    = 8;

    // Procgen-lab-only tile markers — no direct live-game tile equivalent.
    // ProcgenRoomConverter maps these to spawn descriptors or AIR.
    public static final byte PICKUP       = 9;
    public static final byte ENEMY_SPAWN  = 10;
    public static final byte SAVE_POINT   = 11;
    public static final byte BOSS_SPAWN   = 12;
    public static final byte SPIKES       = 13;  // hazard surface (was 5)
    public static final byte DOOR         = 14;  // open traversable door opening (was 6)

    private Tile() {}
}
