package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEcho;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AsymmetricAbilityLockTest {

    private static final String PID = "aal_0";

    // ── Spawn ─────────────────────────────────────────────────────────────────

    @Test
    void aalEchoAutoSpawnsLoopingOnRoomLoad() {
        GameSimulator sim = new GameSimulator(123L, "test_hub",
            LevelLayout.buildAalFixtureLayout(123L, PID));

        assertThat(sim.getEchoes()).hasSize(1);
        SimEcho echo = sim.getEchoes().get(0);
        assertThat(echo.echoId).isEqualTo("aal_echo_" + PID);
        assertThat(echo.looping).isTrue();
        assertThat(echo.active).isTrue();
        assertThat(echo.completed).isFalse();
    }

    // ── Proximity gate ────────────────────────────────────────────────────────

    @Test
    void jumpWithinProximityUnlocksAalDoor() {
        LevelLayout layout = LevelLayout.buildAalFixtureLayout(124L, PID);
        GameSimulator sim = new GameSimulator(124L, "test_hub", layout);

        SimEcho echo = sim.getEchoes().get(0);
        // Place player directly at echo position — well within 96px proximity
        SimPlayer player = new SimPlayer("p1", 0, echo.x, echo.y);
        sim.addPlayer(player);

        InputCommand jump = new InputCommand(0);
        jump.jump = true;
        sim.step(Map.of(0, jump));

        assertThat(sim.getSolvedPuzzles()).contains("aal_door_" + PID);
    }

    @Test
    void jumpOutOfProximityDoesNotUnlockAalDoor() {
        LevelLayout layout = LevelLayout.buildAalFixtureLayout(125L, PID);
        GameSimulator sim = new GameSimulator(125L, "test_hub", layout);

        SimEcho echo = sim.getEchoes().get(0);
        // Place player 200px away from echo — beyond the 96px threshold
        SimPlayer player = new SimPlayer("p1", 0, echo.x + 200f, echo.y);
        sim.addPlayer(player);

        InputCommand jump = new InputCommand(0);
        jump.jump = true;
        sim.step(Map.of(0, jump));

        assertThat(sim.getSolvedPuzzles()).doesNotContain("aal_door_" + PID);
    }

    // ── Looping ───────────────────────────────────────────────────────────────

    @Test
    void aalEchoRemainsActiveAfterReplayExhausted() {
        GameSimulator sim = new GameSimulator(126L, "test_hub",
            LevelLayout.buildAalFixtureLayout(126L, PID));

        SimEcho echo = sim.getEchoes().get(0);

        // Step 20 ticks — the one-frame idle replay loops many times
        for (int i = 0; i < 20; i++) {
            sim.step(Map.of());
        }

        // Looping echo must stay active and never reach the completed state
        assertThat(echo.active).isTrue();
        assertThat(echo.failed).isFalse();
        assertThat(echo.completed).isFalse();
    }
}
