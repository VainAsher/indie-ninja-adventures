"""
Phase 6: Integration & UI Tests

Tests for UI components and play mode system.

Version: v0.6.0 (Phase 6)
"""

import unittest
import pygame
from game.play_mode import (
    PlayMode, PlayModeManager, ArcadeModeConfig, CampaignModeConfig,
    PlaytestModeConfig, get_mode_settings
)
from rendering.objective_hud import (
    ObjectiveHUDRenderer, ObjectiveDisplay,
    create_kill_objective, create_collect_objective
)
from rendering.loot_notification import (
    LootNotificationManager, LootNotification
)
from ui.inventory_ui import InventoryUI
from ui.shop_ui import ShopUI
from ui.mission_menu import MissionMenuUI, MissionDisplay, MissionStatus


class TestPlayModeSystem(unittest.TestCase):
    """Test play mode management"""

    def test_play_mode_enum(self):
        """Test play mode enum values"""
        self.assertEqual(PlayMode.ARCADE.value, "arcade")
        self.assertEqual(PlayMode.CAMPAIGN.value, "campaign")
        self.assertEqual(PlayMode.PLAYTEST.value, "playtest")

    def test_arcade_mode_start(self):
        """Test starting arcade mode"""
        manager = PlayModeManager()
        config = manager.start_arcade_mode(seed=42, shape="snake", rooms=10)

        self.assertTrue(manager.is_arcade_mode())
        self.assertFalse(manager.is_campaign_mode())
        self.assertEqual(config.seed, 42)
        self.assertEqual(config.shape, "snake")
        self.assertEqual(config.rooms, 10)

    def test_campaign_mode_start(self):
        """Test starting campaign mode"""
        manager = PlayModeManager()
        config = manager.start_campaign_mode(world_seed=12345)

        self.assertTrue(manager.is_campaign_mode())
        self.assertFalse(manager.is_arcade_mode())
        self.assertEqual(config.world_seed, 12345)
        self.assertEqual(config.current_hub, "central_hub")

    def test_playtest_mode_start(self):
        """Test starting playtest mode"""
        manager = PlayModeManager()
        config = manager.start_playtest_mode(
            mission_id="forest_1",
            region_id="forest",
            seed=99
        )

        self.assertTrue(manager.is_playtest_mode())
        self.assertEqual(config.mission_id, "forest_1")
        self.assertEqual(config.region_id, "forest")
        self.assertEqual(config.seed, 99)

    def test_mode_settings(self):
        """Test mode-specific settings"""
        arcade_settings = get_mode_settings(PlayMode.ARCADE)
        self.assertTrue(arcade_settings["infinite_progression"])
        self.assertTrue(arcade_settings["replay_enabled"])

        campaign_settings = get_mode_settings(PlayMode.CAMPAIGN)
        self.assertFalse(campaign_settings["infinite_progression"])
        self.assertTrue(campaign_settings["mission_based"])

    def test_mode_reset(self):
        """Test resetting play mode"""
        manager = PlayModeManager()
        manager.start_arcade_mode()
        self.assertTrue(manager.is_arcade_mode())

        manager.reset()
        self.assertIsNone(manager.current_mode)
        self.assertFalse(manager.is_arcade_mode())


class TestObjectiveHUD(unittest.TestCase):
    """Test objective HUD rendering"""

    @classmethod
    def setUpClass(cls):
        """Initialize pygame for rendering tests"""
        pygame.init()

    def test_objective_creation(self):
        """Test creating objectives"""
        obj = create_kill_objective(enemy_count=10, killed=5)

        self.assertEqual(obj.description, "Defeat all enemies")
        self.assertEqual(obj.current, 5)
        self.assertEqual(obj.target, 10)
        self.assertFalse(obj.completed)

    def test_objective_completion(self):
        """Test objective completion"""
        obj = create_collect_objective("Keys", count=3, collected=3)

        self.assertTrue(obj.completed)

    def test_objective_hud_renderer(self):
        """Test creating objective HUD renderer"""
        renderer = ObjectiveHUDRenderer()

        # Should not crash
        surface = pygame.Surface((800, 600))
        objectives = [
            create_kill_objective(10, 5),
            create_collect_objective("Keys", 3, 2)
        ]

        renderer.draw_objectives(surface, objectives)

    def test_objective_complete_popup(self):
        """Test objective completion popup"""
        renderer = ObjectiveHUDRenderer()
        surface = pygame.Surface((800, 600))

        # Should not crash
        renderer.draw_objective_complete_popup(surface, "Defeat all enemies")


class TestLootNotifications(unittest.TestCase):
    """Test loot notification system"""

    @classmethod
    def setUpClass(cls):
        """Initialize pygame"""
        pygame.init()

    def test_loot_notification_creation(self):
        """Test creating loot notification"""
        import time
        notif = LootNotification(
            item_id="sword_1",
            item_name="Iron Sword",
            quantity=1,
            notification_type="item",
            timestamp=time.time()
        )

        self.assertEqual(notif.item_name, "Iron Sword")
        self.assertEqual(notif.quantity, 1)

    def test_loot_notification_manager(self):
        """Test loot notification manager"""
        manager = LootNotificationManager()

        self.assertEqual(manager.get_notification_count(), 0)

        manager.add_item_pickup("sword_1", "Iron Sword")
        self.assertEqual(manager.get_notification_count(), 1)

        manager.add_currency_pickup(50)
        self.assertEqual(manager.get_notification_count(), 2)

    def test_loot_notification_rendering(self):
        """Test loot notification rendering"""
        manager = LootNotificationManager()
        manager.add_item_pickup("sword_1", "Iron Sword")

        surface = pygame.Surface((800, 600))
        manager.draw(surface)  # Should not crash

    def test_loot_notification_expiry(self):
        """Test notification expiry"""
        import time
        notif = LootNotification(
            item_id="test",
            item_name="Test",
            quantity=1,
            notification_type="item",
            timestamp=time.time() - 5.0,  # 5 seconds ago
            duration=3.0  # 3 second duration
        )

        self.assertTrue(notif.is_expired(time.time()))


class TestInventoryUI(unittest.TestCase):
    """Test inventory UI"""

    @classmethod
    def setUpClass(cls):
        """Initialize pygame"""
        pygame.init()

    def test_inventory_ui_creation(self):
        """Test creating inventory UI"""
        ui = InventoryUI()
        self.assertFalse(ui.is_open())

    def test_inventory_ui_open_close(self):
        """Test opening/closing inventory"""
        ui = InventoryUI()

        ui.open()
        self.assertTrue(ui.is_open())

        ui.close()
        self.assertFalse(ui.is_open())

        ui.toggle()
        self.assertTrue(ui.is_open())

    def test_inventory_ui_rendering(self):
        """Test inventory rendering"""
        ui = InventoryUI()
        ui.open()

        surface = pygame.Surface((800, 600))
        items = [
            {"name": "Sword", "quantity": 1, "rarity": "common"},
            {"name": "Potion", "quantity": 5, "rarity": "uncommon"}
        ]

        ui.draw(surface, items, currency=100)  # Should not crash


class TestShopUI(unittest.TestCase):
    """Test shop UI"""

    @classmethod
    def setUpClass(cls):
        """Initialize pygame"""
        pygame.init()

    def test_shop_ui_creation(self):
        """Test creating shop UI"""
        ui = ShopUI()
        self.assertFalse(ui.is_open())

    def test_shop_ui_open_close(self):
        """Test opening/closing shop"""
        ui = ShopUI()

        ui.open("Blacksmith")
        self.assertTrue(ui.is_open())

        ui.close()
        self.assertFalse(ui.is_open())

    def test_shop_ui_rendering(self):
        """Test shop rendering"""
        ui = ShopUI()
        ui.open("Blacksmith")

        surface = pygame.Surface((800, 600))
        npc_items = [
            {"name": "Iron Sword", "price": 50, "quantity": 1},
            {"name": "Health Potion", "price": 10, "quantity": 5}
        ]
        player_items = [
            {"name": "Old Sword", "sell_price": 20, "quantity": 1}
        ]

        ui.draw(surface, npc_items, player_items, player_currency=100)  # Should not crash


class TestMissionMenuUI(unittest.TestCase):
    """Test mission menu UI"""

    @classmethod
    def setUpClass(cls):
        """Initialize pygame"""
        pygame.init()

    def test_mission_display_creation(self):
        """Test creating mission display"""
        mission = MissionDisplay(
            mission_id="forest_1",
            mission_name="Forest Patrol",
            region="forest",
            status=MissionStatus.AVAILABLE,
            difficulty=2,
            objectives=["Defeat 5 goblins"],
            requirements=[],
            rewards=["50 Gold"]
        )

        self.assertEqual(mission.mission_name, "Forest Patrol")
        self.assertEqual(mission.difficulty, 2)

    def test_mission_menu_creation(self):
        """Test creating mission menu"""
        menu = MissionMenuUI()
        self.assertFalse(menu.is_open())

    def test_mission_menu_show_hide(self):
        """Test showing/hiding mission menu"""
        menu = MissionMenuUI()
        missions = [
            MissionDisplay(
                mission_id="forest_1",
                mission_name="Forest Patrol",
                region="forest",
                status=MissionStatus.AVAILABLE,
                difficulty=1,
                objectives=["Test"],
                requirements=[],
                rewards=[]
            )
        ]

        menu.show(missions)
        self.assertTrue(menu.is_open())
        self.assertEqual(len(menu.missions), 1)

        menu.hide()
        self.assertFalse(menu.is_open())

    def test_mission_menu_rendering(self):
        """Test mission menu rendering"""
        menu = MissionMenuUI()
        missions = [
            MissionDisplay(
                mission_id="forest_1",
                mission_name="Forest Patrol",
                region="forest",
                status=MissionStatus.AVAILABLE,
                difficulty=2,
                objectives=["Defeat enemies"],
                requirements=[],
                rewards=["Gold"]
            )
        ]

        menu.show(missions)
        surface = pygame.Surface((800, 600))
        menu.draw(surface)  # Should not crash


def run_tests():
    """Run all Phase 6 tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPlayModeSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestObjectiveHUD))
    suite.addTests(loader.loadTestsFromTestCase(TestLootNotifications))
    suite.addTests(loader.loadTestsFromTestCase(TestInventoryUI))
    suite.addTests(loader.loadTestsFromTestCase(TestShopUI))
    suite.addTests(loader.loadTestsFromTestCase(TestMissionMenuUI))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
