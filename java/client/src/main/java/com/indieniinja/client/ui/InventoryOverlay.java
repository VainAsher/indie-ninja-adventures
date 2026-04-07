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

/**
 * Inventory overlay — toggled with the I key.
 *
 * Renders a 4×5 grid of item slots, equipped weapon/armor, and currency.
 * Drawn in screen-space (caller must set screen-space projection on batch).
 *
 * Port of Python ui/inventory_ui.py InventoryUI.
 */
public final class InventoryOverlay {

    private static final int   COLS       = 4;
    private static final int   ROWS       = 5;
    private static final float SLOT_SIZE  = 48f;
    private static final float SLOT_PAD   = 4f;
    private static final float PANEL_PAD  = 16f;

    private boolean visible = false;

    private final BitmapFont    font;
    private final ShapeRenderer shapes;
    private final GlyphLayout   layout = new GlyphLayout();

    public InventoryOverlay() {
        font   = new BitmapFont();
        shapes = new ShapeRenderer();
    }

    /** Toggle visibility; returns true if now open. */
    public boolean toggle() {
        visible = !visible;
        return visible;
    }

    public boolean isVisible() { return visible; }

    public void hide() { visible = false; }

    /**
     * Handle input — must be called before render().
     * Returns true if input was consumed by the overlay.
     */
    public boolean handleInput() {
        if (!visible) return false;
        // I or ESC closes
        if (Gdx.input.isKeyJustPressed(Input.Keys.I)
                || Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            visible = false;
        }
        return true;  // consume all input while open
    }

    /**
     * Render the inventory panel.
     *
     * @param batch SpriteBatch with screen-space projection already set.
     *              Caller must begin/end the batch.
     * @param snap  Latest player state for the local player slot.
     */
    public void render(SpriteBatch batch, PlayerState snap) {
        if (!visible || snap == null) return;

        InventoryState inv = snap.inventory;
        if (inv == null) inv = new InventoryState();

        float sw = Gdx.graphics.getWidth();
        float sh = Gdx.graphics.getHeight();

        float panelW = COLS * (SLOT_SIZE + SLOT_PAD) + SLOT_PAD + PANEL_PAD * 2f + 120f; // extra for equipped
        float panelH = ROWS * (SLOT_SIZE + SLOT_PAD) + SLOT_PAD + PANEL_PAD * 2f + 40f;
        float panelX = (sw - panelW) * 0.5f;
        float panelY = (sh - panelH) * 0.5f;

        // ── Background ────────────────────────────────────────────────────────
        batch.end();
        shapes.setProjectionMatrix(batch.getProjectionMatrix());
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.05f, 0.05f, 0.15f, 0.92f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.5f, 0.5f, 0.9f, 1f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.end();
        batch.begin();

        // ── Title ─────────────────────────────────────────────────────────────
        font.setColor(0.8f, 0.8f, 1f, 1f);
        font.draw(batch, "INVENTORY  [I] close", panelX + PANEL_PAD, panelY + panelH - PANEL_PAD);

        // ── Currency ──────────────────────────────────────────────────────────
        font.setColor(1f, 0.85f, 0.2f, 1f);
        font.draw(batch, "Coins: " + inv.currency,
            panelX + PANEL_PAD, panelY + panelH - PANEL_PAD - 18f);

        // ── Slot grid ─────────────────────────────────────────────────────────
        float gridX = panelX + PANEL_PAD;
        float gridY = panelY + PANEL_PAD + 10f;

        List<InventoryState.SlotState> slots = inv.slots;

        batch.end();
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        for (int i = 0; i < ROWS * COLS; i++) {
            int col = i % COLS;
            int row = (ROWS - 1) - (i / COLS);  // bottom-up rows
            float sx = gridX + col * (SLOT_SIZE + SLOT_PAD);
            float sy = gridY + row * (SLOT_SIZE + SLOT_PAD);

            InventoryState.SlotState slot = (i < slots.size()) ? slots.get(i) : null;

            if (slot != null && slot.equipped()) {
                shapes.setColor(0.2f, 0.5f, 0.8f, 0.6f);
            } else {
                shapes.setColor(0.15f, 0.15f, 0.25f, 0.8f);
            }
            shapes.rect(sx, sy, SLOT_SIZE, SLOT_SIZE);
        }
        shapes.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.35f, 0.35f, 0.6f, 1f);
        for (int i = 0; i < ROWS * COLS; i++) {
            int col = i % COLS;
            int row = (ROWS - 1) - (i / COLS);
            float sx = gridX + col * (SLOT_SIZE + SLOT_PAD);
            float sy = gridY + row * (SLOT_SIZE + SLOT_PAD);
            shapes.rect(sx, sy, SLOT_SIZE, SLOT_SIZE);
        }
        shapes.end();
        batch.begin();

        // ── Item labels inside slots ──────────────────────────────────────────
        for (int i = 0; i < ROWS * COLS; i++) {
            int col = i % COLS;
            int row = (ROWS - 1) - (i / COLS);
            float sx = gridX + col * (SLOT_SIZE + SLOT_PAD);
            float sy = gridY + row * (SLOT_SIZE + SLOT_PAD);
            InventoryState.SlotState slot = (i < slots.size()) ? slots.get(i) : null;
            if (slot == null) continue;

            // Abbreviated item name
            String label = abbreviate(slot.itemId());
            font.setColor(slot.equipped() ? Color.CYAN : Color.WHITE);
            layout.setText(font, label);
            font.draw(batch, label,
                sx + (SLOT_SIZE - layout.width) * 0.5f,
                sy + SLOT_SIZE * 0.55f + layout.height * 0.5f);

            // Quantity (bottom-right)
            if (slot.quantity() > 1) {
                font.setColor(0.8f, 0.8f, 0.4f, 1f);
                font.draw(batch, "×" + slot.quantity(),
                    sx + SLOT_SIZE - 20f, sy + 14f);
            }
        }

        // ── Equipped panel (right of grid) ────────────────────────────────────
        float eqX = gridX + COLS * (SLOT_SIZE + SLOT_PAD) + 8f;
        float eqY = gridY + ROWS * (SLOT_SIZE + SLOT_PAD) - 20f;

        font.setColor(0.7f, 0.9f, 1f, 1f);
        font.draw(batch, "Equipped:", eqX, eqY);
        eqY -= 18f;

        font.setColor(Color.YELLOW);
        font.draw(batch, "Wpn: " + (inv.equippedWeapon != null ? abbreviate(inv.equippedWeapon) : "—"),
            eqX, eqY);
        eqY -= 16f;
        font.draw(batch, "Arm: " + (inv.equippedArmor != null ? abbreviate(inv.equippedArmor) : "—"),
            eqX, eqY);

        font.setColor(Color.WHITE);
    }

    /** Shorten item ID to a compact display label. */
    private static String abbreviate(String itemId) {
        if (itemId == null) return "?";
        // weapon_steel_sword → Stl.Sw
        // health_potion → H.Pot
        // coin → Coin
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
                // Trim "weapon_" / "armor_" prefix, cap at 6 chars
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
