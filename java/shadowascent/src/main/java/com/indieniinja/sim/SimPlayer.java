package com.indieniinja.sim;

import com.indieniinja.content.GameConfig;
import com.indieniinja.network.InputCommand;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.physics.PhysicsState;

/**
 * Server-side player simulation state.
 *
 * Mirrors the subset of Python's Player/PlayerState that the server needs
 * for authoritative simulation: physics, health, facing, and animation.
 * The server does NOT run the full mechanics pipeline (jump, dash, etc.) in
 * Phase B — movement remains client-authoritative (positions from INPUT).
 * This struct records them so the snapshot builder can read them.
 *
 * Phase C will drive these from the full Java mechanics pipeline.
 */
public final class SimPlayer {

    public final String playerId;
    public final int    slot;

    // Physics — updated from INPUT messages (client-authoritative in Phase B)
    public final PhysicsState physics;

    // State
    public int     health;
    public int     maxHealth = 5;
    public int     facing    = 1;   // 1=right, -1=left
    public boolean isDead    = false;
    public String  animState = "";

    // Respawn — timer counts down from RESPAWN_DELAY after death; -1 = not pending
    public float respawnTimer = -1f;
    /** World-space spawn position (set at construction; used to reset position on respawn). */
    public float spawnX, spawnY;

    // Invincibility frames after taking damage (ticks)
    public int invincibilityTicks = 0;

    // ── Advanced movement mechanics state ────────────────────────────────────
    // Dash
    public float   dashTimer    = 0f;    // seconds remaining while dash is active
    public float   dashCooldown = 0f;    // seconds until next dash is allowed
    public boolean isDashing    = false;

    // Jump
    public int     jumpCount    = 0;     // jumps consumed (0=grounded, 1=first, 2=double)
    public float   coyoteTimer  = 0f;    // seconds remaining to jump after walking off edge
    public float   jumpBuffer   = 0f;    // seconds remaining from a buffered jump press

    // Previous-tick input state for rising-edge detection
    public boolean prevJump     = false;
    public boolean prevDash     = false;
    public boolean prevTeleport = false;
    public boolean prevStanceSwitch = false;

    // Ground state from previous tick (for coyote-time detection)
    public boolean wasOnGround  = false;

    // ── Traverse state (Phase 5/6) ────────────────────────────────────────────
    // Runtime context is computed in GameSimulator each tick (wall-climb intent,
    // ledge hang/climb, water-surface detection, and side-bank water exits).
    public boolean isClimbing   = false;  // player is actively climbing a surface
    public boolean isOnLedge    = false;  // player is hanging on a ledge grab point
    public boolean isLedgeClimbing = false; // playing ledge-climb-up animation
    public boolean atWaterSurface = false;  // water contact near surface for swim-surface anims
    public float ledgeTargetX = 0f;         // resolved top-out X for current ledge context
    public float ledgeTargetY = 0f;         // resolved top-out Y for current ledge context
    public float ledgeHangY   = 0f;         // suspended Y while hanging
    public float ledgeClimbTimer = 0f;      // climb-up animation timer

    // ── Combat state ─────────────────────────────────────────────────────────
    // Melee attack (J key / left mouse)
    public boolean isAttacking      = false;
    public int     attackActiveTicks = 0;    // ticks remaining in active hitbox window
    public float   attackCooldown   = 0f;    // seconds until next attack allowed
    public boolean prevAttack       = false; // rising-edge detection
    public boolean pendingShuriken  = false; // set by applyPlayerInput; consumed by GameSimulator
    // Guard/parry
    public boolean isBlocking       = false;
    public boolean isParrying       = false;
    public float   blockHeldTime    = 0f;    // seconds continuous hold
    public float   blockHitTimer    = 0f;    // block/parry reaction animation hold
    public String  blockHitAnim     = "";    // "block_hit" | "block_hit_hard"

    // Shuriken (K key)
    public int     shurikenAmmo     = 5;     // matches Python default ammo count
    public float   throwCooldown    = 0f;    // seconds until next throw allowed
    public boolean isThrowing       = false; // for "throw" anim state
    public boolean prevThrow        = false; // rising-edge detection

    // Context interaction animation bridge (Phase 7 start):
    // brief animation override window used for readable lever/button/pickup feedback.
    public String  interactionState = "";
    public float   interactionTimer = 0f;

    // Combat constants — delegate to GameConfig so balance edits have one home.
    public static final int   MELEE_DAMAGE         = GameConfig.PLAYER_MELEE_DAMAGE;
    public static final int   ARMED_MELEE_DAMAGE   = GameConfig.PLAYER_ARMED_MELEE_DAMAGE;
    public static final int   MELEE_ACTIVE_TICKS   = GameConfig.PLAYER_MELEE_ACTIVE_TICKS;
    public static final float MELEE_COOLDOWN       = GameConfig.PLAYER_MELEE_COOLDOWN;
    public static final float MELEE_REACH          = GameConfig.PLAYER_MELEE_REACH;
    public static final float MELEE_HEIGHT         = GameConfig.PLAYER_MELEE_HEIGHT;
    public static final float SHURIKEN_SPEED       = GameConfig.PLAYER_SHURIKEN_SPEED;
    public static final float SHURIKEN_COOLDOWN    = GameConfig.PLAYER_SHURIKEN_COOLDOWN;
    public static final int   SHURIKEN_DAMAGE      = GameConfig.PLAYER_SHURIKEN_DAMAGE;
    public static final float SHURIKEN_STUN        = 0.4f;
    public static final int   SHURIKEN_MAX_AMMO    = GameConfig.PLAYER_SHURIKEN_MAX_AMMO;
    public static final float PARRY_WINDOW         = GameConfig.PLAYER_PARRY_WINDOW;
    public static final float BLOCK_DAMAGE_MULT    = GameConfig.PLAYER_BLOCK_DAMAGE_MULT;
    public static final float BLOCK_HIT_TIME       = 0.16f;
    public static final float PARRY_HIT_TIME       = 0.20f;
    public static final float INTERACT_LEVER_TIME  = 0.45f;
    public static final float INTERACT_BUTTON_TIME = 0.32f;
    public static final float INTERACT_PICKUP_TIME = 0.22f;
    public static final float CLIMB_SPEED          = 3.0f;
    public static final float LEDGE_HANG_OFFSET    = 10f;
    public static final float LEDGE_CLIMB_TIME     = 0.22f;

    // ── Teleport state ───────────────────────────────────────────────────────
    // Hold-to-phase system: hold T → ghost cursor moves with directional input,
    // release T → warp to cursor position.
    public float   teleportCooldown    = 0f;    // seconds until next teleport
    public boolean teleportPhaseMode   = false; // currently holding T, cursor active
    public float   teleportCursorX     = 0f;    // ghost cursor world X
    public float   teleportCursorY     = 0f;    // ghost cursor world Y
    public float   teleportOriginX     = 0f;    // position where phase started
    public float   teleportOriginY     = 0f;
    public boolean isTeleporting       = false; // brief invuln window after warp
    public float   teleportInvulnTimer = 0f;

    public float   teleportPhaseTimer  = 0f;    // counts down from TELEPORT_PHASE_TIME

    public static final float TELEPORT_RANGE        = 256f;  // px max cursor range
    public static final float TELEPORT_PHASE_TIME   = 0.6f;  // seconds of phase before auto-warp
    public static final float TELEPORT_COOLDOWN     = 3.0f;  // seconds
    public static final float TELEPORT_INVULN       = 0.25f; // seconds of invuln after warp
    public static final float TELEPORT_CURSOR_SPEED = 420f;  // px/sec (Python: 420/60 * 60)

    // ── Stamina + Mana resources ─────────────────────────────────────────────
    // Mirrors Python PlayerState: stamina drains while running, regens on ground.
    // Mana regens passively; consumed by ninjutsu casts.
    public float stamina    = STAMINA_MAX;
    public float mana       = MANA_MAX;

    public static final float STAMINA_MAX        = 30f;
    public static final float STAMINA_REGEN_RATE = 12f;   // per second on ground (6 in air)
    public static final float STAMINA_RUN_DRAIN  = 4f;    // per second while running
    public static final float MANA_MAX           = 30f;
    public static final float MANA_REGEN_RATE    = 6f;    // per second always

    // ── Ninjutsu state ────────────────────────────────────────────────────────
    // hold L → ninjutsuHeld; release → cast Purify (mana cost 25, cooldown 12s)
    public boolean ninjutsuHeld     = false;   // L was held last tick
    public boolean ninjutsuCasting  = false;   // brief casting anim flag
    public float   ninjutsuCooldown = 0f;      // seconds until next cast
    public float   ninjutsuCastTimer = 0f;     // anim duration countdown

    public static final float NINJUTSU_MANA_COST  = 25f;
    public static final float NINJUTSU_COOLDOWN   = 12f;
    public static final float NINJUTSU_CAST_TIME  = 0.4f;

    // ── Wall jump state ──────────────────────────────────────────────────────
    public float   wallCoyoteTimer    = 0f;  // brief window to wall-jump after leaving wall
    public int     lastWallDir        = 0;   // last wall direction (for wall-jump when onWall=false)
    public float   wallJumpLockTimer  = 0f;  // input lock after wall jump — matches Python wall_jump_lock

    public static final float WALL_JUMP_INPUT_LOCK = 0.2f;  // seconds (Python uses 0.12 — slightly
                                                             // longer here since no air friction)

    // ── Wall slide mechanic state ────────────────────────────────────────────
    // Mirrors Python mechanics/wall_slide.py WallSlideMechanic
    public float   wallSlideStamina        = WALL_SLIDE_MAX_STAMINA;
    public boolean isWallSliding           = false;
    public boolean awaitGroundAfterExhaust = false;
    public int     exhaustDetachFrames     = 0;   // nudge off wall for N ticks after exhaust

    // Wall slide constants (match Python WallSlideMechanic)
    public static final float WALL_SLIDE_SPEED        = 3.0f;
    public static final float WALL_SLIDE_MAX_STAMINA  = 3.0f;
    public static final float WALL_SLIDE_REGEN_RATE   = 3.0f / 2.0f;  // full in 2s
    public static final float WALL_SLIDE_MIN_STAMINA  = 0.3f;
    public static final float WALL_SLIDE_EXHAUST_THRESH  = 0.5f;
    public static final float WALL_SLIDE_EXHAUST_PENALTY = 0.25f;
    public static final float WALL_SLIDE_DRAIN_MULT      = 1.6f;
    public static final float WALL_FRICTION_SPEED        = 6.0f;

    // ── Progression (Loop 14 / Loop 20 / Loop 28) ────────────────────────────
    public int experience = 0;
    public int level      = 1;
    /** Ability strings unlocked so far (wire values from Python AbilityRequirement). */
    public final java.util.Set<String> unlockedAbilities = new java.util.LinkedHashSet<>();

    /** Per-player effective mana cap — starts at MANA_MAX, scales with level. */
    public int maxMana    = (int) MANA_MAX;
    /** Per-player effective stamina cap — starts at STAMINA_MAX, scales with level. */
    public int maxStamina = (int) STAMINA_MAX;

    /** XP needed to advance from current level to the next. */
    public int xpToNextLevel() { return level * 50; }

    /**
     * Add XP and handle level-ups.
     * Each level-up: +1 maxHealth, ability unlock at certain levels,
     * and stat bonuses every few levels (Loop 28).
     * Returns the number of levels gained.
     */
    public int addXp(int xp) {
        experience += xp;
        int levelsGained = 0;
        while (experience >= xpToNextLevel()) {
            experience -= xpToNextLevel();
            level++;
            levelsGained++;
            // HP +1 every level
            maxHealth++;
            health = Math.min(health + 1, maxHealth);  // partial heal on level-up
            // Mana +5 every 3 levels
            if (level % 3 == 0) maxMana += 5;
            // Stamina +3 every 4 levels
            if (level % 4 == 0) maxStamina += 3;
            // Shuriken ammo +1 every 5 levels (cap at base+3=8)
            if (level % 5 == 0 && shurikenAmmo < SHURIKEN_MAX_AMMO + 3) shurikenAmmo++;
            grantAbilitiesForLevel(level);
        }
        return levelsGained;
    }

    private void grantAbilitiesForLevel(int lvl) {
        // Mirrors Python CampaignManager ability unlock progression
        switch (lvl) {
            case 2  -> unlockedAbilities.add("double_jump");
            case 3  -> unlockedAbilities.add("dash");
            case 5  -> unlockedAbilities.add("wall_jump");
            case 7  -> unlockedAbilities.add("shuriken");
            case 10 -> unlockedAbilities.add("teleport");
            case 12 -> unlockedAbilities.add("ninjutsu");
            default -> {}
        }
    }

    // ── Yin/Yang & Lantern (M4 — GDD §3.3/§3.4) ─────────────────────────────
    /** Yin/Yang emotional balance component. Ticked by GameSimulator.tickYinYang(). */
    public final YinYangComponent yinYang = new YinYangComponent(-1);
    /** Lantern clarity component. Ticked by GameSimulator.tickLantern(). */
    public final LanternComponent lantern = new LanternComponent(-1);
    /** Active stance mode for P0 readability bridge: "yin" | "yang". */
    public String stanceMode = "yin";

    // ── Flow recency (P1-03A / GDD §3.3) ─────────────────────────────────────
    /**
     * Counts down from FLOW_RECENCY_WINDOW after each meaningful action (dash,
     * attack, shuriken, teleport).  Flow state is only eligible while > 0,
     * preventing accidental passive flow from idle balance drift.
     */
    public float lastMeaningfulActionTimer = 0f;

    // ── Noise / stealth (P1-03A) ──────────────────────────────────────────────
    // noiseLevel decays to 0 over ~0.4s; enemies check it against their detection radius.
    /** Current noise intensity 0..1. Set by actions; decays per tick. */
    public float noiseLevel  = 0f;
    /** World-space noise radius derived from noiseLevel * MAX_NOISE_RADIUS. */
    public float noiseRadius = 0f;

    // ── Phase Teleport variant (P1-03A / GDD §3.3) ───────────────────────────
    /** Resolved on phase-start from stance: "shadow" | "thunder" | "harmonic". */
    public String teleportType = "shadow";

    // ── Weapon / animation state ──────────────────────────────────────────────
    /** Current weapon set wire string: "unarmed" | "sword" | "pistol".
     *  Drives animation key prefix in EntityRenderer (animation Phase 4). */
    public String weaponState = "unarmed";
    /** Optional Yang posture override from direct hot-swap input ("1"/"2"). */
    public String yangPreferredWeaponState = "";

    // ── Inventory ─────────────────────────────────────────────────────────────
    public final SimInventory inventory = new SimInventory();

    // Input — written by Netty I/O thread, read by sim thread via AtomicRef in PlayerRecord
    public InputCommand latestInput = InputCommand.neutral(0);
    // Shadow Ascent M6: last 10 seconds of input history for echo playback.
    public final EchoRecorder echoRecorder = new EchoRecorder();

    public SimPlayer(String playerId, int slot, float spawnX, float spawnY) {
        this.playerId = playerId;
        this.slot     = slot;
        this.spawnX   = spawnX;
        this.spawnY   = spawnY;
        this.physics  = new PhysicsState(
            spawnX, spawnY,
            PhysicsConstants.PLAYER_WIDTH,
            PhysicsConstants.PLAYER_HEIGHT
        );
        this.health = maxHealth;
    }

    public boolean isAlive() {
        return health > 0 && !isDead;
    }

    /** Apply damage; set isDead flag if health reaches 0. Also decays the Lantern. */
    public void takeDamage(int dmg) {
        if (invincibilityTicks > 0) return;
        health = Math.max(0, health - dmg);
        if (health <= 0) isDead = true;
        invincibilityTicks = GameConfig.PLAYER_INVINCIBILITY_TICKS;
        lantern.onDamage();       // taking damage dims the lantern
    }

    /** Called each tick; decrements invincibility timer. */
    public void tickInvincibility() {
        if (invincibilityTicks > 0) invincibilityTicks--;
    }
}
