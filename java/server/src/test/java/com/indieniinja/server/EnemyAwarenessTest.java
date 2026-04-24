package com.indieniinja.server;

import com.indieniinja.content.GameConfig;
import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.EnemyAwarenessState;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEnemy;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * Enemy awareness FSM tests (P1-03A / GDD §3.3).
 *
 * Yang dash emits enough noise to trigger SUSPICIOUS on a nearby enemy.
 * Yin crouch-walk emits no noise and leaves the enemy UNAWARE.
 */
class EnemyAwarenessTest {

    private static GameSimulator buildSim() {
        LevelLayout layout = LevelLayout.buildTestLayout(5L);
        return new GameSimulator(5L, "test_hub", layout);
    }

    /** Player firmly in Yang stance. */
    private static SimPlayer yangPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("yang_p", 0, x, y);
        p.stanceMode   = "yang";
        p.yinYang.yin  = 0.1f;
        p.yinYang.yang = 0.9f;
        return p;
    }

    /** Player firmly in Yin stance. */
    private static SimPlayer yinPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("yin_p", 0, x, y);
        p.stanceMode   = "yin";
        p.yinYang.yin  = 0.9f;
        p.yinYang.yang = 0.1f;
        return p;
    }

    // ── Noise emission constants ───────────────────────────────────────────────

    @Test
    void yangDashNoiseLevelIsAboveYinDash() {
        assertThat(GameConfig.NOISE_YANG_DASH).isGreaterThan(GameConfig.NOISE_YIN_DASH);
    }

    @Test
    void yinCrouchWalkEmitsNoNoise() {
        assertThat(GameConfig.NOISE_YIN_CROUCH_WALK).isEqualTo(0f);
    }

    @Test
    void yangDashRadiusReachesMaxNoiseRange() {
        float expectedRadius = GameConfig.NOISE_YANG_DASH * GameConfig.MAX_NOISE_RADIUS;
        assertThat(expectedRadius).isGreaterThan(100f); // must be significant
    }

    // ── Player noise state ─────────────────────────────────────────────────────

    @Test
    void yangDashSetsNoiseLevelOnPlayer() {
        GameSimulator sim = buildSim();
        SimPlayer yang = yangPlayer(400f, 800f);
        sim.addPlayer(yang);

        InputCommand dash = new InputCommand(0);
        dash.right = true;
        dash.dash  = true;

        sim.step(Map.of(0, dash));

        // noiseLevel is set to NOISE_YANG_DASH during applyPlayerInput, then
        // tickNoise decays it within the same step — use a tolerance of one tick.
        float oneTickDecay = GameConfig.NOISE_DECAY_RATE / 60f;
        assertThat(yang.noiseLevel)
            .as("Yang dash should raise noiseLevel close to NOISE_YANG_DASH")
            .isCloseTo(GameConfig.NOISE_YANG_DASH, within(oneTickDecay + 0.01f));
        assertThat(yang.noiseRadius)
            .as("noiseRadius should be positive after a Yang dash")
            .isGreaterThan(0f);
    }

    @Test
    void noiseLevelDecaysOverTime() {
        GameSimulator sim = buildSim();
        SimPlayer yang = yangPlayer(400f, 800f);
        sim.addPlayer(yang);

        // Emit noise via dash
        InputCommand dash = new InputCommand(0);
        dash.right = true;
        dash.dash  = true;
        sim.step(Map.of(0, dash));

        float afterDash = yang.noiseLevel;

        // Run 30 more idle ticks — noise should decay
        InputCommand idle = new InputCommand(0);
        for (int i = 0; i < 30; i++) sim.step(Map.of(0, idle));

        assertThat(yang.noiseLevel)
            .as("noiseLevel should decay below dash level after 30 idle ticks")
            .isLessThan(afterDash);
    }

    @Test
    void noiseFullyDecaysAfterEnoughTicks() {
        GameSimulator sim = buildSim();
        SimPlayer yang = yangPlayer(400f, 800f);
        sim.addPlayer(yang);

        InputCommand dash = new InputCommand(0);
        dash.right = true;
        dash.dash  = true;
        sim.step(Map.of(0, dash));

        // NOISE_DECAY_RATE = 2.5/s, max level = 0.8 → clears in < 0.8/2.5 = 0.32 s = ~20 ticks
        InputCommand idle = new InputCommand(0);
        for (int i = 0; i < 60; i++) sim.step(Map.of(0, idle));

        assertThat(yang.noiseLevel)
            .as("noiseLevel should be 0 after 60 idle ticks (~1 second)")
            .isEqualTo(0f);
    }

    // ── Enemy awareness transitions ────────────────────────────────────────────

    @Test
    void yangDashAlertingNearbyEnemyMakesItSuspicious() {
        GameSimulator sim = buildSim();

        // Place player near first enemy in the test layout
        List<SimEnemy> enemies = sim.getEnemies();
        assertThat(enemies).isNotEmpty();
        SimEnemy target = enemies.get(0);

        // Position player right next to the enemy, within Yang dash noise radius
        float px = target.physics.x - 60f;
        float py = target.physics.y;
        SimPlayer yang = yangPlayer(px, py);
        sim.addPlayer(yang);

        // Verify enemy starts UNAWARE
        assertThat(target.awarenessState).isEqualTo(EnemyAwarenessState.UNAWARE);

        // Yang dash
        InputCommand dash = new InputCommand(0);
        dash.right = true;
        dash.dash  = true;
        sim.step(Map.of(0, dash));

        // After one tick the awareness update runs; enemy should be SUSPICIOUS or ALERTED
        assertThat(target.awarenessState)
            .as("Yang dash should make nearby enemy at least SUSPICIOUS")
            .isNotEqualTo(EnemyAwarenessState.UNAWARE);
    }

    @Test
    void yinCrouchWalkDoesNotAlertEnemy() {
        GameSimulator sim = buildSim();

        List<SimEnemy> enemies = sim.getEnemies();
        assertThat(enemies).isNotEmpty();
        SimEnemy target = enemies.get(0);

        // Position player next to the enemy
        float px = target.physics.x - 60f;
        float py = target.physics.y;
        SimPlayer yin = yinPlayer(px, py);
        sim.addPlayer(yin);

        // Yin crouch-walk for 30 ticks (0.5 s)
        InputCommand crouchWalk = new InputCommand(0);
        crouchWalk.right  = true;
        crouchWalk.crouch = true;

        for (int i = 0; i < 30; i++) sim.step(Map.of(0, crouchWalk));

        assertThat(target.awarenessState)
            .as("Yin crouch-walk emits zero noise and should not alert the enemy")
            .isEqualTo(EnemyAwarenessState.UNAWARE);
    }
}
