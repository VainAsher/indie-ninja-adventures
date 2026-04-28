package com.indieniinja.client.game.cutscene;

/** Controls when a player is allowed to skip a cutscene. */
public enum SkipPolicy {
    /** Cannot be skipped under any circumstances. */
    NEVER,
    /** Can always be skipped. */
    ALWAYS,
    /** Blocked on first view; allowed on every subsequent replay. */
    ALLOW_AFTER_FIRST_VIEW,
    /** Only skippable when DevConsole is active (internal QA). */
    DEBUG_ONLY
}
