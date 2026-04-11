package com.indieniinja.client.game;

/**
 * Shadow Ascent narrative act definitions (GDD §5).
 *
 * Each act carries two rendering parameters that drive the HUD and world feel:
 *   {@code hudAlpha}       — opacity of all HUD elements (Act IV near-zero: dissociation)
 *   {@code lanternDefault} — starting Lantern value for a new session in this act
 *
 * Act transitions are driven by boss defeats, fragment milestones, and hub state
 * changes. See {@link StoryManager} for the transition logic.
 *
 * Wire format: ordinal integer (0–6) stored in player_progress.
 */
public enum Act {

    ACT_I_RISE       (1.0f, 1.0f),   // Full HUD, full Lantern — hopeful start
    ACT_II_FALL      (0.6f, 0.6f),   // HUD dims, Lantern falters as hub corrupts
    ACT_III_LABYRINTH(0.4f, 0.4f),   // Deeper fog, proof tokens, echo puzzles begin
    ACT_IV_BREAK     (0.1f, 0.2f),   // Near-invisible HUD, gravity heavy — depression
    ACT_V_HEARTH     (0.5f, 0.5f),   // Gradual restoration — warmth returning
    ACT_VI_ASCENT    (0.7f, 0.7f),   // Building toward completion, abilities restored
    ACT_VII_UPPER    (1.0f, 1.0f);   // Full HUD, full Lantern — earned resolution

    /** Opacity for all HUD elements this act. Act IV = 0.1 (near-invisible). */
    public final float hudAlpha;
    /** Default Lantern value when entering a new session mid-act. */
    public final float lanternDefault;

    Act(float hudAlpha, float lanternDefault) {
        this.hudAlpha       = hudAlpha;
        this.lanternDefault = lanternDefault;
    }

    /** Wire integer (ordinal) for storage. */
    public int wire()       { return ordinal(); }
    public String label()   { return name().replace('_', ' '); }

    public static Act fromWire(int ordinal) {
        Act[] vals = values();
        return (ordinal >= 0 && ordinal < vals.length) ? vals[ordinal] : ACT_I_RISE;
    }

    public static Act fromString(String s) {
        if (s == null) return ACT_I_RISE;
        try { return valueOf(s); } catch (IllegalArgumentException e) {
            // Try numeric fallback
            try { return fromWire(Integer.parseInt(s)); } catch (NumberFormatException ignored) {}
        }
        return ACT_I_RISE;
    }
}
