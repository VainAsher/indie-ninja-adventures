package com.indieniinja.network;

import java.util.Map;

/**
 * Decoded wire message: a typed envelope with a payload map.
 * Direct Java equivalent of Python's network/protocol.py Message dataclass.
 */
public record WireMessage(String type, Map<String, Object> payload) {

    /** Convenience accessor — returns null if key absent. */
    public Object get(String key) {
        return payload.get(key);
    }

    public String getString(String key, String fallback) {
        Object v = payload.get(key);
        return v != null ? v.toString() : fallback;
    }

    public int getInt(String key, int fallback) {
        Object v = payload.get(key);
        if (v instanceof Number n) return n.intValue();
        return fallback;
    }

    public long getLong(String key, long fallback) {
        Object v = payload.get(key);
        if (v instanceof Number n) return n.longValue();
        return fallback;
    }

    public boolean getBool(String key, boolean fallback) {
        Object v = payload.get(key);
        if (v instanceof Boolean b) return b;
        return fallback;
    }
}
