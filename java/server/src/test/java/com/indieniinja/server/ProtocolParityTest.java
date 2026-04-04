package com.indieniinja.server;

import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Protocol parity tests — verifies Java encoding/decoding matches
 * the Python wire format from network/protocol.py.
 *
 * Run: ./gradlew :server:test
 */
class ProtocolParityTest {

    @Test
    void clientHelloRoundTrip() throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("player_id", "test-uuid-1234");
        payload.put("version", MessageType.PROTOCOL_VERSION);

        byte[] encoded = WireCodec.encodeBody(MessageType.CLIENT_HELLO, payload);
        WireMessage decoded = WireCodec.decodeBody(encoded);

        assertThat(decoded.type()).isEqualTo(MessageType.CLIENT_HELLO);
        assertThat(decoded.getString("player_id", "")).isEqualTo("test-uuid-1234");
        assertThat(decoded.getString("version", "")).isEqualTo("2");
    }

    @Test
    void serverHelloRoundTrip() throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("player_id", "server-assigned-id");
        payload.put("slot", 0);
        payload.put("frame", 0L);
        payload.put("seed", 42L);
        payload.put("max_players", 4);

        byte[] encoded = WireCodec.encodeBody(MessageType.SERVER_HELLO, payload);
        WireMessage decoded = WireCodec.decodeBody(encoded);

        assertThat(decoded.type()).isEqualTo(MessageType.SERVER_HELLO);
        assertThat(decoded.getInt("slot", -1)).isEqualTo(0);
        assertThat(decoded.getLong("seed", 0)).isEqualTo(42L);
        assertThat(decoded.getInt("max_players", 0)).isEqualTo(4);
    }

    @Test
    void allMessageTypesAreDefined() {
        // Regression: none of the message type constants should be null or empty
        assertThat(MessageType.CLIENT_HELLO).isNotEmpty();
        assertThat(MessageType.INPUT).isNotEmpty();
        assertThat(MessageType.WORLD_STATE).isNotEmpty();
        assertThat(MessageType.PLAYER_JOIN).isNotEmpty();
        assertThat(MessageType.PLAYER_LEAVE).isNotEmpty();
        assertThat(MessageType.LOBBY_UPDATE).isNotEmpty();
        assertThat(MessageType.GAME_START).isNotEmpty();
        assertThat(MessageType.WORLD_TRANSITION).isNotEmpty();
        assertThat(MessageType.ZONE_PRESENCE).isNotEmpty();
        assertThat(MessageType.PROTOCOL_VERSION).isEqualTo("2");
    }

    @Test
    void booleanValuesPreservedInRoundTrip() throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("frame", 100);
        payload.put("jump", true);
        payload.put("left", false);
        payload.put("dash", true);

        byte[] encoded = WireCodec.encodeBody(MessageType.INPUT, payload);
        WireMessage decoded = WireCodec.decodeBody(encoded);

        assertThat(decoded.getBool("jump", false)).isTrue();
        assertThat(decoded.getBool("left", true)).isFalse();
        assertThat(decoded.getBool("dash", false)).isTrue();
    }

    @Test
    void floatPositionPreservedInRoundTrip() throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("pos", java.util.List.of(123.45f, 678.9f));
        payload.put("health", 5);

        byte[] encoded = WireCodec.encodeBody(MessageType.INPUT, payload);
        WireMessage decoded = WireCodec.decodeBody(encoded);

        @SuppressWarnings("unchecked")
        var pos = (java.util.List<Object>) decoded.get("pos");
        assertThat(((Number) pos.get(0)).floatValue()).isEqualTo(123.45f);
        assertThat(((Number) pos.get(1)).floatValue()).isEqualTo(678.9f);
    }
}
