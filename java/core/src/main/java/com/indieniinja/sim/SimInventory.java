package com.indieniinja.sim;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Server-side player inventory.
 * Port of Python game/inventory_system.py Inventory.
 *
 * 20 slots; items stack up to ItemDefinition.maxStack.
 * Currency tracked separately (not a slot).
 */
public final class SimInventory {

    public static final int MAX_SLOTS    = 20;
    public static final int MAX_CURRENCY = 999_999;

    // ── State ─────────────────────────────────────────────────────────────────

    public int    currency      = 0;
    public String equippedWeapon = null;
    public String equippedArmor  = null;

    /** Sparse slot array — null = empty. */
    public final Slot[] slots = new Slot[MAX_SLOTS];

    // ── Slot record ───────────────────────────────────────────────────────────

    public record Slot(String itemId, int quantity, boolean equipped) {
        public Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>(4);
            m.put("item_id",  itemId);
            m.put("quantity", quantity);
            m.put("equipped", equipped);
            return m;
        }
    }

    // ── Currency ──────────────────────────────────────────────────────────────

    public void addCurrency(int amount) {
        if (amount <= 0) return;
        currency = Math.min(MAX_CURRENCY, currency + amount);
    }

    public boolean removeCurrency(int amount) {
        if (amount <= 0 || currency < amount) return false;
        currency -= amount;
        return true;
    }

    // ── Items ─────────────────────────────────────────────────────────────────

    /**
     * Add items to inventory (stacks + new slots).
     * Returns true if all items were added; false if inventory is full.
     */
    public boolean addItem(String itemId, int qty) {
        if (qty <= 0) return false;
        ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
        if (def == null) return false;

        int remaining = qty;

        // Try to stack into existing slots first
        if (def.maxStack() > 1) {
            for (int i = 0; i < MAX_SLOTS && remaining > 0; i++) {
                if (slots[i] != null && slots[i].itemId().equals(itemId)) {
                    int space = def.maxStack() - slots[i].quantity();
                    if (space > 0) {
                        int add = Math.min(remaining, space);
                        slots[i] = new Slot(itemId, slots[i].quantity() + add, slots[i].equipped());
                        remaining -= add;
                    }
                }
            }
        }

        // Fill empty slots
        while (remaining > 0) {
            int idx = findEmpty();
            if (idx < 0) return false;   // inventory full
            int stack = Math.min(remaining, def.maxStack());
            slots[idx] = new Slot(itemId, stack, false);
            remaining -= stack;
        }
        return true;
    }

    public boolean removeItem(String itemId, int qty) {
        if (qty <= 0 || countItem(itemId) < qty) return false;
        int remaining = qty;
        for (int i = 0; i < MAX_SLOTS && remaining > 0; i++) {
            if (slots[i] != null && slots[i].itemId().equals(itemId)) {
                int take = Math.min(remaining, slots[i].quantity());
                if (slots[i].quantity() - take <= 0) {
                    // Unequip if this slot was equipped
                    if (slots[i].equipped()) unequipItem(itemId);
                    slots[i] = null;
                } else {
                    slots[i] = new Slot(itemId, slots[i].quantity() - take, slots[i].equipped());
                }
                remaining -= take;
            }
        }
        return true;
    }

    public boolean hasItem(String itemId, int qty) {
        return countItem(itemId) >= qty;
    }

    public int countItem(String itemId) {
        int total = 0;
        for (Slot s : slots) if (s != null && s.itemId().equals(itemId)) total += s.quantity();
        return total;
    }

    // ── Equipment ─────────────────────────────────────────────────────────────

    public boolean equipItem(String itemId) {
        ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
        if (def == null) return false;
        for (int i = 0; i < MAX_SLOTS; i++) {
            if (slots[i] != null && slots[i].itemId().equals(itemId)) {
                if ("weapon".equals(def.type())) {
                    if (equippedWeapon != null) unequipItem(equippedWeapon);
                    equippedWeapon = itemId;
                    slots[i] = new Slot(itemId, slots[i].quantity(), true);
                    return true;
                } else if ("armor".equals(def.type())) {
                    if (equippedArmor != null) unequipItem(equippedArmor);
                    equippedArmor = itemId;
                    slots[i] = new Slot(itemId, slots[i].quantity(), true);
                    return true;
                }
            }
        }
        return false;
    }

    public void unequipItem(String itemId) {
        for (int i = 0; i < MAX_SLOTS; i++) {
            if (slots[i] != null && slots[i].itemId().equals(itemId) && slots[i].equipped()) {
                slots[i] = new Slot(itemId, slots[i].quantity(), false);
            }
        }
        if (itemId.equals(equippedWeapon)) equippedWeapon = null;
        if (itemId.equals(equippedArmor))  equippedArmor  = null;
    }

    // ── Consumable ────────────────────────────────────────────────────────────

    /**
     * Use one consumable from inventory.
     * Returns the healthRestore amount (0 if not a health consumable or not found).
     */
    public int useConsumable(String itemId) {
        ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
        if (def == null || !def.consumable()) return 0;
        if (!removeItem(itemId, 1)) return 0;
        return def.healthRestore();
    }

    // ── Stat totals ───────────────────────────────────────────────────────────

    public int totalAttackBonus() {
        int bonus = 0;
        if (equippedWeapon != null) {
            ItemDatabase.ItemDef d = ItemDatabase.get(equippedWeapon);
            if (d != null) bonus += d.attackBonus();
        }
        return bonus;
    }

    public int totalDefenseBonus() {
        int bonus = 0;
        if (equippedArmor != null) {
            ItemDatabase.ItemDef d = ItemDatabase.get(equippedArmor);
            if (d != null) bonus += d.defenseBonus();
        }
        return bonus;
    }

    // ── Serialisation ─────────────────────────────────────────────────────────

    public Map<String, Object> toMap() {
        List<Object> slotList = new ArrayList<>(MAX_SLOTS);
        for (Slot s : slots) slotList.add(s != null ? s.toMap() : null);
        Map<String, Object> m = new LinkedHashMap<>(4);
        m.put("slots",           slotList);
        m.put("currency",        currency);
        m.put("equipped_weapon", equippedWeapon);
        m.put("equipped_armor",  equippedArmor);
        return m;
    }

    @SuppressWarnings("unchecked")
    public static SimInventory fromMap(Map<String, Object> m) {
        SimInventory inv = new SimInventory();
        Object raw = m.get("slots");
        if (raw instanceof List<?> list) {
            for (int i = 0; i < Math.min(list.size(), MAX_SLOTS); i++) {
                Object s = list.get(i);
                if (s instanceof Map<?,?> sm) {
                    Map<String, Object> sm2 = (Map<String, Object>) sm;
                    String itemId  = str(sm2, "item_id");
                    int    qty     = num(sm2, "quantity", 1);
                    boolean eq     = bool(sm2, "equipped");
                    if (itemId != null) inv.slots[i] = new Slot(itemId, qty, eq);
                }
            }
        }
        inv.currency       = num(m, "currency", 0);
        inv.equippedWeapon = str(m, "equipped_weapon");
        inv.equippedArmor  = str(m, "equipped_armor");
        return inv;
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private int findEmpty() {
        for (int i = 0; i < MAX_SLOTS; i++) if (slots[i] == null) return i;
        return -1;
    }

    private static String  str(Map<String,Object> m, String k)         { Object v = m.get(k); return v instanceof String s ? s : null; }
    private static int     num(Map<String,Object> m, String k, int d)  { Object v = m.get(k); return v instanceof Number n ? n.intValue() : d; }
    private static boolean bool(Map<String,Object> m, String k)        { Object v = m.get(k); return v instanceof Boolean b && b; }
}
