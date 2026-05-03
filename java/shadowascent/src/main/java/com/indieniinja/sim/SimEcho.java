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

    /** Animation state string derived from replayed input — used by EntityRenderer. */
    public String animState   = "idle";
    /** Weapon state captured from spawning player — drives sprite prefix. */
    public String weaponState = "unarmed";

    /** If false, recalling before playback completes fails the puzzle. */
    public final boolean recallable;

    /** Stance variant at spawn time: "silent" (Yin) | "riot" (Yang) | "resonant" (Flow). */
    public final String echoType;

    /** True while this echo can continue replaying commands. */
    public boolean active = true;
    /** True once replay reaches end-of-log naturally. */
    public boolean completed = false;
    /** True when recalled early while recallable=false. */
    public boolean failed = false;
    /**
     * When true, the replay restarts from tick 0 each time it completes.
     * Used by ASYMMETRIC_ABILITY_LOCK to keep the echo visible indefinitely.
     */
    public boolean looping = false;

    private long tickCursor = 0L;
    private InputCommand currentInput = InputCommand.neutral(0);

    public SimEcho(String echoId, int ownerSlot, float startX, float startY,
                   ReplayPlayer replay, boolean recallable, String weaponState, String echoType) {
        this.echoId      = echoId;
        this.ownerSlot   = ownerSlot;
        this.x           = startX;
        this.y           = startY;
        this.replay      = replay;
        this.recallable  = recallable;
        this.weaponState = weaponState != null ? weaponState : "unarmed";
        this.echoType    = echoType != null ? echoType : "silent";
    }

    /** Advance replay by one tick. Looping echoes restart automatically on completion. */
    public void step() {
        if (!active || replay == null) return;

        if (replay.isDone(tickCursor)) {
            if (looping) {
                tickCursor = 0L;
                completed = false;
            } else {
                completed = true;
                active = false;
                return;
            }
        }

        InputCommand cmd = pickCommand(replay.inputsForTick(tickCursor));
        if (cmd != null) {
            currentInput = InputCommand.fromMap(cmd.toMap());
            if (currentInput.left && !currentInput.right) facing = -1;
            if (currentInput.right && !currentInput.left) facing = 1;
            // Derive a simple anim state for rendering (full physics not re-simulated)
            if (currentInput.jump)  animState = "jump";
            else if (currentInput.dash) animState = "dash";
            else if (currentInput.attack) animState = "attack";
            else if (currentInput.left || currentInput.right) animState = "run";
            else animState = "idle";
        }

        tickCursor++;
        if (!looping && replay.isDone(tickCursor)) {
            completed = true;
            active = false;
        }
    }

    /** Restart playback from tick 0 (used by SIMULTANEOUS_TIMING on failed sync). */
    public void restart() {
        tickCursor = 0L;
        completed = false;
        failed = false;
        active = true;
        animState = "idle";
        currentInput = InputCommand.neutral(ownerSlot);
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
