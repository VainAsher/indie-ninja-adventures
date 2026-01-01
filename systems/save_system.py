"""
Save System - Persistent data management

Handles saving and loading:
- Player progress (levels completed, stats)
- Game settings (volume, controls, graphics)
- Statistics (total playtime, deaths, coins)

Architecture:
- JSON-based save files
- Versioned save format
- Auto-save on key events
- Backup system for safety
"""

import hashlib
import hmac
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ============================================================
# Save File Integrity Constants
# ============================================================

# Secret key for HMAC signature (in production, this should be in a separate config file)
SAVE_SECRET_KEY = b"ninja_dash_v0_3_save_integrity_key_2025"

# Validation limits to detect tampering
MAX_CURRENCY_LIMIT = 999999  # Maximum reasonable currency
MAX_PLAYTIME_LIMIT = 100000.0  # Maximum reasonable playtime (hours)
MAX_MISSIONS_LIMIT = 1000  # Maximum reasonable mission count
MAX_ABILITIES_LIMIT = 50  # Maximum reasonable abilities


@dataclass
class PlayerProgress:
    """Player progression data"""

    levels_completed: list[str]  # List of completed level IDs
    current_level: str = "level_1"
    total_playtime: float = 0.0  # seconds
    total_coins: int = 0
    total_collectibles: int = 0
    total_deaths: int = 0
    best_times: dict[str, float] = None  # level_id -> best completion time
    tutorials_seen: list[str] = None  # List of tutorial IDs shown

    def __post_init__(self):
        if self.best_times is None:
            self.best_times = {}
        if self.tutorials_seen is None:
            self.tutorials_seen = []


@dataclass
class GameSettings:
    """Game settings/preferences"""

    # Audio
    master_volume: float = 1.0
    music_volume: float = 0.8
    sfx_volume: float = 1.0

    # Graphics
    fullscreen: bool = False
    window_width: int = 1280
    window_height: int = 720
    vsync: bool = True
    show_fps: bool = False

    # Gameplay
    camera_shake: bool = True
    screen_flash: bool = True
    particles: bool = True

    # Controls (placeholder for future keybinding)
    control_scheme: str = "keyboard"


@dataclass
class GameStatistics:
    """Lifetime game statistics"""

    total_playtime: float = 0.0
    total_levels_completed: int = 0
    total_deaths: int = 0
    total_coins_collected: int = 0
    total_collectibles_found: int = 0
    total_damage_taken: int = 0
    total_jumps: int = 0
    total_dashes: int = 0
    fastest_level_time: float = 0.0
    perfect_runs: int = 0  # No deaths, all collectibles


@dataclass
class CampaignSaveData:
    """Campaign progression data (v0.7.0)"""

    # World state
    world_seed: int = 0
    current_hub_id: str = "central_hub"
    current_hub_position: tuple[float, float] = (0.0, 0.0)

    # Progression
    unlocked_regions: set[str] = field(default_factory=lambda: {"central_hub", "forest"})
    completed_missions: set[str] = field(default_factory=set)
    unlocked_abilities: set[str] = field(default_factory=lambda: {"basic_movement", "jump"})

    # Mission tracking
    mission_attempts: dict[str, int] = field(default_factory=dict)
    mission_best_times: dict[str, float] = field(default_factory=dict)

    # Inventory (item_id -> quantity)
    player_inventory: dict[str, int] = field(default_factory=dict)
    equipped_weapon: str | None = None
    equipped_armor: str | None = None

    # Currency
    currency: int = 0

    # Statistics
    total_deaths: int = 0
    total_play_time: float = 0.0

    # Story state (The Hollowed Ninja narrative) - v0.7.0
    story_state: dict[str, Any] | None = None


@dataclass
class SaveData:
    """Complete save file data"""

    version: str = "0.7.0"
    save_date: str = ""
    player_progress: PlayerProgress = None
    settings: GameSettings = None
    statistics: GameStatistics = None
    campaign: CampaignSaveData = None  # Campaign mode data (v0.6.0+, story added in v0.7.0)

    def __post_init__(self):
        if self.player_progress is None:
            self.player_progress = PlayerProgress(levels_completed=[])
        if self.settings is None:
            self.settings = GameSettings()
        if self.statistics is None:
            self.statistics = GameStatistics()
        if self.campaign is None:
            self.campaign = CampaignSaveData()
        if not self.save_date:
            self.save_date = time.strftime("%Y-%m-%d %H:%M:%S")


class SaveManager:
    """
    Manages game save data

    Features:
    - Save/load to JSON files
    - Versioned save format
    - Backup system (keeps last 3 saves)
    - Auto-save on key events
    - Statistics tracking
    - Campaign mode support (v0.6.0)
    - Story progression support (v0.7.0)
    """

    SAVE_VERSION = "0.7.0"

    def __init__(self, save_dir: str = None):
        """
        Initialize save manager

        Args:
            save_dir: Directory for save files (defaults to user_data/saves)
        """
        if save_dir is None:
            save_dir = os.path.join("user_data", "saves")

        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.save_file = self.save_dir / "savegame.json"
        self.backup_dir = self.save_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Current save data
        self.data: SaveData = SaveData()

        # Auto-save tracking
        self.last_save_time = 0.0
        self.auto_save_interval = 60.0  # Auto-save every 60 seconds
        self.needs_save = False

    def _calculate_signature(self, data_dict: dict[str, Any]) -> str:
        """
        Calculate HMAC signature for save data integrity

        Args:
            data_dict: Save data dictionary

        Returns:
            Hexadecimal signature string
        """
        # Create canonical JSON representation (sorted keys for consistency)
        data_str = json.dumps(data_dict, sort_keys=True)

        # Calculate HMAC-SHA256 signature
        signature = hmac.new(SAVE_SECRET_KEY, data_str.encode("utf-8"), hashlib.sha256).hexdigest()

        return signature

    def _verify_signature(self, data_dict: dict[str, Any], expected_signature: str) -> bool:
        """
        Verify save data signature

        Args:
            data_dict: Save data dictionary
            expected_signature: Expected signature

        Returns:
            True if signature is valid
        """
        calculated_signature = self._calculate_signature(data_dict)
        return hmac.compare_digest(calculated_signature, expected_signature)

    def _validate_save_data(self, save_dict: dict[str, Any]) -> list[str]:
        """
        Validate save data for suspicious values

        Args:
            save_dict: Save data dictionary

        Returns:
            List of validation warnings (empty if all valid)
        """
        warnings = []

        # Validate campaign data
        if "campaign" in save_dict:
            campaign = save_dict["campaign"]

            # Check currency limits
            currency = campaign.get("currency", 0)
            if currency > MAX_CURRENCY_LIMIT:
                warnings.append(f"Currency exceeds limit: {currency} > {MAX_CURRENCY_LIMIT}")
                campaign["currency"] = MAX_CURRENCY_LIMIT  # Clamp to max
            if currency < 0:
                warnings.append(f"Negative currency detected: {currency}")
                campaign["currency"] = 0  # Fix negative

            # Check playtime limits
            playtime = campaign.get("total_play_time", 0.0)
            if playtime > MAX_PLAYTIME_LIMIT:
                warnings.append(f"Playtime exceeds limit: {playtime} > {MAX_PLAYTIME_LIMIT}")
                campaign["total_play_time"] = MAX_PLAYTIME_LIMIT
            if playtime < 0:
                warnings.append(f"Negative playtime detected: {playtime}")
                campaign["total_play_time"] = 0.0

            # Check completed missions count
            completed_missions = campaign.get("completed_missions", [])
            if len(completed_missions) > MAX_MISSIONS_LIMIT:
                warnings.append(
                    f"Too many completed missions: {len(completed_missions)} > {MAX_MISSIONS_LIMIT}"
                )

            # Check unlocked abilities count
            unlocked_abilities = campaign.get("unlocked_abilities", [])
            if len(unlocked_abilities) > MAX_ABILITIES_LIMIT:
                warnings.append(
                    f"Too many abilities: {len(unlocked_abilities)} > {MAX_ABILITIES_LIMIT}"
                )

            # Check inventory for negative values
            inventory = campaign.get("player_inventory", {})
            for item_id, quantity in inventory.items():
                if quantity < 0:
                    warnings.append(f"Negative inventory item: {item_id} = {quantity}")
                    inventory[item_id] = 0
                if quantity > 9999:
                    warnings.append(f"Excessive inventory item: {item_id} = {quantity}")
                    inventory[item_id] = 999

        # Validate statistics
        if "statistics" in save_dict:
            stats = save_dict["statistics"]

            # Check total playtime
            total_playtime = stats.get("total_playtime", 0.0)
            if total_playtime < 0:
                warnings.append(f"Negative total_playtime: {total_playtime}")
                stats["total_playtime"] = 0.0

            # Check for negative counts
            for field in ["total_deaths", "total_coins_collected", "total_jumps", "total_dashes"]:
                value = stats.get(field, 0)
                if value < 0:
                    warnings.append(f"Negative {field}: {value}")
                    stats[field] = 0

        return warnings

    def load(self) -> bool:
        """
        Load save file

        Returns:
            True if loaded successfully, False if no save exists
        """
        if not self.save_file.exists():
            print("[SAVE] No save file found, creating new save")
            self.data = SaveData()
            return False

        try:
            with open(self.save_file) as f:
                save_wrapper = json.load(f)

            # Check if save file has integrity signature (new format)
            if "signature" in save_wrapper and "data" in save_wrapper:
                # New format with signature
                signature = save_wrapper["signature"]
                save_dict = save_wrapper["data"]

                # Verify signature
                if not self._verify_signature(save_dict, signature):
                    print(
                        "[SAVE] WARNING: Save file signature invalid! File may have been tampered with."
                    )
                    print("[SAVE] Loading anyway but applying strict validation...")
                else:
                    print("[SAVE] Save file signature verified ✓")
            else:
                # Old format without signature (backwards compatibility)
                print("[SAVE] Old save format detected (no signature)")
                save_dict = save_wrapper

            # Validate save data for suspicious values
            validation_warnings = self._validate_save_data(save_dict)
            if validation_warnings:
                print("[SAVE] WARNING: Save data validation issues detected:")
                for warning in validation_warnings:
                    print(f"[SAVE]   - {warning}")
                print("[SAVE] Suspicious values have been clamped to safe ranges.")

            # Version check
            version = save_dict.get("version", "0.0.0")
            if version != self.SAVE_VERSION:
                print(f"[SAVE] Save file version mismatch: {version} vs {self.SAVE_VERSION}")
                print("[SAVE] Attempting to migrate save data...")
                save_dict = self._migrate_save(save_dict, version)

            # Reconstruct save data from dict
            self.data = self._dict_to_savedata(save_dict)

            print(f"[SAVE] Loaded save file from {self.save_file}")
            print(
                f"[SAVE] Player progress: {len(self.data.player_progress.levels_completed)} levels completed"
            )
            print(f"[SAVE] Playtime: {self.data.statistics.total_playtime:.1f}s")

            return True

        except Exception as e:
            print(f"[SAVE] Error loading save file: {e}")
            print("[SAVE] Creating new save")
            self.data = SaveData()
            return False

    def save(self, force: bool = False) -> bool:
        """
        Save current data to file

        Args:
            force: Force save even if not needed

        Returns:
            True if saved successfully
        """
        if not force and not self.needs_save:
            return False

        try:
            # Update save date
            self.data.save_date = time.strftime("%Y-%m-%d %H:%M:%S")
            self.data.version = self.SAVE_VERSION

            # Create backup before saving
            if self.save_file.exists():
                self._create_backup()

            # Convert to dict
            save_dict = self._savedata_to_dict(self.data)

            # Calculate signature for integrity checking
            signature = self._calculate_signature(save_dict)

            # Create save wrapper with signature
            save_wrapper = {"version": self.SAVE_VERSION, "signature": signature, "data": save_dict}

            # Write to file
            with open(self.save_file, "w") as f:
                json.dump(save_wrapper, f, indent=2)

            self.needs_save = False
            self.last_save_time = time.time()

            print(f"[SAVE] Saved game to {self.save_file} (with integrity signature)")
            return True

        except Exception as e:
            print(f"[SAVE] Error saving file: {e}")
            return False

    def auto_save(self, current_time: float):
        """
        Auto-save if interval has passed

        Args:
            current_time: Current time in seconds
        """
        if self.needs_save and (current_time - self.last_save_time) >= self.auto_save_interval:
            if self.save():
                print("[SAVE] Auto-saved game")

    def mark_dirty(self):
        """Mark save data as needing to be saved"""
        self.needs_save = True

    def _create_backup(self):
        """Create backup of current save file"""
        if not self.save_file.exists():
            return

        # Backup filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"savegame_{timestamp}.json"

        shutil.copy2(self.save_file, backup_file)

        # Clean old backups (keep last 3)
        backups = sorted(self.backup_dir.glob("savegame_*.json"))
        while len(backups) > 3:
            oldest = backups.pop(0)
            oldest.unlink()

    def _savedata_to_dict(self, data: SaveData) -> dict[str, Any]:
        """Convert SaveData to dictionary"""
        save_dict = {
            "version": data.version,
            "save_date": data.save_date,
            "player_progress": asdict(data.player_progress),
            "settings": asdict(data.settings),
            "statistics": asdict(data.statistics),
        }

        # Handle campaign data with sets and tuples
        if data.campaign:
            campaign_dict = {
                "world_seed": data.campaign.world_seed,
                "current_hub_id": data.campaign.current_hub_id,
                "current_hub_position": list(data.campaign.current_hub_position),
                "unlocked_regions": list(data.campaign.unlocked_regions),
                "completed_missions": list(data.campaign.completed_missions),
                "unlocked_abilities": list(data.campaign.unlocked_abilities),
                "mission_attempts": data.campaign.mission_attempts,
                "mission_best_times": data.campaign.mission_best_times,
                "player_inventory": data.campaign.player_inventory,
                "equipped_weapon": data.campaign.equipped_weapon,
                "equipped_armor": data.campaign.equipped_armor,
                "currency": data.campaign.currency,
                "total_deaths": data.campaign.total_deaths,
                "total_play_time": data.campaign.total_play_time,
                "story_state": data.campaign.story_state,  # v0.7.0: Story progression
            }
            save_dict["campaign"] = campaign_dict

        return save_dict

    def _dict_to_savedata(self, data_dict: dict[str, Any]) -> SaveData:
        """Convert dictionary to SaveData"""
        # Handle campaign data with sets and tuples
        campaign = None
        if "campaign" in data_dict:
            campaign_dict = data_dict["campaign"]
            campaign = CampaignSaveData(
                world_seed=campaign_dict.get("world_seed", 0),
                current_hub_id=campaign_dict.get("current_hub_id", "central_hub"),
                current_hub_position=tuple(campaign_dict.get("current_hub_position", [0.0, 0.0])),
                unlocked_regions=set(
                    campaign_dict.get("unlocked_regions", ["central_hub", "forest"])
                ),
                completed_missions=set(campaign_dict.get("completed_missions", [])),
                unlocked_abilities=set(
                    campaign_dict.get("unlocked_abilities", ["basic_movement", "jump"])
                ),
                mission_attempts=campaign_dict.get("mission_attempts", {}),
                mission_best_times=campaign_dict.get("mission_best_times", {}),
                player_inventory=campaign_dict.get("player_inventory", {}),
                equipped_weapon=campaign_dict.get("equipped_weapon"),
                equipped_armor=campaign_dict.get("equipped_armor"),
                currency=campaign_dict.get("currency", 0),
                total_deaths=campaign_dict.get("total_deaths", 0),
                total_play_time=campaign_dict.get("total_play_time", 0.0),
                story_state=campaign_dict.get("story_state", None),  # v0.7.0: Story progression
            )

        return SaveData(
            version=data_dict.get("version", self.SAVE_VERSION),
            save_date=data_dict.get("save_date", ""),
            player_progress=PlayerProgress(**data_dict.get("player_progress", {})),
            settings=GameSettings(**data_dict.get("settings", {})),
            statistics=GameStatistics(**data_dict.get("statistics", {})),
            campaign=campaign,
        )

    def _migrate_save(self, save_dict: dict[str, Any], old_version: str) -> dict[str, Any]:
        """
        Migrate old save format to current version

        Args:
            save_dict: Old save data
            old_version: Old version string

        Returns:
            Migrated save data
        """
        print(f"[SAVE] Migrating from version {old_version} to {self.SAVE_VERSION}")

        # Ensure all required fields exist with defaults
        if "player_progress" not in save_dict:
            save_dict["player_progress"] = asdict(PlayerProgress(levels_completed=[]))
        if "settings" not in save_dict:
            save_dict["settings"] = asdict(GameSettings())
        if "statistics" not in save_dict:
            save_dict["statistics"] = asdict(GameStatistics())

        # Add campaign data for v0.6.0+ (migrate from v0.5.0)
        if "campaign" not in save_dict:
            print("[SAVE] Adding campaign data for v0.6.0")
            save_dict["campaign"] = {
                "world_seed": 0,
                "current_hub_id": "central_hub",
                "current_hub_position": [0.0, 0.0],
                "unlocked_regions": ["central_hub", "forest"],
                "completed_missions": [],
                "unlocked_abilities": ["basic_movement", "jump"],
                "mission_attempts": {},
                "mission_best_times": {},
                "player_inventory": {},
                "equipped_weapon": None,
                "equipped_armor": None,
                "currency": 0,
                "total_deaths": 0,
                "total_play_time": 0.0,
                "story_state": None,
            }

        # Add story state for v0.7.0+ (migrate from v0.6.0)
        if "campaign" in save_dict and "story_state" not in save_dict["campaign"]:
            print("[SAVE] Adding story state for v0.7.0")
            save_dict["campaign"]["story_state"] = None  # Will be initialized by StoryManager

        save_dict["version"] = self.SAVE_VERSION

        return save_dict

    # Convenience methods for common operations

    def complete_level(self, level_id: str, completion_time: float, collectibles: str, deaths: int):
        """Record level completion"""
        progress = self.data.player_progress

        # Add to completed levels if not already there
        if level_id not in progress.levels_completed:
            progress.levels_completed.append(level_id)
            self.data.statistics.total_levels_completed += 1

        # Update best time
        if level_id not in progress.best_times or completion_time < progress.best_times[level_id]:
            progress.best_times[level_id] = completion_time

        # Update statistics
        self.data.statistics.total_deaths += deaths

        # Check for perfect run (no deaths, all collectibles)
        collected, total = map(int, collectibles.split("/"))
        if deaths == 0 and collected == total:
            self.data.statistics.perfect_runs += 1

        self.mark_dirty()

    def update_playtime(self, delta_time: float):
        """Update total playtime"""
        self.data.statistics.total_playtime += delta_time
        self.mark_dirty()

    def add_coins(self, count: int):
        """Add collected coins"""
        self.data.player_progress.total_coins += count
        self.data.statistics.total_coins_collected += count
        self.mark_dirty()

    def add_collectibles(self, count: int):
        """Add collected collectibles"""
        self.data.player_progress.total_collectibles += count
        self.data.statistics.total_collectibles_found += count
        self.mark_dirty()

    def record_death(self):
        """Record a death"""
        self.data.statistics.total_deaths += 1
        self.mark_dirty()

    def record_damage(self, amount: int):
        """Record damage taken"""
        self.data.statistics.total_damage_taken += amount
        self.mark_dirty()

    def get_settings(self) -> GameSettings:
        """Get current settings"""
        return self.data.settings

    def update_settings(self, **kwargs):
        """Update settings with keyword arguments"""
        for key, value in kwargs.items():
            if hasattr(self.data.settings, key):
                setattr(self.data.settings, key, value)
        self.mark_dirty()

    def get_statistics(self) -> GameStatistics:
        """Get current statistics"""
        return self.data.statistics

    def reset_progress(self):
        """Reset player progress (keep settings and stats)"""
        self.data.player_progress = PlayerProgress(levels_completed=[])
        self.mark_dirty()
        print("[SAVE] Player progress reset")

    def reset_all(self):
        """Reset everything (new game)"""
        self.data = SaveData()
        self.mark_dirty()
        print("[SAVE] All data reset")

    # ============================================================
    # Campaign Mode Methods (v0.6.0)
    # ============================================================

    def complete_mission(
        self,
        mission_id: str,
        completion_time: float,
        abilities_unlocked: list[str] | None = None,
        currency_reward: int = 0,
    ):
        """
        Record mission completion

        Args:
            mission_id: Mission identifier
            completion_time: Time to complete in seconds
            abilities_unlocked: List of newly unlocked abilities
            currency_reward: Currency earned
        """
        campaign = self.data.campaign

        # Mark mission as completed
        campaign.completed_missions.add(mission_id)

        # Update mission attempts
        if mission_id not in campaign.mission_attempts:
            campaign.mission_attempts[mission_id] = 0
        campaign.mission_attempts[mission_id] += 1

        # Update best time
        if mission_id not in campaign.mission_best_times:
            campaign.mission_best_times[mission_id] = completion_time
        else:
            campaign.mission_best_times[mission_id] = min(
                campaign.mission_best_times[mission_id], completion_time
            )

        # Unlock abilities
        if abilities_unlocked:
            for ability in abilities_unlocked:
                campaign.unlocked_abilities.add(ability)
                print(f"[SAVE] Unlocked ability: {ability}")

        # Award currency
        campaign.currency += currency_reward
        if currency_reward > 0:
            print(f"[SAVE] Earned {currency_reward} currency")

        self.mark_dirty()
        print(f"[SAVE] Mission {mission_id} completed in {completion_time:.1f}s")

    def unlock_region(self, region_id: str):
        """
        Unlock a campaign region

        Args:
            region_id: Region identifier
        """
        if region_id not in self.data.campaign.unlocked_regions:
            self.data.campaign.unlocked_regions.add(region_id)
            self.mark_dirty()
            print(f"[SAVE] Unlocked region: {region_id}")
            return True
        return False

    def save_hub_position(self, hub_id: str, position: tuple[float, float]):
        """
        Save current hub and position

        Args:
            hub_id: Hub identifier
            position: Player position (x, y)
        """
        self.data.campaign.current_hub_id = hub_id
        self.data.campaign.current_hub_position = position
        self.mark_dirty()

    def save_inventory(
        self,
        inventory_dict: dict[str, int],
        equipped_weapon: str | None = None,
        equipped_armor: str | None = None,
        currency: int = 0,
    ):
        """
        Save player inventory state

        Args:
            inventory_dict: Item ID -> quantity mapping
            equipped_weapon: Currently equipped weapon ID
            equipped_armor: Currently equipped armor ID
            currency: Player currency amount
        """
        campaign = self.data.campaign
        campaign.player_inventory = inventory_dict.copy()
        campaign.equipped_weapon = equipped_weapon
        campaign.equipped_armor = equipped_armor
        campaign.currency = currency
        self.mark_dirty()

    def load_inventory(self) -> dict[str, Any]:
        """
        Load player inventory state

        Returns:
            Dictionary with keys: 'items', 'equipped_weapon', 'equipped_armor', 'currency'
        """
        campaign = self.data.campaign
        return {
            "items": campaign.player_inventory.copy(),
            "equipped_weapon": campaign.equipped_weapon,
            "equipped_armor": campaign.equipped_armor,
            "currency": campaign.currency,
        }

    def get_campaign_progress(self) -> dict[str, Any]:
        """
        Get campaign progress statistics

        Returns:
            Dictionary with campaign stats
        """
        campaign = self.data.campaign
        return {
            "world_seed": campaign.world_seed,
            "current_hub": campaign.current_hub_id,
            "unlocked_regions": len(campaign.unlocked_regions),
            "completed_missions": len(campaign.completed_missions),
            "unlocked_abilities": len(campaign.unlocked_abilities),
            "currency": campaign.currency,
            "total_deaths": campaign.total_deaths,
            "total_play_time": campaign.total_play_time,
        }

    def start_new_campaign(self, world_seed: int):
        """
        Start a new campaign

        Args:
            world_seed: World generation seed
        """
        self.data.campaign = CampaignSaveData(world_seed=world_seed)
        self.mark_dirty()
        print(f"[SAVE] Started new campaign with seed {world_seed}")
