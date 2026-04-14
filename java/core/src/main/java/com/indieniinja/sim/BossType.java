package com.indieniinja.sim;

/**
 * Boss type definitions.
 *
 * Shadow Ascent narrative bosses (M5): SIREN, ECHO_WARDEN, TIME_LEECH_LORD, MEMORY_EATER.
 * Each has a distinct psychological pattern (see BossPatternLibrary).
 *
 * Legacy generic types kept for backward compatibility with existing rooms.
 * The boss spawned in a given room is driven by BossPatternLibrary.selectForAct()
 * in narrative mode, or deterministically from room seed in generic/arcade mode.
 */
public enum BossType {
    // ── Shadow Ascent narrative bosses (M5) ──────────────────────────────────
    /** Act II — scripted loss; invincible; strips Yin/Yang to 0; triggers hub collapse */
    SIREN          ("siren",           8,  0, 48f,  "boss_siren"),
    /** Act III — mirrors player movement with 0.5 s delay; exploitable via hazards */
    ECHO_WARDEN    ("echo_warden",     20, 3, 72f,  "boss_echo_warden"),
    /** Act IV — drains Lantern each tick; spawns time_leech enemies; speed burst at 30% */
    TIME_LEECH_LORD("time_leech_lord", 25, 4, 84f,  "boss_time_leech_lord"),
    /** Act VI — resets platform positions each phase; can re-lock unlocked doors */
    MEMORY_EATER   ("memory_eater",    30, 3, 60f,  "boss_memory_eater"),

    // Campaign-authored boss IDs (mission objective compatibility)
    SHADOW_LORD    ("shadow_lord",     25, 1, 80f,  "boss_shadow_lord"),
    FIRE_DEMON     ("fire_demon",      30, 1, 100f, "boss_fire_demon"),
    ICE_QUEEN      ("ice_queen",       28, 1, 70f,  "boss_ice_queen"),
    NECROMANCER    ("necromancer",     20, 1, 60f,  "boss_necromancer"),
    DRAGON         ("dragon",          35, 1, 90f,  "boss_dragon"),
    VEIL_MAIDEN    ("veil_maiden",     40, 1, 90f,  "boss_veil_maiden"),

    // ── Legacy generic bosses (pre-Shadow Ascent; used in arcade/seed rooms) ─
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
