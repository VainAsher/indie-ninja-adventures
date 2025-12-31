"""
Integration tests for play mode manager/configurations.

Covers:
- Arcade mode startup and config
- Campaign mode startup and config
- Sandbox mode startup and config (scope-freeze target)
- Mode settings helpers returning expected flags
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from game.play_mode import (  # noqa: E402
    PlayMode,
    PlayModeManager,
    create_arcade_session,
    create_campaign_session,
    create_sandbox_session,
    get_mode_settings,
)


def test_arcade_mode_config():
    """Arcade mode should set mode and basic config fields."""
    manager, settings = create_arcade_session(seed=123)

    assert manager.is_arcade_mode()
    cfg = manager.get_config()
    assert cfg.seed == 123
    assert cfg.infinite is True
    assert settings["infinite_progression"] is True
    assert "basic_movement" in settings["starting_abilities"]


def test_campaign_mode_config():
    """Campaign mode should set mode and enable save progress."""
    manager, settings = create_campaign_session(world_seed=777)

    assert manager.is_campaign_mode()
    cfg = manager.get_config()
    assert cfg.world_seed == 777
    assert settings["save_progress"] is True
    assert settings["mission_based"] is True


def test_sandbox_mode_config():
    """Sandbox mode should unlock abilities for freeform testing."""
    manager, settings = create_sandbox_session(seed=999, rooms=4)

    assert manager.is_sandbox_mode()
    cfg = manager.get_config()
    assert cfg.rooms == 4
    assert cfg.enable_all_abilities is True
    assert settings["all_abilities_unlocked"] is True
    assert settings["sandbox_tools"] is True
    assert "double_jump" in settings["starting_abilities"]


def test_mode_settings_cover_scope_freeze_modes():
    """Mode settings helper should return non-empty configs for primary modes."""
    assert get_mode_settings(PlayMode.ARCADE)
    assert get_mode_settings(PlayMode.CAMPAIGN)
    assert get_mode_settings(PlayMode.SANDBOX)
