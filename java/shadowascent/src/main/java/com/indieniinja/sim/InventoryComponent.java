package com.indieniinja.sim;

import com.indieniinja.core.Component;
import com.indieniinja.core.SerializableComponent;

import java.util.Map;

/**
 * Inventory component — wraps {@link SimInventory} as an ECS component.
 *
 * Delegates all serialisation to SimInventory.toMap() / fromMap(), keeping
 * the inventory logic in one place.
 */
public final class InventoryComponent extends Component implements SerializableComponent {

    public final SimInventory inventory;

    public InventoryComponent(int entityId) {
        super(entityId);
        this.inventory = new SimInventory();
    }

    private InventoryComponent(int entityId, SimInventory inv) {
        super(entityId);
        this.inventory = inv;
    }

    // ── SerializableComponent ─────────────────────────────────────────────────

    @Override
    public Map<String, Object> toMap() {
        return inventory.toMap();
    }

    public static InventoryComponent fromMap(int entityId, Map<String, Object> m) {
        SimInventory inv = SimInventory.fromMap(m);
        return new InventoryComponent(entityId, inv);
    }
}
