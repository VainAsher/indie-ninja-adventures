package com.indieniinja.server;

import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.assertj.core.api.Assertions.assertThat;

class GameSimulatorScriptedLossSignalTest {

    @Test
    void scriptedLossDrainIsSingleUseAfterTrigger() throws Exception {
        GameSimulator sim = new GameSimulator(42L, "test_hub", LevelLayout.buildTestLayout(42L));

        Method trigger = GameSimulator.class.getDeclaredMethod("triggerSirenScriptedLoss");
        trigger.setAccessible(true);
        trigger.invoke(sim);

        assertThat(sim.drainPendingScriptedLoss()).isTrue();
        assertThat(sim.drainPendingScriptedLoss()).isFalse();
    }
}
