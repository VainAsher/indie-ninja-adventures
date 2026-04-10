package com.indieniinja.server;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.indieniinja.sim.ItemDatabase.ItemDef;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * Redis cache for the item definition list (INV-6).
 *
 * Key:   {@code items:all}  (no TTL — invalidated explicitly on admin item update)
 * Value: JSON array of ItemDef fields, one object per item.
 *
 * Cache-aside pattern:
 * <pre>
 *   List&lt;ItemDef&gt; defs = itemCache.getAll();
 *   if (defs == null) {
 *       defs = loadFromDb();
 *       itemCache.putAll(defs);
 *   }
 * </pre>
 *
 * Call {@link #invalidate()} whenever an item is added/modified via the admin path
 * so the next read reloads from PostgreSQL.
 *
 * If Redis is unavailable (pool == null or connection error), every operation
 * degrades gracefully: {@link #getAll()} returns {@code null} (cache miss),
 * writes are silently skipped.
 */
public final class ItemCache {

    private static final Logger log = LoggerFactory.getLogger(ItemCache.class);
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final byte[] KEY = "items:all".getBytes(StandardCharsets.UTF_8);

    private final JedisPool pool;

    public ItemCache(JedisPool pool) {
        this.pool = pool;
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    /**
     * Fetch all item definitions from Redis.
     *
     * @return list of {@link ItemDef}, or {@code null} on a cache miss / Redis down
     */
    public List<ItemDef> getAll() {
        if (pool == null) return null;
        try (Jedis j = pool.getResource()) {
            byte[] raw = j.get(KEY);
            if (raw == null) return null;
            return deserialize(raw);
        } catch (Exception e) {
            log.debug("ItemCache.getAll miss (Redis unavailable): {}", e.getMessage());
            return null;
        }
    }

    // ── Write ─────────────────────────────────────────────────────────────────

    /**
     * Store all item definitions in Redis (no TTL — valid until {@link #invalidate()}).
     */
    public void putAll(Collection<ItemDef> defs) {
        if (pool == null) return;
        try (Jedis j = pool.getResource()) {
            j.set(KEY, serialize(defs));
        } catch (Exception e) {
            log.debug("ItemCache.putAll write failed (non-fatal): {}", e.getMessage());
        }
    }

    // ── Invalidate ────────────────────────────────────────────────────────────

    /**
     * Remove the {@code items:all} key so the next read forces a DB reload.
     * Call after any admin-side item add/update.
     */
    public void invalidate() {
        if (pool == null) return;
        try (Jedis j = pool.getResource()) {
            j.del(KEY);
            log.info("ItemCache invalidated (items:all deleted)");
        } catch (Exception e) {
            log.debug("ItemCache.invalidate failed (non-fatal): {}", e.getMessage());
        }
    }

    // ── Serialization ─────────────────────────────────────────────────────────

    private static byte[] serialize(Collection<ItemDef> defs) throws Exception {
        List<Map<String, Object>> list = new ArrayList<>(defs.size());
        for (ItemDef d : defs) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id",             d.id());
            m.put("type",           d.type());
            m.put("rarity",         d.rarity());
            m.put("name",           d.name());
            m.put("desc",           d.desc());
            m.put("maxStack",       d.maxStack());
            m.put("value",          d.value());
            m.put("consumable",     d.consumable());
            m.put("attackBonus",    d.attackBonus());
            m.put("defenseBonus",   d.defenseBonus());
            m.put("speedBonus",     d.speedBonus());
            m.put("healthBonus",    d.healthBonus());
            m.put("healthRestore",  d.healthRestore());
            m.put("abilityId",      d.abilityId());  // null is written as JSON null
            list.add(m);
        }
        return JSON.writeValueAsBytes(list);
    }

    private static List<ItemDef> deserialize(byte[] raw) throws Exception {
        List<Map<String, Object>> list = JSON.readValue(raw, new TypeReference<>() {});
        List<ItemDef> result = new ArrayList<>(list.size());
        for (Map<String, Object> m : list) {
            result.add(new ItemDef(
                str(m, "id"),
                str(m, "type"),
                str(m, "rarity"),
                str(m, "name"),
                str(m, "desc"),
                num(m, "maxStack"),
                num(m, "value"),
                bool(m, "consumable"),
                num(m, "attackBonus"),
                num(m, "defenseBonus"),
                flt(m, "speedBonus"),
                num(m, "healthBonus"),
                num(m, "healthRestore"),
                str(m, "abilityId")
            ));
        }
        return result;
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private static String  str(Map<String, Object> m, String k) { Object v = m.get(k); return v instanceof String s ? s : null; }
    private static int     num(Map<String, Object> m, String k) { Object v = m.get(k); return v instanceof Number n ? n.intValue() : 0; }
    private static float   flt(Map<String, Object> m, String k) { Object v = m.get(k); return v instanceof Number n ? n.floatValue() : 0f; }
    private static boolean bool(Map<String, Object> m, String k){ Object v = m.get(k); return v instanceof Boolean b && b; }
}
