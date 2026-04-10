package com.indieniinja.server;

import com.indieniinja.sim.CraftingRecipe;
import com.indieniinja.sim.ItemDatabase;
import com.indieniinja.sim.ItemDatabase.ItemDef;
import com.indieniinja.sim.RecipeBook;
import com.indieniinja.sim.SimInventory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Regression tests for the inventory subsystem (INV-1..INV-6).
 *
 * Tests run entirely in-memory — no live PostgreSQL or Redis required.
 * DB/cache integration is covered by {@link InventoryRepository} and
 * {@link ItemCache} independently.
 */
class InventoryPersistenceTest {

    // ── ItemDatabase reload ───────────────────────────────────────────────────

    @Test
    void itemDatabaseReloadReplacesRegistry() {
        // Arrange: build a minimal replacement set
        List<ItemDef> replacement = List.of(
            ItemDef.of("test_sword", "weapon", "common", "Test Sword", "desc", 1, 10, false, 3, 0, 0f, 0, 0),
            ItemDef.of("test_potion", "consumable", "common", "Test Potion", "desc", 99, 5, true, 0, 0, 0f, 0, 1)
        );

        // Act
        ItemDatabase.reload(replacement);

        // Assert new items are present, old ones are gone
        assertThat(ItemDatabase.get("test_sword")).isNotNull();
        assertThat(ItemDatabase.get("test_potion")).isNotNull();
        assertThat(ItemDatabase.get("weapon_dagger")).isNull();  // old item evicted

        // Restore original data for other tests
        ItemDatabase.reload(originalItems);
    }

    @Test
    void itemDatabaseGetUnknownReturnsNull() {
        assertThat(ItemDatabase.get("nonexistent_item_xyz")).isNull();
    }

    @Test
    void addItemWithUnknownIdReturnsFalse() {
        SimInventory inv = new SimInventory();
        boolean added = inv.addItem("nonexistent_item_xyz", 1);
        assertThat(added).isFalse();
    }

    // ── RecipeBook reload ─────────────────────────────────────────────────────

    @Test
    void recipeBookReloadReplacesRegistry() {
        List<CraftingRecipe> replacement = List.of(
            new CraftingRecipe("test_recipe", "test_sword", 1,
                List.of(new CraftingRecipe.Ingredient("material_iron", 2)),
                "weapon", "test recipe")
        );

        RecipeBook.reload(replacement);

        assertThat(RecipeBook.get("test_recipe")).isNotNull();
        assertThat(RecipeBook.get("craft_dagger")).isNull();    // evicted

        // Restore
        RecipeBook.reload(originalRecipes);
    }

    // ── Ability items ─────────────────────────────────────────────────────────

    @Test
    void abilityItemsAreRegistered() {
        assertThat(ItemDatabase.get("ability_double_jump")).isNotNull();
        assertThat(ItemDatabase.get("ability_dash")).isNotNull();
        assertThat(ItemDatabase.get("ability_wall_jump")).isNotNull();
        assertThat(ItemDatabase.get("ability_teleport")).isNotNull();
        assertThat(ItemDatabase.get("ability_ninjutsu")).isNotNull();
    }

    @Test
    void abilityItemTypeIsCorrect() {
        ItemDef def = ItemDatabase.get("ability_double_jump");
        assertThat(def).isNotNull();
        assertThat(def.type()).isEqualTo("ability");
        assertThat(def.abilityId()).isEqualTo("double_jump");
    }

    @Test
    void abilityItemCanBeAddedToInventory() {
        SimInventory inv = new SimInventory();
        assertThat(inv.addItem("ability_double_jump", 1)).isTrue();
        assertThat(inv.hasItem("ability_double_jump")).isTrue();
        assertThat(inv.hasItem("ability_double_jump", 1)).isTrue();
    }

    @Test
    void hasItemConvenienceReturnsFalseWhenAbsent() {
        SimInventory inv = new SimInventory();
        assertThat(inv.hasItem("ability_dash")).isFalse();
    }

    // ── Inventory serialisation round-trip ────────────────────────────────────

    @Test
    void inventoryToMapFromMapRoundTrip() {
        SimInventory original = new SimInventory();
        original.addCurrency(250);
        original.addItem("weapon_dagger", 1);
        original.addItem("health_potion", 5);
        original.equipItem("weapon_dagger");

        Map<String, Object> map = original.toMap();
        SimInventory restored = SimInventory.fromMap(map);

        assertThat(restored.currency).isEqualTo(250);
        assertThat(restored.countItem("weapon_dagger")).isEqualTo(1);
        assertThat(restored.countItem("health_potion")).isEqualTo(5);
        assertThat(restored.equippedWeapon).isEqualTo("weapon_dagger");
    }

    @Test
    void emptyInventoryRoundTrip() {
        SimInventory inv = new SimInventory();
        SimInventory restored = SimInventory.fromMap(inv.toMap());
        assertThat(restored.currency).isZero();
        assertThat(restored.equippedWeapon).isNull();
        assertThat(restored.equippedArmor).isNull();
    }

    // ── Crafting consistency — coin/currency fix (INV-5) ─────────────────────

    @Test
    void craftIronFromCoinSucceedsWhenCurrencyIsAvailable() {
        SimInventory inv = new SimInventory();
        inv.addCurrency(10);                         // 10 coins in currency field

        CraftingRecipe recipe = RecipeBook.get("craft_iron_from_coin");
        assertThat(recipe).as("craft_iron_from_coin recipe must exist").isNotNull();

        assertThat(recipe.canCraft(inv)).isTrue();
        boolean crafted = recipe.craft(inv);

        assertThat(crafted).isTrue();
        assertThat(inv.currency).isZero();            // 10 coins consumed
        assertThat(inv.countItem("material_iron")).isEqualTo(3); // 3 iron produced
    }

    @Test
    void craftIronFromCoinFailsWhenInsufficientCurrency() {
        SimInventory inv = new SimInventory();
        inv.addCurrency(9);                          // 1 short of the required 10

        CraftingRecipe recipe = RecipeBook.get("craft_iron_from_coin");
        assertThat(recipe.canCraft(inv)).isFalse();
        assertThat(recipe.craft(inv)).isFalse();
        assertThat(inv.currency).isEqualTo(9);       // unchanged
    }

    @Test
    void craftIronFromCoinDoesNotConsumeSlotItems() {
        // Coins must be taken from currency field, not from any slot item named "coin"
        SimInventory inv = new SimInventory();
        inv.addCurrency(10);
        // Manually force a "coin" slot entry (should not be touched by crafting)
        inv.slots[0] = new SimInventory.Slot("coin", 99, false);

        CraftingRecipe recipe = RecipeBook.get("craft_iron_from_coin");
        recipe.craft(inv);

        assertThat(inv.currency).isZero();            // currency drained
        assertThat(inv.slots[0]).isNotNull();          // slot coin untouched
        assertThat(inv.slots[0].quantity()).isEqualTo(99);
    }

    @Test
    void normalRecipeStillConsumesSlotIngredients() {
        SimInventory inv = new SimInventory();
        inv.addItem("material_iron", 2);

        CraftingRecipe recipe = RecipeBook.get("craft_dagger");
        assertThat(recipe.canCraft(inv)).isTrue();
        recipe.craft(inv);

        assertThat(inv.countItem("material_iron")).isZero();
        assertThat(inv.countItem("weapon_dagger")).isEqualTo(1);
    }

    // ── ItemCache (no-Redis path) ─────────────────────────────────────────────

    @Test
    void itemCacheWithNullPoolIsAlwaysMiss() {
        ItemCache cache = new ItemCache(null);
        assertThat(cache.getAll()).isNull();           // cache miss, no exception
    }

    @Test
    void itemCacheInvalidateWithNullPoolIsNoOp() {
        ItemCache cache = new ItemCache(null);
        cache.invalidate();                            // must not throw
    }

    @Test
    void itemCachePutAllWithNullPoolIsNoOp() {
        ItemCache cache = new ItemCache(null);
        cache.putAll(ItemDatabase.allDefs());          // must not throw
    }

    // ── Setup: snapshot default registries before any reload test ────────────

    private List<ItemDef>         originalItems;
    private List<CraftingRecipe>  originalRecipes;

    @BeforeEach
    void snapshotDefaults() {
        originalItems   = List.copyOf(ItemDatabase.allDefs());
        originalRecipes = List.copyOf(RecipeBook.all());
    }
}
