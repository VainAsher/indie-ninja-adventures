"""
Data Integrity Tests

Validates mission data references against item/enemy/hazard definitions.
"""

import json
import re
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from entities.boss import BossType as LegacyBossType
from entities.boss_manager import BossType as CampaignBossType
from entities.enemy import EnemyType
from game.mission_system import get_mission_registry as get_legacy_mission_registry
from game.trading_system import SHOP_TIER_POOLS


class TestDataIntegrity(unittest.TestCase):
    """Validate mission data references."""

    DIALOGUE_EVENT_KEYS = {
        "start_mission",
        "open_shop",
        "advance_act",
        "tutorial_completed",
        "town_lore_learned",
        "act2_elder_conversation_complete",
        "act2_elder_patience_shown",
        "act3_final_blessing_received",
        "act3_elder_final_conversation",
        "open_mission_menu",
        "switch_activated",
        "reach_location",
        "collect_item",
    }

    DIALOGUE_EVENT_KEYS_REQUIRING_ARG = {
        "start_mission",
        "switch_activated",
        "reach_location",
        "collect_item",
    }

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parent.parent
        cls.missions = json.loads((root / "data" / "missions.json").read_text(encoding="utf-8"))
        cls.items = json.loads((root / "data" / "items.json").read_text(encoding="utf-8"))
        cls.dialogues = json.loads((root / "data" / "dialogues.json").read_text(encoding="utf-8"))
        cls.java_runtime_boss_ids = cls._load_java_runtime_boss_ids(root)
        cls.dialogue_events = cls._extract_dialogue_events(cls.dialogues)

        cls.mission_ids = {mission["mission_id"] for mission in cls.missions.get("missions", [])}
        cls.item_ids = {item["item_id"] for item in cls.items.get("items", [])}
        cls.enemy_ids = {enemy.value for enemy in EnemyType}
        # Canonical mission boss contract:
        # - legacy lowercase wire IDs from entities/boss.py
        # - campaign boss IDs normalized to lowercase enum names from entities/boss_manager.py
        cls.boss_ids = {boss.value for boss in LegacyBossType}
        cls.boss_ids.update({boss.name.lower() for boss in CampaignBossType})
        cls.hazard_ids = {"spike", "poison", "void"}

    @staticmethod
    def _load_java_runtime_boss_ids(root: Path) -> set[str]:
        boss_type_java = (
            root
            / "java"
            / "core"
            / "src"
            / "main"
            / "java"
            / "com"
            / "indieniinja"
            / "sim"
            / "BossType.java"
        )
        text = boss_type_java.read_text(encoding="utf-8")
        wire_ids = set(
            re.findall(r"^\s*[A-Z0-9_]+\s*\(\s*\"([a-z_]+)\"\s*,", text, flags=re.MULTILINE)
        )
        if not wire_ids:
            raise AssertionError("Could not parse Java runtime boss IDs from BossType.java")
        return wire_ids

    @staticmethod
    def _extract_dialogue_events(dialogues: dict) -> list[str]:
        events: list[str] = []
        for tree in dialogues.values():
            if not isinstance(tree, dict):
                continue
            nodes = tree.get("nodes", {})
            if not isinstance(nodes, dict):
                continue
            for node in nodes.values():
                if not isinstance(node, dict):
                    continue
                on_exit = node.get("on_exit_event")
                if on_exit:
                    events.append(str(on_exit).strip())
                choices = node.get("choices", [])
                if not isinstance(choices, list):
                    continue
                for choice in choices:
                    if not isinstance(choice, dict):
                        continue
                    on_select = choice.get("on_select_event")
                    if on_select:
                        events.append(str(on_select).strip())
        return events

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
        non_canonical_case = set()
        for mission in self.missions.get("missions", []):
            for obj in mission.get("objectives", []):
                boss_id = obj.get("boss")
                if not boss_id:
                    continue
                canonical = boss_id.strip().lower()
                if boss_id != canonical:
                    non_canonical_case.add(boss_id)
                if canonical not in self.boss_ids:
                    missing.add(canonical)

        self.assertFalse(
            non_canonical_case,
            f"Boss ids must be lowercase canonical IDs: {sorted(non_canonical_case)}",
        )
        self.assertFalse(missing, f"Missing boss ids: {sorted(missing)}")

    def test_mission_boss_ids_runtime_compatible(self):
        incompatible = set()
        for mission in self.missions.get("missions", []):
            mission_id = mission.get("mission_id", "<unknown>")

            for obj in mission.get("objectives", []):
                boss_id = obj.get("boss")
                if boss_id and boss_id not in self.java_runtime_boss_ids:
                    incompatible.add(f"{mission_id}:{boss_id}")

            mission_boss = mission.get("boss")
            if mission_boss and mission_boss not in self.java_runtime_boss_ids:
                incompatible.add(f"{mission_id}:{mission_boss}")

        self.assertFalse(
            incompatible,
            "Mission defeat_boss objectives target boss IDs not emitted by Java runtime: "
            f"{sorted(incompatible)}",
        )

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

    def test_dialogue_events_supported_by_runtime_router(self):
        unsupported = set()
        for event in self.dialogue_events:
            if not event:
                continue
            key = event.split(":", 1)[0].strip()
            if key not in self.DIALOGUE_EVENT_KEYS:
                unsupported.add(key)

        self.assertFalse(
            unsupported,
            "Authored dialogue events are not explicitly handled by GameScreen router: "
            f"{sorted(unsupported)}",
        )

    def test_dialogue_events_requiring_arguments_include_argument(self):
        missing_args = set()
        for event in self.dialogue_events:
            if not event:
                continue
            key, sep, arg = event.partition(":")
            key = key.strip()
            if key in self.DIALOGUE_EVENT_KEYS_REQUIRING_ARG and (not sep or not arg.strip()):
                missing_args.add(event)

        self.assertFalse(
            missing_args,
            "Dialogue events requiring arguments are missing argument payloads: "
            f"{sorted(missing_args)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
