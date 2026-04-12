package com.indieniinja.sim;

/**
 * Enemy AI behaviour states.
 * Java equivalent of Python entities/enemy.py EnemyAIState enum.
 * String values must match Python for correct WorldSnapshot serialisation.
 */
public enum EnemyAIState {
    IDLE     ("idle"),
    PATROL   ("patrol"),
    CHASE    ("chase"),
    ATTACK   ("attack"),
    FLEE     ("flee"),    // retreat when HP is critically low
    GUARD    ("guard"),   // skeleton: raise shield, block incoming melee
    STUNNED  ("stunned"),
    DEAD     ("dead");

    public final String wire;   // wire value used in EnemyState.ai_state

    EnemyAIState(String wire) { this.wire = wire; }
}
