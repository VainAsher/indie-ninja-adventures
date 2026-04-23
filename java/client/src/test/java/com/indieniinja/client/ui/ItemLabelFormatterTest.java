package com.indieniinja.client.ui;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ItemLabelFormatterTest {

    @Test
    void inventoryAbbreviationMatchesLegacyFormatting() {
        assertEquals("?", ItemLabelFormatter.abbreviateForInventory(null));
        assertEquals("Sword", ItemLabelFormatter.abbreviateForInventory("weapon_sword"));
        assertEquals("DrkEss", ItemLabelFormatter.abbreviateForInventory("material_dark_essence"));
        assertEquals("super.", ItemLabelFormatter.abbreviateForInventory("weapon_super_lance"));
    }

    @Test
    void shopAbbreviationMatchesLegacyFormatting() {
        assertEquals("?", ItemLabelFormatter.abbreviateForShop(null));
        assertEquals("sword", ItemLabelFormatter.abbreviateForShop("weapon_sword"));
        assertEquals("hpot.large", ItemLabelFormatter.abbreviateForShop("health_potion_large"));
        assertEquals("dark.essen", ItemLabelFormatter.abbreviateForShop("material_dark_essence_shard"));
    }

    @Test
    void sellPriceMatchesLegacyTable() {
        assertEquals(200, ItemLabelFormatter.estimatedSellPrice("weapon_dark_blade"));
        assertEquals(2, ItemLabelFormatter.estimatedSellPrice("material_iron"));
        assertEquals(1, ItemLabelFormatter.estimatedSellPrice("unknown_item"));
        assertEquals(1, ItemLabelFormatter.estimatedSellPrice(null));
    }

    @Test
    void shopBuyLineMatchesLegacyFormatting() {
        String expectedAfford = String.format("%-10s stk:%-2d  %dg%s", "sword", 2, 15, "");
        String expectedNoAfford = String.format("%-10s stk:%-2d  %dg%s", "sword", 2, 15, " !");
        assertEquals(expectedAfford, ItemLabelFormatter.formatShopBuyLine("weapon_sword", 2, 15, true));
        assertEquals(expectedNoAfford, ItemLabelFormatter.formatShopBuyLine("weapon_sword", 2, 15, false));
    }

    @Test
    void inventorySellLineMatchesLegacyFormatting() {
        String expected = String.format("%-10s x%-2d  sell %dg", "sword", 3, 15);
        assertEquals(expected, ItemLabelFormatter.formatInventorySellLine("weapon_sword", 3));
    }
}
