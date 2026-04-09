package com.indieniinja.core;

import java.util.Map;

/**
 * Mixin for {@link Component} subclasses that can be round-tripped through
 * a plain {@code Map<String, Object>} — the same wire format used by
 * {@link com.indieniinja.network.WireCodec} and Python's snapshot dicts.
 *
 * Usage:
 * <pre>
 *   class HealthComponent extends Component implements SerializableComponent {
 *       public Map&lt;String, Object&gt; toMap() { return Map.of("hp", hp, "maxHp", maxHp); }
 *   }
 *
 *   // Serialize:
 *   Map&lt;String, Object&gt; data = entity.getComponent(HealthComponent.class).toMap();
 *
 *   // Deserialize — each component provides a static factory:
 *   HealthComponent hc = HealthComponent.fromMap(entityId, data);
 * </pre>
 *
 * The {@code fromMap} factory cannot be declared here (Java interfaces cannot
 * mandate static methods). Each implementing class must provide one with the
 * signature {@code static T fromMap(int entityId, Map&lt;String, Object&gt; m)}.
 */
public interface SerializableComponent {

    /**
     * Serialize this component's state to a plain map suitable for JSON
     * encoding or network transmission.
     * Keys must be stable across versions — treat them as public API.
     */
    Map<String, Object> toMap();
}
