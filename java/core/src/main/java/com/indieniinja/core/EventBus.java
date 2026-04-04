package com.indieniinja.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/**
 * Type-safe priority event bus.
 *
 * Java equivalent of Python's core/event_bus.py EventBus.
 * Subscribers run in descending priority order (higher number = runs first),
 * matching the Python implementation (physics at 60, collision at 45, mechanics at 40).
 *
 * Thread-safety: subscribe/emit must be called from the same simulation thread.
 * The server's ZoneSimulationLoop is the sole caller — no synchronisation needed here.
 */
public final class EventBus {

    private record Handler<E extends GameEvent>(Consumer<E> fn, int priority) {}

    /** Map from event class → handlers sorted descending by priority. */
    private final Map<Class<?>, List<Handler<?>>> subscribers = new HashMap<>();

    /**
     * Subscribe to events of type {@code eventClass}.
     *
     * @param eventClass  The event type to listen for.
     * @param handler     Consumer called with each emitted event.
     * @param priority    Higher runs first (physics=60, collision=45, mechanics=40).
     */
    public <E extends GameEvent> void subscribe(
            Class<E> eventClass,
            Consumer<E> handler,
            int priority) {

        List<Handler<?>> list = subscribers.computeIfAbsent(eventClass, k -> new ArrayList<>());
        list.add(new Handler<>(handler, priority));
        // Keep sorted descending by priority
        list.sort((a, b) -> Integer.compare(b.priority(), a.priority()));
    }

    /**
     * Emit an event synchronously, calling all subscribers in priority order.
     * Equivalent to Python's emit() + immediate process() in one step.
     */
    @SuppressWarnings("unchecked")
    public <E extends GameEvent> void emit(E event) {
        List<Handler<?>> list = subscribers.get(event.getClass());
        if (list == null) return;
        for (Handler<?> h : list) {
            ((Handler<E>) h).fn().accept(event);
        }
    }

    /** Remove all subscribers (used between simulation resets). */
    public void clear() {
        subscribers.clear();
    }
}
