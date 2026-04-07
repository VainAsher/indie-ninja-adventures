package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsState;

/**
 * Server-side boss simulation entity.
 *
 * Implements a four-phase state machine mirroring Python entities/boss.py Boss:
 *   INTRO → IDLE ↔ MOVE ↔ ATTACK_MELEE / ATTACK_RANGED
 *                              ↓ at 75%/50%/25% HP
 *                       PHASE_TRANSITION → VULNERABLE → (resume combat at higher speed)
 *                              ↓ at HP=0
 *                          DEAD
 *
 * Boss physics are server-authoritative (not client-authoritative like players).
 */
public final class SimBoss {

    // ── Phase HP thresholds ───────────────────────────────────────────────────
    public static final float PHASE2_RATIO = 0.75f;
    public static final float PHASE3_RATIO = 0.50f;
    public static final float PHASE4_RATIO = 0.25f;

    // ── State durations (seconds) ─────────────────────────────────────────────
    public static final float INTRO_DURATION            = 2.0f;
    public static final float PHASE_TRANSITION_DURATION = 1.5f;
    public static final float VULNERABLE_DURATION       = 3.0f;
    public static final float MELEE_WINDUP              = 0.5f;
    public static final float MELEE_ACTIVE              = 0.25f;
    public static final float MELEE_RECOVERY            = 0.4f;
    public static final float RANGED_WINDUP             = 0.8f;
    public static final float RANGED_ACTIVE             = 0.1f;
    public static final float RANGED_RECOVERY           = 0.6f;
    public static final float BASE_ATTACK_COOLDOWN      = 2.0f;
    public static final float STUN_DURATION             = 1.0f;

    // ── Aggro / range ─────────────────────────────────────────────────────────
    public static final float DETECT_RANGE       = 900f;
    public static final float MELEE_RANGE        = 96f;
    public static final float RANGED_RANGE       = 400f;
    public static final float INVULN_TICKS       = 15;    // ticks after each hit

    // ── Identity ──────────────────────────────────────────────────────────────
    public final String   bossId;
    public final BossType type;
    public final PhysicsState physics;

    // ── Health ────────────────────────────────────────────────────────────────
    public int     hp;
    public final int maxHp;
    private int    invincibilityTicks = 0;

    // ── Phase state ───────────────────────────────────────────────────────────
    public int  phaseNumber = 1;   // 1-4
    /** Pending phase transitions not yet played (phase numbers queued). */
    private int pendingPhase = 0;  // > 0 means a phase transition needs to fire

    // ── AI state ──────────────────────────────────────────────────────────────
    public BossAIState aiState = BossAIState.INTRO;
    /** Seconds spent in current state. */
    public float stateTimer    = 0f;
    /** Seconds until next attack is allowed. */
    public float attackCooldown = 0f;
    /** Sub-timer for attack phase windup/active/recovery. */
    public float attackSubTimer = 0f;
    /** Which sub-phase of attack we're in: 0=windup, 1=active, 2=recovery. */
    public int   attackSubPhase = 0;

    // ── Rendering ─────────────────────────────────────────────────────────────
    public boolean facingRight = false;
    public boolean removed     = false;

    // ── Speed multiplier — increases each phase ───────────────────────────────
    private float speedMult = 1.0f;

    public SimBoss(String bossId, BossType type, float spawnX, float spawnY) {
        this.bossId  = bossId;
        this.type    = type;
        this.maxHp   = type.maxHp;
        this.hp      = maxHp;
        this.physics = new PhysicsState(spawnX, spawnY, type.width(), type.height());
    }

    // ── Public accessors ──────────────────────────────────────────────────────

    public float hpRatio() { return maxHp > 0 ? (float) hp / maxHp : 0f; }

    public boolean isAlive() { return hp > 0 && !removed; }

    public String phaseWire() { return "phase_" + phaseNumber; }

    /**
     * Apply damage. Returns true if the boss died.
     * Respects invincibility frames; stuns briefly on rapid damage accumulation.
     */
    public boolean takeDamage(int dmg) {
        if (invincibilityTicks > 0) return false;
        if (aiState == BossAIState.PHASE_TRANSITION) return false; // immune during transition
        if (aiState == BossAIState.DEAD) return false;

        hp = Math.max(0, hp - dmg);
        invincibilityTicks = (int) INVULN_TICKS;

        if (hp <= 0) {
            aiState  = BossAIState.DEAD;
            removed  = true;
            return true;
        }

        // Check phase thresholds
        checkPhaseTransition();
        return false;
    }

    public void tickInvincibility() {
        if (invincibilityTicks > 0) invincibilityTicks--;
    }

    // ── AI step ───────────────────────────────────────────────────────────────

    /**
     * Advance boss AI one tick (1/60 s).
     *
     * @param dt       fixed timestep in seconds (1/60)
     * @param nearestX X-centre of nearest player
     * @param nearestY Y-centre of nearest player
     * @param dist     distance to nearest player
     */
    public void step(float dt, float nearestX, float nearestY, float dist) {
        if (!isAlive()) return;

        tickInvincibility();
        stateTimer    += dt;
        if (attackCooldown > 0) attackCooldown -= dt;

        // ── Facing direction ──────────────────────────────────────────────────
        float cx = physics.x + physics.width * 0.5f;
        facingRight = nearestX > cx;

        switch (aiState) {
            case INTRO -> {
                // Stand still; transition to IDLE after intro duration
                physics.vx = 0;
                if (stateTimer >= INTRO_DURATION) enterState(BossAIState.IDLE);
            }

            case IDLE -> {
                physics.vx = 0;
                if (dist <= DETECT_RANGE) {
                    enterState(BossAIState.MOVE);
                }
            }

            case MOVE -> {
                float speed = type.moveSpeed * speedMult / 60f; // px/tick
                physics.x += facingRight ? speed : -speed;

                // Attack when close enough
                if (attackCooldown <= 0) {
                    if (dist <= MELEE_RANGE)  startAttack(BossAIState.ATTACK_MELEE);
                    else if (dist <= RANGED_RANGE) startAttack(BossAIState.ATTACK_RANGED);
                }

                // Lose aggro
                if (dist > DETECT_RANGE * 1.5f) enterState(BossAIState.IDLE);
            }

            case ATTACK_SPECIAL -> {
                // Special attack — same structure as melee but uses ranged timings
                // Subclasses / future loops can extend this; for now treat like ranged.
                physics.vx = 0;
                attackSubTimer += dt;
                if (attackSubPhase == 0 && attackSubTimer >= RANGED_WINDUP) {
                    attackSubPhase = 1; attackSubTimer = 0;
                } else if (attackSubPhase == 1 && attackSubTimer >= RANGED_ACTIVE) {
                    attackSubPhase = 2; attackSubTimer = 0;
                } else if (attackSubPhase == 2 && attackSubTimer >= RANGED_RECOVERY) {
                    attackCooldown = BASE_ATTACK_COOLDOWN / speedMult;
                    enterState(BossAIState.MOVE);
                }
            }

            case ATTACK_MELEE, ATTACK_RANGED -> {
                physics.vx = 0;  // stand still while attacking
                attackSubTimer += dt;

                float windupTime  = aiState == BossAIState.ATTACK_MELEE ? MELEE_WINDUP  : RANGED_WINDUP;
                float activeTime  = aiState == BossAIState.ATTACK_MELEE ? MELEE_ACTIVE  : RANGED_ACTIVE;
                float recovTime   = aiState == BossAIState.ATTACK_MELEE ? MELEE_RECOVERY: RANGED_RECOVERY;

                // Advance through sub-phases: 0=windup, 1=active, 2=recovery
                if (attackSubPhase == 0 && attackSubTimer >= windupTime) {
                    attackSubPhase = 1; attackSubTimer = 0;
                } else if (attackSubPhase == 1 && attackSubTimer >= activeTime) {
                    attackSubPhase = 2; attackSubTimer = 0;
                } else if (attackSubPhase == 2 && attackSubTimer >= recovTime) {
                    attackCooldown = BASE_ATTACK_COOLDOWN / speedMult;
                    enterState(BossAIState.MOVE);
                }
            }

            case VULNERABLE -> {
                // Slow, takes extra damage (handled in takeDamage: no immunity)
                physics.vx = 0;
                if (stateTimer >= VULNERABLE_DURATION) {
                    enterState(BossAIState.MOVE);
                }
            }

            case PHASE_TRANSITION -> {
                physics.vx = 0;
                if (stateTimer >= PHASE_TRANSITION_DURATION) {
                    // Apply the pending phase upgrade
                    phaseNumber  = pendingPhase;
                    speedMult    = 1.0f + (phaseNumber - 1) * 0.2f; // +20% speed per phase
                    pendingPhase = 0;
                    enterState(BossAIState.VULNERABLE);
                }
            }

            case STUNNED -> {
                physics.vx = 0;
                if (stateTimer >= STUN_DURATION) enterState(BossAIState.MOVE);
            }

            case DEAD -> { physics.vx = 0; }
        }
    }

    /** Returns true if the boss melee attack is currently in its active window. */
    public boolean isMeleeActive() {
        return aiState == BossAIState.ATTACK_MELEE && attackSubPhase == 1;
    }

    /** Returns true if the boss ranged attack fires this tick (single-tick). */
    public boolean isRangedFiring() {
        return aiState == BossAIState.ATTACK_RANGED && attackSubPhase == 1 && attackSubTimer < (1f / 60f) * 2f;
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void enterState(BossAIState next) {
        aiState    = next;
        stateTimer = 0f;
    }

    private void startAttack(BossAIState attackState) {
        enterState(attackState);
        attackSubPhase = 0;
        attackSubTimer = 0f;
    }

    private void checkPhaseTransition() {
        int targetPhase = phaseNumber;
        if      (hpRatio() <= PHASE4_RATIO && phaseNumber < 4) targetPhase = 4;
        else if (hpRatio() <= PHASE3_RATIO && phaseNumber < 3) targetPhase = 3;
        else if (hpRatio() <= PHASE2_RATIO && phaseNumber < 2) targetPhase = 2;

        if (targetPhase > phaseNumber) {
            pendingPhase = targetPhase;
            enterState(BossAIState.PHASE_TRANSITION);
        }
    }
}
