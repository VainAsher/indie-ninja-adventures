package com.indieniinja.sim;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Static registry of all crafting recipes.
 *
 * Mirrors Python game/crafting.py RECIPE_BOOK.
 * Recipes are keyed by recipeId for O(1) lookup.
 */
public final class RecipeBook {

    private static final Map<String, CraftingRecipe> BY_ID = new LinkedHashMap<>();
    private static final List<CraftingRecipe>         ALL   = new ArrayList<>();

    static {
        reg("craft_dagger",
            "weapon_dagger",   1,
            List.of(new CraftingRecipe.Ingredient("material_iron", 2)),
            "weapon", "Forge 2 iron ingots into a quick dagger.");

        reg("craft_sword",
            "weapon_sword",    1,
            List.of(new CraftingRecipe.Ingredient("material_iron", 4)),
            "weapon", "A reliable iron sword, crafted from 4 ingots.");

        reg("craft_steel_sword",
            "weapon_steel_sword", 1,
            List.of(
                new CraftingRecipe.Ingredient("material_iron",  5),
                new CraftingRecipe.Ingredient("material_cloth", 1)
            ),
            "weapon", "Superior blade: 5 iron + 1 cloth for the grip.");

        reg("craft_leather_armor",
            "armor_leather",   1,
            List.of(
                new CraftingRecipe.Ingredient("material_leather", 3),
                new CraftingRecipe.Ingredient("material_cloth",   2)
            ),
            "armor", "Light armor from 3 leather and 2 cloth.");

        reg("craft_chain_mail",
            "armor_chain_mail", 1,
            List.of(new CraftingRecipe.Ingredient("material_iron", 6)),
            "armor", "Interlocked chain mail — 6 iron ingots.");

        reg("craft_health_potion",
            "health_potion",   2,
            List.of(new CraftingRecipe.Ingredient("material_cloth", 1)),
            "consumable", "Craft 2 health potions from 1 cloth.");

        reg("craft_medium_potion",
            "health_potion_medium", 1,
            List.of(
                new CraftingRecipe.Ingredient("material_cloth",   2),
                new CraftingRecipe.Ingredient("material_leather", 1)
            ),
            "consumable", "Stronger potion: 2 cloth + 1 leather.");

        reg("craft_iron_from_coin",
            "material_iron",   3,
            List.of(new CraftingRecipe.Ingredient("coin", 10)),
            "material", "Trade 10 coins for 3 iron ingots.");
    }

    private static void reg(String id, String outputId, int qty,
                             List<CraftingRecipe.Ingredient> ings,
                             String cat, String desc) {
        CraftingRecipe r = new CraftingRecipe(id, outputId, qty, ings, cat, desc);
        BY_ID.put(id, r);
        ALL.add(r);
    }

    /** All recipes in definition order. */
    public static List<CraftingRecipe> all() { return Collections.unmodifiableList(ALL); }

    /**
     * Replace the entire recipe registry at runtime (e.g. after loading from DB).
     * Rebuilds both the ordered list and the by-id map atomically.
     */
    public static void reload(List<CraftingRecipe> recipes) {
        BY_ID.clear();
        ALL.clear();
        for (CraftingRecipe r : recipes) {
            BY_ID.put(r.recipeId, r);
            ALL.add(r);
        }
    }

    /** Look up a recipe by ID, or null if unknown. */
    public static CraftingRecipe get(String recipeId) { return BY_ID.get(recipeId); }

    /** All recipes for a given category ("weapon", "armor", "consumable", "material"). */
    public static List<CraftingRecipe> byCategory(String cat) {
        List<CraftingRecipe> result = new ArrayList<>();
        for (CraftingRecipe r : ALL) if (cat.equals(r.category)) result.add(r);
        return result;
    }

    private RecipeBook() {}
}
