package com.indieniinja.client.network;

import com.indieniinja.client.GameStateBuffer;
import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireMessage;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ScriptedLossMessageFlowTest {

    @Test
    void gameStateBufferScriptedLossFlagIsSingleUse() {
        GameStateBuffer buffer = new GameStateBuffer();

        buffer.markScriptedLoss();

        assertTrue(buffer.pollScriptedLoss());
        assertFalse(buffer.pollScriptedLoss());
    }

    @Test
    void networkMessageHandlerMarksScriptedLossInBuffer() throws Exception {
        GameStateBuffer buffer = new GameStateBuffer();
        NetworkClientThread client = new NetworkClientThread("127.0.0.1", 7777, buffer);

        Method handleMessage = NetworkClientThread.class
            .getDeclaredMethod("handleMessage", WireMessage.class);
        handleMessage.setAccessible(true);
        handleMessage.invoke(
            client,
            new WireMessage(MessageType.SCRIPTED_LOSS, Map.of(
                "hub_id", "test_hub",
                "event", "siren_scripted_loss"
            ))
        );

        assertTrue(buffer.pollScriptedLoss());
        assertFalse(buffer.pollScriptedLoss());
    }
}
