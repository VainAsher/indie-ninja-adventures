package com.indieniinja.sim;

import com.indieniinja.core.Component;
import com.indieniinja.core.SerializableComponent;
import java.util.Map;

/**
 * Yin/Yang balance mechanic (GDD §3.3).
 *
 * <ul>
 *   <li><b>Yin (Emotion)</b> — reveals hidden platforms, environmental awareness</li>
 *   <li><b>Yang (Discipline)</b> — attack strength, movement precision</li>
 *   <li><b>Flow Mode</b> — when {@code |yin − yang| < BALANCE_THRESHOLD} both values
 *       contribute simultaneously; animation blending becomes smooth</li>
 * </ul>
 *
 * Server effects applied in {@code GameSimulator.tickYinYang()}:
 * <ul>
 *   <li>yin &gt; 0.7 → set {@code ABILITY_YIN_SIGHT} on {@code PhysicsState.abilityFlags};
 *       hidden-platform tiles become solid for this entity</li>
 *   <li>yang &gt; 0.7 → attack damage multiplier 1.5×; dash stamina cost −30%</li>
 *   <li>{@link #isBalanced()} → set {@code flowMode = true} on player state</li>
 * </ul>
 *
 * Values decay towards 0.5 (neutral) at {@link #DECAY_RATE} per second when not in an
 * active area — intentionally slow so players feel the emotional weight of shifts.
 */
public final class YinYangComponent extends Component implements SerializableComponent {

    /** Balance threshold — |yin − yang| below this activates Flow Mode. */
    public static final float BALANCE_THRESHOLD = 0.15f;
    /** High-Yin threshold — above this activates Yin Sight. */
    public static final float HIGH_YIN_THRESHOLD = 0.7f;
    /** High-Yang threshold — above this activates Yang Surge. */
    public static final float HIGH_YANG_THRESHOLD = 0.7f;
    /** Passive decay rate towards neutral (per second). */
    public static final float DECAY_RATE = 0.005f;
    /** Neutral value — both values start here. */
    public static final float NEUTRAL = 0.5f;

    /** 0.0 – 1.0 (Emotion). */
    public float yin  = NEUTRAL;
    /** 0.0 – 1.0 (Discipline). */
    public float yang = NEUTRAL;

    public YinYangComponent(int entityId) {
        super(entityId);
    }

    // ── Mutations ──────────────────────────────────────────────────────────────

    public void absorbYin(float amount) {
        yin = Math.min(1.0f, yin + amount);
    }

    public void absorbYang(float amount) {
        yang = Math.min(1.0f, yang + amount);
    }

    /**
     * Passive decay towards neutral — called once per tick on the server.
     * @param dt seconds per tick (typically {@code PhysicsConstants.FIXED_DT})
     */
    public void decay(float dt) {
        float d = DECAY_RATE * dt;
        yin  = approach(yin,  NEUTRAL, d);
        yang = approach(yang, NEUTRAL, d);
    }

    private static float approach(float value, float target, float step) {
        if (value < target) return Math.min(target, value + step);
        if (value > target) return Math.max(target, value - step);
        return value;
    }

    // ── Queries ────────────────────────────────────────────────────────────────

    /** True when both values are close enough to trigger Flow Mode. */
    public boolean isBalanced() {
        return Math.abs(yin - yang) < BALANCE_THRESHOLD;
    }

    /** True when Yin is high enough to activate Yin Sight. */
    public boolean hasYinSight() {
        return yin > HIGH_YIN_THRESHOLD;
    }

    /** True when Yang is high enough to activate Yang Surge (damage × 1.5, dash cost −30%). */
    public boolean hasYangSurge() {
        return yang > HIGH_YANG_THRESHOLD;
    }

    // ── Serialisation ──────────────────────────────────────────────────────────

    @Override
    public Map<String, Object> toMap() {
        return Map.of("yin", yin, "yang", yang);
    }

    /** Restore from a saved/network map.  Missing keys default to neutral. */
    public static YinYangComponent fromMap(int entityId, Map<String, Object> m) {
        YinYangComponent c = new YinYangComponent(entityId);
        if (m == null) return c;
        c.yin  = flt(m, "yin",  NEUTRAL);
        c.yang = flt(m, "yang", NEUTRAL);
        return c;
    }

    private static float flt(Map<String, Object> m, String k, float def) {
        Object v = m.get(k);
        return v instanceof Number n ? n.floatValue() : def;
    }

    @Override public String toString() {
        return "YinYang{yin=" + yin + ", yang=" + yang + ", flow=" + isBalanced() + "}";
    }
}
