package com.indieniinja.client.ui;

/**
 * Shared item label and pricing helpers used by inventory/shop overlays.
 *
 * These methods intentionally preserve existing overlay formatting output.
 */
final class ItemLabelFormatter {

    private ItemLabelFormatter() {}

    static String abbreviateForInventory(String itemId) {
        if (itemId == null) return "?";
        return switch (itemId) {
            case "weapon_dagger"         -> "Dagger";
            case "weapon_sword"          -> "Sword";
            case "weapon_steel_sword"    -> "Stl.Sw";
            case "weapon_crystal_blade"  -> "Crys.Bl";
            case "weapon_dark_blade"     -> "Drk.Bl";
            case "armor_cloth"           -> "Cloth";
            case "armor_leather"         -> "Leathr";
            case "armor_chain_mail"      -> "ChainM";
            case "armor_bark_plate"      -> "BarkPl";
            case "armor_crystal_plate"   -> "CrysPl";
            case "health_potion"         -> "H.Pot";
            case "health_potion_small"   -> "H.PotS";
            case "health_potion_medium"  -> "H.PotM";
            case "health_potion_large"   -> "H.PotL";
            case "speed_boost_potion"    -> "SpeedP";
            case "invincibility_potion"  -> "InvPot";
            case "max_hp_upgrade"        -> "HPCrys";
            case "coin"                  -> "Coin";
            case "material_iron"         -> "Iron";
            case "material_crystal"      -> "Cryst";
            case "material_dark_essence" -> "DrkEss";
            default -> truncate(stripStandardPrefixes(itemId).replace("_", "."), 6);
        };
    }

    static String abbreviateForShop(String itemId) {
        if (itemId == null) return "?";
        String normalized = stripStandardPrefixes(itemId)
            .replace("health_potion", "hpot")
            .replace("_potion", "pot")
            .replace("_", ".");
        return truncate(normalized, 10);
    }

    static int estimatedSellPrice(String itemId) {
        // Client-side estimate: 50% of base value × rarity mult (matches server logic).
        // We avoid importing ItemDatabase here because it lives in server modules.
        return switch (itemId != null ? itemId : "") {
            case "weapon_dagger"         -> 7;
            case "weapon_sword"          -> 15;
            case "weapon_steel_sword"    -> 30;
            case "weapon_crystal_blade"  -> 80;
            case "weapon_dark_blade"     -> 200;
            case "armor_cloth"           -> 5;
            case "armor_leather"         -> 10;
            case "armor_chain_mail"      -> 24;
            case "health_potion"         -> 2;
            case "health_potion_small"   -> 1;
            case "health_potion_medium"  -> 4;
            case "health_potion_large"   -> 10;
            case "speed_boost_potion"    -> 6;
            case "invincibility_potion"  -> 20;
            case "max_hp_upgrade"        -> 40;
            case "coin"                  -> 1;
            case "material_iron"         -> 2;
            case "material_crystal"      -> 8;
            case "material_dark_essence" -> 24;
            default -> 1;
        };
    }

    static String formatShopBuyLine(String itemId, int stock, int buyPrice, boolean canAfford) {
        return String.format("%-10s stk:%-2d  %dg%s",
            abbreviateForShop(itemId), stock, buyPrice, canAfford ? "" : " !");
    }

    static String formatInventorySellLine(String itemId, int quantity) {
        return String.format("%-10s x%-2d  sell %dg",
            abbreviateForShop(itemId), quantity, estimatedSellPrice(itemId));
    }

    private static String stripStandardPrefixes(String itemId) {
        return itemId.replace("weapon_", "")
            .replace("armor_", "")
            .replace("material_", "");
    }

    private static String truncate(String value, int maxLen) {
        return value.length() > maxLen ? value.substring(0, maxLen) : value;
    }
}
