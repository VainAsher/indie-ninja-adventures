package com.indieniinja.physics;

/**
 * Physics constants — single source of truth for the Java engine.
 *
 * Values MUST match config/physics_constants.py EXACTLY.
 * Do not add or change constants here without updating the Python file too.
 *
 * All units: pixels per tick (tick = 1/60 second).
 */
public final class PhysicsConstants {
    private PhysicsConstants() {}

    // ── Gravity & falling ─────────────────────────────────────────────────────
    public static final float GRAVITY           = 0.4f;
    public static final float FALL_GRAVITY_MULT = 1.5f;   // falling faster than rising
    public static final float FAST_FALL_MULT    = 2.0f;   // holding down while falling
    public static final float JUMP_CUT_MULT     = 3.0f;   // jump released mid-air
    public static final float MAX_FALL_SPEED    = 12.0f;  // terminal velocity

    // ── Movement ──────────────────────────────────────────────────────────────
    public static final float MAX_RUN_SPEED   = 8.0f;
    public static final float GROUND_ACCEL    = 180.0f;
    public static final float GROUND_FRICTION = 0.8f;
    public static final float AIR_ACCEL_MULT  = 0.65f;
    public static final float AIR_FRICTION    = 0.95f;

    // ── Jumping ───────────────────────────────────────────────────────────────
    public static final float JUMP_POWER         = 14.5f;
    public static final float DOUBLE_JUMP_POWER  = 14.5f;
    public static final float WALL_JUMP_POWER_X  = 8.5f;
    public static final float WALL_JUMP_POWER_Y  = 14.5f;
    public static final float COYOTE_TIME        = 0.12f;  // seconds
    public static final float JUMP_BUFFER_TIME   = 0.14f;  // seconds
    public static final float CROUCH_JUMP_MULT   = 0.7f;

    // ── Dash ──────────────────────────────────────────────────────────────────
    public static final float DASH_SPEED    = 16.0f;
    public static final float DASH_DURATION = 0.16f;   // seconds
    public static final float DASH_COOLDOWN = 0.45f;   // seconds

    // ── Crouch ────────────────────────────────────────────────────────────────
    public static final float CROUCH_SPEED_MULT  = 0.6f;
    public static final float CROUCH_ACCEL_MULT  = 0.8f;
    public static final float CROUCH_HEIGHT_RATIO = 0.5f;

    // ── Wall slide ────────────────────────────────────────────────────────────
    public static final float WALL_SLIDE_SPEED    = 3.0f;
    public static final float WALL_SLIDE_FRICTION = 0.7f;
    public static final float WALL_FRICTION_CLAMP = 5.0f;
    public static final float MAX_WALL_STAMINA    = 3.0f;
    public static final float STAMINA_REGEN_RATE  = 2.0f;
    public static final float EXHAUST_THRESHOLD   = 0.1f;
    public static final float EXHAUST_PENALTY     = 0.5f;

    // ── Medium effects ────────────────────────────────────────────────────────
    /** Per-axis velocity multiplier applied every tick inside a GAS tile. */
    public static final float GAS_DRAG              = 0.97f;

    // ── Ability flags (bitmask stored in PhysicsState.abilityFlags) ───────────
    /** Entity is immune to WATER drag / fall-cap effects (e.g., WaterWalk ability). */
    public static final int ABILITY_WATER_WALK = 1 << 0;
    /** Entity is immune to ICE friction reduction (e.g., IceGrip ability). */
    public static final int ABILITY_ICE_GRIP   = 1 << 1;
    /** Entity is immune to GAS drag (e.g., GasResist ability). */
    public static final int ABILITY_GAS_RESIST = 1 << 2;

    // ── Collision ─────────────────────────────────────────────────────────────
    /** Activate swept (sub-step) collision when speed exceeds this threshold. */
    public static final float SWEPT_COLLISION_THRESHOLD = 8.0f;
    /** Sub-step size for swept collision (pixels per sub-step). */
    public static final float SWEPT_STEP_SIZE            = 12.0f;
    public static final int   PLATFORM_GRACE_PIXELS      = 4;
    public static final int   CORNER_MIN_OVERLAP         = 4;
    public static final int   CORNER_MAX_OVERLAP         = 14;

    // ── Player dimensions ─────────────────────────────────────────────────────
    public static final int PLAYER_WIDTH         = 28;
    public static final int PLAYER_HEIGHT        = 56;
    public static final int PLAYER_CROUCH_HEIGHT = 28;

    // ── World / tiles ─────────────────────────────────────────────────────────
    public static final int TILE_SIZE       = 32;
    public static final int TILES_PER_ZONE  = 8;
    public static final int ROOM_WIDTH_TILES  = 128;
    public static final int ROOM_HEIGHT_TILES = 128;

    // ── Game clock ────────────────────────────────────────────────────────────
    public static final int   TARGET_FPS      = 60;
    public static final float FIXED_DT        = 1.0f / 60.0f;  // 0.016667 s
    public static final float MAX_FRAME_TIME  = 0.25f;          // spiral-of-death guard
}
