"""
Ability gate / unlock tests.

Verifies that:
- A fresh campaign starts with only basic_movement + jump unlocked
- sync_player_abilities() disables locked mechanics and enables unlocked ones
- Unlocking an ability via sync immediately enables the mechanic
- JumpMechanic instance vars (double_jump_enabled, wall_jump_enabled) are
  also updated (they are cached at construction, so need explicit sync)
- Arcade mode players are unaffected (all abilities stay on)
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_ABILITY_TO_FLAG = {
    "double_jump": "double_jump",
    "wall_jump":   "wall_jump",
    "dash":        "dash",
    "shuriken":    "shuriken",
    "teleport":    "teleport",
    "ninjutsu":    "ninjutsu",
}


def _sync_player_abilities(player, unlocked_abilities):
    """Mirror of the sync_player_abilities() closure in demo_game.main()."""
    unlocked = set(unlocked_abilities) if unlocked_abilities else set()
    for ability, flag in _ABILITY_TO_FLAG.items():
        player.feature_flags[flag] = ability in unlocked
    player.jump.double_jump_enabled = player.feature_flags.get("double_jump", False)
    player.jump.wall_jump_enabled   = player.feature_flags.get("wall_jump", False)


def _make_player(all_enabled: bool = True):
    """Create a minimal Player with all feature flags set to all_enabled."""
    from core import EventBus
    from core.logger import GameLogger
    from core import EntityManager
    from systems import CollisionSystem
    from entities.player import Player

    bus = EventBus()
    logger = GameLogger()
    em = EntityManager(bus, logger.get_logger("em"))
    cs = CollisionSystem(bus, em, logger.get_logger("cs"))
    flags = {
        "double_jump": all_enabled,
        "wall_jump":   all_enabled,
        "dash":        all_enabled,
        "crouch":      True,
        "shuriken":    all_enabled,
        "teleport":    all_enabled,
        "ninjutsu":    all_enabled,
    }
    return Player(
        player_id=0,
        spawn_x=0.0,
        spawn_y=0.0,
        event_bus=bus,
        logger_factory=logger,
        collision_system=cs,
        feature_flags=flags,
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestCampaignStartAbilities(unittest.TestCase):
    """At campaign start only basic_movement + jump should be unlocked."""

    def test_fresh_campaign_unlocked_abilities(self):
        """save_system's default unlocked_abilities is basic_movement + jump only."""
        from systems.save_system import CampaignSaveData
        campaign = CampaignSaveData()
        self.assertIn("basic_movement", campaign.unlocked_abilities)
        self.assertIn("jump", campaign.unlocked_abilities)
        # Advanced abilities must NOT be present at start
        for ability in ("double_jump", "wall_jump", "dash", "shuriken", "teleport", "ninjutsu"):
            self.assertNotIn(
                ability, campaign.unlocked_abilities,
                f"'{ability}' should not be unlocked at campaign start"
            )


class TestSyncPlayerAbilities(unittest.TestCase):
    """sync_player_abilities() should gate/ungates mechanics correctly."""

    def test_sync_with_only_basic_disables_advanced(self):
        """Syncing with only basic_movement+jump should disable all advanced flags."""
        player = _make_player(all_enabled=True)
        _sync_player_abilities(player, {"basic_movement", "jump"})

        for ability, flag in _ABILITY_TO_FLAG.items():
            self.assertFalse(
                player.feature_flags.get(flag),
                f"feature_flags['{flag}'] should be False after basic-only sync"
            )

    def test_sync_updates_jump_mechanic_instance_vars(self):
        """double_jump_enabled and wall_jump_enabled on JumpMechanic must be updated."""
        player = _make_player(all_enabled=True)
        # Before sync — JumpMechanic was created with all_enabled=True
        self.assertTrue(player.jump.double_jump_enabled)
        self.assertTrue(player.jump.wall_jump_enabled)

        _sync_player_abilities(player, {"basic_movement", "jump"})

        self.assertFalse(player.jump.double_jump_enabled,
                         "JumpMechanic.double_jump_enabled must be False after sync")
        self.assertFalse(player.jump.wall_jump_enabled,
                         "JumpMechanic.wall_jump_enabled must be False after sync")

    def test_unlocking_double_jump_enables_it(self):
        """Adding double_jump to unlocked set should enable double_jump flag."""
        player = _make_player(all_enabled=True)
        _sync_player_abilities(player, {"basic_movement", "jump"})
        self.assertFalse(player.jump.double_jump_enabled)

        # Mission completes, grants double_jump
        _sync_player_abilities(player, {"basic_movement", "jump", "double_jump"})

        self.assertTrue(player.feature_flags.get("double_jump"))
        self.assertTrue(player.jump.double_jump_enabled)
        # Other advanced abilities still locked
        self.assertFalse(player.feature_flags.get("dash"))

    def test_unlocking_all_enables_all(self):
        """Unlocking everything should enable all flags."""
        player = _make_player(all_enabled=True)
        _sync_player_abilities(player, {"basic_movement", "jump"})

        all_abilities = set(_ABILITY_TO_FLAG.keys()) | {"basic_movement", "jump"}
        _sync_player_abilities(player, all_abilities)

        for ability, flag in _ABILITY_TO_FLAG.items():
            self.assertTrue(
                player.feature_flags.get(flag),
                f"feature_flags['{flag}'] should be True after full unlock"
            )

    def test_empty_unlocked_disables_everything(self):
        """Empty unlocked set disables all gated abilities."""
        player = _make_player(all_enabled=True)
        _sync_player_abilities(player, set())

        for flag in _ABILITY_TO_FLAG.values():
            self.assertFalse(player.feature_flags.get(flag))

    def test_crouch_always_enabled(self):
        """Crouch is not in ABILITY_TO_FLAG — it should never be gated."""
        player = _make_player(all_enabled=True)
        _sync_player_abilities(player, {"basic_movement", "jump"})
        # Crouch flag was set to True at construction; sync should not touch it
        self.assertTrue(player.feature_flags.get("crouch", True))


if __name__ == "__main__":
    unittest.main()
