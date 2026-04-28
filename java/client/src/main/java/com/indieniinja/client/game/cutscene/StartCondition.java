package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.StoryManager;

import java.util.Map;

/**
 * A single guard condition that must be satisfied before a cutscene may start.
 *
 * JSON shape (one field required):
 *   { "flag_not_set": "act1_linzi_met" }
 *   { "flag_set":     "act1_social_grounding_done" }
 */
public final class StartCondition {

    /** If non-null: cutscene only starts when this flag is absent. */
    public final String flagNotSet;

    /** If non-null: cutscene only starts when this flag is present. */
    public final String flagSet;

    public StartCondition(String flagNotSet, String flagSet) {
        this.flagNotSet = flagNotSet;
        this.flagSet    = flagSet;
    }

    public static StartCondition fromMap(Map<String, Object> m) {
        Object fns = m.get("flag_not_set");
        Object fs  = m.get("flag_set");
        return new StartCondition(
                fns instanceof String s ? s : null,
                fs  instanceof String s ? s : null
        );
    }

    /** Returns true when this condition passes given the current story flags. */
    public boolean isMet(StoryManager story) {
        if (flagNotSet != null && story.hasFlag(flagNotSet)) return false;
        if (flagSet    != null && !story.hasFlag(flagSet))   return false;
        return true;
    }
}
