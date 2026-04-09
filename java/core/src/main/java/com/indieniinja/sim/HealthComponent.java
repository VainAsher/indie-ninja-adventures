package com.indieniinja.sim;

import com.indieniinja.core.Component;
import com.indieniinja.core.SerializableComponent;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Health component — hp, maxHp, and isDead flag.
 *
 * Mirrors the health fields on {@link SimPlayer} but as a reusable component
 * that any entity type (player, boss, destructible) can carry.
 *
 * Serialization keys match Python snapshot dicts:
 *   "hp", "max_hp", "is_dead"
 */
public final class HealthComponent extends Component implements SerializableComponent {

    public int     hp;
    public int     maxHp;
    public boolean isDead = false;

    public HealthComponent(int entityId, int maxHp) {
        super(entityId);
        this.maxHp = maxHp;
        this.hp    = maxHp;
    }

    // ── Mutation ──────────────────────────────────────────────────────────────

    public void applyDamage(int dmg) {
        if (dmg <= 0 || isDead) return;
        hp = Math.max(0, hp - dmg);
        if (hp == 0) isDead = true;
    }

    public void heal(int amount) {
        if (amount <= 0 || isDead) return;
        hp = Math.min(maxHp, hp + amount);
    }

    public boolean isAlive() { return !isDead; }

    // ── SerializableComponent ─────────────────────────────────────────────────

    @Override
    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(4);
        m.put("hp",     hp);
        m.put("max_hp", maxHp);
        m.put("is_dead", isDead);
        return m;
    }

    public static HealthComponent fromMap(int entityId, Map<String, Object> m) {
        int maxHp = num(m, "max_hp", 5);
        HealthComponent hc = new HealthComponent(entityId, maxHp);
        hc.hp     = num(m, "hp", maxHp);
        hc.isDead = bool(m, "is_dead");
        return hc;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static int     num(Map<String,Object> m, String k, int d)  { Object v = m.get(k); return v instanceof Number n ? n.intValue() : d; }
    private static boolean bool(Map<String,Object> m, String k)        { Object v = m.get(k); return v instanceof Boolean b && b; }
}
