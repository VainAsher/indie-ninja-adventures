package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEcho;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class SimultaneousTimingTest {

    private static final String PID = "st_0";

    // ── Spawn ─────────────────────────────────────────────────────────────────

    @Test
    void stTriggerInteractionSpawnsLoopingNonRecallableEcho() {
        LevelLayout layout = LevelLayout.buildStFixtureLayout(200L, PID);
        GameSimulator sim = new GameSimulator(200L, "test_hub", layout);
        SimPlayer player = new SimPlayer("p1", 0, layout.spawnX, layout.spawnY);
        sim.addPlayer(player);

        // Tick 0: record a jump (gives echo a non-empty replay to loop)
        InputCommand jump = new InputCommand(0);
        jump.jump = true;
        sim.step(Map.of(0, jump));

        // Tick 1: interact with st_trigger_ NPC → echo spawns
        InputCommand interact = new InputCommand(1);
        interact.interact = true;
        sim.step(Map.of(0, interact));

        assertThat(sim.getEchoes()).hasSize(1);
        SimEcho echo = sim.getEchoes().get(0);
        assertThat(echo.looping).isTrue();
        assertThat(echo.recallable).isFalse();
    }

    // ── Sync unlock ───────────────────────────────────────────────────────────

    @Test
    void threeSynchronisedJumpsUnlockStDoor() {
        LevelLayout layout = LevelLayout.buildStFixtureLayout(201L, PID);
        GameSimulator sim = new GameSimulator(201L, "test_hub", layout);
        SimPlayer player = new SimPlayer("p1", 0, layout.spawnX, layout.spawnY);
        sim.addPlayer(player);

        // Tick 0: jump recorded — echo replay will have jump at position 0
        InputCommand jump = new InputCommand(0);
        jump.jump = true;
        sim.step(Map.of(0, jump));

        // Tick 1: interact — echo spawns with [jump, interact] recording
        InputCommand interact = new InputCommand(1);
        interact.interact = true;
        sim.step(Map.of(0, interact));

        // Ticks 2, 4, 6: on every other tick the echo loops back to replay position 0
        // (jump=true), matching the player's simultaneous jump → 3 syncs → door unlocks.
        for (int tick = 2; tick <= 8; tick++) {
            InputCommand cmd = new InputCommand(tick);
            cmd.jump = true;        // player always jumps
            sim.step(Map.of(0, cmd));
            if (sim.getSolvedPuzzles().contains("st_door_" + PID)) break;
        }

        assertThat(sim.getSolvedPuzzles()).contains("st_door_" + PID);
    }

    // ── Early recall ──────────────────────────────────────────────────────────

    @Test
    void earlyRecallOfStEchoSetsFailed() {
        LevelLayout layout = LevelLayout.buildStFixtureLayout(202L, PID);
        GameSimulator sim = new GameSimulator(202L, "test_hub", layout);
        SimPlayer player = new SimPlayer("p1", 0, layout.spawnX, layout.spawnY);
        sim.addPlayer(player);

        // Tick 0: jump, then tick 1: interact → echo spawns
        InputCommand jump = new InputCommand(0);
        jump.jump = true;
        sim.step(Map.of(0, jump));

        InputCommand interact = new InputCommand(1);
        interact.interact = true;
        sim.step(Map.of(0, interact));

        SimEcho echo = sim.getEchoes().get(0);
        assertThat(echo.recallable).isFalse();

        // Attempt early recall before playback completes
        boolean result = echo.recall();

        assertThat(result).isFalse();
        assertThat(echo.failed).isTrue();
        assertThat(echo.active).isFalse();
    }
}
