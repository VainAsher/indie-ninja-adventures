package com.indieniinja.server;

import com.indieniinja.content.GameConfig;
import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEcho;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * Echo Art stance variant tests (P1-03A / GDD §3.3).
 *
 * Silent Echo (Yin): no noise emitted on spawn.
 * Riot Echo (Yang): emits NOISE_ECHO_RIOT noise on spawn.
 * Resonant Echo (Flow): no noise, resolved from balanced stance.
 */
class SimEchoTypeTest {

    private static GameSimulator buildSim() {
        LevelLayout layout = LevelLayout.buildTestLayout(9L);
        return new GameSimulator(9L, "test_hub", layout);
    }

    private static SimPlayer yinPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("yin_p", 0, x, y);
        p.stanceMode   = "yin";
        p.yinYang.yin  = 0.9f;
        p.yinYang.yang = 0.1f;
        return p;
    }

    private static SimPlayer yangPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("yang_p", 0, x, y);
        p.stanceMode   = "yang";
        p.yinYang.yin  = 0.1f;
        p.yinYang.yang = 0.9f;
        return p;
    }

    private static SimPlayer flowPlayer(float x, float y) {
        SimPlayer p = new SimPlayer("flow_p", 0, x, y);
        p.stanceMode   = "yin";
        p.yinYang.yin  = 0.5f;
        p.yinYang.yang = 0.5f;
        p.lastMeaningfulActionTimer = com.indieniinja.content.GameConfig.FLOW_RECENCY_WINDOW;
        return p;
    }

    /** Run a few ticks of input to populate the echo recorder. */
    private static void recordInputs(GameSimulator sim, int slot) {
        InputCommand move = new InputCommand(slot);
        move.right = true;
        for (int i = 0; i < 5; i++) sim.step(Map.of(slot, move));
    }

    // ── GameConfig constant sanity ────────────────────────────────────────────

    @Test
    void riotNoiseIsSignificant() {
        assertThat(GameConfig.NOISE_ECHO_RIOT).isGreaterThan(0.3f);
    }

    // ── Echo type resolution ──────────────────────────────────────────────────

    @Test
    void yinPlayerSpawnsSilentEcho() {
        GameSimulator sim = buildSim();
        SimPlayer yin = yinPlayer(400f, 800f);
        sim.addPlayer(yin);
        recordInputs(sim, 0);

        SimEcho echo = sim.spawnEchoFromPlayer(0, true);

        assertThat(echo).isNotNull();
        assertThat(echo.echoType)
            .as("Yin player should spawn a Silent echo")
            .isEqualTo("silent");
    }

    @Test
    void yangPlayerSpawnsRiotEcho() {
        GameSimulator sim = buildSim();
        SimPlayer yang = yangPlayer(400f, 800f);
        sim.addPlayer(yang);
        recordInputs(sim, 0);

        SimEcho echo = sim.spawnEchoFromPlayer(0, true);

        assertThat(echo).isNotNull();
        assertThat(echo.echoType)
            .as("Yang player should spawn a Riot echo")
            .isEqualTo("riot");
    }

    @Test
    void flowPlayerSpawnsResonantEcho() {
        GameSimulator sim = buildSim();
        SimPlayer flow = flowPlayer(400f, 800f);
        sim.addPlayer(flow);
        recordInputs(sim, 0);

        SimEcho echo = sim.spawnEchoFromPlayer(0, true);

        assertThat(echo).isNotNull();
        assertThat(echo.echoType)
            .as("Flow player should spawn a Resonant echo")
            .isEqualTo("resonant");
    }

    // ── Noise emission on spawn ───────────────────────────────────────────────

    @Test
    void riotEchoEmitsNoiseOnSpawn() {
        GameSimulator sim = buildSim();
        SimPlayer yang = yangPlayer(400f, 800f);
        sim.addPlayer(yang);
        recordInputs(sim, 0);

        float noiseBefore = yang.noiseLevel;
        sim.spawnEchoFromPlayer(0, true);

        assertThat(yang.noiseLevel)
            .as("Riot Echo should raise player noiseLevel on spawn")
            .isGreaterThan(noiseBefore);
        assertThat(yang.noiseLevel)
            .as("Riot Echo noise should be close to NOISE_ECHO_RIOT")
            .isCloseTo(GameConfig.NOISE_ECHO_RIOT, within(0.01f));
    }

    @Test
    void silentEchoDoesNotEmitNoise() {
        GameSimulator sim = buildSim();
        SimPlayer yin = yinPlayer(400f, 800f);
        sim.addPlayer(yin);
        recordInputs(sim, 0);

        // Ensure noise is 0 before spawn
        yin.noiseLevel = 0f;
        sim.spawnEchoFromPlayer(0, true);

        assertThat(yin.noiseLevel)
            .as("Silent Echo should not emit noise")
            .isEqualTo(0f);
    }

    // ── Wire format round-trip ────────────────────────────────────────────────

    @Test
    void echoStateWireRoundTripPreservesEchoType() {
        com.indieniinja.network.EchoState es = new com.indieniinja.network.EchoState();
        es.echoType = "riot";

        com.indieniinja.network.EchoState rt =
            com.indieniinja.network.EchoState.fromMap(es.toMap());

        assertThat(rt).isNotNull();
        assertThat(rt.echoType).isEqualTo("riot");
    }
}
