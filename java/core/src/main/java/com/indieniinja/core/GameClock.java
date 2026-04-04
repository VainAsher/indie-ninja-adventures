package com.indieniinja.core;

import com.indieniinja.physics.PhysicsConstants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Fixed-timestep game clock — Glenn Fiedler pattern.
 * Java equivalent of Python core/clock.py GameClock.
 *
 * The server's ZoneSimulationLoop already handles its own 60 Hz timing via
 * LockSupport.parkNanos; it calls GameClock.stepOne() directly rather than
 * tick() (which measures wall-clock time and is suited for the Pygame client).
 *
 * tick()    — client-style: measures elapsed wall time, drains accumulator
 * stepOne() — server-style: advance exactly one fixed tick, no wall-clock I/O
 */
public final class GameClock {

    private static final Logger log = LoggerFactory.getLogger(GameClock.class);

    public static final int   PHYSICS_HZ  = PhysicsConstants.TARGET_FPS;  // 60
    public static final float PHYSICS_DT  = PhysicsConstants.FIXED_DT;    // 1/60
    public static final float MAX_FRAME   = PhysicsConstants.MAX_FRAME_TIME; // 0.25

    private final EventBus bus;

    private double accumulator  = 0.0;
    private long   lastTimeNs   = System.nanoTime();
    private long   tickCount    = 0;
    private int    frameCount   = 0;

    public GameClock(EventBus bus) {
        this.bus = bus;
    }

    /**
     * Client-style tick: measure elapsed wall time, run as many fixed steps as
     * the accumulator allows, then emit a RenderEvent.
     * Prevents spiral of death by capping frame time at MAX_FRAME.
     */
    public void tick() {
        long nowNs     = System.nanoTime();
        double elapsed = (nowNs - lastTimeNs) / 1_000_000_000.0;
        lastTimeNs     = nowNs;

        if (elapsed > MAX_FRAME) elapsed = MAX_FRAME;
        accumulator += elapsed;

        int steps = 0;
        while (accumulator >= PHYSICS_DT) {
            bus.emit(new TickEvent(PHYSICS_DT, tickCount++));
            accumulator -= PHYSICS_DT;
            if (++steps >= 10) {          // safety guard (matches Python)
                log.error("Physics falling behind — resetting accumulator");
                accumulator = 0.0;
                break;
            }
        }
        frameCount++;
    }

    /**
     * Server-style single-step: advance exactly one fixed tick.
     * The ZoneSimulationLoop controls wall-clock timing via LockSupport.parkNanos;
     * it calls stepOne() once per iteration.
     */
    public void stepOne() {
        bus.emit(new TickEvent(PHYSICS_DT, tickCount++));
    }

    public float getAlpha()    { return (float)(accumulator / PHYSICS_DT); }
    public long  getTickCount(){ return tickCount; }
    public int   getFrameCount(){ return frameCount; }

    public void reset() {
        accumulator = 0.0;
        lastTimeNs  = System.nanoTime();
        tickCount   = 0;
        frameCount  = 0;
    }
}
