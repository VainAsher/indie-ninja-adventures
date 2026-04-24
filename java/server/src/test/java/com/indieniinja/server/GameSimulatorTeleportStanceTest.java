package com.indieniinja.server;

import com.indieniinja.content.GameConfig;
import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.EnemyAIState;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEnemy;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Phase Teleport stance variant tests (P1-03A / GDD §3.3).
 *
 * ShadowStep (Yin): silent, no AoE, longer cooldown than base.
 * ThunderStep (Yang): loud, AoE stuns nearby enemies, longer cooldown.
 * HarmonicStep (Flow): neutral, no AoE, shorter cooldown.
 */
class GameSimulatorTeleportStanceTest {

    private static GameSimulator buildSim() {
        LevelLayout layout = LevelLayout.buildTestLayout(7L);
        return new GameSimulator(7L, "test_hub", layout);
    }

    /** Player firmly in Yin stance. */
    private static SimPlayer yinPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("yin_p", 0, x, y);
        p.stanceMode   = "yin";
        p.yinYang.yin  = 0.9f;
        p.yinYang.yang = 0.1f;
        return p;
    }

    /** Player firmly in Yang stance. */
    private static SimPlayer yangPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("yang_p", 0, x, y);
        p.stanceMode   = "yang";
        p.yinYang.yin  = 0.1f;
        p.yinYang.yang = 0.9f;
        return p;
    }

    /** Player in Flow (balanced). */
    private static SimPlayer flowPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("flow_p", 0, x, y);
        p.stanceMode   = "yin";  // dominant stance doesn't matter when balanced
        p.yinYang.yin  = 0.5f;
        p.yinYang.yang = 0.5f;
        return p;
    }

    private static InputCommand teleportPress(int slot) {
        InputCommand cmd = new InputCommand(slot);
        cmd.teleport = true;
        return cmd;
    }

    // ── GameConfig constant sanity ────────────────────────────────────────────

    @Test
    void thunderCooldownMultIsAboveBase() {
        assertThat(GameConfig.THUNDER_STEP_COOLDOWN_MULT).isGreaterThan(1.0f);
    }

    @Test
    void harmonicCooldownMultIsBelowBase() {
        assertThat(GameConfig.HARMONIC_STEP_COOLDOWN_MULT).isLessThan(1.0f);
    }

    @Test
    void thunderStunRadiusIsPositive() {
        assertThat(GameConfig.THUNDER_STEP_STUN_RADIUS).isGreaterThan(0f);
    }

    @Test
    void thunderNoiseIsSignificant() {
        assertThat(GameConfig.THUNDER_STEP_NOISE).isGreaterThan(0.3f);
    }

    // ── Teleport type resolution ──────────────────────────────────────────────

    @Test
    void yinPlayerResolvesShadowStep() {
        GameSimulator sim = buildSim();
        SimPlayer yin = yinPlayer(400f, 800f);
        sim.addPlayer(yin);

        sim.step(Map.of(0, teleportPress(0)));

        assertThat(yin.teleportType)
            .as("Yin player should resolve ShadowStep")
            .isEqualTo("shadow");
    }

    @Test
    void yangPlayerResolvesThunderStep() {
        GameSimulator sim = buildSim();
        SimPlayer yang = yangPlayer(400f, 800f);
        sim.addPlayer(yang);

        sim.step(Map.of(0, teleportPress(0)));

        assertThat(yang.teleportType)
            .as("Yang player should resolve ThunderStep")
            .isEqualTo("thunder");
    }

    @Test
    void flowPlayerResolvesHarmonicStep() {
        GameSimulator sim = buildSim();
        SimPlayer flow = flowPlayer(400f, 800f);
        sim.addPlayer(flow);

        sim.step(Map.of(0, teleportPress(0)));

        assertThat(flow.teleportType)
            .as("Flow player should resolve HarmonicStep")
            .isEqualTo("harmonic");
    }

    // ── ThunderStep AoE stun ──────────────────────────────────────────────────

    @Test
    void thunderStepStudsNearbyEnemy() {
        GameSimulator sim = buildSim();

        List<SimEnemy> enemies = sim.getEnemies();
        assertThat(enemies).isNotEmpty();
        SimEnemy target = enemies.get(0);

        // Place Yang player at enemy position — teleport cursor will start there,
        // warp is blocked by self-position, so use a 1-px offset to land next to it.
        float px = target.physics.x - 10f;
        float py = target.physics.y;
        SimPlayer yang = yangPlayer(px, py);
        sim.addPlayer(yang);

        // Press and hold teleport for TELEPORT_PHASE_TIME ticks to trigger warp
        int phaseTicks = (int) Math.ceil(SimPlayer.TELEPORT_PHASE_TIME * 60) + 2;
        InputCommand press = teleportPress(0);
        sim.step(Map.of(0, press));
        // Hold: timer counts down; on expiry warp fires and arrival effects apply
        InputCommand hold = teleportPress(0);
        for (int i = 1; i < phaseTicks; i++) sim.step(Map.of(0, hold));

        assertThat(target.aiState)
            .as("ThunderStep should stun a nearby enemy")
            .isEqualTo(EnemyAIState.STUNNED);
    }

    @Test
    void shadowStepDoesNotStunEnemy() {
        GameSimulator sim = buildSim();

        List<SimEnemy> enemies = sim.getEnemies();
        assertThat(enemies).isNotEmpty();
        SimEnemy target = enemies.get(0);

        float px = target.physics.x - 10f;
        float py = target.physics.y;
        SimPlayer yin = yinPlayer(px, py);
        sim.addPlayer(yin);

        int phaseTicks = (int) Math.ceil(SimPlayer.TELEPORT_PHASE_TIME * 60) + 2;
        sim.step(Map.of(0, teleportPress(0)));
        for (int i = 1; i < phaseTicks; i++) sim.step(Map.of(0, teleportPress(0)));

        assertThat(target.aiState)
            .as("ShadowStep should NOT stun nearby enemies")
            .isNotEqualTo(EnemyAIState.STUNNED);
    }

    // ── Cooldown scaling ──────────────────────────────────────────────────────

    @Test
    void thunderStepHasLongerCooldownThanShadowStep() {
        float thunderCd = SimPlayer.TELEPORT_COOLDOWN * GameConfig.THUNDER_STEP_COOLDOWN_MULT;
        float shadowCd  = SimPlayer.TELEPORT_COOLDOWN * GameConfig.SHADOW_STEP_COOLDOWN_MULT;
        assertThat(thunderCd).isGreaterThan(shadowCd);
    }

    @Test
    void harmonicStepHasShortestCooldown() {
        float harmonicCd = SimPlayer.TELEPORT_COOLDOWN * GameConfig.HARMONIC_STEP_COOLDOWN_MULT;
        float shadowCd   = SimPlayer.TELEPORT_COOLDOWN * GameConfig.SHADOW_STEP_COOLDOWN_MULT;
        float thunderCd  = SimPlayer.TELEPORT_COOLDOWN * GameConfig.THUNDER_STEP_COOLDOWN_MULT;
        assertThat(harmonicCd).isLessThan(shadowCd);
        assertThat(harmonicCd).isLessThan(thunderCd);
    }
}
