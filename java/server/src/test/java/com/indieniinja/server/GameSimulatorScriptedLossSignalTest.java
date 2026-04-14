package com.indieniinja.server;

import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import com.indieniinja.world.HubState;
import com.indieniinja.world.HubStateMachine;
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

    @Test
    void scriptedLossAlsoCollapsesHubAndDrainsPlayerYinYang() throws Exception {
        GameSimulator sim = new GameSimulator(99L, "test_hub", LevelLayout.buildTestLayout(99L));
        HubStateMachine hub = new HubStateMachine("central_hub");
        sim.setHub(hub);

        SimPlayer player = new SimPlayer("p1", 0, 256f, 256f);
        player.yinYang.yin = 0.77f;
        player.yinYang.yang = 0.83f;
        sim.addPlayer(player);

        Method trigger = GameSimulator.class.getDeclaredMethod("triggerSirenScriptedLoss");
        trigger.setAccessible(true);
        trigger.invoke(sim);

        assertThat(player.yinYang.yin).isZero();
        assertThat(player.yinYang.yang).isZero();
        assertThat(hub.getState()).isEqualTo(HubState.EMPTY);
    }
}
