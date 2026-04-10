package com.indieniinja.server;

import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * Redis-backed authoritative zone state cache (NET-4).
 *
 * Key format: {@code zone:{hubId}:state}
 * Value:      msgpack WireMessage body (type=WORLD_STATE, payload=WorldSnapshot.toMap())
 * TTL:        300 s (5 minutes)
 *
 * Written on every full snapshot broadcast so reconnecting clients receive
 * authoritative world state immediately instead of waiting up to ~3 s for
 * the next full-snapshot interval.
 *
 * A null pool disables the cache silently; the server operates correctly
 * without Redis, just without the reconnect fast-path.
 */
final class ZoneStateCache {

    private static final int TTL_SECONDS = 300;

    private final JedisPool pool;

    ZoneStateCache(JedisPool pool) {
        this.pool = pool;
    }

    /**
     * Persist a full snapshot map to Redis.
     * No-op if pool is null or encoding/network fails.
     */
    void put(String hubId, Map<String, Object> snapshotMap) {
        if (pool == null) return;
        byte[] key = buildKey(hubId);
        byte[] value;
        try {
            value = encodeMap(snapshotMap);
        } catch (IOException e) {
            return;
        }
        try (Jedis j = pool.getResource()) {
            j.setex(key, TTL_SECONDS, value);
        } catch (Exception ignored) {
            // Redis unavailable — non-fatal; reconnect waits for next full snapshot
        }
    }

    /**
     * Retrieve a cached snapshot map for the given hub.
     *
     * @return the decoded payload map, or {@code null} on a cache miss or error.
     */
    Map<String, Object> get(String hubId) {
        if (pool == null) return null;
        byte[] key = buildKey(hubId);
        try (Jedis j = pool.getResource()) {
            byte[] raw = j.get(key);
            return raw != null ? decodeMap(raw) : null;
        } catch (Exception e) {
            return null;
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static byte[] buildKey(String hubId) {
        return ("zone:" + hubId + ":state").getBytes(StandardCharsets.UTF_8);
    }

    /**
     * Encode a snapshot map as a msgpack WireMessage body.
     * Package-private to allow testing the codec without a Redis instance.
     */
    static byte[] encodeMap(Map<String, Object> map) throws IOException {
        return WireCodec.encodeBody(MessageType.WORLD_STATE, map);
    }

    /**
     * Decode a stored WireMessage body and return the payload map.
     * Package-private to allow testing the codec without a Redis instance.
     */
    static Map<String, Object> decodeMap(byte[] raw) throws IOException {
        return WireCodec.decodeBody(raw).payload();
    }
}
