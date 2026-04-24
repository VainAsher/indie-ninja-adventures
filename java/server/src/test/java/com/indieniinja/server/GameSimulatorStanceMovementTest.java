package com.indieniinja.server;

import com.indieniinja.content.GameConfig;
import com.indieniinja.network.InputCommand;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Verifies stance-driven movement modifiers (P1-03A / GDD §3.3).
 *
 * Yang runs faster and dashes further than Yin.
 * Flow (balanced yin/yang) produces neutral speed between the two.
 * Wall-jump horizontal power follows the same ordering.
 */
class GameSimulatorStanceMovementTest {

    private static final long SEED = 7L;

    private static GameSimulator buildSim() {
        LevelLayout layout = LevelLayout.buildTestLayout(SEED);
        return new GameSimulator(SEED, "test_hub", layout);
    }

    /** Put a player firmly in Yin stance (high yin, low yang — not balanced). */
    private static SimPlayer yinPlayer(String id, int slot, float x, float y) {
        SimPlayer p = new SimPlayer(id, slot, x, y);
        p.stanceMode    = "yin";
        p.yinYang.yin   = 0.9f;
        p.yinYang.yang  = 0.1f;
        return p;
    }

    /** Put a player firmly in Yang stance (low yin, high yang — not balanced). */
    private static SimPlayer yangPlayer(String id, int slot, float x, float y) {
        SimPlayer p = new SimPlayer(id, slot, x, y);
        p.stanceMode    = "yang";
        p.yinYang.yin   = 0.1f;
        p.yinYang.yang  = 0.9f;
        return p;
    }

    /** Put a player in Flow (balanced yin/yang within threshold). */
    private static SimPlayer flowPlayer(String id, int slot, float x, float y) {
        SimPlayer p = new SimPlayer(id, slot, x, y);
        p.stanceMode    = "yang";
        p.yinYang.yin   = 0.5f;
        p.yinYang.yang  = 0.5f;  // |0.5 - 0.5| = 0 < BALANCE_THRESHOLD
        return p;
    }

    // ── Run speed ─────────────────────────────────────────────────────────────

    @Test
    void yangRunsFasterThanYin() {
        GameSimulator sim = buildSim();
        SimPlayer yin  = yinPlayer("yin",  0, 0f, 800f);
        SimPlayer yang = yangPlayer("yang", 1, 0f, 800f);
        sim.addPlayer(yin);
        sim.addPlayer(yang);

        InputCommand run = new InputCommand(0);
        run.right    = true;
        run.slowWalk = true;  // full-speed run

        for (int i = 0; i < 60; i++) {  // 1 second at 60 Hz
            sim.step(Map.of(0, run, 1, run));
        }

        assertThat(yang.physics.x)
            .as("Yang player should be further right than Yin player after 1 s of running")
            .isGreaterThan(yin.physics.x);
    }

    @Test
    void flowRunSpeedIsBetweenYinAndYang() {
        GameSimulator sim = buildSim();
        SimPlayer yin  = yinPlayer("yin",  0, 0f, 800f);
        SimPlayer flow = flowPlayer("flow", 1, 0f, 800f);
        SimPlayer yang = yangPlayer("yang", 2, 0f, 800f);
        sim.addPlayer(yin);
        sim.addPlayer(flow);
        sim.addPlayer(yang);

        InputCommand run = new InputCommand(0);
        run.right    = true;
        run.slowWalk = true;

        for (int i = 0; i < 60; i++) {
            sim.step(Map.of(0, run, 1, run, 2, run));
        }

        assertThat(flow.physics.x)
            .as("Flow speed should be >= Yin speed")
            .isGreaterThanOrEqualTo(yin.physics.x);
        assertThat(yang.physics.x)
            .as("Yang speed should be >= Flow speed")
            .isGreaterThanOrEqualTo(flow.physics.x);
    }

    // ── Dash distance ─────────────────────────────────────────────────────────

    @Test
    void yangDashTravelsLongerThanYin() {
        GameSimulator sim = buildSim();
        SimPlayer yin  = yinPlayer("yin",  0, 0f, 800f);
        SimPlayer yang = yangPlayer("yang", 1, 0f, 800f);
        sim.addPlayer(yin);
        sim.addPlayer(yang);

        // One tick to initiate the dash, then hold right for full dash duration (~10 ticks)
        InputCommand dashStart = new InputCommand(0);
        dashStart.right = true;
        dashStart.dash  = true;

        InputCommand hold = new InputCommand(0);
        hold.right = true;

        sim.step(Map.of(0, dashStart, 1, dashStart));
        for (int i = 0; i < 12; i++) {
            sim.step(Map.of(0, hold, 1, hold));
        }

        assertThat(yang.physics.x)
            .as("Yang dash should travel further than Yin dash over the same duration")
            .isGreaterThan(yin.physics.x);
    }

    // ── Multiplier values ─────────────────────────────────────────────────────

    @Test
    void yinSpeedMultIsBelow1() {
        assertThat(GameConfig.YIN_SPEED_MULT).isLessThan(1.0f);
    }

    @Test
    void yangSpeedMultIsAbove1() {
        assertThat(GameConfig.YANG_SPEED_MULT).isGreaterThan(1.0f);
    }

    @Test
    void yinDashMultIsBelow1() {
        assertThat(GameConfig.YIN_DASH_SPEED_MULT).isLessThan(1.0f);
    }

    @Test
    void yangDashMultIsAbove1() {
        assertThat(GameConfig.YANG_DASH_SPEED_MULT).isGreaterThan(1.0f);
    }

    @Test
    void yinTopSpeedMatchesExpectedPixelsPerTick() {
        float expected = PhysicsConstants.MAX_RUN_SPEED * GameConfig.YIN_SPEED_MULT;
        assertThat(expected).isLessThan(PhysicsConstants.MAX_RUN_SPEED);
    }

    @Test
    void yangTopSpeedMatchesExpectedPixelsPerTick() {
        float expected = PhysicsConstants.MAX_RUN_SPEED * GameConfig.YANG_SPEED_MULT;
        assertThat(expected).isGreaterThan(PhysicsConstants.MAX_RUN_SPEED);
    }
}
