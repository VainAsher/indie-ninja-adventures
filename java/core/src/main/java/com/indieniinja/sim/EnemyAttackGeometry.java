package com.indieniinja.sim;

/**
 * Shared enemy attack-hitbox geometry used by server combat and client debug.
 *
 * Coordinates are world-space AABB rectangles.
 */
public final class EnemyAttackGeometry {

    private EnemyAttackGeometry() {}

    /** Immutable AABB rectangle. */
    public static final class Rect {
        public final float x;
        public final float y;
        public final float w;
        public final float h;

        public Rect(float x, float y, float w, float h) {
            this.x = x;
            this.y = y;
            this.w = w;
            this.h = h;
        }
    }

    /** Default attack ranges matching GameSimulator.buildEnemy() type definitions. */
    public static float defaultAttackRange(String enemyType) {
        return switch (normalizeType(enemyType)) {
            case "bat"      -> 28f;
            case "slime"    -> 40f;
            case "skeleton" -> 64f;
            case "spearman" -> 80f;
            case "archer"   -> 200f;
            case "goblin", "swordsman", "default" -> 32f;
            default -> 32f;
        };
    }

    /**
     * Build an attack AABB for a single attack progress sample.
     *
     * @param attackProgress 0..1 progress across active attack window.
     */
    public static Rect attackRect(String enemyType,
                                  float bodyX, float bodyY,
                                  float bodyW, float bodyH,
                                  float attackRange,
                                  boolean facingRight,
                                  float attackProgress) {
        float p = clamp01(attackProgress);
        return switch (normalizeType(enemyType)) {
            case "goblin", "swordsman" ->
                greatswordSweep(bodyX, bodyY, bodyW, bodyH, attackRange, facingRight, p);
            case "spearman" ->
                forwardThrust(bodyX, bodyY, bodyW, bodyH, Math.max(attackRange, 88f), facingRight, 0.55f);
            case "archer" ->
                forwardThrust(bodyX, bodyY, bodyW, bodyH, 36f, facingRight, 0.60f);
            case "slime" ->
                radialSwipe(bodyX, bodyY, bodyW, bodyH, 1.25f, 0.85f, 0.10f);
            case "bat" ->
                forwardThrust(bodyX, bodyY, bodyW, bodyH, 28f, facingRight, 0.70f);
            default ->
                forwardThrust(bodyX, bodyY, bodyW, bodyH, Math.max(attackRange * 0.70f, 42f), facingRight, 0.75f);
        };
    }

    /**
     * Build debug rectangles for current attack state.
     * Greatsword types render three sampled phases to visualize the sweep arc.
     */
    public static Rect[] debugAttackRects(String enemyType,
                                          float bodyX, float bodyY,
                                          float bodyW, float bodyH,
                                          float attackRange,
                                          boolean facingRight) {
        String t = normalizeType(enemyType);
        if ("goblin".equals(t) || "swordsman".equals(t)) {
            return new Rect[] {
                attackRect(t, bodyX, bodyY, bodyW, bodyH, attackRange, facingRight, 0.18f),
                attackRect(t, bodyX, bodyY, bodyW, bodyH, attackRange, facingRight, 0.52f),
                attackRect(t, bodyX, bodyY, bodyW, bodyH, attackRange, facingRight, 0.88f)
            };
        }
        return new Rect[] {
            attackRect(t, bodyX, bodyY, bodyW, bodyH, attackRange, facingRight, 0.90f)
        };
    }

    private static Rect greatswordSweep(float bodyX, float bodyY, float bodyW, float bodyH,
                                        float attackRange, boolean facingRight, float progress) {
        float swingReach = Math.max(attackRange, 56f);

        if (progress < 0.34f) {
            float w = Math.max(36f, swingReach * 0.72f);
            float h = Math.max(24f, bodyH * 0.62f);
            float x = facingRight
                ? bodyX - w + bodyW * 0.35f
                : bodyX + bodyW - bodyW * 0.35f;
            float y = bodyY + bodyH * 0.35f;
            return new Rect(x, y, w, h);
        }

        if (progress < 0.67f) {
            float lift = Math.max(16f, bodyH * 0.30f);
            float w = bodyW + Math.max(26f, swingReach * 0.50f);
            float h = bodyH + lift;
            float x = bodyX - (w - bodyW) * 0.5f;
            float y = bodyY - lift * 0.75f;
            return new Rect(x, y, w, h);
        }

        float w = Math.max(40f, swingReach);
        float h = Math.max(28f, bodyH * 0.82f);
        float x = facingRight
            ? bodyX + bodyW * 0.45f
            : bodyX - w + bodyW * 0.55f;
        float y = bodyY + bodyH * 0.16f;
        return new Rect(x, y, w, h);
    }

    private static Rect forwardThrust(float bodyX, float bodyY, float bodyW, float bodyH,
                                      float reach, boolean facingRight, float heightRatio) {
        float h = Math.max(22f, bodyH * heightRatio);
        float x = facingRight
            ? bodyX + bodyW - 4f
            : bodyX - reach + 4f;
        float y = bodyY + bodyH * 0.20f;
        return new Rect(x, y, reach, h);
    }

    private static Rect radialSwipe(float bodyX, float bodyY, float bodyW, float bodyH,
                                    float widthMult, float heightMult, float yOffsetRatio) {
        float w = bodyW * widthMult;
        float h = bodyH * heightMult;
        float x = bodyX - (w - bodyW) * 0.5f;
        float y = bodyY + bodyH * yOffsetRatio;
        return new Rect(x, y, w, h);
    }

    private static String normalizeType(String enemyType) {
        if (enemyType == null || enemyType.isBlank()) return "default";
        return enemyType;
    }

    private static float clamp01(float v) {
        if (v < 0f) return 0f;
        if (v > 1f) return 1f;
        return v;
    }
}
