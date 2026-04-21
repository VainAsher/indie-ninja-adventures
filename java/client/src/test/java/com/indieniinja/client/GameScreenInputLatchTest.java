package com.indieniinja.client;

import com.indieniinja.network.InputCommand;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GameScreenInputLatchTest {

    @Test
    void oneShotActionsAreLatchedUntilConsumed() throws Exception {
        GameScreen screen = new GameScreen(null, "localhost", 7777, "solo");

        InputCommand quickTap = new InputCommand();
        quickTap.stanceSwitch = true;
        quickTap.left = true;
        latch(screen, quickTap);

        // Simulate later render frames with no new stance press before physics catches up.
        InputCommand laterFrame = new InputCommand();
        laterFrame.left = true;
        latch(screen, laterFrame);

        InputCommand consumed = consume(screen);
        assertTrue(consumed.stanceSwitch, "stance switch tap should survive until next sim tick");
        assertTrue(consumed.left, "held movement state should reflect latest sampled frame");
    }

    @Test
    void consumingClearsOneShotFlagsButKeepsHeldState() throws Exception {
        GameScreen screen = new GameScreen(null, "localhost", 7777, "solo");

        InputCommand frame = new InputCommand();
        frame.left = true;
        frame.stanceSwitch = true;
        latch(screen, frame);

        InputCommand firstTick = consume(screen);
        InputCommand secondTick = consume(screen);

        assertTrue(firstTick.stanceSwitch);
        assertFalse(secondTick.stanceSwitch, "stance switch is edge-triggered and should fire once per press");
        assertTrue(secondTick.left, "held direction should remain active across ticks");
    }

    private static void latch(GameScreen screen, InputCommand cmd) throws Exception {
        Method m = GameScreen.class.getDeclaredMethod("latchRealtimeInput", InputCommand.class);
        m.setAccessible(true);
        m.invoke(screen, cmd);
    }

    private static InputCommand consume(GameScreen screen) throws Exception {
        Method m = GameScreen.class.getDeclaredMethod("consumeLatchedRealtimeInput");
        m.setAccessible(true);
        return (InputCommand) m.invoke(screen);
    }
}
