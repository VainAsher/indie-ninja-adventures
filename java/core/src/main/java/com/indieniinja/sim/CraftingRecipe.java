package com.indieniinja.sim;

import java.util.List;

/**
 * A single crafting recipe — mirrors Python game/crafting.py CraftingRecipe.
 *
 * At a crafting NPC the player can combine ingredients to produce the output item.
 * All item IDs match ItemDatabase entries.
 */
public final class CraftingRecipe {

    public record Ingredient(String itemId, int count) {}

    public final String           recipeId;
    public final String           outputItemId;
    public final int              outputCount;
    public final List<Ingredient> ingredients;
    public final String           category;   // "weapon", "armor", "consumable", "material"
    public final String           description;

    public CraftingRecipe(String recipeId, String outputItemId, int outputCount,
                          List<Ingredient> ingredients, String category, String description) {
        this.recipeId     = recipeId;
        this.outputItemId = outputItemId;
        this.outputCount  = outputCount;
        this.ingredients  = ingredients;
        this.category     = category;
        this.description  = description;
    }

    /** Check whether the given inventory contains all ingredients. */
    public boolean canCraft(SimInventory inv) {
        for (Ingredient ing : ingredients) {
            if (inv.countItem(ing.itemId()) < ing.count()) return false;
        }
        return true;
    }

    /**
     * Consume ingredients and add the output to the inventory.
     * Returns true on success; false if ingredients are missing.
     */
    public boolean craft(SimInventory inv) {
        if (!canCraft(inv)) return false;
        for (Ingredient ing : ingredients) inv.removeItem(ing.itemId(), ing.count());
        inv.addItem(outputItemId, outputCount);
        return true;
    }
}
