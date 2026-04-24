package com.indieniinja.content;

/**
 * Centralized tunable constants for Shadow Ascent gameplay.
 * All balance changes should modify this file, not individual sim classes.
 * Physics constants stay in PhysicsConstants — this file covers gameplay tuning only.
 */
public final class GameConfig {
    private GameConfig() {}

    // ── Player Combat ──────────────────────────────────────────────────────────
    /** Unarmed hit damage (KO, non-lethal). */
    public static final int   PLAYER_MELEE_DAMAGE          = 1;
    /** Armed hit damage (lethal, drops loot). */
    public static final int   PLAYER_ARMED_MELEE_DAMAGE     = 2;
    /** Frames the melee hitbox is live. */
    public static final int   PLAYER_MELEE_ACTIVE_TICKS     = 8;
    /** Seconds between melee swings. */
    public static final float PLAYER_MELEE_COOLDOWN         = 0.4f;
    /** Melee hitbox reach forward from player center in px. */
    public static final float PLAYER_MELEE_REACH            = 48f;
    /** Melee hitbox height in px. */
    public static final float PLAYER_MELEE_HEIGHT           = 40f;
    /** Shuriken speed px/tick. */
    public static final float PLAYER_SHURIKEN_SPEED         = 10f;
    /** Seconds between shuriken throws. */
    public static final float PLAYER_SHURIKEN_COOLDOWN      = 0.35f;
    /** Shuriken damage. */
    public static final int   PLAYER_SHURIKEN_DAMAGE        = 1;
    /** Maximum shuriken ammo. */
    public static final int   PLAYER_SHURIKEN_MAX_AMMO      = 5;
    /** Parry window in seconds. */
    public static final float PLAYER_PARRY_WINDOW           = 0.10f;
    /** Damage multiplier while blocking. */
    public static final float PLAYER_BLOCK_DAMAGE_MULT      = 0.35f;
    /** Frames of invincibility after being hit. */
    public static final int   PLAYER_INVINCIBILITY_TICKS    = 30;
    /** Coyote time in ticks (can jump after walking off a ledge). */
    public static final float PLAYER_COYOTE_TICKS           = 8f;
    /** Jump input buffer in ticks. */
    public static final int   PLAYER_JUMP_BUFFER_TICKS      = 10;
    /** Seconds player is in respawn-delay after death. */
    public static final float PLAYER_RESPAWN_DELAY          = 5.0f;

    // ── Enemy Combat ──────────────────────────────────────────────────────────
    /** Default attack windup in seconds when not set by EnemyDefinition. */
    public static final float ENEMY_ATTACK_WINDUP_DEFAULT   = 0.6f;
    /** HP fraction below which enemies flee (0 = never flee). */
    public static final float ENEMY_FLEE_HP_THRESHOLD       = 0.40f;
    /** Default knockout duration in ticks. */
    public static final float ENEMY_KNOCKOUT_DURATION       = 180f;
    /** Detection range multiplier when player has been spotted before. */
    public static final float ENEMY_DETECTION_AGGRO_MULT    = 1.15f;
    /** Skeleton attack range multiplier. */
    public static final float SKELETON_RANGE_MULT           = 1.15f;
    /** Skeleton guard retreat speed multiplier. */
    public static final float SKELETON_GUARD_RETREAT_SPEED_MULT = 0.35f;

    // ── Archer-specific ───────────────────────────────────────────────────────
    /** Archer projectile speed as fraction of player shuriken speed. */
    public static final float ARCHER_PROJECTILE_SPEED_MULT  = 0.90f;
    /** Archer minimum preferred combat range in px. */
    public static final float ARCHER_MIN_COMBAT_RANGE       = 112f;
    /** Archer maximum preferred combat range in px. */
    public static final float ARCHER_MAX_COMBAT_RANGE       = 220f;

    // ── Stance / Flow / Lantern ───────────────────────────────────────────────
    /** Balance threshold below which stance is considered neutral. */
    public static final float FLOW_BALANCE_THRESHOLD        = 0.15f;
    /** Stance drift toward neutral per second. */
    public static final float STANCE_DRIFT_PER_SECOND       = 0.09f;
    /** Balance boost per stance-switch input. */
    public static final float STANCE_SWITCH_BOOST           = 0.035f;
    /** Duration of parry stun on enemy in seconds. */
    public static final float PARRY_STUN_DURATION           = 0.80f;
    /** Lantern restore rate per second while in Flow state. */
    public static final float LANTERN_FLOW_RESTORE_RATE     = 0.012f;

    // ── Stance movement modifiers (GDD §3.3 / design-request P1-03A) ─────────
    // Applied as multipliers over base PhysicsConstants values.
    // Yin = precision/stealth; Yang = force/speed; Flow = neutral but smooth.

    /** Yin run speed multiplier — tighter, quieter, more controlled. */
    public static final float YIN_SPEED_MULT        = 0.88f;
    /** Yang run speed multiplier — faster, committed, louder. */
    public static final float YANG_SPEED_MULT       = 1.10f;
    /** Flow run speed multiplier — neutral baseline, smoothing deferred to animation pass. */
    public static final float FLOW_SPEED_MULT       = 1.00f;

    /** Yin dash speed multiplier — short silent slip. */
    public static final float YIN_DASH_SPEED_MULT   = 0.75f;
    /** Yang dash speed multiplier — long forceful burst. */
    public static final float YANG_DASH_SPEED_MULT  = 1.20f;
    /** Flow dash speed multiplier — neutral. */
    public static final float FLOW_DASH_SPEED_MULT  = 1.00f;

    /** Yin wall-jump horizontal power multiplier — stable, controlled push-off. */
    public static final float YIN_WALL_JUMP_X_MULT  = 0.90f;
    /** Yang wall-jump horizontal power multiplier — forceful launch. */
    public static final float YANG_WALL_JUMP_X_MULT = 1.15f;
    /** Flow wall-jump horizontal power multiplier — neutral. */
    public static final float FLOW_WALL_JUMP_X_MULT = 1.00f;

    // ── World Generation ──────────────────────────────────────────────────────
    /** World room count for acts 1-2. */
    public static final int   DEFAULT_WORLD_SIZE_ACT_1_2    = 6;
    /** World room count for act 3+. */
    public static final int   DEFAULT_WORLD_SIZE_ACT_3_PLUS = 24;
    /** Probability of adding a back-edge between non-adjacent rooms. */
    public static final float BACK_EDGE_PROBABILITY         = 0.15f;
    /** Maximum enemies spawned per room. */
    public static final int   MAX_ENEMIES_PER_ROOM          = 8;

    // ── Economy ───────────────────────────────────────────────────────────────
    /** Maximum currency a player can hold. */
    public static final int   CURRENCY_CAP                  = 999_999;
    /** Probability a shop restocks between zones. */
    public static final float SHOP_RESTOCK_PROBABILITY      = 0.6f;
}
