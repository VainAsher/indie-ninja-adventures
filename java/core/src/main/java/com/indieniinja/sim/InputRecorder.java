package com.indieniinja.sim;

import com.indieniinja.network.InputCommand;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * Records per-frame player inputs during a live session so the simulation can
 * be replayed deterministically.
 *
 * Each entry captures the tick number, player slot, and the full InputCommand
 * that was applied that tick.  The log is written to a newline-delimited JSON
 * file (one entry per line) so it can be streamed without loading everything
 * into memory.
 *
 * File format (NDJSON):
 *   {"tick":0,"slot":0,"left":false,"right":true,...}
 *   {"tick":0,"slot":1,"left":false,"right":false,...}
 *   ...
 *
 * Usage:
 *   recorder.startRecording(seed);
 *   // each tick:
 *   recorder.record(tick, playerId, slot, cmd);
 *   // on session end:
 *   recorder.stopRecording("session_42.ndjson");
 */
public final class InputRecorder {

    /** One recorded frame entry. */
    public record FrameEntry(long tick, int slot, InputCommand cmd) {}

    private final List<FrameEntry> buffer = new ArrayList<>(8192);
    private boolean recording = false;
    private long    worldSeed = 0L;

    public void startRecording(long worldSeed) {
        this.worldSeed = worldSeed;
        buffer.clear();
        recording = true;
    }

    public boolean isRecording() { return recording; }

    /** Record one player's input for the current tick. */
    public void record(long tick, int slot, InputCommand cmd) {
        if (!recording || cmd == null) return;
        buffer.add(new FrameEntry(tick, slot, cmd));
    }

    /**
     * Stop recording and write the log to {@code path}.
     * The first line contains a header: {"type":"header","seed":...,"entries":...}
     */
    public void stopRecording(Path path) throws IOException {
        recording = false;
        try (BufferedWriter w = Files.newBufferedWriter(path)) {
            // Header line
            w.write("{\"type\":\"header\",\"seed\":" + worldSeed
                    + ",\"entries\":" + buffer.size() + "}");
            w.newLine();
            // Data lines
            for (FrameEntry e : buffer) {
                w.write(entryToJson(e));
                w.newLine();
            }
        }
    }

    private static String entryToJson(FrameEntry e) {
        InputCommand c = e.cmd();
        return "{\"tick\":" + e.tick()
             + ",\"slot\":" + e.slot()
             + ",\"left\":"      + c.left
             + ",\"right\":"     + c.right
             + ",\"jump\":"      + c.jump
             + ",\"dash\":"      + c.dash
             + ",\"attack\":"    + c.attack
             + ",\"throw\":"     + c.throwShuriken
             + ",\"crouch\":"    + c.crouch
             + ",\"ninjutsu\":"  + c.ninjutsu
             + ",\"interact\":"  + c.interact
             + ",\"slowWalk\":"  + c.slowWalk
             + ",\"stanceSwitch\":" + c.stanceSwitch
             + "}";
    }
}
