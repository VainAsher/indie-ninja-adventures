package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * ENG-D2: tick-duration regression gate.
 *
 * Runs 2000 ticks and asserts average wall-clock ms/tick stays under the ceiling
 * defined here.  CI fails if a change regresses sim performance beyond 10x the
 * expected baseline.  The ceiling is intentionally generous (5 ms/tick) so only
 * pathological regressions fail — not noisy CI VMs.
 */
class TickDurationRegressionTest {

    /** Ceiling in milliseconds per tick.  Matches perf_baseline.json. */
    private static final double TICK_MS_CEILING = 5.0;
    private static final int    TICKS           = 2000;

    @Test
    void averageTickDurationUnderCeiling() {
        LevelLayout layout = LevelLayout.buildTestLayout(42L);
        GameSimulator sim  = new GameSimulator(42L, "test_hub", layout);

        SimPlayer player = new SimPlayer("p1", 0, 200f, 800f);
        sim.addPlayer(player);

        InputCommand idle = new InputCommand(0);

        // Warm-up: 200 ticks outside measurement window
        for (int i = 0; i < 200; i++) sim.step(Map.of(0, idle));

        long startNs = System.nanoTime();
        for (int i = 0; i < TICKS; i++) sim.step(Map.of(0, idle));
        long elapsedNs = System.nanoTime() - startNs;

        double avgMs = elapsedNs / 1_000_000.0 / TICKS;
        assertThat(avgMs)
            .as("avg ms/tick (%.3f ms) must be < %.1f ms ceiling", avgMs, TICK_MS_CEILING)
            .isLessThan(TICK_MS_CEILING);
    }
}
