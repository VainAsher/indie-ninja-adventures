package com.indieniinja.sim;

/**
 * Boss AI states — mirrors Python entities/boss.py BossAIState.
 */
public enum BossAIState {
    INTRO            ("intro"),
    IDLE             ("idle"),
    MOVE             ("move"),
    ATTACK_MELEE     ("attack_melee"),
    ATTACK_RANGED    ("attack_ranged"),
    ATTACK_SPECIAL   ("attack_special"),
    VULNERABLE       ("vulnerable"),
    STUNNED          ("stunned"),
    PHASE_TRANSITION ("phase_transition"),
    DEAD             ("dead");

    public final String wire;
    BossAIState(String wire) { this.wire = wire; }
}
