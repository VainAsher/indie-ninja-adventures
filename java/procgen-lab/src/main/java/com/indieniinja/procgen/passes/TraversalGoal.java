package com.indieniinja.procgen.passes;

/** Contract strings shared between CarvePass (writer) and TraversalValidator (reader, S4). */
public final class TraversalGoal {
    public static final String HORIZONTAL_INTRO    = "horizontal_intro";
    public static final String CROSS_GAP_WITH_DASH = "cross_gap_with_dash";
    public static final String VERTICAL_ASCENT     = "vertical_ascent";
    public static final String MOVEMENT_PRESSURE   = "movement_pressure";
    public static final String REST                = "rest";
    public static final String DASH_MASTERY        = "dash_mastery";
    public static final String OPTIONAL_REWARD     = "optional_reward";

    private TraversalGoal() {}
}
