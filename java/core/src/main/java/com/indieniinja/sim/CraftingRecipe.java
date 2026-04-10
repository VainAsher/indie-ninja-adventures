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
            if (!hasEnough(inv, ing)) return false;
        }
        return true;
    }

    /**
     * Consume ingredients and add the output to the inventory.
     * Returns true on success; false if ingredients are missing.
     */
    public boolean craft(SimInventory inv) {
        if (!canCraft(inv)) return false;
        for (Ingredient ing : ingredients) consume(inv, ing);
        inv.addItem(outputItemId, outputCount);
        return true;
    }

    // ── Currency-aware ingredient helpers ────────────────────────────────────

    /**
     * Returns true when the inventory holds enough of this ingredient.
     * Coins are tracked in {@code SimInventory.currency}, not in slots.
     */
    private static boolean hasEnough(SimInventory inv, Ingredient ing) {
        if ("coin".equals(ing.itemId())) {
            return inv.currency >= ing.count();
        }
        return inv.countItem(ing.itemId()) >= ing.count();
    }

    /**
     * Deduct one ingredient from the inventory.
     * Coins are removed via {@link SimInventory#removeCurrency}.
     */
    private static void consume(SimInventory inv, Ingredient ing) {
        if ("coin".equals(ing.itemId())) {
            inv.removeCurrency(ing.count());
        } else {
            inv.removeItem(ing.itemId(), ing.count());
        }
    }
}
