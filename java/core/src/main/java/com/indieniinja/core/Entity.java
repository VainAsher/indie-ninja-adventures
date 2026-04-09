package com.indieniinja.core;

import com.indieniinja.physics.PhysicsState;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Entity — composed of a unique ID, type, optional physics, and components.
 * Java equivalent of Python core/entity_system.py Entity dataclass.
 *
 * Not thread-safe; all access from the simulation thread only.
 */
public final class Entity {

    public final int        entityId;
    public final EntityType entityType;
    public       PhysicsState physics;      // null for entities with no physics
    public       boolean    active = true;

    /** Set by EntityManager on creation so addTag/removeTag auto-update the index. */
    EntityManager manager;

    private final Map<Class<? extends Component>, Component> components = new HashMap<>();
    private final Set<String> tags = new HashSet<>();

    Entity(int entityId, EntityType entityType) {
        this.entityId   = entityId;
        this.entityType = entityType;
    }

    // ── Components ────────────────────────────────────────────────────────────

    public void addComponent(Component c) {
        components.put(c.getClass(), c);
    }

    @SuppressWarnings("unchecked")
    public <T extends Component> T getComponent(Class<T> type) {
        return (T) components.get(type);
    }

    public boolean hasComponent(Class<? extends Component> type) {
        return components.containsKey(type);
    }

    public void removeComponent(Class<? extends Component> type) {
        Component c = components.remove(type);
        if (c != null) c.cleanup();
    }

    public Iterable<Component> components() {
        return Collections.unmodifiableCollection(components.values());
    }

    // ── Tags ──────────────────────────────────────────────────────────────────

    public void addTag(String tag) {
        if (tags.add(tag) && manager != null) manager.indexTag(this, tag);
    }

    public void removeTag(String tag) {
        if (tags.remove(tag) && manager != null) manager.deindexTag(this, tag);
    }
    public boolean hasTag(String tag) { return tags.contains(tag); }
    public Set<String> getTags()      { return Collections.unmodifiableSet(tags); }
}
