package com.indieniinja.world.puzzle;

/**
 * Describes an ability gate on a directed room edge.
 *
 * PuzzlePlanner assigns one gate per eligible edge; AbilityLayer converts
 * it into actual tile geometry (raised platform, wide gap, or vertical shaft).
 */
public final class AbilityGate {

    /**
     * The player ability required to pass this gate.
     * String values match HubRegistry.requiredAbility() and SimPlayer ability set.
     */
    public enum GateType {
        DOUBLE_JUMP ("double_jump"),
        WALL_JUMP   ("wall_jump"),
        DASH        ("dash"),
        SHURIKEN    ("shuriken"),
        TELEPORT    ("teleport");

        public final String abilityString;
        GateType(String s) { this.abilityString = s; }
    }

    /**
     * Physical manifestation technique used by AbilityLayer.
     *
     * RAISED_PLATFORM — platform elevated beyond single-jump reach (DOUBLE_JUMP)
     * WIDE_GAP        — horizontal gap too wide to cross without dash (DASH)
     * VERTICAL_SHAFT  — narrow vertical shaft requiring wall-jump to ascend (WALL_JUMP)
     */
    public enum Technique {
        RAISED_PLATFORM,
        WIDE_GAP,
        VERTICAL_SHAFT
    }

    public final GateType  type;
    public final Technique technique;

    public AbilityGate(GateType type, Technique technique) {
        this.type      = type;
        this.technique = technique;
    }

    /** The ability string that matches HubRegistry / SimPlayer ability checks. */
    public String requiredAbilityString() {
        return type.abilityString;
    }

    @Override
    public String toString() {
        return "AbilityGate(" + type + " via " + technique + ")";
    }
}
