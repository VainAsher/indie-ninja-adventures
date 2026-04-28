package com.indieniinja.client.game.cutscene;

import java.util.Map;

/**
 * One step in an authored cutscene sequence.
 *
 * Fields are optional per step type:
 *   LOCK_PLAYER / UNLOCK_PLAYER  — no extra fields required
 *   DIALOGUE                     — speaker, textKey
 *   WAIT                         — duration (seconds)
 *   SET_FLAG                     — flag, value
 *   CAMERA_FOCUS                 — target (entityId or markerName), duration
 *   CAMERA_PAN                   — target, duration
 *   ENTITY_FACE                  — entity, target
 *   ENTITY_MOVE_TO               — entity, target, duration
 *   ENTITY_SET_VISIBLE           — entity, value ("true"/"false")
 *   ENTITY_PLAY_ANIM             — entity, value (animation key)
 *   HUB_CHANGE                   — value (hub change key)
 *   TITLE_CARD                   — textKey
 *   START_MISSION                — value (missionId)
 */
public final class CutsceneStep {

    public final CutsceneStepType type;

    /** Generic string value (true/false for lock, animKey, missionId, hub change key). */
    public final String value;

    /** Flag name for SET_FLAG steps. */
    public final String flag;

    /** Speaker display name for DIALOGUE steps. */
    public final String speaker;

    /** Dialogue text key (looked up in localisation / inline). */
    public final String textKey;

    /** Duration in seconds for WAIT, CAMERA_*, ENTITY_MOVE_TO. */
    public final float duration;

    /** Target entity id or marker name for CAMERA_*, ENTITY_*, ENTITY_FACE. */
    public final String target;

    /** Entity id for ENTITY_* steps. */
    public final String entity;

    private CutsceneStep(Builder b) {
        this.type     = b.type;
        this.value    = b.value;
        this.flag     = b.flag;
        this.speaker  = b.speaker;
        this.textKey  = b.textKey;
        this.duration = b.duration;
        this.target   = b.target;
        this.entity   = b.entity;
    }

    /** Parse from a JSON-decoded map (Jackson/Gson-style Map<String, Object>). */
    public static CutsceneStep fromMap(Map<String, Object> m, String cutsceneId, int stepIndex) {
        String typeStr = str(m, "type");
        if (typeStr == null) throw new CutsceneLoadException(
                cutsceneId + " step[" + stepIndex + "]: missing 'type' field");

        CutsceneStepType type;
        try {
            type = CutsceneStepType.valueOf(typeStr.toUpperCase());
        } catch (IllegalArgumentException e) {
            throw new CutsceneLoadException(
                    cutsceneId + " step[" + stepIndex + "]: unknown step type '" + typeStr + "'");
        }

        return new Builder(type)
                .value(str(m, "value"))
                .flag(str(m, "flag"))
                .speaker(str(m, "speaker"))
                .textKey(str(m, "text_key"))
                .duration(floatVal(m, "duration"))
                .target(str(m, "target"))
                .entity(str(m, "entity"))
                .build();
    }

    @Override
    public String toString() {
        return "CutsceneStep{type=" + type + ", speaker=" + speaker + ", flag=" + flag + "}";
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static String str(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v instanceof String s ? s : null;
    }

    private static float floatVal(Map<String, Object> m, String key) {
        Object v = m.get(key);
        if (v instanceof Number n) return n.floatValue();
        return 0f;
    }

    // ── Builder ───────────────────────────────────────────────────────────────

    public static final class Builder {
        private final CutsceneStepType type;
        private String value, flag, speaker, textKey, target, entity;
        private float  duration;

        public Builder(CutsceneStepType type) { this.type = type; }

        public Builder value(String v)    { this.value    = v; return this; }
        public Builder flag(String v)     { this.flag     = v; return this; }
        public Builder speaker(String v)  { this.speaker  = v; return this; }
        public Builder textKey(String v)  { this.textKey  = v; return this; }
        public Builder duration(float v)  { this.duration = v; return this; }
        public Builder target(String v)   { this.target   = v; return this; }
        public Builder entity(String v)   { this.entity   = v; return this; }

        public CutsceneStep build()       { return new CutsceneStep(this); }
    }
}
