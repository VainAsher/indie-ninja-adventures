package com.indieniinja.core;

/**
 * Observer for entity creation and destruction events.
 *
 * Register with {@link EntityManager#addLifecycleListener} to be notified
 * whenever an entity is spawned or removed from the world.
 *
 * Callbacks fire synchronously on the simulation thread — implementations
 * must not modify the entity list from within them.
 */
public interface EntityLifecycleListener {

    /** Called immediately after {@code entity} has been added to the EntityManager. */
    void onCreate(Entity entity);

    /**
     * Called immediately before {@code entity} is removed from the EntityManager
     * and its components are cleaned up.
     */
    void onDestroy(Entity entity);
}
