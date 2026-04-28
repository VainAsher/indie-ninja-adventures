package com.indieniinja.client.game.cutscene;

/** All step types supported by the cutscene sequencer. */
public enum CutsceneStepType {

    // ── Phase 1 — core sequencer ──────────────────────────────────────────────
    LOCK_PLAYER,
    UNLOCK_PLAYER,
    DIALOGUE,
    WAIT,
    SET_FLAG,

    // ── Phase 2 — camera ─────────────────────────────────────────────────────
    CAMERA_FOCUS,
    CAMERA_PAN,
    CAMERA_RESTORE_PLAYER,

    // ── Phase 2 — entity ─────────────────────────────────────────────────────
    ENTITY_FACE,
    ENTITY_MOVE_TO,
    ENTITY_SET_VISIBLE,
    ENTITY_PLAY_ANIM,

    // ── Optional / future ─────────────────────────────────────────────────────
    FADE_IN,
    FADE_OUT,
    TITLE_CARD,
    HUB_CHANGE,
    START_MISSION
}
