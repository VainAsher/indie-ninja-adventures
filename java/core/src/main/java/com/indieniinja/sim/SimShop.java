package com.indieniinja.sim;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Server-side NPC shop.
 * Port of Python game/trading_system.py NPCInventory / TradingManager.
 *
 * Tiered shop pools (1–5); buy price = base_value × rarity_mult,
 * sell price = 50% of buy price.  Stock decrements on purchase.
 */
public final class SimShop {

    // ── Tier pools (mirrors Python SHOP_TIER_POOLS) ───────────────────────────

    private static final String[][] TIER_ITEMS = {
        // Tier 1 – common
        {"weapon_dagger", "weapon_sword",
         "armor_cloth", "armor_leather",
         "health_potion_small", "health_potion", "health_potion_medium",
         "material_cloth", "material_leather", "material_iron"},
        // Tier 2 – uncommon
        {"weapon_sword", "armor_leather", "armor_chain_mail",
         "health_potion", "health_potion_medium", "health_potion_large",
         "speed_boost_potion", "material_iron", "material_crystal"},
        // Tier 3 – rare
        {"weapon_steel_sword", "armor_chain_mail", "armor_bark_plate",
         "health_potion_large", "invincibility_potion",
         "material_crystal", "material_dark_essence"},
        // Tier 4 – epic
        {"weapon_crystal_blade", "armor_crystal_plate",
         "health_potion_large", "invincibility_potion", "max_hp_upgrade",
         "material_dark_essence"},
        // Tier 5 – legendary
        {"weapon_dark_blade",
         "max_hp_upgrade", "invincibility_potion",
         "material_dark_essence"},
    };

    // ── State ─────────────────────────────────────────────────────────────────

    public record Entry(String itemId, int stock, int buyPrice, int sellPrice) {
        public Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>(4);
            m.put("item_id",    itemId);
            m.put("stock",      stock);
            m.put("buy_price",  buyPrice);
            m.put("sell_price", sellPrice);
            return m;
        }
    }

    public final String npcId;
    public final int    tier;
    private final List<Entry> items = new ArrayList<>();
    private int shopCurrency = 10_000;  // NPC has plenty of gold

    // ── Construction ──────────────────────────────────────────────────────────

    public SimShop(String npcId, int tier, long seed) {
        this.npcId = npcId;
        this.tier  = Math.max(1, Math.min(5, tier));
        generate(seed);
    }

    private void generate(long seed) {
        String[] pool    = TIER_ITEMS[tier - 1];
        Random   rng     = new Random(seed);
        int      count   = 6 + rng.nextInt(5);   // 6–10 items

        // Deterministic shuffle
        String[] shuffled = pool.clone();
        for (int i = shuffled.length - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            String tmp = shuffled[i]; shuffled[i] = shuffled[j]; shuffled[j] = tmp;
        }

        items.clear();
        for (int i = 0; i < Math.min(count, shuffled.length); i++) {
            String itemId = shuffled[i];
            ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
            if (def == null) continue;
            int buyPrice  = Math.max(1, (int)(def.value() * ItemDatabase.rarityMult(def.rarity())));
            int sellPrice = Math.max(0, buyPrice / 2);
            int stock     = 2 + rng.nextInt(4);  // 2–5
            items.add(new Entry(itemId, stock, buyPrice, sellPrice));
        }
    }

    // ── Transactions ──────────────────────────────────────────────────────────

    /**
     * Player buys from shop: deducts currency, decrements stock, adds item to inventory.
     * Returns true on success.
     */
    public boolean buy(String itemId, int qty, SimInventory playerInv) {
        for (int i = 0; i < items.size(); i++) {
            Entry e = items.get(i);
            if (!e.itemId().equals(itemId)) continue;
            if (e.stock() < qty) return false;
            int cost = e.buyPrice() * qty;
            if (playerInv.currency < cost) return false;
            if (!playerInv.addItem(itemId, qty)) return false;  // inventory full?
            playerInv.currency -= cost;
            shopCurrency += cost;
            items.set(i, new Entry(e.itemId(), e.stock() - qty, e.buyPrice(), e.sellPrice()));
            return true;
        }
        return false;
    }

    /**
     * Player sells to shop: removes from inventory, grants sell-price currency.
     * Returns true on success.
     */
    public boolean sell(String itemId, int qty, SimInventory playerInv) {
        if (!playerInv.hasItem(itemId, qty)) return false;
        ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
        if (def == null) return false;
        // No buying quest/key items
        if ("quest_item".equals(def.type()) || "key_item".equals(def.type())) return false;

        // Find sell price from shop's own list, otherwise 50% of base
        int sellPrice = 0;
        for (Entry e : items) {
            if (e.itemId().equals(itemId)) { sellPrice = e.sellPrice(); break; }
        }
        if (sellPrice == 0) {
            sellPrice = Math.max(0, (int)(def.value() * ItemDatabase.rarityMult(def.rarity()) * 0.5f));
        }
        int total = sellPrice * qty;
        if (shopCurrency < total) return false;
        if (!playerInv.removeItem(itemId, qty)) return false;
        playerInv.addCurrency(total);
        shopCurrency -= total;
        return true;
    }

    // ── Serialisation ─────────────────────────────────────────────────────────

    public List<Entry> getItems() { return Collections.unmodifiableList(items); }

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(3);
        m.put("npc_id", npcId);
        m.put("tier",   tier);
        List<Object> itemList = new ArrayList<>(items.size());
        for (Entry e : items) itemList.add(e.toMap());
        m.put("items",  itemList);
        return m;
    }
}
