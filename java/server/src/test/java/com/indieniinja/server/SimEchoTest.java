package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.ReplayPlayer;
import com.indieniinja.sim.SimEcho;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class SimEchoTest {

    @Test
    void nonRecallableEchoFailsIfRecalledEarly() {
        InputCommand c0 = new InputCommand(0);
        c0.right = true;
        InputCommand c1 = new InputCommand(1);
        c1.right = true;

        ReplayPlayer replay = ReplayPlayer.fromInputSequence(7L, 0, List.of(c0, c1));
        SimEcho echo = new SimEcho("echo_0", 0, 0f, 0f, replay, false);

        echo.step();
        boolean recallOk = echo.recall();

        assertThat(recallOk).isFalse();
        assertThat(echo.failed).isTrue();
        assertThat(echo.active).isFalse();
        assertThat(echo.completed).isFalse();
    }

    @Test
    void echoCompletesPlaybackThenSafeRecallSucceeds() {
        InputCommand c0 = new InputCommand(0);
        c0.left = true;
        InputCommand c1 = new InputCommand(1);
        c1.right = true;

        ReplayPlayer replay = ReplayPlayer.fromInputSequence(7L, 0, List.of(c0, c1));
        SimEcho echo = new SimEcho("echo_1", 0, 0f, 0f, replay, false);

        echo.step();
        assertThat(echo.facing).isEqualTo(-1);
        echo.step();

        assertThat(echo.completed).isTrue();
        assertThat(echo.active).isFalse();
        assertThat(echo.currentInput().right).isTrue();
        assertThat(echo.recall()).isTrue();
    }

    @Test
    void gameSimulatorSpawnsEchoFromRecorderAndTicksIt() {
        GameSimulator sim = new GameSimulator(42L, "test_hub", LevelLayout.buildTestLayout(42L));
        SimPlayer p = new SimPlayer("p1", 0, 200f, 800f);
        sim.addPlayer(p);

        InputCommand moveRight = new InputCommand(0);
        moveRight.right = true;
        for (int i = 0; i < 4; i++) {
            sim.step(Map.of(0, moveRight));
        }

        SimEcho echo = sim.spawnEchoFromPlayer(0, true);
        assertThat(echo).isNotNull();
        assertThat(sim.getEchoes()).contains(echo);
        assertThat(echo.ticksPlayed()).isEqualTo(0);

        sim.step(Map.of());

        assertThat(echo.ticksPlayed()).isEqualTo(1);
        assertThat(echo.currentInput().right).isTrue();
    }
}
