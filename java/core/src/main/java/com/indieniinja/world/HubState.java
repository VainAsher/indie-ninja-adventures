package com.indieniinja.world;

/**
 * Hub evolution states for the Shadow Ascent narrative arc (GDD §4).
 *
 * Each hub progresses through these states as the story advances.
 * The transition logic lives in {@link HubStateMachine}.
 *
 * Hub 1 (Bamboo Courtyard) path: FULL → CORRUPTED → EMPTY
 * Hub 2 (Chasm of Still Shadows) path: FRACTURED → RECOVERING → WHOLE
 */
public enum HubState {
    /** Act I — All NPCs present, stable environment. */
    FULL,
    /** Act II — NPCs disappearing, prices rise, some areas close. */
    CORRUPTED,
    /** Act II end — Only Siren remains; hub has collapsed. */
    EMPTY,
    /** Hub 2 initial state — Shattered, few NPCs, oppressive atmosphere. */
    FRACTURED,
    /** Act V — NPCs return one by one as the player heals. */
    RECOVERING,
    /** Act VI–VII — Full NPC roster restored, all abilities accessible. */
    WHOLE
}
