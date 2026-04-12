package com.indieniinja.sim;

import com.indieniinja.physics.PhysicsState;

/**
 * Server-side enemy simulation entity.
 * Java equivalent of the runtime fields read by Python's GameSimulator.get_snapshot().
 *
 * AI logic: simple patrol ↔ chase state machine, matching the Python
 * entities/enemy.py EnemyManager behaviour for the four ground types.
 * Flying enemies (Bat) skip gravity application.
 */
public final class SimEnemy {

    // ── Identity ──────────────────────────────────────────────────────────────
    public final String enemyId;
    public final String enemyType;   // "goblin", "bat", "slime", "skeleton", "wolf"
    public final boolean canFly;

    // ── Physics ───────────────────────────────────────────────────────────────
    public final PhysicsState physics;

    // ── Stats ─────────────────────────────────────────────────────────────────
    public int   hp;
    public final int   maxHp;
    public final int   baseDamage;
    public final float moveSpeed;        // pixels per second
    public final float detectionRadius;  // pixels
    public final float attackRange;      // pixels
    public final float patrolSpeedMult;  // fraction of moveSpeed while patrolling

    // ── AI state ──────────────────────────────────────────────────────────────
    public EnemyAIState aiState     = EnemyAIState.PATROL;
    public boolean      facingRight = true;

    // Patrol waypoints (x coords; enemy bounces between them)
    public float patrolMinX;
    public float patrolMaxX;

    // Timers (in seconds)
    public float attackTimer      = 0f;   // time until next attack allowed
    public float stunTimer        = 0f;
    public float fleeTimer        = 0f;   // seconds remaining in FLEE state
    public float guardTimer       = 0f;   // seconds remaining in GUARD state

    // Attack sub-state timing (mirrors Python EnemyAttackSubState)
    public float attackWindupTimer    = 0f;
    public float attackActiveTimer    = 0f;
    public float attackRecoveryTimer  = 0f;

    // Respawn tracking
    public boolean removed = false;

    // ── Constants (from Python ENEMY_DEFINITIONS) ─────────────────────────────
    public static final float ATTACK_WINDUP_TIME   = 0.6f;
    public static final float ATTACK_ACTIVE_TIME   = 0.15f;
    public static final float ATTACK_RECOVERY_TIME = 0.4f;
    public static final float STUN_DURATION        = 0.5f;
    public static final float FLEE_DURATION        = 3.0f;   // seconds enemy flees before patrolling
    public static final float GUARD_DURATION       = 2.0f;   // seconds skeleton holds guard stance
    public static final float FLEE_HP_THRESHOLD    = 0.25f;  // flee when HP falls below 25%

    public SimEnemy(
            String enemyId, String enemyType,
            float x, float y, int width, int height,
            int maxHp, int baseDamage, float moveSpeed,
            float detectionRadius, float attackRange,
            float patrolMinX, float patrolMaxX,
            boolean canFly) {

        this.enemyId          = enemyId;
        this.enemyType        = enemyType;
        this.canFly           = canFly;
        this.physics          = new PhysicsState(x, y, width, height);
        this.hp               = maxHp;
        this.maxHp            = maxHp;
        this.baseDamage       = baseDamage;
        this.moveSpeed        = moveSpeed;
        this.detectionRadius  = detectionRadius;
        this.attackRange      = attackRange;
        this.patrolMinX       = patrolMinX;
        this.patrolMaxX       = patrolMaxX;
        this.patrolSpeedMult  = 0.5f;

        // AI owns horizontal movement (stepEnemyAI adds directly to physics.x).
        // PhysicsSystem still integrates vx, so leave it at zero — no double-movement.
        this.physics.vx = 0f;
    }

    public boolean isAlive() { return hp > 0 && !removed; }

    /**
     * Apply damage and transition to STUNNED state.
     * Returns true if the enemy just died.
     */
    public boolean takeDamage(int dmg) {
        if (!isAlive()) return false;
        hp = Math.max(0, hp - dmg);
        if (hp <= 0) {
            aiState = EnemyAIState.DEAD;
            removed = true;
            return true;
        }
        // At critically low HP: flee after stun instead of returning to patrol
        if ((float) hp / maxHp <= FLEE_HP_THRESHOLD) {
            fleeTimer = FLEE_DURATION;
            // Still stun first — flee begins when stun ends (see stepEnemyAI)
        }
        aiState    = EnemyAIState.STUNNED;
        stunTimer  = STUN_DURATION;
        return false;
    }

    /** Distance to a point (e.g. nearest player). */
    public float distanceTo(float tx, float ty) {
        float cx = physics.x + physics.width  * 0.5f;
        float cy = physics.y + physics.height * 0.5f;
        float dx = tx - cx, dy = ty - cy;
        return (float) Math.sqrt(dx * dx + dy * dy);
    }
}
