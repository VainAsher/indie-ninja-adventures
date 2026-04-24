package com.indieniinja.server;

import com.indieniinja.content.GameConfig;
import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Flow recency gate tests (P1-03A / GDD §3.3).
 *
 * Flow mode requires two simultaneous conditions:
 *   1. |yin − yang| < FLOW_BALANCE_THRESHOLD
 *   2. A meaningful action (dash, attack, shuriken, teleport) within the last
 *      FLOW_RECENCY_WINDOW seconds.
 *
 * Idle drift alone — even when perfectly balanced — must NOT grant Flow.
 */
class FlowRecencyTest {

    private static GameSimulator buildSim() {
        LevelLayout layout = LevelLayout.buildTestLayout(11L);
        return new GameSimulator(11L, "test_hub", layout);
    }

    /** Balanced player who has done nothing — no recent action. */
    private static SimPlayer idleBalancedPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("idle_p", 0, x, y);
        p.stanceMode   = "yin";
        p.yinYang.yin  = 0.5f;
        p.yinYang.yang = 0.5f;
        // lastMeaningfulActionTimer starts at 0 — never stamped
        return p;
    }

    /** Balanced player who just performed a meaningful action. */
    private static SimPlayer activeBalancedPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("active_p", 0, x, y);
        p.stanceMode   = "yin";
        p.yinYang.yin  = 0.5f;
        p.yinYang.yang = 0.5f;
        p.lastMeaningfulActionTimer = GameConfig.FLOW_RECENCY_WINDOW;
        return p;
    }

    // ── Flow recency constant sanity ──────────────────────────────────────────

    @Test
    void flowRecencyWindowIsPositive() {
        assertThat(GameConfig.FLOW_RECENCY_WINDOW).isGreaterThan(0f);
    }

    // ── Idle drift does not grant Flow ────────────────────────────────────────

    @Test
    void idleBalancedPlayerIsNotInFlowMode() {
        GameSimulator sim = buildSim();
        SimPlayer p = idleBalancedPlayer(400f, 800f);
        sim.addPlayer(p);

        // Run 60 idle ticks — balance stays near 0.5/0.5 but no action fires
        InputCommand idle = new InputCommand(0);
        for (int i = 0; i < 60; i++) sim.step(Map.of(0, idle));

        // flowMode in snapshot should be false — no recent action
        var snap = sim.getSnapshot(0L);
        var ps = snap.players.stream()
            .filter(x -> x.slot == 0)
            .findFirst().orElseThrow();

        assertThat(ps.flowMode)
            .as("Idle balanced player should NOT enter Flow mode")
            .isFalse();
    }

    // ── Dash stamps recency timer ─────────────────────────────────────────────

    @Test
    void dashStampsRecencyTimerAndEnablesFlow() {
        GameSimulator sim = buildSim();
        SimPlayer p = idleBalancedPlayer(400f, 800f);
        sim.addPlayer(p);

        InputCommand dash = new InputCommand(0);
        dash.right = true;
        dash.dash  = true;
        sim.step(Map.of(0, dash));

        assertThat(p.lastMeaningfulActionTimer)
            .as("Dash should stamp lastMeaningfulActionTimer")
            .isGreaterThan(0f);
    }

    @Test
    void recencyTimerDecaysToZeroAfterWindow() {
        GameSimulator sim = buildSim();
        SimPlayer p = idleBalancedPlayer(400f, 800f);
        p.lastMeaningfulActionTimer = GameConfig.FLOW_RECENCY_WINDOW;
        sim.addPlayer(p);

        // Run just over FLOW_RECENCY_WINDOW seconds worth of idle ticks
        int ticks = (int) Math.ceil(GameConfig.FLOW_RECENCY_WINDOW * 60) + 5;
        InputCommand idle = new InputCommand(0);
        for (int i = 0; i < ticks; i++) sim.step(Map.of(0, idle));

        assertThat(p.lastMeaningfulActionTimer)
            .as("Recency timer should decay to 0 after window elapses")
            .isEqualTo(0f);
    }

    @Test
    void flowModeActiveImmediatelyAfterDashWhenBalanced() {
        GameSimulator sim = buildSim();
        SimPlayer p = idleBalancedPlayer(400f, 800f);
        sim.addPlayer(p);

        InputCommand dash = new InputCommand(0);
        dash.right = true;
        dash.dash  = true;
        sim.step(Map.of(0, dash));

        var snap = sim.getSnapshot(0L);
        var ps = snap.players.stream()
            .filter(x -> x.slot == 0)
            .findFirst().orElseThrow();

        assertThat(ps.flowMode)
            .as("Balanced player who just dashed should be in Flow mode")
            .isTrue();
    }
}
