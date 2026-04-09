package com.indieniinja.core;

import com.indieniinja.physics.PhysicsState;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Entity manager — create, destroy, and query entities.
 * Java equivalent of Python core/entity_system.py EntityManager.
 *
 * Not thread-safe; all access from the simulation thread only.
 * PhysicsSystem and CollisionSystem iterate activeEntities() at 60 Hz —
 * that list is pre-built and updated only on spawn/destroy, not per tick.
 */
public final class EntityManager {

    private final EventBus bus;
    private final Map<Integer, Entity> entities = new HashMap<>();
    private int nextId = 0;

    // Indices for fast query
    private final Map<EntityType, Set<Integer>> byType = new HashMap<>();
    private final Map<String,     Set<Integer>> byTag  = new HashMap<>();

    // Lifecycle observers — CopyOnWriteArrayList so listeners can safely
    // add/remove themselves from within a callback without CME.
    private final List<EntityLifecycleListener> lifecycleListeners = new CopyOnWriteArrayList<>();

    // Pre-built list for hot-path iteration (physics, collision)
    private final List<Entity> activeList = new ArrayList<>();
    private boolean activeListDirty = false;

    public EntityManager(EventBus bus) {
        this.bus = bus;
    }

    // ── Lifecycle listeners ───────────────────────────────────────────────────

    public void addLifecycleListener(EntityLifecycleListener listener) {
        lifecycleListeners.add(listener);
    }

    public void removeLifecycleListener(EntityLifecycleListener listener) {
        lifecycleListeners.remove(listener);
    }

    // ── Create / destroy ─────────────────────────────────────────────────────

    public Entity create(EntityType type) {
        return create(type, null);
    }

    public Entity create(EntityType type, PhysicsState physics) {
        int id = nextId++;
        Entity e = new Entity(id, type);
        e.physics = physics;
        entities.put(id, e);
        byType.computeIfAbsent(type, k -> new HashSet<>()).add(id);
        e.manager = this;
        activeListDirty = true;
        for (EntityLifecycleListener l : lifecycleListeners) l.onCreate(e);
        return e;
    }

    public void destroy(int entityId) {
        Entity e = entities.remove(entityId);
        if (e == null) return;
        for (EntityLifecycleListener l : lifecycleListeners) l.onDestroy(e);
        // Cleanup all components
        for (Component c : e.components()) c.cleanup();
        // Remove from indices
        Set<Integer> typeSet = byType.get(e.entityType);
        if (typeSet != null) typeSet.remove(entityId);
        for (String tag : e.getTags()) {
            Set<Integer> tagSet = byTag.get(tag);
            if (tagSet != null) tagSet.remove(entityId);
        }
        activeListDirty = true;
    }

    public void clear() {
        List<Integer> ids = new ArrayList<>(entities.keySet());
        for (int id : ids) destroy(id);
    }

    // ── Queries ───────────────────────────────────────────────────────────────

    public Entity get(int entityId) {
        return entities.get(entityId);
    }

    public List<Entity> byType(EntityType type) {
        Set<Integer> ids = byType.getOrDefault(type, Collections.emptySet());
        List<Entity> result = new ArrayList<>(ids.size());
        for (int id : ids) {
            Entity e = entities.get(id);
            if (e != null) result.add(e);
        }
        return result;
    }

    public List<Entity> byTag(String tag) {
        Set<Integer> ids = byTag.getOrDefault(tag, Collections.emptySet());
        List<Entity> result = new ArrayList<>(ids.size());
        for (int id : ids) {
            Entity e = entities.get(id);
            if (e != null) result.add(e);
        }
        return result;
    }

    /** Live collection of all entities (use for non-hot-path queries). */
    public Collection<Entity> all() {
        return Collections.unmodifiableCollection(entities.values());
    }

    /**
     * Pre-built list of active entities with physics — used by PhysicsSystem
     * and CollisionSystem at 60 Hz. Rebuilt only when dirty.
     */
    public List<Entity> activeEntities() {
        if (activeListDirty) {
            activeList.clear();
            for (Entity e : entities.values()) {
                if (e.active && e.physics != null) activeList.add(e);
            }
            activeListDirty = false;
        }
        return activeList;
    }

    public int size() {
        return entities.size();
    }

    /** Called by Entity.addTag() — adds entity to the tag index. */
    public void indexTag(Entity e, String tag) {
        byTag.computeIfAbsent(tag, k -> new HashSet<>()).add(e.entityId);
    }

    /** Called by Entity.removeTag() — removes entity from the tag index. */
    public void deindexTag(Entity e, String tag) {
        Set<Integer> tagSet = byTag.get(tag);
        if (tagSet != null) tagSet.remove(e.entityId);
    }
}
