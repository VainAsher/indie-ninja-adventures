package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.InventoryState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.ShopState;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * Shop overlay — opened when player presses E on a shop NPC.
 *
 * Two-panel layout:
 *   Left  — NPC shop items (buy)
 *   Right — Player inventory items (sell)
 *
 * Controls:
 *   UP/DOWN  — navigate list
 *   B        — buy selected item from shop
 *   S        — sell selected item from player inventory
 *   TAB      — switch active panel
 *   ESC/E    — close
 *
 * Port of Python ui/shop_ui.py ShopUI.
 */
public final class ShopOverlay {

    private boolean visible = false;
    private ShopState activeShop = null;

    private int selectedShopIdx = 0;
    private int selectedInvIdx  = 0;
    private boolean shopPanelActive = true;  // true = left panel focused

    /** Called when player requests a trade: (npcId, itemId, qty, isBuy). */
    private Consumer<TradeRequest> onTrade;

    public record TradeRequest(String npcId, String itemId, int qty, boolean isBuy) {}

    private final BitmapFont    font;
    private final ShapeRenderer shapes;

    private static final float PANEL_W = 260f;
    private static final float PANEL_H = 320f;
    private static final float PAD     = 12f;
    private static final float ROW_H   = 18f;

    public ShopOverlay() {
        if (Gdx.app != null) {
            font   = new BitmapFont();
            shapes = new ShapeRenderer();
        } else {
            font = null;
            shapes = null;
        }
    }

    public void setOnTrade(Consumer<TradeRequest> handler) { this.onTrade = handler; }

    public boolean isVisible() { return visible; }

    public void open(ShopState shop) {
        activeShop = shop;
        visible    = true;
        selectedShopIdx = 0;
        selectedInvIdx  = 0;
        shopPanelActive = true;
    }

    public void hide() { visible = false; }

    /**
     * Handle input for the shop overlay.
     * Returns true if input was consumed.
     */
    public boolean handleInput(PlayerState localPlayer) {
        if (Gdx.app == null || Gdx.input == null) return false;
        if (!visible) return false;

        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)
                || Gdx.input.isKeyJustPressed(Input.Keys.E)) {
            hide();
            return true;
        }

        // Tab switches panel focus
        if (Gdx.input.isKeyJustPressed(Input.Keys.TAB)) {
            shopPanelActive = !shopPanelActive;
            return true;
        }

        List<ShopState.ShopItemState> shopItems = activeShop != null ? activeShop.items : List.of();
        List<InventoryState.SlotState> invSlots  = inventorySlots(localPlayer);

        if (Gdx.input.isKeyJustPressed(Input.Keys.UP)) {
            if (shopPanelActive) selectedShopIdx = Math.max(0, selectedShopIdx - 1);
            else                 selectedInvIdx  = Math.max(0, selectedInvIdx  - 1);
            return true;
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN)) {
            if (shopPanelActive) selectedShopIdx = Math.min(shopItems.size() - 1, selectedShopIdx + 1);
            else                 selectedInvIdx  = Math.min(invSlots.size()  - 1, selectedInvIdx  + 1);
            return true;
        }

        // B = buy from shop
        if (Gdx.input.isKeyJustPressed(Input.Keys.B) && shopPanelActive) {
            if (activeShop != null && selectedShopIdx < shopItems.size() && onTrade != null) {
                ShopState.ShopItemState item = shopItems.get(selectedShopIdx);
                onTrade.accept(new TradeRequest(activeShop.npcId, item.itemId(), 1, true));
            }
            return true;
        }

        // S = sell from inventory
        if (Gdx.input.isKeyJustPressed(Input.Keys.S) && !shopPanelActive) {
            if (activeShop != null && selectedInvIdx < invSlots.size() && onTrade != null) {
                InventoryState.SlotState slot = invSlots.get(selectedInvIdx);
                if (slot != null) {
                    onTrade.accept(new TradeRequest(activeShop.npcId, slot.itemId(), 1, false));
                }
            }
            return true;
        }

        return true;  // consume all input while open
    }

    /**
     * Render the shop overlay.
     * @param batch SpriteBatch with screen-space projection set. Caller handles begin/end.
     */
    public void render(SpriteBatch batch, PlayerState localPlayer) {
        if (font == null || shapes == null || Gdx.app == null || Gdx.graphics == null) return;
        if (!visible || activeShop == null) return;

        float sw = Gdx.graphics.getWidth();
        float sh = Gdx.graphics.getHeight();

        float totalW = PANEL_W * 2f + PAD * 3f;
        float panelX = (sw - totalW) * 0.5f;
        float panelY = (sh - PANEL_H) * 0.5f - 20f;

        // ── Background ────────────────────────────────────────────────────────
        batch.end();
        shapes.setProjectionMatrix(batch.getProjectionMatrix());
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.04f, 0.04f, 0.14f, 0.93f);
        shapes.rect(panelX - PAD, panelY - PAD, totalW + PAD * 2f, PANEL_H + PAD * 2f + 30f);
        shapes.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.6f, 0.4f, 0.1f, 1f);
        shapes.rect(panelX - PAD, panelY - PAD, totalW + PAD * 2f, PANEL_H + PAD * 2f + 30f);
        shapes.end();
        batch.begin();

        // ── Title ─────────────────────────────────────────────────────────────
        font.setColor(1f, 0.8f, 0.3f, 1f);
        String tierLabel = switch (activeShop.tier) {
            case 2 -> "Uncommon";
            case 3 -> "Rare";
            case 4 -> "Epic";
            case 5 -> "Legendary";
            default -> "Common";
        };
        font.draw(batch, "SHOP  (Tier " + activeShop.tier + " — " + tierLabel + ")  [ESC] close",
            panelX, panelY + PANEL_H + PAD + 18f);
        font.setColor(0.7f, 0.7f, 0.7f, 1f);
        font.draw(batch, "[TAB] switch panel   [B] buy   [S] sell",
            panelX, panelY + PANEL_H + PAD);

        // ── Left panel: shop items ─────────────────────────────────────────────
        renderPanel(batch, "SHOP  (buy)", panelX, panelY, shopPanelActive,
            activeShop.items.stream().map(i -> formatShopItem(i, localPlayer)).toList(),
            selectedShopIdx);

        // ── Right panel: player inventory ─────────────────────────────────────
        List<InventoryState.SlotState> invSlots = inventorySlots(localPlayer);
        List<String> invLines = new ArrayList<>(invSlots.size());
        for (InventoryState.SlotState s : invSlots) {
            if (s == null) continue;
            invLines.add(ItemLabelFormatter.formatInventorySellLine(s.itemId(), s.quantity()));
        }
        renderPanel(batch, "INVENTORY  (sell)", panelX + PANEL_W + PAD, panelY, !shopPanelActive,
            invLines, selectedInvIdx);

        font.setColor(Color.WHITE);
    }

    private void renderPanel(SpriteBatch batch, String title, float x, float y,
                              boolean focused, List<String> lines, int selected) {
        // Border
        batch.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(focused ? new Color(0.8f, 0.6f, 0.2f, 1f) : new Color(0.3f, 0.3f, 0.5f, 1f));
        shapes.rect(x, y, PANEL_W, PANEL_H);
        shapes.end();
        batch.begin();

        font.setColor(focused ? new Color(1f, 0.85f, 0.3f, 1f) : new Color(0.7f, 0.7f, 0.7f, 1f));
        font.draw(batch, title, x + PAD, y + PANEL_H - PAD);

        float rowY = y + PANEL_H - PAD - ROW_H * 1.5f;
        int maxRows = (int)((PANEL_H - PAD * 3f) / ROW_H) - 1;
        int start   = Math.max(0, selected - maxRows / 2);

        for (int i = start; i < lines.size() && i < start + maxRows; i++) {
            boolean sel = (i == selected) && focused;
            font.setColor(sel ? Color.YELLOW : Color.LIGHT_GRAY);
            font.draw(batch, (sel ? "► " : "  ") + lines.get(i), x + PAD, rowY);
            rowY -= ROW_H;
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private String formatShopItem(ShopState.ShopItemState item, PlayerState player) {
        boolean canAfford = player != null && player.inventory != null
            && player.inventory.currency >= item.buyPrice();
        return ItemLabelFormatter.formatShopBuyLine(
            item.itemId(), item.stock(), item.buyPrice(), canAfford);
    }

    private static List<InventoryState.SlotState> inventorySlots(PlayerState p) {
        if (p == null || p.inventory == null) return List.of();
        List<InventoryState.SlotState> result = new ArrayList<>();
        for (InventoryState.SlotState s : p.inventory.slots) {
            if (s != null) result.add(s);
        }
        return result;
    }

    public void dispose() {
        if (font != null) font.dispose();
        if (shapes != null) shapes.dispose();
    }
}
