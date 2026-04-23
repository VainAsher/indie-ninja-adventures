package com.indieniinja.client.ui;

import com.indieniinja.client.rendering.HudRenderer;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;

class ClientConstructorGuardTest {

    @Test
    void overlayConstructorsAreHeadlessSafe() {
        assertDoesNotThrow(() -> {
            HudRenderer hudRenderer = new HudRenderer();
            hudRenderer.dispose();

            DialogueOverlay dialogueOverlay = new DialogueOverlay(null);
            dialogueOverlay.dispose();

            InventoryOverlay inventoryOverlay = new InventoryOverlay();
            inventoryOverlay.dispose();

            CraftingOverlay craftingOverlay = new CraftingOverlay();
            craftingOverlay.dispose();

            ShopOverlay shopOverlay = new ShopOverlay();
            shopOverlay.dispose();

            MissionSelectOverlay missionSelectOverlay = new MissionSelectOverlay(null);
            missionSelectOverlay.dispose();

            MinimapRenderer minimapRenderer = new MinimapRenderer();
            minimapRenderer.dispose();
        });
    }

    @Test
    void screenConstructorsAreHeadlessSafe() {
        assertDoesNotThrow(() -> {
            ModeSelectScreen modeSelectScreen = new ModeSelectScreen(null, "localhost", 7777);
            modeSelectScreen.dispose();

            SlotSelectScreen slotSelectScreen = new SlotSelectScreen(null, "localhost", 7777);
            slotSelectScreen.dispose();

            MainMenuScreen mainMenuScreen = new MainMenuScreen(null, "localhost", 7777);
            mainMenuScreen.dispose();

            PauseScreen pauseScreen = new PauseScreen(null, () -> {});
            pauseScreen.dispose();

            UiStyle.build().dispose();
        });
    }
}
