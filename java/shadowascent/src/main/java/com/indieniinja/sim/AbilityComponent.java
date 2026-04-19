package com.indieniinja.sim;

import com.indieniinja.core.Component;
import com.indieniinja.core.SerializableComponent;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Ability component — tracks which abilities the entity has unlocked.
 *
 * Known ability IDs (matches Python CampaignManager):
 *   "double_jump", "dash", "wall_jump", "shuriken", "teleport", "ninjutsu"
 *
 * Serialization key: "unlocked_abilities" → List&lt;String&gt;
 */
public final class AbilityComponent extends Component implements SerializableComponent {

    private final Set<String> unlocked = new LinkedHashSet<>();

    public AbilityComponent(int entityId) {
        super(entityId);
    }

    // ── Mutation ──────────────────────────────────────────────────────────────

    public void unlock(String ability)  { unlocked.add(ability); }
    public void lock(String ability)    { unlocked.remove(ability); }
    public boolean has(String ability)  { return unlocked.contains(ability); }
    public Set<String> all()            { return java.util.Collections.unmodifiableSet(unlocked); }

    // ── SerializableComponent ─────────────────────────────────────────────────

    @Override
    public Map<String, Object> toMap() {
        return Map.of("unlocked_abilities", new ArrayList<>(unlocked));
    }

    public static AbilityComponent fromMap(int entityId, Map<String, Object> m) {
        AbilityComponent ac = new AbilityComponent(entityId);
        Object raw = m.get("unlocked_abilities");
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                if (o instanceof String s) ac.unlock(s);
            }
        }
        return ac;
    }
}
