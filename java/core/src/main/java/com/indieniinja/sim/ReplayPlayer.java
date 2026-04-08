package com.indieniinja.sim;

import com.indieniinja.network.InputCommand;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * Replays a recorded input log produced by {@link InputRecorder}.
 *
 * Reads the NDJSON file produced by InputRecorder.stopRecording() and
 * replays the inputs back into the simulation at the correct ticks.
 *
 * Usage:
 *   ReplayPlayer rp = ReplayPlayer.load(path);
 *   long seed = rp.seed();
 *   // each tick:
 *   Map<Integer,InputCommand> inputs = rp.inputsForTick(tick);
 *   simulator.step(inputs, DT);
 *   if (rp.isDone(tick)) break;
 */
public final class ReplayPlayer {

    private final long worldSeed;
    private final long totalEntries;
    /** tick → (slot → InputCommand) */
    private final Map<Long, Map<Integer, InputCommand>> log;

    private ReplayPlayer(long worldSeed, long totalEntries,
                          Map<Long, Map<Integer, InputCommand>> log) {
        this.worldSeed    = worldSeed;
        this.totalEntries = totalEntries;
        this.log          = log;
    }

    public long seed()         { return worldSeed; }
    public long totalEntries() { return totalEntries; }

    /** Returns the inputs for the given tick (may be empty if no inputs recorded). */
    public Map<Integer, InputCommand> inputsForTick(long tick) {
        return log.getOrDefault(tick, Collections.emptyMap());
    }

    /** True when tick exceeds the last recorded tick. */
    public boolean isDone(long tick) {
        if (log.isEmpty()) return true;
        return tick > log.keySet().stream().mapToLong(Long::longValue).max().orElse(0L);
    }

    /** Load a replay file produced by InputRecorder.stopRecording(). */
    public static ReplayPlayer load(Path path) throws IOException {
        long seed = 0L;
        long entries = 0L;
        Map<Long, Map<Integer, InputCommand>> log = new LinkedHashMap<>();

        try (BufferedReader r = Files.newBufferedReader(path)) {
            String line;
            boolean first = true;
            while ((line = r.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;
                if (first) {
                    first = false;
                    seed    = parseLong(line, "seed");
                    entries = parseLong(line, "entries");
                    continue;
                }
                long tick = parseLong(line, "tick");
                int  slot = (int) parseLong(line, "slot");
                InputCommand cmd = parseCommand(line);
                log.computeIfAbsent(tick, k -> new LinkedHashMap<>()).put(slot, cmd);
            }
        }
        return new ReplayPlayer(seed, entries, log);
    }

    // ── Minimal JSON field parsers (no external dependency) ──────────────────

    private static long parseLong(String json, String key) {
        String search = "\"" + key + "\":";
        int idx = json.indexOf(search);
        if (idx < 0) return 0L;
        int start = idx + search.length();
        int end = start;
        while (end < json.length() && (Character.isDigit(json.charAt(end)) || json.charAt(end) == '-'))
            end++;
        try { return Long.parseLong(json.substring(start, end)); } catch (NumberFormatException e) { return 0L; }
    }

    private static boolean parseBool(String json, String key) {
        String search = "\"" + key + "\":";
        int idx = json.indexOf(search);
        if (idx < 0) return false;
        return json.startsWith("true", idx + search.length());
    }

    private static InputCommand parseCommand(String json) {
        InputCommand c = new InputCommand();
        c.left          = parseBool(json, "left");
        c.right         = parseBool(json, "right");
        c.jump          = parseBool(json, "jump");
        c.dash          = parseBool(json, "dash");
        c.attack        = parseBool(json, "attack");
        c.throwShuriken = parseBool(json, "throw");
        c.crouch        = parseBool(json, "crouch");
        c.ninjutsu      = parseBool(json, "ninjutsu");
        c.interact      = parseBool(json, "interact");
        c.slowWalk      = parseBool(json, "slowWalk");
        return c;
    }
}
