package com.indieniinja.network;

import org.msgpack.core.MessageBufferPacker;
import org.msgpack.core.MessagePack;
import org.msgpack.core.MessageUnpacker;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Low-level msgpack wire codec matching Python's network/protocol.py.
 *
 * Wire format:
 *   [4 bytes big-endian uint32: payload length][msgpack body]
 *
 * Body is a msgpack map with exactly two keys (in order):
 *   "type"    → String (one of MessageType constants)
 *   "payload" → Map<String, Object>
 *
 * Netty pipeline handles the length-field framing; this class handles
 * the msgpack body encode/decode only.
 */
public final class WireCodec {

    public static final int  HEADER_SIZE       = 4;
    public static final int  MAX_MESSAGE_BYTES = 1_048_576;

    private WireCodec() {}

    /**
     * Encode a typed message to the raw msgpack body bytes (no length header).
     * Netty's LengthFieldPrepender adds the 4-byte header.
     */
    public static byte[] encodeBody(String msgType, Map<String, Object> payload) throws IOException {
        try (MessageBufferPacker packer = MessagePack.newDefaultBufferPacker()) {
            packer.packMapHeader(2);
            packer.packString("type");
            packer.packString(msgType);
            packer.packString("payload");
            packMap(packer, payload);
            return packer.toByteArray();
        }
    }

    /**
     * Decode a raw msgpack body (no length header) into a WireMessage.
     */
    public static WireMessage decodeBody(byte[] bytes) throws IOException {
        try (MessageUnpacker unpacker = MessagePack.newDefaultUnpacker(bytes)) {
            int mapSize = unpacker.unpackMapHeader();
            String type = null;
            Map<String, Object> payload = new LinkedHashMap<>();
            for (int i = 0; i < mapSize; i++) {
                String key = unpacker.unpackString();
                if ("type".equals(key)) {
                    type = unpacker.unpackString();
                } else if ("payload".equals(key)) {
                    payload = unpackMap(unpacker);
                } else {
                    unpacker.skipValue();
                }
            }
            if (type == null) throw new IOException("Missing 'type' field in message");
            return new WireMessage(type, payload);
        }
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    @SuppressWarnings("unchecked")
    public static void packMap(MessageBufferPacker p, Map<String, Object> map) throws IOException {
        p.packMapHeader(map.size());
        for (Map.Entry<String, Object> e : map.entrySet()) {
            p.packString(e.getKey());
            packValue(p, e.getValue());
        }
    }

    @SuppressWarnings("unchecked")
    static void packValue(MessageBufferPacker p, Object v) throws IOException {
        if (v == null)            { p.packNil(); }
        else if (v instanceof Boolean b) { if (b) p.packBoolean(true); else p.packBoolean(false); }
        else if (v instanceof Integer i) { p.packInt(i); }
        else if (v instanceof Long l)    { p.packLong(l); }
        else if (v instanceof Float f)   { p.packFloat(f); }
        else if (v instanceof Double d)  { p.packDouble(d); }
        else if (v instanceof String s)  { p.packString(s); }
        else if (v instanceof java.util.List<?> list) {
            p.packArrayHeader(list.size());
            for (Object item : list) packValue(p, item);
        } else if (v instanceof Map<?,?> m) {
            packMap(p, (Map<String, Object>) m);
        } else {
            p.packString(v.toString());
        }
    }

    public static Map<String, Object> unpackMap(MessageUnpacker u) throws IOException {
        int size = u.unpackMapHeader();
        Map<String, Object> map = new LinkedHashMap<>(size * 2);
        for (int i = 0; i < size; i++) {
            String key = u.unpackString();
            map.put(key, unpackValue(u));
        }
        return map;
    }

    static Object unpackValue(MessageUnpacker u) throws IOException {
        var fmt = u.getNextFormat();
        return switch (fmt.getValueType()) {
            case NIL     -> { u.unpackNil(); yield null; }
            case BOOLEAN -> u.unpackBoolean();
            case INTEGER -> u.unpackLong();
            case FLOAT   -> u.unpackDouble();
            case STRING  -> u.unpackString();
            case MAP     -> unpackMap(u);
            case ARRAY   -> {
                int len = u.unpackArrayHeader();
                var list = new java.util.ArrayList<>(len);
                for (int i = 0; i < len; i++) list.add(unpackValue(u));
                yield list;
            }
            default -> { u.skipValue(); yield null; }
        };
    }
}
