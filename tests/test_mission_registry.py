"""
Mission Registry Tests

Tests for mission loading and querying functionality.

Version: v0.6.0 (Phase 7)
"""

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.mission_registry import (
    MissionRegistry, MissionDefinition, MissionObjective,
    MissionRewards, ObjectiveType,
    get_mission, get_missions_for_region, count_missions_by_region
)


class TestMissionRegistry(unittest.TestCase):
    """Test mission registry functionality"""

    @classmethod
    def setUpClass(cls):
        """Load missions once for all tests"""
        cls.registry = MissionRegistry()

    def test_mission_loading(self):
        """Test that missions are loaded from JSON"""
        self.assertGreater(self.registry.get_mission_count(), 0)
        print(f"\n[INFO] Loaded {self.registry.get_mission_count()} missions")

    def test_mission_count(self):
        """Test total mission count"""
        # Should have 25 missions total
        self.assertEqual(self.registry.get_mission_count(), 25)

    def test_region_distribution(self):
        """Test mission distribution across regions"""
        counts = count_missions_by_region()

        # Expected distribution
        self.assertEqual(counts.get('forest', 0), 5)
        self.assertEqual(counts.get('town', 0), 6)
        self.assertEqual(counts.get('caves', 0), 5)
        self.assertEqual(counts.get('castle', 0), 6)
        self.assertEqual(counts.get('sewer', 0), 3)

    def test_get_mission_by_id(self):
        """Test retrieving a specific mission"""
        mission = get_mission('forest_1')

        self.assertIsNotNone(mission)
        self.assertEqual(mission.mission_id, 'forest_1')
        self.assertEqual(mission.mission_name, 'Forest Patrol')
        self.assertEqual(mission.region, 'forest')
        self.assertEqual(mission.difficulty, 1)

    def test_mission_objectives(self):
        """Test mission objectives are loaded correctly"""
        mission = get_mission('forest_1')

        self.assertEqual(len(mission.objectives), 2)

        # Check first objective (kill all enemies)
        obj1 = mission.objectives[0]
        self.assertEqual(obj1.objective_type, ObjectiveType.KILL_ALL_ENEMIES)
        self.assertEqual(obj1.target, 5)

        # Check second objective (collect items)
        obj2 = mission.objectives[1]
        self.assertEqual(obj2.objective_type, ObjectiveType.COLLECT_ITEMS)
        self.assertEqual(obj2.item, 'forest_key')
        self.assertEqual(obj2.count, 3)

    def test_mission_rewards(self):
        """Test mission rewards are loaded"""
        mission = get_mission('forest_1')

        self.assertEqual(mission.rewards.currency, 50)
        self.assertGreater(len(mission.rewards.items), 0)

    def test_mission_abilities(self):
        """Test mission ability requirements and unlocks"""
        mission = get_mission('forest_1')

        # Required abilities
        self.assertIn('basic_movement', mission.required_abilities)
        self.assertIn('jump', mission.required_abilities)

        # Unlocked abilities
        self.assertIn('double_jump', mission.unlock_abilities)

    def test_missions_by_region(self):
        """Test getting missions for a specific region"""
        forest_missions = get_missions_for_region('forest')

        self.assertEqual(len(forest_missions), 5)

        mission_ids = [m.mission_id for m in forest_missions]
        self.assertIn('forest_1', mission_ids)
        self.assertIn('forest_2', mission_ids)
        self.assertIn('forest_3', mission_ids)
        self.assertIn('forest_4', mission_ids)
        self.assertIn('forest_5', mission_ids)

    def test_available_missions(self):
        """Test filtering available missions"""
        # Starting abilities
        abilities = {'basic_movement', 'jump'}
        completed = set()

        available = self.registry.get_available_missions(abilities, completed)

        # Should have forest_1 available (no prerequisites)
        mission_ids = [m.mission_id for m in available]
        self.assertIn('forest_1', mission_ids)

        # Should NOT have forest_2 (requires double_jump)
        self.assertNotIn('forest_2', mission_ids)

    def test_progression_unlocking(self):
        """Test mission unlocking through progression"""
        abilities = {'basic_movement', 'jump', 'double_jump'}
        completed = {'forest_1'}

        available = self.registry.get_available_missions(abilities, completed)
        mission_ids = [m.mission_id for m in available]

        # forest_2 requires forest_1 completed and double_jump
        self.assertIn('forest_2', mission_ids)

    def test_boss_missions(self):
        """Test identifying boss missions"""
        boss_missions = self.registry.get_boss_missions()

        self.assertGreater(len(boss_missions), 0)

        boss_ids = [m.mission_id for m in boss_missions]

        # Expected boss missions
        self.assertIn('forest_3', boss_ids)  # Forest Guardian
        self.assertIn('town_5', boss_ids)    # Corrupt Mayor
        self.assertIn('caves_4', boss_ids)   # Crystal Golem
        self.assertIn('castle_4', boss_ids)  # Dark Knight
        self.assertIn('sewer_2', boss_ids)   # Plague Rat King

    def test_timed_missions(self):
        """Test identifying timed missions"""
        timed_missions = self.registry.get_timed_missions()

        self.assertGreater(len(timed_missions), 0)

        timed_ids = [m.mission_id for m in timed_missions]

        # Expected timed missions
        self.assertIn('forest_4', timed_ids)  # Speed Trial
        self.assertIn('town_2', timed_ids)    # Rooftop Chase
        self.assertIn('castle_6', timed_ids)  # King's Challenge

    def test_mission_has_boss(self):
        """Test boss detection on missions"""
        forest_3 = get_mission('forest_3')
        forest_1 = get_mission('forest_1')

        self.assertTrue(forest_3.has_boss())
        self.assertFalse(forest_1.has_boss())

    def test_mission_is_timed(self):
        """Test time limit detection"""
        forest_4 = get_mission('forest_4')
        forest_1 = get_mission('forest_1')

        self.assertTrue(forest_4.is_timed())
        self.assertFalse(forest_1.is_timed())

    def test_mission_unlock_requirements(self):
        """Test getting mission unlock requirements"""
        requirements = self.registry.get_mission_unlock_requirements('town_1')

        # Town missions require double_jump, dash, wall_jump
        self.assertIn('basic_movement', requirements['abilities'])
        self.assertIn('jump', requirements['abilities'])

    def test_locked_missions(self):
        """Test getting locked missions"""
        abilities = {'basic_movement', 'jump'}
        completed = set()

        locked = self.registry.get_locked_missions(abilities, completed)

        # Most missions should be locked with starting abilities
        self.assertGreater(len(locked), 15)

        # forest_2 should be locked (requires double_jump)
        locked_ids = [m.mission_id for m in locked]
        self.assertIn('forest_2', locked_ids)

    def test_region_list(self):
        """Test getting all regions"""
        regions = self.registry.get_all_regions()

        self.assertEqual(len(regions), 5)
        self.assertIn('forest', regions)
        self.assertIn('town', regions)
        self.assertIn('caves', regions)
        self.assertIn('castle', regions)
        self.assertIn('sewer', regions)

    def test_difficulty_progression(self):
        """Test difficulty progression within regions"""
        # Forest missions should start easy
        forest_1 = get_mission('forest_1')
        self.assertEqual(forest_1.difficulty, 1)

        # Sewer missions should be hardest
        sewer_missions = get_missions_for_region('sewer')
        for mission in sewer_missions:
            self.assertGreaterEqual(mission.difficulty, 6)

    def test_town_requires_forest(self):
        """Test that town missions require forest completion"""
        town_1 = get_mission('town_1')

        # Town missions are available after forest progression
        # (no explicit requirement on town_1, but region unlocking requires forest)
        self.assertIn('basic_movement', town_1.required_abilities)
        self.assertIn('double_jump', town_1.required_abilities)
        self.assertIn('dash', town_1.required_abilities)

    def test_full_progression_chain(self):
        """Test full ability progression chain"""
        # Start with basic abilities
        abilities = {'basic_movement', 'jump'}
        completed = set()

        # Complete forest_1 → unlock double_jump
        completed.add('forest_1')
        abilities.add('double_jump')

        # Complete forest_3 → unlock dash
        completed.add('forest_3')
        abilities.add('dash')

        # Complete town_3 → unlock wall_jump
        completed.add('town_3')
        abilities.add('wall_jump')

        # Should now have access to many missions
        available = self.registry.get_available_missions(abilities, completed)
        self.assertGreater(len(available), 5)

    def test_mission_rewards_scaling(self):
        """Test that rewards scale with difficulty"""
        forest_1 = get_mission('forest_1')
        sewer_3 = get_mission('sewer_3')

        # Later missions should have higher currency rewards
        self.assertLess(forest_1.get_total_currency_reward(),
                       sewer_3.get_total_currency_reward())

        # Sewer_3 should be valuable endgame mission
        self.assertGreaterEqual(sewer_3.get_total_currency_reward(), 500)


def run_tests():
    """Run all mission registry tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMissionRegistry))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
