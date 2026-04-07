package com.indieniinja.network;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Wire type for player inventory.
 * Sent as part of PlayerState in every WORLD_STATE message.
 * Mirrors Python game/inventory_system.py Inventory.to_dict().
 */
public final class InventoryState {

    public int    currency      = 0;
    public String equippedWeapon = null;
    public String equippedArmor  = null;
    /** Ordered list of 20 slots; null entry = empty slot. */
    public List<SlotState> slots = new ArrayList<>(20);

    public record SlotState(String itemId, int quantity, boolean equipped) {

        public Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>(3);
            m.put("item_id",  itemId);
            m.put("quantity", quantity);
            m.put("equipped", equipped);
            return m;
        }

        @SuppressWarnings("unchecked")
        public static SlotState fromMap(Map<String, Object> m) {
            String  id  = m.getOrDefault("item_id", "").toString();
            int     qty = m.get("quantity") instanceof Number n ? n.intValue() : 0;
            boolean eq  = m.get("equipped") instanceof Boolean b && b;
            return new SlotState(id, qty, eq);
        }
    }

    // ── Wire serialisation ────────────────────────────────────────────────────

    public Map<String, Object> toMap() {
        List<Object> slotList = new ArrayList<>(slots.size());
        for (SlotState s : slots) slotList.add(s != null ? s.toMap() : null);
        Map<String, Object> m = new LinkedHashMap<>(4);
        m.put("slots",           slotList);
        m.put("currency",        currency);
        m.put("equipped_weapon", equippedWeapon);
        m.put("equipped_armor",  equippedArmor);
        return m;
    }

    @SuppressWarnings("unchecked")
    public static InventoryState fromMap(Map<String, Object> m) {
        if (m == null) return new InventoryState();
        InventoryState s = new InventoryState();
        s.currency = m.get("currency") instanceof Number n ? n.intValue() : 0;
        Object ew = m.get("equipped_weapon");
        s.equippedWeapon = (ew != null && !ew.toString().equals("null")) ? ew.toString() : null;
        Object ea = m.get("equipped_armor");
        s.equippedArmor  = (ea != null && !ea.toString().equals("null")) ? ea.toString() : null;
        if (m.get("slots") instanceof List<?> sl) {
            for (Object slot : sl) {
                if (slot instanceof Map<?,?> sm)
                    s.slots.add(SlotState.fromMap((Map<String, Object>) sm));
                else
                    s.slots.add(null);
            }
        }
        return s;
    }
}
