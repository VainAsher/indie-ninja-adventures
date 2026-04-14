package com.indieniinja.client;

import com.indieniinja.client.game.SaveData;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.ItemDatabase;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimInventory;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class GameScreenSaveRestoreTest {

    @Test
    void restoreSoloPlayerFromSaveIgnoresPositionWhenSavedHubDiffers() throws Exception {
        Harness h = harness("central_hub", 12, 8);
        h.player.physics.x = 128f;
        h.player.physics.y = 256f;
        h.player.physics.vx = 11f;
        h.player.physics.vy = -7f;

        SaveData save = new SaveData();
        save.currentHubId = "other_hub";
        save.currentHubX = 999f;
        save.currentHubY = 777f;

        invokeRestore(h.screen, save);

        assertEquals(128f, h.player.physics.x, 0.0001f);
        assertEquals(256f, h.player.physics.y, 0.0001f);
        assertEquals(11f, h.player.physics.vx, 0.0001f);
        assertEquals(-7f, h.player.physics.vy, 0.0001f);
    }

    @Test
    void restoreSoloPlayerFromSaveClampsSameHubPositionAndResetsVelocity() throws Exception {
        Harness h = harness("central_hub", 2, 2);
        h.player.physics.vx = 5f;
        h.player.physics.vy = -3f;

        SaveData save = new SaveData();
        save.currentHubId = "central_hub";
        save.currentHubX = -50f;
        save.currentHubY = 9999f;

        invokeRestore(h.screen, save);

        float worldPxW = 2f * PhysicsConstants.TILE_SIZE;
        float worldPxH = 2f * PhysicsConstants.TILE_SIZE;
        float maxY = Math.max(0f, worldPxH - h.player.physics.height);

        assertEquals(0f, h.player.physics.x, 0.0001f);
        assertEquals(maxY, h.player.physics.y, 0.0001f);
        assertEquals(0f, h.player.physics.vx, 0.0001f);
        assertEquals(0f, h.player.physics.vy, 0.0001f);
    }

    @Test
    void restoreSoloPlayerFromSaveClampsCurrencyAndCapsOverflowingInventory() throws Exception {
        Harness h = harness("central_hub", 8, 8);
        SaveData save = new SaveData();
        save.currency = SimInventory.MAX_CURRENCY + 12345;
        save.playerInventory = Map.of("health_potion", 99999);

        invokeRestore(h.screen, save);

        int potionStack = ItemDatabase.get("health_potion").maxStack();
        int potionCapacity = SimInventory.MAX_SLOTS * potionStack;

        assertEquals(SimInventory.MAX_CURRENCY, h.player.inventory.currency);
        assertEquals(potionCapacity, h.player.inventory.countItem("health_potion"));
        assertNull(h.player.inventory.equippedWeapon);
        assertNull(h.player.inventory.equippedArmor);
    }

    @Test
    void restoreSoloPlayerFromSaveRehydratesEquipmentAndAbilities() throws Exception {
        Harness h = harness("central_hub", 8, 8);
        SaveData save = new SaveData();
        Map<String, Integer> inventory = new LinkedHashMap<>();
        inventory.put("weapon_sword", 1);
        inventory.put("armor_leather", 1);
        inventory.put("health_potion", 4);
        save.playerInventory = inventory;
        save.equippedWeapon = "weapon_sword";
        save.equippedArmor = "armor_leather";
        save.unlockedAbilities = Arrays.asList("dash", "teleport", "", null, "dash");

        invokeRestore(h.screen, save);

        assertEquals("weapon_sword", h.player.inventory.equippedWeapon);
        assertEquals("armor_leather", h.player.inventory.equippedArmor);
        assertEquals("sword", h.player.weaponState);
        assertEquals(Set.of("dash", "teleport"), h.player.unlockedAbilities);
    }

    private static Harness harness(String hubId, int megamapW, int megamapH) throws Exception {
        GameScreen screen = new GameScreen(null, "localhost", 7777, "solo");
        GameSimulator sim = new GameSimulator(42L, hubId, LevelLayout.buildTestLayout(42L));
        SimPlayer player = new SimPlayer("test_player", 0, 96f, 128f);
        sim.addPlayer(player);

        setField(screen, "localSim", sim);
        setField(screen, "megamapW", megamapW);
        setField(screen, "megamapH", megamapH);
        return new Harness(screen, player);
    }

    private static void invokeRestore(GameScreen screen, SaveData save) throws Exception {
        Method restore = GameScreen.class.getDeclaredMethod("restoreSoloPlayerFromSave", SaveData.class);
        restore.setAccessible(true);
        restore.invoke(screen, save);
    }

    private static void setField(Object target, String fieldName, Object value) throws Exception {
        Field f = target.getClass().getDeclaredField(fieldName);
        f.setAccessible(true);
        f.set(target, value);
    }

    private record Harness(GameScreen screen, SimPlayer player) {}
}
