"""
Phase 2 Boss Integration Tests

Tests covering boss spawning, BossDeathEvent emission, ability gate wiring,
and mission data integrity for boss missions.

Version: v0.7.1 (Phase 2 integration)
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestBossManagerSpawn(unittest.TestCase):
    """BossManager spawning and death event emission"""

    def _make_bus(self):
        """Create a minimal EventBus that records emitted events."""
        from core import EventBus

        bus = EventBus()
        self._emitted = []
        original_emit = bus.emit

        def recording_emit(event, immediate=False):
            self._emitted.append(event)
            original_emit(event, immediate=True)  # process immediately for tests

        bus.emit = recording_emit
        return bus

    def test_spawn_boss_creates_active_boss(self):
        """spawn_boss() should create an active boss entity."""
        from core import EventBus
        from entities.boss_manager import BossManager, BossType

        bus = EventBus()
        manager = BossManager(bus, level_seed=42)
        self.assertFalse(manager.is_boss_active())

        manager.spawn_boss(BossType.SHADOW_LORD, x=100.0, y=200.0)
        self.assertTrue(manager.is_boss_active())

    def test_spawn_boss_position(self):
        """Spawned boss should be at the requested position."""
        from core import EventBus
        from entities.boss_manager import BossManager, BossType

        bus = EventBus()
        manager = BossManager(bus, level_seed=0)
        boss = manager.spawn_boss(BossType.FIRE_DEMON, x=500.0, y=300.0)

        bx, by, _, _ = boss.get_rect()
        self.assertAlmostEqual(bx, 500.0, places=0)
        self.assertAlmostEqual(by, 300.0, places=0)

    def test_damage_boss_reduces_health(self):
        """damage_boss() should reduce boss HP once invulnerability is cleared."""
        from core import EventBus
        from entities.boss_manager import BossManager, BossType

        bus = EventBus()
        manager = BossManager(bus, level_seed=0)
        boss = manager.spawn_boss(BossType.ICE_QUEEN, x=0.0, y=0.0)
        boss.invulnerable = False  # Clear intro invulnerability
        initial_hp = boss.health

        manager.damage_boss(5)
        self.assertLess(boss.health, initial_hp, "Boss health should decrease after taking damage")

    def test_boss_death_emits_BossDeathEvent(self):
        """Killing a boss should emit a BossDeathEvent (not a raw dict)."""
        from core import EventBus
        from entities.boss_manager import BossManager, BossType
        from game.objective_tracker import BossDeathEvent

        bus = EventBus()
        received = []
        bus.subscribe(BossDeathEvent, lambda e: received.append(e))

        manager = BossManager(bus, level_seed=0)
        boss = manager.spawn_boss(BossType.SHADOW_LORD, x=0.0, y=0.0)
        boss.invulnerable = False  # Clear intro invulnerability so damage lands

        manager.damage_boss(boss.health + 100)
        bus.process()  # Flush queued events

        self.assertEqual(len(received), 1, "Exactly one BossDeathEvent should be emitted")
        self.assertEqual(received[0].boss_type, "SHADOW_LORD")

    def test_clear_removes_boss(self):
        """clear() should remove the active boss."""
        from core import EventBus
        from entities.boss_manager import BossManager, BossType

        bus = EventBus()
        manager = BossManager(bus, level_seed=0)
        manager.spawn_boss(BossType.DRAGON, x=0.0, y=0.0)
        self.assertTrue(manager.is_boss_active())

        manager.clear()
        self.assertFalse(manager.is_boss_active())


class TestBossDeathObjectiveChain(unittest.TestCase):
    """objective_tracker reacts to BossDeathEvent via EventBus."""

    def test_objective_tracker_receives_boss_death(self):
        """objective_tracker._on_boss_death should be called when BossDeathEvent is emitted."""
        from core import EventBus
        from game.objective_tracker import BossDeathEvent, ObjectiveTracker

        bus = EventBus()
        tracker = ObjectiveTracker(bus)

        received = []
        original = tracker._on_boss_death

        def spy(event):
            received.append(event)
            original(event)

        tracker._on_boss_death = spy
        bus.subscribe(BossDeathEvent, spy)

        event = BossDeathEvent(
            boss_id="boss_shadow_lord", boss_type="SHADOW_LORD", position=(100.0, 200.0)
        )
        bus.emit(event, immediate=True)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].boss_type, "SHADOW_LORD")


class TestMissionsBossField(unittest.TestCase):
    """data/missions.json boss field correctness."""

    def _load_missions(self):
        missions_path = Path(__file__).parent.parent / "data" / "missions.json"
        with open(missions_path, encoding="utf-8") as f:
            return json.load(f)["missions"]

    def test_each_region_has_one_boss_mission(self):
        """Each region should have exactly one mission with a 'boss' field set."""
        missions = self._load_missions()
        from collections import Counter

        boss_counts = Counter(m["region"] for m in missions if m.get("boss"))
        expected_regions = {"forest", "town", "caves", "castle", "sewer", "hollow_depths"}
        for region in expected_regions:
            self.assertEqual(boss_counts[region], 1, f"{region} should have exactly 1 boss mission")

    def test_boss_types_are_valid(self):
        """Boss field values should match BossType enum names."""
        from entities.boss_manager import BossType

        valid = {bt.name for bt in BossType}
        missions = self._load_missions()
        for m in missions:
            boss = m.get("boss")
            if boss:
                self.assertIn(
                    boss, valid, f"Mission {m['mission_id']} has unknown boss type '{boss}'"
                )


class TestAbilityGateManager(unittest.TestCase):
    """GateManager places and blocks correctly."""

    def test_gate_blocks_player_without_ability(self):
        """A LOCKED_DOOR gate should block a player who lacks the key ability."""
        from entities.ability_gate import AbilityRequirement, GateManager, GateType

        gm = GateManager()
        gm.add_gate(GateType.LOCKED_DOOR, x=100.0, y=100.0)

        blocked = gm.check_gate_collision(
            player_x=100.0,
            player_y=100.0,
            player_width=28,
            player_height=56,
            unlocked_abilities={AbilityRequirement.BASIC_MOVEMENT, AbilityRequirement.JUMP},
        )
        self.assertIsNotNone(blocked, "Gate should block player without required ability")

    def test_gate_does_not_block_with_ability(self):
        """A WIDE_GAP gate should not block a player who has dash."""
        from entities.ability_gate import AbilityRequirement, GateManager, GateType

        gm = GateManager()
        gm.add_gate(GateType.WIDE_GAP, x=100.0, y=100.0)

        blocked = gm.check_gate_collision(
            player_x=100.0,
            player_y=100.0,
            player_width=28,
            player_height=56,
            unlocked_abilities={
                AbilityRequirement.BASIC_MOVEMENT,
                AbilityRequirement.JUMP,
                AbilityRequirement.DASH,
            },
        )
        self.assertIsNone(blocked, "Gate should NOT block player who has dash")

    def test_clear_removes_all_gates(self):
        """clear() should remove all gates."""
        from entities.ability_gate import GateManager, GateType

        gm = GateManager()
        gm.add_gate(GateType.HIGH_LEDGE, x=0.0, y=0.0)
        gm.add_gate(GateType.WIDE_GAP, x=200.0, y=0.0)
        self.assertEqual(len(gm.get_all_gates()), 2)

        gm.clear()
        self.assertEqual(len(gm.get_all_gates()), 0)


if __name__ == "__main__":
    unittest.main()
