package com.indieniinja.sim;

/**
 * Enemy awareness tier — parallel to EnemyAIState, driven by player noise (P1-03A / GDD §3.3).
 *
 * UNAWARE  → normal patrol, oblivious to the player
 * SUSPICIOUS → heard something; investigates noise source; transitions to ALERTED on sight
 * SEARCHING  → lost sight/sound after ALERTED; sweeps last known position before returning
 * ALERTED  → spotted or confirmed player; overrides aiState to CHASE
 */
public enum EnemyAwarenessState {
    UNAWARE,
    SUSPICIOUS,
    SEARCHING,
    ALERTED
}
