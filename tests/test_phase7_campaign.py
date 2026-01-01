"""
Phase 7: Campaign System Tests

Tests for Campaign Manager and Save System integration.

Version: v0.6.0 (Phase 7)
"""

import os
import shutil
import sys
import tempfile
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.campaign_manager import (
    CampaignManager,
    Region,
    create_campaign,
    get_region_description,
    get_region_display_name,
)
from systems.save_system import CampaignSaveData, SaveManager


class TestCampaignManager(unittest.TestCase):
    """Test campaign manager functionality"""

    def test_campaign_creation(self):
        """Test creating a new campaign"""
        campaign = create_campaign(world_seed=12345)

        self.assertEqual(campaign.state.world_seed, 12345)
        self.assertIn("central_hub", campaign.state.unlocked_regions)
        self.assertIn("forest", campaign.state.unlocked_regions)
        self.assertIn("basic_movement", campaign.state.unlocked_abilities)
        self.assertIn("jump", campaign.state.unlocked_abilities)

    def test_initial_region_unlocking(self):
        """Test initially unlocked regions"""
        campaign = CampaignManager(world_seed=42)

        self.assertTrue(campaign.is_region_unlocked(Region.CENTRAL_HUB))
        self.assertTrue(campaign.is_region_unlocked(Region.FOREST))
        self.assertFalse(campaign.is_region_unlocked(Region.TOWN))
        self.assertFalse(campaign.is_region_unlocked(Region.CAVES))

    def test_mission_completion(self):
        """Test completing a mission"""
        campaign = CampaignManager(world_seed=100)

        self.assertFalse(campaign.has_completed_mission("forest_1"))

        # Complete mission
        campaign.complete_mission(
            mission_id="forest_1",
            completion_time=120.5,
            abilities_unlocked=["double_jump"],
            currency_reward=50,
        )

        self.assertTrue(campaign.has_completed_mission("forest_1"))
        self.assertTrue(campaign.has_ability("double_jump"))
        self.assertEqual(campaign.state.currency, 50)
        self.assertEqual(campaign.state.mission_best_times["forest_1"], 120.5)

    def test_mission_best_time(self):
        """Test best time tracking"""
        campaign = CampaignManager(world_seed=200)

        # First completion
        campaign.complete_mission("forest_1", 150.0)
        self.assertEqual(campaign.state.mission_best_times["forest_1"], 150.0)

        # Faster time
        campaign.complete_mission("forest_1", 120.0)
        self.assertEqual(campaign.state.mission_best_times["forest_1"], 120.0)

        # Slower time (should not update)
        campaign.complete_mission("forest_1", 180.0)
        self.assertEqual(campaign.state.mission_best_times["forest_1"], 120.0)

    def test_region_unlock_requirements(self):
        """Test region unlock requirements"""
        campaign = CampaignManager(world_seed=300)

        # Town requires 3 forest missions
        can_unlock, missing = campaign.can_unlock_region(Region.TOWN)
        self.assertFalse(can_unlock)
        self.assertEqual(len(missing), 3)

        # Complete forest missions
        campaign.complete_mission("forest_1", 100.0)
        campaign.complete_mission("forest_2", 100.0)
        campaign.complete_mission("forest_3", 100.0)

        can_unlock, missing = campaign.can_unlock_region(Region.TOWN)
        self.assertTrue(can_unlock)
        self.assertEqual(len(missing), 0)

    def test_ability_unlock_requirements(self):
        """Test regions requiring abilities"""
        campaign = CampaignManager(world_seed=400)

        # Caves requires double_jump and dash
        can_unlock, missing = campaign.can_unlock_region(Region.CAVES)
        self.assertFalse(can_unlock)
        self.assertGreater(len(missing), 0)

        # Unlock abilities
        campaign.unlock_ability("double_jump")
        campaign.unlock_ability("dash")

        can_unlock, missing = campaign.can_unlock_region(Region.CAVES)
        self.assertTrue(can_unlock)
        self.assertEqual(len(missing), 0)

    def test_auto_region_unlock(self):
        """Test automatic region unlocking when requirements met"""
        campaign = CampaignManager(world_seed=500)

        self.assertFalse(campaign.is_region_unlocked(Region.TOWN))

        # Complete requirements
        campaign.complete_mission("forest_1", 100.0)
        campaign.complete_mission("forest_2", 100.0)
        campaign.complete_mission("forest_3", 100.0)

        # Should auto-unlock town
        self.assertTrue(campaign.is_region_unlocked(Region.TOWN))

    def test_region_completion_percent(self):
        """Test region completion percentage"""
        campaign = CampaignManager(world_seed=600)

        # No missions completed
        percent = campaign.get_region_completion_percent(Region.FOREST)
        self.assertEqual(percent, 0.0)

        # Complete some missions (forest has 5)
        campaign.complete_mission("forest_1", 100.0)
        campaign.complete_mission("forest_2", 100.0)

        percent = campaign.get_region_completion_percent(Region.FOREST)
        self.assertEqual(percent, 2.0 / 5.0)

        # Complete all missions
        campaign.complete_mission("forest_3", 100.0)
        campaign.complete_mission("forest_4", 100.0)
        campaign.complete_mission("forest_5", 100.0)

        percent = campaign.get_region_completion_percent(Region.FOREST)
        self.assertEqual(percent, 1.0)

    def test_overall_completion(self):
        """Test overall campaign completion"""
        campaign = CampaignManager(world_seed=700)

        # Complete all forest missions (1/5 regions = 20%)
        for i in range(1, 6):
            campaign.complete_mission(f"forest_{i}", 100.0)

        overall = campaign.get_overall_completion_percent()
        self.assertAlmostEqual(overall, 0.2, places=2)

    def test_statistics(self):
        """Test campaign statistics"""
        campaign = CampaignManager(world_seed=800)

        campaign.complete_mission("forest_1", 120.0, currency_reward=50)
        campaign.complete_mission("forest_2", 150.0, currency_reward=75)

        stats = campaign.get_statistics()

        self.assertEqual(stats["completed_missions"], 2)
        self.assertEqual(stats["currency"], 125)
        self.assertEqual(stats["unlocked_regions"], 2)  # central_hub + forest

    def test_save_and_load(self):
        """Test saving and loading campaign state"""
        campaign = CampaignManager(world_seed=900)

        # Make progress
        campaign.complete_mission("forest_1", 100.0, abilities_unlocked=["double_jump"])
        campaign.unlock_ability("dash")
        campaign.state.current_hub = "forest"
        campaign.state.current_position = (100.0, 200.0)

        # Save to dict
        save_dict = campaign.save_to_dict()

        # Create new campaign and load
        new_campaign = CampaignManager(world_seed=0)
        new_campaign.load_from_dict(save_dict)

        # Verify state
        self.assertEqual(new_campaign.state.world_seed, 900)
        self.assertTrue(new_campaign.has_completed_mission("forest_1"))
        self.assertTrue(new_campaign.has_ability("double_jump"))
        self.assertTrue(new_campaign.has_ability("dash"))
        self.assertEqual(new_campaign.state.current_hub, "forest")
        self.assertEqual(new_campaign.state.current_position, (100.0, 200.0))


class TestCampaignSaveSystem(unittest.TestCase):
    """Test save system with campaign data"""

    def setUp(self):
        """Create temporary save directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_manager = SaveManager(save_dir=self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_campaign_save_data_creation(self):
        """Test creating campaign save data"""
        campaign_data = CampaignSaveData(world_seed=12345)

        self.assertEqual(campaign_data.world_seed, 12345)
        self.assertEqual(campaign_data.current_hub_id, "central_hub")
        self.assertIn("forest", campaign_data.unlocked_regions)
        self.assertEqual(campaign_data.currency, 0)

    def test_start_new_campaign(self):
        """Test starting a new campaign"""
        self.save_manager.start_new_campaign(world_seed=42)

        self.assertEqual(self.save_manager.data.campaign.world_seed, 42)
        self.assertTrue(self.save_manager.needs_save)

    def test_complete_mission_save(self):
        """Test completing a mission updates save"""
        self.save_manager.start_new_campaign(world_seed=100)

        self.save_manager.complete_mission(
            mission_id="forest_1",
            completion_time=120.5,
            abilities_unlocked=["double_jump"],
            currency_reward=50,
        )

        campaign = self.save_manager.data.campaign
        self.assertIn("forest_1", campaign.completed_missions)
        self.assertIn("double_jump", campaign.unlocked_abilities)
        self.assertEqual(campaign.currency, 50)
        self.assertEqual(campaign.mission_best_times["forest_1"], 120.5)

    def test_unlock_region_save(self):
        """Test unlocking a region"""
        self.save_manager.start_new_campaign(world_seed=200)

        # First unlock returns True
        result = self.save_manager.unlock_region("town")
        self.assertTrue(result)
        self.assertIn("town", self.save_manager.data.campaign.unlocked_regions)

        # Second unlock returns False
        result = self.save_manager.unlock_region("town")
        self.assertFalse(result)

    def test_save_hub_position(self):
        """Test saving hub position"""
        self.save_manager.start_new_campaign(world_seed=300)

        self.save_manager.save_hub_position("forest", (100.0, 200.0))

        campaign = self.save_manager.data.campaign
        self.assertEqual(campaign.current_hub_id, "forest")
        self.assertEqual(campaign.current_hub_position, (100.0, 200.0))

    def test_save_and_load_inventory(self):
        """Test saving and loading inventory"""
        self.save_manager.start_new_campaign(world_seed=400)

        # Save inventory
        inventory = {"sword_1": 1, "potion": 5, "key": 3}
        self.save_manager.save_inventory(
            inventory_dict=inventory,
            equipped_weapon="sword_1",
            equipped_armor="armor_1",
            currency=150,
        )

        # Load inventory
        loaded = self.save_manager.load_inventory()

        self.assertEqual(loaded["items"], inventory)
        self.assertEqual(loaded["equipped_weapon"], "sword_1")
        self.assertEqual(loaded["equipped_armor"], "armor_1")
        self.assertEqual(loaded["currency"], 150)

    def test_campaign_progress_stats(self):
        """Test getting campaign progress"""
        self.save_manager.start_new_campaign(world_seed=500)

        self.save_manager.complete_mission("forest_1", 100.0, currency_reward=50)
        self.save_manager.unlock_region("town")

        progress = self.save_manager.get_campaign_progress()

        self.assertEqual(progress["world_seed"], 500)
        self.assertEqual(progress["current_hub"], "central_hub")
        self.assertEqual(progress["unlocked_regions"], 3)  # central_hub, forest, town
        self.assertEqual(progress["completed_missions"], 1)
        self.assertEqual(progress["currency"], 50)

    def test_save_and_load_file(self):
        """Test saving to file and loading"""
        self.save_manager.start_new_campaign(world_seed=600)
        self.save_manager.complete_mission("forest_1", 100.0, currency_reward=50)
        self.save_manager.save_inventory({"sword": 1}, currency=50)

        # Save to file
        self.save_manager.save(force=True)

        # Create new manager and load
        new_manager = SaveManager(save_dir=self.temp_dir)
        loaded = new_manager.load()

        self.assertTrue(loaded)
        self.assertEqual(new_manager.data.campaign.world_seed, 600)
        self.assertIn("forest_1", new_manager.data.campaign.completed_missions)
        self.assertEqual(new_manager.data.campaign.currency, 50)
        self.assertEqual(new_manager.data.campaign.player_inventory, {"sword": 1})

    def test_save_version_migration(self):
        """Test migrating from v0.5.0 to v0.6.0"""
        # Create old save data (v0.5.0 without campaign)
        old_save = {
            "version": "0.5.0",
            "save_date": "2024-01-01 12:00:00",
            "player_progress": {
                "levels_completed": ["level_1"],
                "current_level": "level_2",
                "total_playtime": 100.0,
                "total_coins": 50,
                "total_collectibles": 10,
                "total_deaths": 5,
                "best_times": {},
                "tutorials_seen": [],
            },
            "settings": {},
            "statistics": {},
        }

        # Migrate
        migrated = self.save_manager._migrate_save(old_save, "0.5.0")

        # Should have campaign data with defaults
        self.assertIn("campaign", migrated)
        self.assertEqual(migrated["version"], "0.6.0")
        self.assertEqual(migrated["campaign"]["world_seed"], 0)
        self.assertIn("central_hub", migrated["campaign"]["unlocked_regions"])
        self.assertIn("forest", migrated["campaign"]["unlocked_regions"])


class TestRegionHelpers(unittest.TestCase):
    """Test region helper functions"""

    def test_region_display_names(self):
        """Test region display name retrieval"""
        self.assertEqual(get_region_display_name(Region.CENTRAL_HUB), "Central Hub")
        self.assertEqual(get_region_display_name(Region.FOREST), "Whispering Forest")
        self.assertEqual(get_region_display_name(Region.TOWN), "Merchant Town")
        self.assertEqual(get_region_display_name(Region.CAVES), "Crystal Caves")
        self.assertEqual(get_region_display_name(Region.CASTLE), "Dark Castle")
        self.assertEqual(get_region_display_name(Region.SEWER), "Ancient Sewer")

    def test_region_descriptions(self):
        """Test region description retrieval"""
        self.assertEqual(
            get_region_description(Region.CENTRAL_HUB), "Safe haven connecting all regions"
        )
        self.assertEqual(
            get_region_description(Region.FOREST), "Dense woodland filled with creatures"
        )
        self.assertEqual(get_region_description(Region.SEWER), "Ancient depths beneath the castle")


def run_tests():
    """Run all Phase 7 tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestCampaignManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCampaignSaveSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestRegionHelpers))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys

    success = run_tests()
    sys.exit(0 if success else 1)
