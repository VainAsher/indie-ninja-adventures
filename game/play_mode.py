"""
Play Mode System - Manages different game modes

Supports three play modes:
- ARCADE: Infinite procedural generation (existing mode)
- CAMPAIGN: Story-driven mission progression
- PLAYTEST: Developer mode for testing specific missions

Version: v0.6.0 (Phase 6)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

# ============================================================
# Play Modes
# ============================================================


class PlayMode(Enum):
    """Game play modes"""

    ARCADE = "arcade"  # Infinite procedural (existing)
    CAMPAIGN = "campaign"  # Story progression with missions
    SANDBOX = "sandbox"  # Custom multiplayer (future)
    PLAYTEST = "playtest"  # Developer mission testing


# ============================================================
# Play Mode Configuration
# ============================================================


@dataclass
class ArcadeModeConfig:
    """Configuration for arcade mode"""

    seed: int | None = None
    shape: str = "snake"
    rooms: int = 10
    difficulty: int = 1
    infinite: bool = True


@dataclass
class CampaignModeConfig:
    """Configuration for campaign mode"""

    world_seed: int
    current_hub: str = "central_hub"
    current_region: str | None = None
    resume_from_save: bool = True


@dataclass
class SandboxModeConfig:
    """Configuration for sandbox mode (freeform testing/building)"""

    seed: int | None = None
    shape: str = "grid"
    rooms: int = 6
    enable_all_abilities: bool = True
    save_progress: bool = False
    infinite: bool = False


@dataclass
class PlaytestModeConfig:
    """Configuration for playtest mode"""

    mission_id: str
    region_id: str
    seed: int
    skip_validation: bool = False


# ============================================================
# Play Mode Manager
# ============================================================


class PlayModeManager:
    """
    Manages play mode state and transitions.

    Responsibilities:
    - Track current play mode
    - Initialize mode-specific configurations
    - Handle mode transitions
    - Provide mode-specific settings
    """

    def __init__(self):
        self.current_mode: PlayMode | None = None
        self.mode_config: Any | None = None

    def start_arcade_mode(
        self, seed: int | None = None, shape: str = "snake", rooms: int = 10, difficulty: int = 1
    ) -> ArcadeModeConfig:
        """
        Start arcade mode (infinite procedural).

        Args:
            seed: World seed (None for random)
            shape: Level shape (snake, blob, loop)
            rooms: Number of rooms per level
            difficulty: Difficulty level (1-5)

        Returns:
            Arcade mode configuration
        """
        self.current_mode = PlayMode.ARCADE
        self.mode_config = ArcadeModeConfig(
            seed=seed, shape=shape, rooms=rooms, difficulty=difficulty, infinite=True
        )

        return self.mode_config

    def start_campaign_mode(
        self, world_seed: int, resume_from_save: bool = True
    ) -> CampaignModeConfig:
        """
        Start campaign mode.

        Args:
            world_seed: Campaign world seed
            resume_from_save: Load from save file

        Returns:
            Campaign mode configuration
        """
        self.current_mode = PlayMode.CAMPAIGN
        self.mode_config = CampaignModeConfig(
            world_seed=world_seed,
            current_hub="central_hub",
            current_region=None,
            resume_from_save=resume_from_save,
        )

        return self.mode_config

    def start_sandbox_mode(
        self,
        seed: int | None = None,
        shape: str = "grid",
        rooms: int = 6,
        enable_all_abilities: bool = True,
    ) -> SandboxModeConfig:
        """
        Start sandbox mode (freeform testing).

        Args:
            seed: World seed (None for random)
            shape: Level shape
            rooms: Number of rooms
            enable_all_abilities: Unlock all movement abilities

        Returns:
            Sandbox mode configuration
        """
        self.current_mode = PlayMode.SANDBOX
        self.mode_config = SandboxModeConfig(
            seed=seed,
            shape=shape,
            rooms=rooms,
            enable_all_abilities=enable_all_abilities,
            save_progress=False,
            infinite=False,
        )

        return self.mode_config

    def start_playtest_mode(
        self, mission_id: str, region_id: str, seed: int = 42, skip_validation: bool = False
    ) -> PlaytestModeConfig:
        """
        Start playtest mode (developer mode).

        Args:
            mission_id: Mission to test
            region_id: Region the mission belongs to
            seed: Mission seed
            skip_validation: Skip gate validation

        Returns:
            Playtest mode configuration
        """
        self.current_mode = PlayMode.PLAYTEST
        self.mode_config = PlaytestModeConfig(
            mission_id=mission_id, region_id=region_id, seed=seed, skip_validation=skip_validation
        )

        return self.mode_config

    def is_arcade_mode(self) -> bool:
        """Check if in arcade mode"""
        return self.current_mode == PlayMode.ARCADE

    def is_campaign_mode(self) -> bool:
        """Check if in campaign mode"""
        return self.current_mode == PlayMode.CAMPAIGN

    def is_sandbox_mode(self) -> bool:
        """Check if in sandbox mode"""
        return self.current_mode == PlayMode.SANDBOX

    def is_playtest_mode(self) -> bool:
        """Check if in playtest mode"""
        return self.current_mode == PlayMode.PLAYTEST

    def get_mode_name(self) -> str:
        """Get current mode name"""
        if self.current_mode is None:
            return "None"
        return self.current_mode.value.title()

    def get_config(self) -> Any | None:
        """Get current mode configuration"""
        return self.mode_config

    def reset(self):
        """Reset play mode"""
        self.current_mode = None
        self.mode_config = None


# ============================================================
# Mode-Specific Settings
# ============================================================


def get_arcade_settings() -> dict[str, Any]:
    """Get default arcade mode settings"""
    return {
        "infinite_progression": True,
        "seed_increment": True,
        "save_progress": True,
        "replay_enabled": True,
        "level_transition": "instant",
        "difficulty_scaling": True,
        "permadeath": False,
        "starting_abilities": ["basic_movement", "jump"],
        "unlock_abilities": True,
    }


def get_campaign_settings() -> dict[str, Any]:
    """Get default campaign mode settings"""
    return {
        "infinite_progression": False,
        "seed_increment": False,
        "save_progress": True,
        "replay_enabled": False,
        "level_transition": "hub_return",
        "difficulty_scaling": False,
        "permadeath": False,
        "starting_abilities": ["basic_movement", "jump"],
        "unlock_abilities": True,
        "mission_based": True,
        "hub_worlds": True,
        "ability_gates": True,
    }


def get_sandbox_settings() -> dict[str, Any]:
    """Get default sandbox mode settings"""
    return {
        "infinite_progression": False,
        "seed_increment": False,
        "save_progress": False,
        "replay_enabled": True,
        "level_transition": "instant",
        "difficulty_scaling": False,
        "permadeath": False,
        "starting_abilities": [
            "basic_movement",
            "jump",
            "double_jump",
            "wall_jump",
            "dash",
            "crouch",
        ],
        "unlock_abilities": False,
        "all_abilities_unlocked": True,
        "sandbox_tools": True,
    }


def get_playtest_settings() -> dict[str, Any]:
    """Get default playtest mode settings"""
    return {
        "infinite_progression": False,
        "seed_increment": False,
        "save_progress": False,
        "replay_enabled": True,
        "level_transition": "instant_retry",
        "difficulty_scaling": False,
        "permadeath": False,
        "starting_abilities": [
            "basic_movement",
            "jump",
            "double_jump",
            "wall_jump",
            "dash",
            "crouch",
        ],
        "unlock_abilities": False,
        "all_abilities_unlocked": True,
        "skip_validation": True,
        "debug_mode": True,
    }


def get_mode_settings(mode: PlayMode) -> dict[str, Any]:
    """
    Get settings for a specific play mode.

    Args:
        mode: Play mode

    Returns:
        Settings dictionary
    """
    if mode == PlayMode.ARCADE:
        return get_arcade_settings()
    elif mode == PlayMode.CAMPAIGN:
        return get_campaign_settings()
    elif mode == PlayMode.SANDBOX:
        return get_sandbox_settings()
    elif mode == PlayMode.PLAYTEST:
        return get_playtest_settings()
    else:
        return {}


# ============================================================
# Utility Functions
# ============================================================


def create_arcade_session(seed: int | None = None) -> tuple[PlayModeManager, dict[str, Any]]:
    """
    Create arcade mode session.

    Args:
        seed: World seed

    Returns:
        (PlayModeManager, settings dict)
    """
    manager = PlayModeManager()
    manager.start_arcade_mode(seed=seed)
    settings = get_arcade_settings()

    return manager, settings


def create_campaign_session(world_seed: int) -> tuple[PlayModeManager, dict[str, Any]]:
    """
    Create campaign mode session.

    Args:
        world_seed: Campaign world seed

    Returns:
        (PlayModeManager, settings dict)
    """
    manager = PlayModeManager()
    manager.start_campaign_mode(world_seed=world_seed)
    settings = get_campaign_settings()

    return manager, settings


def create_playtest_session(
    mission_id: str, region_id: str, seed: int = 42
) -> tuple[PlayModeManager, dict[str, Any]]:
    """
    Create playtest mode session.

    Args:
        mission_id: Mission to test
        region_id: Region ID
        seed: Mission seed

    Returns:
        (PlayModeManager, settings dict)
    """
    manager = PlayModeManager()
    manager.start_playtest_mode(mission_id=mission_id, region_id=region_id, seed=seed)
    settings = get_playtest_settings()

    return manager, settings


def create_sandbox_session(
    seed: int | None = None, shape: str = "grid", rooms: int = 6
) -> tuple[PlayModeManager, dict[str, Any]]:
    """
    Create sandbox mode session.

    Args:
        seed: World seed
        shape: World shape
        rooms: Number of rooms

    Returns:
        (PlayModeManager, settings dict)
    """
    manager = PlayModeManager()
    manager.start_sandbox_mode(seed=seed, shape=shape, rooms=rooms)
    settings = get_sandbox_settings()

    return manager, settings
