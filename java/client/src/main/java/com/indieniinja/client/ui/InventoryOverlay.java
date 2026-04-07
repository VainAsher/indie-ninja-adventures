package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.GlyphLayout;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.InventoryState;
import com.indieniinja.network.PlayerState;

import java.util.List;
import java.util.function.Consumer;

/**
 * Inventory overlay — toggled with the I key.
 *
 * Renders a 4×5 grid of item slots with keyboard navigation:
 *   Arrow keys — move selection
 *   U           — use consumable in selected slot
 *   E           — equip / unequip weapon or armor in selected slot
 *   I / ESC     — close
 *
 * Port of Python ui/inventory_ui.py InventoryUI.
 */
public final class InventoryOverlay {

    private static final int   COLS       = 4;
    private static final int   ROWS       = 5;
    private static final float SLOT_SIZE  = 52f;
    private static final float SLOT_PAD   =  5f;
    private static final float PANEL_PAD  = 18f;

    private boolean visible     = false;
    private int     selectedIdx = 0;

    // Callbacks wired by GameScreen
    private Consumer<String> onUseItem   = id -> {};
    private Consumer<String> onEquipItem = id -> {};

    private final BitmapFont    font;
    private final ShapeRenderer shapes;
    private final GlyphLayout   layout = new GlyphLayout();

    public InventoryOverlay() {
        font   = new BitmapFont();
        shapes = new ShapeRenderer();
    }

    public void setOnUseItem(Consumer<String> cb)   { this.onUseItem   = cb; }
    public void setOnEquipItem(Consumer<String> cb) { this.onEquipItem = cb; }

    /** Toggle visibility; returns true if now open. */
    public boolean toggle() {
        visible = !visible;
        if (visible) selectedIdx = 0;
        return visible;
    }

    public boolean isVisible() { return visible; }

    public void hide() { visible = false; }

    /**
     * Handle keyboard input — call before render().
     * Returns true if input was consumed by the overlay.
     */
    public boolean handleInput() {
        if (!visible) return false;

        // Navigation
        if (Gdx.input.isKeyJustPressed(Input.Keys.LEFT)) {
            selectedIdx = (selectedIdx - 1 + COLS * ROWS) % (COLS * ROWS);
        } else if (Gdx.input.isKeyJustPressed(Input.Keys.RIGHT)) {
            selectedIdx = (selectedIdx + 1) % (COLS * ROWS);
        } else if (Gdx.input.isKeyJustPressed(Input.Keys.UP)) {
            selectedIdx = (selectedIdx - COLS + COLS * ROWS) % (COLS * ROWS);
        } else if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN)) {
            selectedIdx = (selectedIdx + COLS) % (COLS * ROWS);
        }

        // Actions — stashed so GameScreen can supply the current snap via render()
        // We resolve the item ID inside render() by reading the latest snap there;
        // here we just flag which action was requested this frame.
        if (Gdx.input.isKeyJustPressed(Input.Keys.U)) {
            pendingUse   = true;
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.E)) {
            pendingEquip = true;
        }

        // Close
        if (Gdx.input.isKeyJustPressed(Input.Keys.I)
                || Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            visible = false;
        }
        return true;  // consume all input while open
    }

    /** Set by handleInput(), consumed in render() to fire callbacks with item ID. */
    private boolean pendingUse   = false;
    private boolean pendingEquip = false;

    /**
     * Render the inventory panel and fire any pending item actions.
     *
     * @param batch SpriteBatch with screen-space projection (caller manages begin/end).
     * @param snap  Latest player state for the local player slot; may be null.
     */
    public void render(SpriteBatch batch, PlayerState snap) {
        if (!visible || snap == null) return;

        InventoryState inv = snap.inventory;
        if (inv == null) inv = new InventoryState();

        List<InventoryState.SlotState> slots = inv.slots;
        int totalSlots = COLS * ROWS;

        // ── Fire pending actions ──────────────────────────────────────────────
        if (pendingUse || pendingEquip) {
            if (selectedIdx < slots.size() && slots.get(selectedIdx) != null) {
                String itemId = slots.get(selectedIdx).itemId();
                if (pendingUse)   onUseItem.accept(itemId);
                if (pendingEquip) onEquipItem.accept(itemId);
            }
            pendingUse   = false;
            pendingEquip = false;
        }

        float sw = Gdx.graphics.getWidth();
        float sh = Gdx.graphics.getHeight();

        float gridAreaW = COLS * (SLOT_SIZE + SLOT_PAD) + SLOT_PAD;
        float equipW    = 130f;
        float panelW    = gridAreaW + equipW + PANEL_PAD * 2f;
        float panelH    = ROWS * (SLOT_SIZE + SLOT_PAD) + SLOT_PAD + PANEL_PAD * 2f + 46f;
        float panelX    = (sw - panelW) * 0.5f;
        float panelY    = (sh - panelH) * 0.5f;

        // ── Background ────────────────────────────────────────────────────────
        batch.end();
        shapes.setProjectionMatrix(batch.getProjectionMatrix());
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.05f, 0.05f, 0.15f, 0.93f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.5f, 0.5f, 0.9f, 1f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.end();

        // ── Slot backgrounds + selection highlight ────────────────────────────
        float gridX = panelX + PANEL_PAD;
        float gridY = panelY + PANEL_PAD + 10f;

        shapes.begin(ShapeRenderer.ShapeType.Filled);
        for (int i = 0; i < totalSlots; i++) {
            int col = i % COLS;
            int row = (ROWS - 1) - (i / COLS);
            float sx = gridX + col * (SLOT_SIZE + SLOT_PAD);
            float sy = gridY + row * (SLOT_SIZE + SLOT_PAD);
            InventoryState.SlotState slot = (i < slots.size()) ? slots.get(i) : null;

            if (i == selectedIdx) {
                shapes.setColor(0.4f, 0.4f, 0.85f, 0.75f);  // selection
            } else if (slot != null && slot.equipped()) {
                shapes.setColor(0.2f, 0.5f, 0.8f, 0.55f);   // equipped
            } else {
                shapes.setColor(0.15f, 0.15f, 0.25f, 0.8f);  // normal
            }
            shapes.rect(sx, sy, SLOT_SIZE, SLOT_SIZE);
        }
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        for (int i = 0; i < totalSlots; i++) {
            int col = i % COLS;
            int row = (ROWS - 1) - (i / COLS);
            float sx = gridX + col * (SLOT_SIZE + SLOT_PAD);
            float sy = gridY + row * (SLOT_SIZE + SLOT_PAD);
            if (i == selectedIdx) {
                shapes.setColor(0.9f, 0.9f, 1f, 1f);
            } else {
                shapes.setColor(0.35f, 0.35f, 0.6f, 1f);
            }
            shapes.rect(sx, sy, SLOT_SIZE, SLOT_SIZE);
        }
        shapes.end();

        batch.begin();

        // ── Title ─────────────────────────────────────────────────────────────
        font.setColor(0.8f, 0.8f, 1f, 1f);
        font.draw(batch, "INVENTORY", panelX + PANEL_PAD, panelY + panelH - PANEL_PAD);

        // ── Controls hint ─────────────────────────────────────────────────────
        font.getData().setScale(0.72f);
        font.setColor(0.6f, 0.6f, 0.8f, 1f);
        font.draw(batch, "[Arrows] nav  [U] use  [E] equip  [I/ESC] close",
            panelX + PANEL_PAD, panelY + panelH - PANEL_PAD - 16f);
        font.getData().setScale(1f);

        // ── Currency ──────────────────────────────────────────────────────────
        font.setColor(1f, 0.85f, 0.2f, 1f);
        font.draw(batch, "◆ " + inv.currency + "g",
            panelX + PANEL_PAD, panelY + panelH - PANEL_PAD - 32f);

        // ── Item labels ───────────────────────────────────────────────────────
        for (int i = 0; i < totalSlots; i++) {
            int col = i % COLS;
            int row = (ROWS - 1) - (i / COLS);
            float sx = gridX + col * (SLOT_SIZE + SLOT_PAD);
            float sy = gridY + row * (SLOT_SIZE + SLOT_PAD);
            InventoryState.SlotState slot = (i < slots.size()) ? slots.get(i) : null;
            if (slot == null) continue;

            String label = abbreviate(slot.itemId());
            font.setColor(slot.equipped() ? Color.CYAN : i == selectedIdx ? Color.WHITE : new Color(0.85f, 0.85f, 0.85f, 1f));
            layout.setText(font, label);
            font.draw(batch, label,
                sx + (SLOT_SIZE - layout.width) * 0.5f,
                sy + SLOT_SIZE * 0.58f + layout.height * 0.5f);

            if (slot.quantity() > 1) {
                font.getData().setScale(0.72f);
                font.setColor(0.8f, 0.8f, 0.4f, 1f);
                font.draw(batch, "×" + slot.quantity(), sx + SLOT_SIZE - 22f, sy + 14f);
                font.getData().setScale(1f);
            }
        }

        // ── Selected item detail (bottom of grid) ─────────────────────────────
        if (selectedIdx < slots.size() && slots.get(selectedIdx) != null) {
            InventoryState.SlotState sel = slots.get(selectedIdx);
            font.getData().setScale(0.80f);
            font.setColor(0.9f, 0.9f, 1f, 1f);
            font.draw(batch, sel.itemId().replace("_", " "),
                gridX, gridY - 4f);
            font.getData().setScale(1f);
        }

        // ── Equipped panel (right of grid) ────────────────────────────────────
        float eqX = gridX + COLS * (SLOT_SIZE + SLOT_PAD) + 12f;
        float eqY = gridY + ROWS * (SLOT_SIZE + SLOT_PAD) - 4f;

        font.setColor(0.7f, 0.9f, 1f, 1f);
        font.draw(batch, "Equipped:", eqX, eqY);
        eqY -= 20f;

        font.setColor(Color.YELLOW);
        font.draw(batch, "Wpn:", eqX, eqY);
        font.setColor(Color.WHITE);
        font.draw(batch, inv.equippedWeapon != null ? abbreviate(inv.equippedWeapon) : "—",
            eqX + 36f, eqY);
        eqY -= 18f;

        font.setColor(Color.YELLOW);
        font.draw(batch, "Arm:", eqX, eqY);
        font.setColor(Color.WHITE);
        font.draw(batch, inv.equippedArmor != null ? abbreviate(inv.equippedArmor) : "—",
            eqX + 36f, eqY);

        font.setColor(Color.WHITE);
    }

    /** Shorten item ID to a compact display label. */
    private static String abbreviate(String itemId) {
        if (itemId == null) return "?";
        return switch (itemId) {
            case "weapon_dagger"        -> "Dagger";
            case "weapon_sword"         -> "Sword";
            case "weapon_steel_sword"   -> "Stl.Sw";
            case "weapon_crystal_blade" -> "Crys.Bl";
            case "weapon_dark_blade"    -> "Drk.Bl";
            case "armor_cloth"          -> "Cloth";
            case "armor_leather"        -> "Leathr";
            case "armor_chain_mail"     -> "ChainM";
            case "armor_bark_plate"     -> "BarkPl";
            case "armor_crystal_plate"  -> "CrysPl";
            case "health_potion"        -> "H.Pot";
            case "health_potion_small"  -> "H.PotS";
            case "health_potion_medium" -> "H.PotM";
            case "health_potion_large"  -> "H.PotL";
            case "speed_boost_potion"   -> "SpeedP";
            case "invincibility_potion" -> "InvPot";
            case "max_hp_upgrade"       -> "HPCrys";
            case "coin"                 -> "Coin";
            case "material_iron"        -> "Iron";
            case "material_crystal"     -> "Cryst";
            case "material_dark_essence"-> "DrkEss";
            default -> {
                String s = itemId.replace("weapon_", "").replace("armor_", "")
                                  .replace("material_", "").replace("_", ".");
                yield s.length() > 6 ? s.substring(0, 6) : s;
            }
        };
    }

    public void dispose() {
        font.dispose();
        shapes.dispose();
    }
}
