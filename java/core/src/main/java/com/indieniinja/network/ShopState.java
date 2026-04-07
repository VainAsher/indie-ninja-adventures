package com.indieniinja.network;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Wire type for an NPC shop inventory.
 * Sent in full WorldSnapshot messages so the client can populate ShopOverlay.
 * Mirrors Python game/trading_system.py NPCInventory.to_dict().
 */
public final class ShopState {

    public String npcId = "";
    public int    tier  = 1;
    public List<ShopItemState> items = new ArrayList<>();

    public record ShopItemState(String itemId, int stock, int buyPrice, int sellPrice) {

        public Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>(4);
            m.put("item_id",    itemId);
            m.put("stock",      stock);
            m.put("buy_price",  buyPrice);
            m.put("sell_price", sellPrice);
            return m;
        }

        public static ShopItemState fromMap(Map<?, ?> m) {
            Object itemIdObj = m.get("item_id");
            return new ShopItemState(
                itemIdObj != null ? itemIdObj.toString() : "",
                m.get("stock")     instanceof Number n  ? n.intValue()  : 0,
                m.get("buy_price") instanceof Number n2 ? n2.intValue() : 0,
                m.get("sell_price")instanceof Number n3 ? n3.intValue() : 0
            );
        }
    }

    // ── Wire serialisation ────────────────────────────────────────────────────

    public Map<String, Object> toMap() {
        List<Object> itemList = new ArrayList<>(items.size());
        for (ShopItemState i : items) itemList.add(i.toMap());
        Map<String, Object> m = new LinkedHashMap<>(3);
        m.put("npc_id", npcId);
        m.put("tier",   tier);
        m.put("items",  itemList);
        return m;
    }

    public static ShopState fromMap(Map<?, ?> m) {
        ShopState s = new ShopState();
        Object npcIdObj = m.get("npc_id");
        s.npcId = npcIdObj != null ? npcIdObj.toString() : "";
        s.tier  = m.get("tier") instanceof Number n ? n.intValue() : 1;
        if (m.get("items") instanceof List<?> l) {
            for (Object item : l) {
                if (item instanceof Map<?,?> im) s.items.add(ShopItemState.fromMap(im));
            }
        }
        return s;
    }
}
