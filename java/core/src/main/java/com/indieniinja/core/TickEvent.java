package com.indieniinja.core;

/**
 * Emitted once per physics tick (60 Hz fixed timestep).
 * Equivalent to Python's core/event_bus.py TickEvent.
 */
public final class TickEvent extends GameEvent {

    /** Fixed timestep in seconds — always PhysicsConstants.FIXED_DT (1/60). */
    public final float dt;

    /** Monotonically increasing tick counter since simulation start. */
    public final long tickNumber;

    public TickEvent(float dt, long tickNumber) {
        this.dt         = dt;
        this.tickNumber = tickNumber;
    }
}
