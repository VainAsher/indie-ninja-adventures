package com.indieniinja.procgen.room;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.validation.ValidationResult;

import java.util.ArrayList;
import java.util.List;

public final class RoomGenerationReport {
    public final long       seed;
    public final RoomIntent intent;
    public final List<String> passLog = new ArrayList<>();
    public final List<String> errors  = new ArrayList<>();

    public ValidationResult validation;

    public RoomGenerationReport(long seed, RoomIntent intent) {
        this.seed   = seed;
        this.intent = intent;
    }

    public void logPass(String name, boolean ok) {
        passLog.add(String.format("PASS: %-30s %s", name, ok ? "✓" : "✗"));
    }

    public boolean hasErrors() {
        return !errors.isEmpty();
    }
}
