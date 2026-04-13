package com.indieniinja.sim;

import com.indieniinja.network.InputCommand;

import java.util.Map;

/**
 * Server-side echo playback entity.
 *
 * The echo reads one tick of inputs at a time from ReplayPlayer and exposes the
 * currently replayed command. Puzzle systems can consume this state to evaluate
 * timing/pressure-plate logic without reading raw recorder buffers directly.
 */
public final class SimEcho {

    public final String echoId;
    public final int ownerSlot;
    public final ReplayPlayer replay;

    public float x;
    public float y;
    public int facing = 1;

    /** If false, recalling before playback completes fails the puzzle. */
    public final boolean recallable;

    /** True while this echo can continue replaying commands. */
    public boolean active = true;
    /** True once replay reaches end-of-log naturally. */
    public boolean completed = false;
    /** True when recalled early while recallable=false. */
    public boolean failed = false;

    private long tickCursor = 0L;
    private InputCommand currentInput = InputCommand.neutral(0);

    public SimEcho(String echoId, int ownerSlot, float startX, float startY,
                   ReplayPlayer replay, boolean recallable) {
        this.echoId = echoId;
        this.ownerSlot = ownerSlot;
        this.x = startX;
        this.y = startY;
        this.replay = replay;
        this.recallable = recallable;
    }

    /** Advance replay by one tick. */
    public void step() {
        if (!active || replay == null) return;

        if (replay.isDone(tickCursor)) {
            completed = true;
            active = false;
            return;
        }

        InputCommand cmd = pickCommand(replay.inputsForTick(tickCursor));
        if (cmd != null) {
            currentInput = InputCommand.fromMap(cmd.toMap());
            if (currentInput.left && !currentInput.right) facing = -1;
            if (currentInput.right && !currentInput.left) facing = 1;
        }

        tickCursor++;
        if (replay.isDone(tickCursor)) {
            completed = true;
            active = false;
        }
    }

    /**
     * Attempt to recall this echo.
     * Returns true for a safe recall, false if this causes puzzle failure.
     */
    public boolean recall() {
        if (failed) return false;
        if (completed) {
            active = false;
            return true;
        }
        if (!recallable) {
            failed = true;
            active = false;
            return false;
        }
        active = false;
        return true;
    }

    public long ticksPlayed() {
        return tickCursor;
    }

    public InputCommand currentInput() {
        return InputCommand.fromMap(currentInput.toMap());
    }

    private InputCommand pickCommand(Map<Integer, InputCommand> inputs) {
        if (inputs == null || inputs.isEmpty()) return null;
        InputCommand owned = inputs.get(ownerSlot);
        if (owned != null) return owned;
        return inputs.values().iterator().next();
    }
}
