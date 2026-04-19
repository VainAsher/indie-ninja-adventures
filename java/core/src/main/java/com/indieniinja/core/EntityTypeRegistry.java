package com.indieniinja.core;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * String-keyed registry mapping game-specific type IDs to their base EntityType.
 *
 * Decouples entity creation from hardcoded enum switches. Game modules (e.g.
 * :shadowascent) register their types at startup via a bootstrap class; the
 * engine only knows about the base EntityType enum.
 *
 * Thread-safety: register() must be called before any tick runs. After bootstrap,
 * only get/contains are called from the sim thread — no synchronisation needed.
 */
public final class EntityTypeRegistry {

    public record EntityTypeDefinition(String id, EntityType baseType) {}

    private final Map<String, EntityTypeDefinition> defs = new LinkedHashMap<>();

    /**
     * Register a type ID. Overwrites an existing registration silently (last writer wins).
     *
     * @param id       Lowercase snake_case type identifier, e.g. "enemy_skeleton"
     * @param baseType The canonical EntityType this maps to
     */
    public void register(String id, EntityType baseType) {
        String key = id.toLowerCase();
        defs.put(key, new EntityTypeDefinition(key, baseType));
    }

    /** Return the definition for {@code id}, or null if not registered. */
    public EntityTypeDefinition get(String id) {
        return defs.get(id.toLowerCase());
    }

    /** Return the base EntityType for {@code id}, or null if not registered. */
    public EntityType baseTypeOf(String id) {
        EntityTypeDefinition def = get(id);
        return def != null ? def.baseType() : null;
    }

    public boolean contains(String id) {
        return defs.containsKey(id.toLowerCase());
    }

    public Set<String> typeIds() {
        return Collections.unmodifiableSet(defs.keySet());
    }

    public int size() {
        return defs.size();
    }
}
