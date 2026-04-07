package com.indieniinja.sim;

/**
 * Boss type definitions — mirrors Python entities/boss.py BossType + BOSS_DEFINITIONS.
 *
 * Five boss types, each with distinct stats. The boss spawned in a "boss" room
 * is determined deterministically from the room seed.
 */
public enum BossType {
    FOREST_GUARDIAN("forest_guardian", 15, 2, 72f,  "boss_forest_guardian"),
    CORRUPT_MAYOR  ("corrupt_mayor",   12, 1, 60f,  "boss_corrupt_mayor"),
    CRYSTAL_GOLEM  ("crystal_golem",   20, 3, 48f,  "boss_crystal_golem"),
    DARK_KNIGHT    ("dark_knight",     16, 2, 84f,  "boss_dark_knight"),
    PLAGUE_RAT     ("plague_rat",      14, 2, 96f,  "boss_plague_rat");

    /** Wire string used in BossState.bossType. */
    public final String wire;
    /** Base max HP. */
    public final int    maxHp;
    /** Base damage per attack. */
    public final int    baseDamage;
    /** Movement speed in pixels/second. */
    public final float  moveSpeed;
    /** Animation atlas key prefix. */
    public final String atlasKey;

    BossType(String wire, int maxHp, int baseDamage, float moveSpeed, String atlasKey) {
        this.wire       = wire;
        this.maxHp      = maxHp;
        this.baseDamage = baseDamage;
        this.moveSpeed  = moveSpeed;
        this.atlasKey   = atlasKey;
    }

    /** Physics width in pixels. */
    public int width()  { return 64; }
    /** Physics height in pixels. */
    public int height() { return 96; }
    /** XP rewarded on kill. */
    public int xpReward() { return 80 + ordinal() * 20; }

    /** Deterministically pick a boss type from a room seed. */
    public static BossType fromSeed(long seed) {
        BossType[] vals = values();
        return vals[(int)(Math.abs(seed) % vals.length)];
    }

    public static BossType fromWire(String wire) {
        for (BossType t : values()) if (t.wire.equals(wire)) return t;
        return FOREST_GUARDIAN;
    }
}
