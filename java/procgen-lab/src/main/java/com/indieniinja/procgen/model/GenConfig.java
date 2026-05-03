package com.indieniinja.procgen.model;

public final class GenConfig {
    // Zone grid dimensions — aligned to 128×128 live game room size.
    // 128 tiles / 8 tile stamp = 16 zones per axis.
    public static final int ZONE_W    = 16;
    public static final int ZONE_H    = 16;
    public static final int ZONE_SIZE = 8;

    public static final int ROOM_W = ZONE_W * ZONE_SIZE; // 128
    public static final int ROOM_H = ZONE_H * ZONE_SIZE; // 128

    private GenConfig() {}
}
