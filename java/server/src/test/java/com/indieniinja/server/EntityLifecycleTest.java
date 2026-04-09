package com.indieniinja.server;

import com.indieniinja.core.Entity;
import com.indieniinja.core.EntityLifecycleListener;
import com.indieniinja.core.EntityManager;
import com.indieniinja.core.EntityType;
import com.indieniinja.core.EventBus;
import com.indieniinja.sim.AbilityComponent;
import com.indieniinja.sim.HealthComponent;
import com.indieniinja.sim.InventoryComponent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Regression tests for ECS lifecycle hooks, tag auto-indexing, and
 * component serialization.
 *
 * Covers:
 *   ECS-1  onCreate fires after entity is created
 *   ECS-2  onDestroy fires before components are cleaned up
 *   ECS-3  removeLifecycleListener stops notifications
 *   ECS-4  Entity.addTag() auto-indexes in byTag; removeTag() de-indexes
 *   ECS-5  HealthComponent toMap/fromMap round-trip
 *   ECS-6  InventoryComponent toMap/fromMap round-trip
 *   ECS-7  AbilityComponent toMap/fromMap round-trip
 *   ECS-8  HealthComponent.applyDamage sets isDead at 0 hp
 */
class EntityLifecycleTest {

    private EntityManager em;

    @BeforeEach
    void setUp() {
        em = new EntityManager(new EventBus());
    }

    // ── ECS-1: onCreate fires ─────────────────────────────────────────────────

    @Test
    void onCreateFiresAfterEntityAdded() {
        List<Integer> created = new ArrayList<>();
        em.addLifecycleListener(new EntityLifecycleListener() {
            public void onCreate(Entity e)  { created.add(e.entityId); }
            public void onDestroy(Entity e) {}
        });

        Entity e = em.create(EntityType.PLAYER);
        assertThat(created).containsExactly(e.entityId);
    }

    // ── ECS-2: onDestroy fires before cleanup ─────────────────────────────────

    @Test
    void onDestroyFiresBeforeComponentCleanup() {
        // The listener checks that the entity still has its component at callback time
        List<Boolean> hadComponent = new ArrayList<>();
        em.addLifecycleListener(new EntityLifecycleListener() {
            public void onCreate(Entity e)  {}
            public void onDestroy(Entity e) {
                hadComponent.add(e.hasComponent(HealthComponent.class));
            }
        });

        Entity e = em.create(EntityType.PLAYER);
        e.addComponent(new HealthComponent(e.entityId, 10));
        em.destroy(e.entityId);

        assertThat(hadComponent).containsExactly(true);
    }

    // ── ECS-3: removeLifecycleListener stops notifications ────────────────────

    @Test
    void removedListenerReceivesNoMoreCallbacks() {
        List<Integer> created = new ArrayList<>();
        EntityLifecycleListener listener = new EntityLifecycleListener() {
            public void onCreate(Entity e)  { created.add(e.entityId); }
            public void onDestroy(Entity e) {}
        };

        em.addLifecycleListener(listener);
        em.create(EntityType.PLAYER);           // fires
        em.removeLifecycleListener(listener);
        em.create(EntityType.PLAYER);           // should NOT fire

        assertThat(created).hasSize(1);
    }

    // ── ECS-4: addTag auto-indexes; removeTag de-indexes ─────────────────────

    @Test
    void addTagAutoIndexesAndRemoveTagDeindexes() {
        Entity e = em.create(EntityType.PLAYER);
        e.addTag("elite");

        assertThat(em.byTag("elite")).contains(e);

        e.removeTag("elite");

        assertThat(em.byTag("elite")).doesNotContain(e);
    }

    // ── ECS-5: HealthComponent round-trip ─────────────────────────────────────

    @Test
    void healthComponentRoundTrip() {
        HealthComponent hc = new HealthComponent(1, 10);
        hc.applyDamage(3);

        Map<String, Object> map = hc.toMap();
        HealthComponent restored = HealthComponent.fromMap(1, map);

        assertThat(restored.hp).isEqualTo(7);
        assertThat(restored.maxHp).isEqualTo(10);
        assertThat(restored.isDead).isFalse();
    }

    // ── ECS-6: InventoryComponent round-trip ──────────────────────────────────

    @Test
    void inventoryComponentRoundTrip() {
        InventoryComponent ic = new InventoryComponent(1);
        ic.inventory.addCurrency(250);

        Map<String, Object> map = ic.toMap();
        InventoryComponent restored = InventoryComponent.fromMap(1, map);

        assertThat(restored.inventory.currency).isEqualTo(250);
    }

    // ── ECS-7: AbilityComponent round-trip ───────────────────────────────────

    @Test
    void abilityComponentRoundTrip() {
        AbilityComponent ac = new AbilityComponent(1);
        ac.unlock("double_jump");
        ac.unlock("dash");

        Map<String, Object> map = ac.toMap();
        AbilityComponent restored = AbilityComponent.fromMap(1, map);

        assertThat(restored.has("double_jump")).isTrue();
        assertThat(restored.has("dash")).isTrue();
        assertThat(restored.has("wall_jump")).isFalse();
    }

    // ── ECS-8: HealthComponent.applyDamage sets isDead at 0 hp ───────────────

    @Test
    void applyDamageSetsIsDeadWhenHpReachesZero() {
        HealthComponent hc = new HealthComponent(1, 5);
        hc.applyDamage(5);

        assertThat(hc.hp).isEqualTo(0);
        assertThat(hc.isDead).isTrue();
        assertThat(hc.isAlive()).isFalse();

        // Damage after death is a no-op
        hc.applyDamage(99);
        assertThat(hc.hp).isEqualTo(0);
    }
}
