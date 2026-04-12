package com.indieniinja.sim;

import com.indieniinja.core.Component;
import com.indieniinja.core.SerializableComponent;
import java.util.Map;

/**
 * Lantern (Emotional Clarity) mechanic (GDD §3.4).
 *
 * A per-player float [0.0–1.0] that measures the Hollowed Ninja's emotional clarity.
 * Persisted to {@code player_progress}.  Acts as a global modifier for world clarity
 * and physics.
 *
 * <table>
 *   <tr><th>Value</th><th>Physics effect</th><th>Visual</th></tr>
 *   <tr><td>&lt; 0.3</td><td>Some PLATFORM tiles treated as SOLID (trap)</td>
 *       <td>Full vignette, oppressive atmosphere</td></tr>
 *   <tr><td>0.3–0.7</td><td>Normal</td><td>Partial shadow</td></tr>
 *   <tr><td>&gt; 0.7</td><td>Jump height +20%, coyote time 4→8 ticks</td>
 *       <td>Clear, warm lighting</td></tr>
 * </table>
 *
 * Server effects applied in {@code GameSimulator.tickLantern()}:
 * <ul>
 *   <li>Decays at {@link #DARK_DECAY_RATE} per second in dark areas or on damage</li>
 *   <li>Restored by NPC interaction (+0.05) and Lantern fragments (+0.2)</li>
 * </ul>
 */
public final class LanternComponent extends Component implements SerializableComponent {

    // ── Thresholds ────────────────────────────────────────────────────────────
    public static final float LOW_THRESHOLD  = 0.3f;   // below = oppressive mode
    public static final float HIGH_THRESHOLD = 0.7f;   // above = elevated mode

    // ── Decay/restore rates ───────────────────────────────────────────────────
    /** Passive decay per second in dark areas (or on damage tick). */
    public static final float DARK_DECAY_RATE = 0.01f;
    /** Restoration per NPC interaction event. */
    public static final float NPC_RESTORE     = 0.05f;
    /** Restoration per Lantern fragment pickup. */
    public static final float FRAGMENT_RESTORE = 0.20f;
    /** Restoration per damage-taken event (player pain can paradoxically clarify). */
    public static final float DAMAGE_DECAY    = 0.05f;

    // ── Enhanced movement bonuses (applied via GameSimulator when value > HIGH_THRESHOLD) ──
    public static final float HIGH_JUMP_BONUS  = 0.20f; // +20% jump power
    public static final int   HIGH_COYOTE_TICKS = 8;    // 4→8 coyote ticks

    /** Current lantern value. Range [0.0, 1.0]. */
    public float value = 0.8f;   // start bright — darkens as Act progresses

    public LanternComponent(int entityId) {
        super(entityId);
    }

    // ── Mutations ──────────────────────────────────────────────────────────────

    /**
     * Passive decay — call once per server tick.
     * @param dt seconds per tick
     * @param inDark whether player is in a dark/oppressive zone
     */
    public void decay(float dt, boolean inDark) {
        if (inDark) {
            value = Math.max(0f, value - DARK_DECAY_RATE * dt);
        }
    }

    /** Restore lantern value (e.g. NPC interaction or fragment pickup). */
    public void restore(float amount) {
        value = Math.min(1.0f, value + amount);
    }

    /** Reduce on damage. */
    public void onDamage() {
        value = Math.max(0f, value - DAMAGE_DECAY);
    }

    // ── Queries ────────────────────────────────────────────────────────────────

    /** True when lantern is low — world feels oppressive, some platforms trap player. */
    public boolean isLow() {
        return value < LOW_THRESHOLD;
    }

    /** True when lantern is high — movement bonuses active. */
    public boolean isHigh() {
        return value > HIGH_THRESHOLD;
    }

    /**
     * Vignette intensity for the ChunkRenderer.
     * Returns 0 (clear) when high, 1 (full dark) when low.
     */
    public float vignetteIntensity() {
        return 1.0f - Math.min(1.0f, Math.max(0f, (value - LOW_THRESHOLD) / (HIGH_THRESHOLD - LOW_THRESHOLD)));
    }

    // ── Serialisation ──────────────────────────────────────────────────────────

    @Override
    public Map<String, Object> toMap() {
        return Map.of("lantern", value);
    }

    public static LanternComponent fromMap(int entityId, Map<String, Object> m) {
        LanternComponent c = new LanternComponent(entityId);
        if (m == null) return c;
        c.value = flt(m, "lantern", 0.8f);
        return c;
    }

    private static float flt(Map<String, Object> m, String k, float def) {
        Object v = m.get(k);
        return v instanceof Number n ? n.floatValue() : def;
    }

    @Override public String toString() {
        return "Lantern{value=" + value + ", vignette=" + vignetteIntensity() + "}";
    }
}
