"""
Phase 4 Settings Wiring Tests

Covers:
- Key binding name → pygame constant resolution
- Player.set_key_bindings() is accepted without error
- settings persistence (save → reload)
- SettingsMenu includes Fullscreen and SFX Volume items
"""

import os
import pathlib
import tempfile
import unittest
from unittest.mock import MagicMock

# Headless pygame for all tests
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()


class TestKeyBindingResolution(unittest.TestCase):
    """Key name strings should map to valid pygame key constants."""

    def _build_key_bindings(self, settings_dict: dict) -> dict:
        """Mirror of the _build_key_bindings() helper in demo_game.main()."""
        _KEY_NAME_MAP = {
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
            "up": pygame.K_UP,
            "down": pygame.K_DOWN,
            "space": pygame.K_SPACE,
            "return": pygame.K_RETURN,
            "shift": pygame.K_LSHIFT,
            "lshift": pygame.K_LSHIFT,
            "rshift": pygame.K_RSHIFT,
            "ctrl": pygame.K_LCTRL,
            "alt": pygame.K_LALT,
            **{
                chr(c): getattr(pygame, f"K_{chr(c)}", None)
                for c in range(ord("a"), ord("z") + 1)
            },
        }
        result = {}
        for action in ("left", "right", "jump", "dash", "crouch"):
            name = settings_dict.get(f"key_{action}")
            if name:
                key_code = _KEY_NAME_MAP.get(str(name).lower())
                if key_code is not None:
                    result[action] = key_code
        return result

    def test_default_settings_map_to_valid_keys(self):
        """Default settings string values should all resolve to real key codes."""
        from config.settings import GameSettings

        td = pathlib.Path(tempfile.mkdtemp())
        settings = GameSettings(user_data_dir=td)
        bindings = self._build_key_bindings(settings.settings)

        for action, code in bindings.items():
            self.assertIsInstance(
                code, int, f"Key code for '{action}' should be an int, got {code}"
            )
            self.assertGreater(code, 0, f"Key code for '{action}' should be > 0")

    def test_custom_binding_resolves_correctly(self):
        """Setting key_jump to 'z' should resolve to pygame.K_z."""
        bindings = self._build_key_bindings({"key_jump": "z"})
        self.assertIn("jump", bindings)
        self.assertEqual(bindings["jump"], pygame.K_z)

    def test_unknown_key_name_is_ignored(self):
        """An unrecognised key name should be silently dropped (not crash)."""
        bindings = self._build_key_bindings({"key_jump": "GAMEPAD_A"})
        self.assertNotIn("jump", bindings)

    def test_missing_key_setting_produces_no_entry(self):
        """If a key setting is absent, the action should not appear in bindings."""
        bindings = self._build_key_bindings({})
        self.assertEqual(bindings, {})


class TestPlayerKeyBindings(unittest.TestCase):
    """Player.set_key_bindings() should be accepted without error."""

    def _make_player(self):
        from core import EventBus
        from core.logger import GameLogger
        from entities.player import Player
        from systems import CollisionSystem
        from core import EntityManager

        bus = EventBus()
        logger = GameLogger()
        entity_manager = EntityManager(bus, logger.get_logger("em"))
        cs = CollisionSystem(bus, entity_manager, logger.get_logger("cs"))
        return Player(
            player_id=0,
            spawn_x=0.0,
            spawn_y=0.0,
            event_bus=bus,
            logger_factory=logger,
            collision_system=cs,
        )

    def test_set_key_bindings_accepted(self):
        """Player.set_key_bindings should store bindings without error."""
        player = self._make_player()
        player.set_key_bindings({"left": pygame.K_LEFT, "jump": pygame.K_SPACE})
        self.assertEqual(player._key_bindings["left"], pygame.K_LEFT)
        self.assertEqual(player._key_bindings["jump"], pygame.K_SPACE)

    def test_empty_bindings_accepted(self):
        """Empty bindings dict should not crash."""
        player = self._make_player()
        player.set_key_bindings({})
        self.assertEqual(player._key_bindings, {})


class TestSettingsPersistence(unittest.TestCase):
    """GameSettings save/load round-trip should preserve values."""

    def test_volume_sfx_persists(self):
        """volume_sfx set and saved should reload with the same value."""
        from config.settings import GameSettings

        td = pathlib.Path(tempfile.mkdtemp())
        s1 = GameSettings(user_data_dir=td)
        s1.set("volume_sfx", 0.25)
        s1.save()

        s2 = GameSettings(user_data_dir=td)
        self.assertAlmostEqual(s2.get("volume_sfx"), 0.25, places=5)

    def test_fullscreen_persists(self):
        """fullscreen toggle persists across reload."""
        from config.settings import GameSettings

        td = pathlib.Path(tempfile.mkdtemp())
        s1 = GameSettings(user_data_dir=td)
        s1.set("fullscreen", True)
        s1.save()

        s2 = GameSettings(user_data_dir=td)
        self.assertTrue(s2.get("fullscreen"))

    def test_key_binding_persists(self):
        """Custom key binding persists across reload."""
        from config.settings import GameSettings

        td = pathlib.Path(tempfile.mkdtemp())
        s1 = GameSettings(user_data_dir=td)
        s1.set("key_jump", "z")
        s1.save()

        s2 = GameSettings(user_data_dir=td)
        self.assertEqual(s2.get("key_jump"), "z")


class TestSettingsMenuItems(unittest.TestCase):
    """SettingsMenu should expose all expected configuration items."""

    def _make_menu(self):
        from config.settings import GameSettings
        from ui.menu_system import SettingsMenu

        td = pathlib.Path(tempfile.mkdtemp())
        settings = GameSettings(user_data_dir=td)
        return SettingsMenu(1280, 720, settings=settings, on_change=None)

    def test_sfx_volume_item_present(self):
        menu = self._make_menu()
        labels = [item.label for item in menu.items]
        self.assertTrue(any("SFX Volume" in l for l in labels))

    def test_fullscreen_item_present(self):
        menu = self._make_menu()
        labels = [item.label for item in menu.items]
        self.assertTrue(any("Fullscreen" in l for l in labels))

    def test_sfx_volume_cycles(self):
        """Cycling SFX Volume should change the setting."""
        from config.settings import GameSettings
        from ui.menu_system import SettingsMenu

        td = pathlib.Path(tempfile.mkdtemp())
        settings = GameSettings(user_data_dir=td)
        menu = SettingsMenu(1280, 720, settings=settings, on_change=None)

        initial = settings.get("volume_sfx")
        # Activate the SFX volume item
        menu.items[menu._idx_sfx_vol].callback()
        after = settings.get("volume_sfx")
        self.assertNotEqual(initial, after, "Cycling SFX Volume should change the value")


if __name__ == "__main__":
    unittest.main()
