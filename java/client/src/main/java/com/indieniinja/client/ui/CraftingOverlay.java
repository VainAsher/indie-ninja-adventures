package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.PlayerState;
import com.indieniinja.sim.CraftingRecipe;
import com.indieniinja.sim.RecipeBook;

import java.util.List;

/**
 * Crafting overlay — shown when E is pressed near a "crafter" NPC.
 *
 * Layout (full-screen modal):
 *   Left panel  — scrollable recipe list, grouped by category
 *   Right panel — selected recipe details: ingredients (green=have, red=missing) + CRAFT button
 *
 * Controls: UP/DOWN select recipe, ENTER/SPACE craft, ESC/E close.
 * Sends CRAFT_REQUEST to server when the player has all ingredients.
 */
public final class CraftingOverlay {

    private static final float OV_W   = 600f;
    private static final float OV_H   = 400f;
    private static final float PAD    = 14f;
    private static final float ROW_H  = 20f;

    private final ShapeRenderer shapes;
    private final BitmapFont    font;

    private boolean visible    = false;
    private int     selected   = 0;
    private final List<CraftingRecipe> recipes = RecipeBook.all();

    /** Inventory snapshot supplied each frame from the local PlayerState. */
    private PlayerState cachedPlayer = null;

    /** Callback called when CRAFT is confirmed — (recipeId) → void. */
    private java.util.function.Consumer<String> onCraft = recipeId -> {};

    public CraftingOverlay() {
        shapes = new ShapeRenderer();
        font   = new BitmapFont();
        font.getData().setScale(0.9f);
    }

    public void setOnCraft(java.util.function.Consumer<String> cb) { this.onCraft = cb; }

    public void open()  { visible = true;  selected = 0; }
    public void close() { visible = false; }
    public boolean isVisible() { return visible; }

    /**
     * Handle input, render, return true if input was consumed.
     * Call with the current local PlayerState so ingredient checks are live.
     */
    public boolean handleInputAndRender(SpriteBatch batch, PlayerState player, float delta) {
        if (!visible) return false;
        cachedPlayer = player;

        // Input
        if (Gdx.input.isKeyJustPressed(Input.Keys.UP))
            selected = Math.max(0, selected - 1);
        if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN))
            selected = Math.min(recipes.size() - 1, selected + 1);
        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)
                || Gdx.input.isKeyJustPressed(Input.Keys.E)) {
            close(); return true;
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER)
                || Gdx.input.isKeyJustPressed(Input.Keys.SPACE)) {
            tryCraft();
        }

        render(batch);
        return true;
    }

    private void tryCraft() {
        if (recipes.isEmpty()) return;
        CraftingRecipe r = recipes.get(selected);
        if (cachedPlayer == null || cachedPlayer.inventory == null) return;
        // Check client-side (inventory state may be slightly stale but gives immediate feedback)
        boolean canCraft = r.ingredients.stream().allMatch(ing ->
            countItem(cachedPlayer.inventory, ing.itemId()) >= ing.count());
        if (canCraft) onCraft.accept(r.recipeId);
    }

    /** Count how many of itemId the player currently has (scans InventoryState slots). */
    private static int countItem(com.indieniinja.network.InventoryState inv, String itemId) {
        if (inv == null || itemId == null) return 0;
        int total = 0;
        for (com.indieniinja.network.InventoryState.SlotState slot : inv.slots) {
            if (slot != null && itemId.equals(slot.itemId())) total += slot.quantity();
        }
        return total;
    }

    private void render(SpriteBatch batch) {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();
        float ox = (sw - OV_W) * 0.5f;
        float oy = (sh - OV_H) * 0.5f;
        float midX = ox + OV_W * 0.5f;

        // Background
        shapes.getProjectionMatrix().setToOrtho2D(0, 0, sw, sh);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0f, 0f, 0f, 0.7f);
        shapes.rect(0, 0, sw, sh);
        shapes.setColor(0.10f, 0.10f, 0.16f, 0.97f);
        shapes.rect(ox, oy, OV_W, OV_H);
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.4f, 0.7f, 0.4f, 1f);
        shapes.rect(ox, oy, OV_W, OV_H);
        shapes.line(midX, oy, midX, oy + OV_H);
        shapes.end();

        // Text
        batch.getProjectionMatrix().setToOrtho2D(0, 0, sw, sh);
        batch.begin();

        // Title
        font.getData().setScale(1.3f);
        font.setColor(0.4f, 0.9f, 0.4f, 1f);
        font.draw(batch, "CRAFTING", ox + PAD, oy + OV_H - 6f);
        font.getData().setScale(0.9f);
        font.setColor(new Color(0.5f, 0.5f, 0.55f, 1f));
        font.draw(batch, "[ \u2191\u2193 ] select   [ ENTER ] craft   [ ESC ] close",
            ox + PAD, oy + OV_H - 26f);

        // Recipe list (left panel)
        float listTop = oy + OV_H - 50f;
        int visible = (int)((OV_H - 60f) / ROW_H);
        int startIdx = Math.max(0, selected - visible / 2);
        for (int i = startIdx; i < Math.min(startIdx + visible, recipes.size()); i++) {
            CraftingRecipe r = recipes.get(i);
            float rowY = listTop - (i - startIdx) * ROW_H;
            if (i == selected) {
                shapes.begin(ShapeRenderer.ShapeType.Filled);
                shapes.setColor(0.2f, 0.35f, 0.2f, 0.85f);
                shapes.rect(ox + 2, rowY - ROW_H + 4f, midX - ox - 4f, ROW_H);
                shapes.end();
                font.setColor(Color.WHITE);
            } else {
                font.setColor(0.65f, 0.65f, 0.70f, 1f);
            }
            // Show item name + green tick if craftable
            boolean canCraft = canCraft(r);
            font.draw(batch,
                (canCraft ? "\u2713 " : "  ") + displayName(r.outputItemId) + " x" + r.outputCount,
                ox + PAD, rowY);
        }

        // Recipe detail (right panel)
        if (!recipes.isEmpty()) {
            CraftingRecipe sel = recipes.get(selected);
            float dx = midX + PAD;
            float dy = listTop;

            font.getData().setScale(1.1f);
            font.setColor(0.9f, 0.9f, 0.9f, 1f);
            font.draw(batch, displayName(sel.outputItemId) + " x" + sel.outputCount, dx, dy);
            font.getData().setScale(0.85f);
            font.setColor(0.55f, 0.55f, 0.60f, 1f);
            font.draw(batch, sel.description, dx, dy - 18f);
            font.draw(batch, "Ingredients:", dx, dy - 38f);

            float iy = dy - 55f;
            for (CraftingRecipe.Ingredient ing : sel.ingredients) {
                int have = cachedPlayer != null && cachedPlayer.inventory != null
                    ? countItem(cachedPlayer.inventory, ing.itemId()) : 0;
                boolean ok = have >= ing.count();
                font.setColor(ok ? new Color(0.3f, 1f, 0.4f, 1f) : new Color(1f, 0.35f, 0.3f, 1f));
                font.draw(batch,
                    displayName(ing.itemId()) + " x" + ing.count() + " (" + have + " owned)",
                    dx, iy);
                iy -= ROW_H;
            }

            // CRAFT button
            boolean craftable = canCraft(sel);
            shapes.begin(ShapeRenderer.ShapeType.Filled);
            shapes.setColor(craftable ? new Color(0.2f, 0.6f, 0.2f, 1f) : new Color(0.25f, 0.25f, 0.25f, 1f));
            shapes.rect(midX + PAD, oy + PAD, OV_W * 0.5f - PAD * 2, 26f);
            shapes.end();
            font.getData().setScale(1.0f);
            font.setColor(craftable ? Color.WHITE : new Color(0.5f, 0.5f, 0.5f, 1f));
            font.draw(batch, craftable ? "[ ENTER ] CRAFT" : "Missing ingredients",
                midX + PAD + 10f, oy + PAD + 18f);
        }

        font.getData().setScale(1f);
        font.setColor(Color.WHITE);
        batch.end();
    }

    private boolean canCraft(CraftingRecipe r) {
        if (cachedPlayer == null || cachedPlayer.inventory == null) return false;
        return r.ingredients.stream().allMatch(ing ->
            countItem(cachedPlayer.inventory, ing.itemId()) >= ing.count());
    }

    private static String displayName(String itemId) {
        if (itemId == null) return "?";
        // Convert snake_case item id to Title Case display name
        String[] parts = itemId.replace("material_", "").replace("weapon_", "")
            .replace("armor_", "").replace("item_", "").split("_");
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            if (!p.isEmpty()) sb.append(Character.toUpperCase(p.charAt(0)))
                .append(p.substring(1)).append(' ');
        }
        return sb.toString().trim();
    }

    public void dispose() {
        shapes.dispose();
        font.dispose();
    }
}
