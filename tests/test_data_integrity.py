"""
Data Integrity Tests

Validates mission data references against item/enemy/hazard definitions.
"""

import json
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from entities.boss import BossType
from entities.enemy import EnemyType
from game.mission_system import get_mission_registry as get_legacy_mission_registry
from game.trading_system import SHOP_TIER_POOLS


class TestDataIntegrity(unittest.TestCase):
    """Validate mission data references."""

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parent.parent
        cls.missions = json.loads((root / "data" / "missions.json").read_text(encoding="utf-8"))
        cls.items = json.loads((root / "data" / "items.json").read_text(encoding="utf-8"))

        cls.mission_ids = {mission["mission_id"] for mission in cls.missions.get("missions", [])}
        cls.item_ids = {item["item_id"] for item in cls.items.get("items", [])}
        cls.enemy_ids = {enemy.value for enemy in EnemyType}
        cls.boss_ids = {boss.value for boss in BossType}
        cls.hazard_ids = {"spike", "poison", "void"}

    def test_mission_objective_items_exist(self):
        missing = set()
        for mission in self.missions.get("missions", []):
            for obj in mission.get("objectives", []):
                item_id = obj.get("item")
                if item_id and item_id not in self.item_ids:
                    missing.add(item_id)

        self.assertFalse(missing, f"Missing objective items: {sorted(missing)}")

    def test_mission_reward_items_exist(self):
        missing = set()
        for mission in self.missions.get("missions", []):
            rewards = mission.get("rewards", {}).get("items", [])
            for reward in rewards:
                if isinstance(reward, dict):
                    item_id = reward.get("id") or reward.get("item_id")
                else:
                    item_id = reward
                if item_id and item_id not in self.item_ids:
                    missing.add(item_id)

        self.assertFalse(missing, f"Missing reward items: {sorted(missing)}")

    def test_mission_enemy_types_exist(self):
        missing = set()
        for mission in self.missions.get("missions", []):
            for enemy_id in mission.get("enemy_types", []):
                if enemy_id not in self.enemy_ids:
                    missing.add(enemy_id)

        self.assertFalse(missing, f"Missing enemy types: {sorted(missing)}")

    def test_mission_hazards_exist(self):
        missing = set()
        for mission in self.missions.get("missions", []):
            for hazard_id in mission.get("hazards", []):
                if hazard_id not in self.hazard_ids:
                    missing.add(hazard_id)

        self.assertFalse(missing, f"Missing hazard types: {sorted(missing)}")

    def test_mission_boss_ids_exist(self):
        missing = set()
        for mission in self.missions.get("missions", []):
            for obj in mission.get("objectives", []):
                boss_id = obj.get("boss")
                if boss_id and boss_id not in self.boss_ids:
                    missing.add(boss_id)

        self.assertFalse(missing, f"Missing boss ids: {sorted(missing)}")

    def test_shop_pool_items_exist(self):
        missing = set()
        for tier, pool in SHOP_TIER_POOLS.items():
            for item_id in pool.allowed_item_ids:
                if item_id not in self.item_ids:
                    missing.add(f"{tier.name}:{item_id}")

        self.assertFalse(missing, f"Missing shop pool items: {sorted(missing)}")

    def test_legacy_mission_system_ids_match(self):
        legacy_registry = get_legacy_mission_registry()
        legacy_ids = set(legacy_registry.missions.keys())

        missing_in_legacy = self.mission_ids - legacy_ids
        extra_in_legacy = legacy_ids - self.mission_ids

        self.assertFalse(
            missing_in_legacy or extra_in_legacy,
            "Legacy mission_system ids mismatch. "
            f"Missing: {sorted(missing_in_legacy)} "
            f"Extra: {sorted(extra_in_legacy)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
