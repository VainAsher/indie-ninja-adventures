package com.indieniinja.physics;

/**
 * Physics-side tile type constants — mirrors WorldGenerator byte values.
 *
 * Provides the physics package a named reference to tile types without
 * a compile-time dependency on com.indieniinja.world.WorldGenerator (PHYS-1).
 *
 * Values MUST stay in sync with WorldGenerator static byte constants.
 * Byte IDs 0-6 match existing tile constants; 7 = GAS (new, PHYS-2).
 */
public enum TileType {
    AIR        ((byte) 0),
    SOLID      ((byte) 1),
    PLATFORM   ((byte) 2),
    ICE        ((byte) 3),
    WATER      ((byte) 4),
    LAVA       ((byte) 5),
    DOOR_LOCKED((byte) 6),
    GAS        ((byte) 7);

    public final byte id;

    TileType(byte id) { this.id = id; }

    private static final TileType[] BY_ID;
    static {
        TileType[] vals = values();
        int max = 0;
        for (TileType t : vals) if (t.id > max) max = t.id;
        BY_ID = new TileType[max + 1];
        for (TileType t : vals) BY_ID[t.id] = t;
    }

    /**
     * Look up TileType by raw byte id.
     * Returns {@link #AIR} for any unknown value.
     */
    public static TileType of(byte id) {
        return (id >= 0 && id < BY_ID.length && BY_ID[id] != null) ? BY_ID[id] : AIR;
    }
}
