package com.indieniinja.sim;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

/**
 * Static item definition database.
 * Port of Python game/inventory_system.py ItemDefinition + ItemDatabase.
 * Items are registered once at class load; no mutable state.
 */
public final class ItemDatabase {

    public record ItemDef(
        String id,
        String type,       // weapon, armor, consumable, material, currency, quest_item, key_item, ability
        String rarity,     // common, uncommon, rare, epic, legendary
        String name,
        String desc,
        int    maxStack,
        int    value,      // base gold value
        boolean consumable,
        int    attackBonus,
        int    defenseBonus,
        float  speedBonus,
        int    healthBonus,
        int    healthRestore,
        String abilityId   // non-null only when type == "ability"
    ) {
        /** Backwards-compat factory: no abilityId (non-ability items). */
        public static ItemDef of(String id, String type, String rarity, String name, String desc,
                                 int maxStack, int value, boolean consumable,
                                 int atk, int def, float spd, int hp, int restore) {
            return new ItemDef(id, type, rarity, name, desc,
                               maxStack, value, consumable, atk, def, spd, hp, restore, null);
        }
    }

    private static final Map<String, ItemDef> ITEMS = new HashMap<>();

    static {
        // ── Weapons ──────────────────────────────────────────────────────────────
        reg("weapon_dagger",        "weapon",     "common",    "Dagger",           "A small, quick blade.",                   1,  15, false, 1, 0, 0f, 0, 0);
        reg("weapon_sword",         "weapon",     "uncommon",  "Iron Sword",       "A reliable iron sword.",                  1,  30, false, 2, 0, 0f, 0, 0);
        reg("weapon_steel_sword",   "weapon",     "rare",      "Steel Sword",      "A finely crafted steel sword.",           1,  75, false, 4, 0, 0f, 0, 0);
        reg("weapon_crystal_blade", "weapon",     "epic",      "Crystal Blade",    "Blade infused with crystal magic.",       1, 200, false, 6, 1, 0f, 5, 0);
        reg("weapon_dark_blade",    "weapon",     "legendary", "Dark Blade",       "Ancient blade from the shadow realm.",    1, 500, false,10, 2, 0f,10, 0);

        // ── Armor ─────────────────────────────────────────────────────────────────
        reg("armor_cloth",          "armor",      "common",    "Cloth Armor",      "Simple cloth protection.",                1,  10, false, 0, 1, 0f, 0, 0);
        reg("armor_leather",        "armor",      "uncommon",  "Leather Armor",    "Sturdy leather armor.",                   1,  25, false, 0, 2, 0f, 5, 0);
        reg("armor_chain_mail",     "armor",      "rare",      "Chain Mail",       "Interlocked rings of metal.",             1,  60, false, 0, 4, 0f,10, 0);
        reg("armor_bark_plate",     "armor",      "rare",      "Bark Plate",       "Nature-infused bark armor.",              1,  80, false, 0, 4, 0f,10, 0);
        reg("armor_crystal_plate",  "armor",      "epic",      "Crystal Plate",    "Crystalline armor of great power.",       1, 200, false, 1, 6, 0f,15, 0);

        // ── Consumables ───────────────────────────────────────────────────────────
        reg("health_potion",        "consumable", "common",    "Health Potion",    "Restores 2 HP.",                         99,   5, true,  0, 0, 0f, 0, 2);
        reg("health_potion_small",  "consumable", "common",    "Small Potion",     "Restores 1 HP.",                         99,   3, true,  0, 0, 0f, 0, 1);
        reg("health_potion_medium", "consumable", "uncommon",  "Medium Potion",    "Restores 3 HP.",                         99,  10, true,  0, 0, 0f, 0, 3);
        reg("health_potion_large",  "consumable", "rare",      "Large Potion",     "Restores 5 HP.",                         99,  25, true,  0, 0, 0f, 0, 5);
        reg("speed_boost_potion",   "consumable", "uncommon",  "Speed Potion",     "Temporarily boosts speed.",              99,  15, true,  0, 0, 1f, 0, 0);
        reg("invincibility_potion", "consumable", "rare",      "Invincibility Pot","Brief invulnerability.",                 10,  50, true,  0, 0, 0f, 0, 0);
        reg("max_hp_upgrade",       "consumable", "epic",      "HP Crystal",       "Permanently raises max HP by 1.",        10, 100, true,  0, 0, 0f, 1, 0);

        // ── Currency (pseudo-item for wallet representation) ─────────────────────
        reg("coin",                 "currency",   "common",    "Coin",             "Gold coin — the realm's currency.",      999,  1, false, 0, 0, 0f, 0, 0);

        // ── Materials ─────────────────────────────────────────────────────────────
        reg("material_cloth",       "material",   "common",    "Cloth",            "Woven fabric for crafting.",              99,  2, false, 0, 0, 0f, 0, 0);
        reg("material_leather",     "material",   "common",    "Leather",          "Tanned hide for crafting.",               99,  4, false, 0, 0, 0f, 0, 0);
        reg("material_iron",        "material",   "common",    "Iron Ingot",       "Raw iron for crafting.",                  99,  5, false, 0, 0, 0f, 0, 0);
        reg("material_crystal",     "material",   "rare",      "Crystal Shard",    "Magical crystal fragment.",               99, 20, false, 0, 0, 0f, 0, 0);
        reg("material_dark_essence","material",   "epic",      "Dark Essence",     "Essence from the shadow realm.",          99, 60, false, 0, 0, 0f, 0, 0);

        // ── Ability items (traversal unlocks) ─────────────────────────────────────
        regAbility("ability_double_jump", "uncommon", "Double Jump Scroll",  "Grants the power of double jump.",       "double_jump");
        regAbility("ability_dash",        "uncommon", "Dash Talisman",       "Grants the power of dash.",              "dash");
        regAbility("ability_wall_jump",   "rare",     "Wall Jump Charm",     "Grants the power of wall jump.",         "wall_jump");
        regAbility("ability_shuriken",    "rare",     "Shuriken Scroll",     "Grants the power to throw shurikens.",   "shuriken");
        regAbility("ability_teleport",    "epic",     "Teleport Crystal",    "Grants the power of teleportation.",     "teleport");
        regAbility("ability_ninjutsu",    "legendary","Ninjutsu Tome",       "Grants mastery of ninjutsu.",            "ninjutsu");
    }

    private static void reg(String id, String type, String rarity, String name, String desc,
                             int stack, int value, boolean consumable,
                             int atk, int def, float spd, int hp, int restore) {
        ITEMS.put(id, ItemDef.of(id, type, rarity, name, desc,
                                 stack, value, consumable, atk, def, spd, hp, restore));
    }

    /** Register an ability item. abilityId must match the string used in SimPlayer.unlockedAbilities. */
    private static void regAbility(String id, String rarity, String name, String desc, String abilityId) {
        ITEMS.put(id, new ItemDef(id, "ability", rarity, name, desc,
                                  1, 0, false, 0, 0, 0f, 0, 0, abilityId));
    }

    /**
     * Replace the entire item map at runtime (e.g. after loading from DB).
     * Thread-safe: builds a new map then swaps the reference.
     */
    public static void reload(java.util.Collection<ItemDef> defs) {
        Map<String, ItemDef> fresh = new HashMap<>(defs.size() * 2);
        for (ItemDef d : defs) fresh.put(d.id(), d);
        ITEMS.clear();
        ITEMS.putAll(fresh);
    }

    public static ItemDef get(String id) {
        return ITEMS.get(id);
    }

    public static Collection<String> allIds() {
        return ITEMS.keySet();
    }

    public static java.util.Collection<ItemDef> allDefs() {
        return ITEMS.values();
    }

    /** Price multiplier by rarity (mirrors Python RARITY_PRICE_MULTIPLIERS). */
    public static float rarityMult(String rarity) {
        return switch (rarity != null ? rarity : "common") {
            case "uncommon"  -> 2f;
            case "rare"      -> 4f;
            case "epic"      -> 8f;
            case "legendary" -> 16f;
            default          -> 1f;
        };
    }

    private ItemDatabase() {}
}
