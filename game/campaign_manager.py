"""
Campaign Manager - Orchestrates mission-based campaign progression

Manages campaign state, region unlocking, mission progression,
and ability unlocks through the story.

Version: v0.7.0 (Phase 8 - Story Integration)
"""

from dataclasses import dataclass, field
from enum import Enum

from game.story_manager import StoryManager

# ============================================================
# Region Definitions
# ============================================================


class Region(Enum):
    """Campaign regions"""

    CENTRAL_HUB = "central_hub"
    FOREST = "forest"
    TOWN = "town"
    CAVES = "caves"
    CASTLE = "castle"
    SEWER = "sewer"
    HOLLOW_DEPTHS = "hollow_depths"  # Act 2 - Recovery zone after Veil Maiden defeat


# ============================================================
# Campaign State
# ============================================================


@dataclass
class CampaignState:
    """Current campaign state"""

    world_seed: int
    current_hub: str = "central_hub"
    current_region: str | None = None
    current_position: tuple[float, float] = (0.0, 0.0)

    # Progression
    unlocked_regions: set[str] = field(default_factory=lambda: {"central_hub", "forest"})
    completed_missions: set[str] = field(default_factory=set)
    unlocked_abilities: set[str] = field(default_factory=lambda: {"basic_movement", "jump"})

    # Statistics
    mission_attempts: dict[str, int] = field(default_factory=dict)
    mission_best_times: dict[str, float] = field(default_factory=dict)
    total_deaths: int = 0
    total_play_time: float = 0.0

    # Inventory (simplified - full system in inventory_system.py)
    currency: int = 0
    collected_items: set[str] = field(default_factory=set)


# ============================================================
# Campaign Manager
# ============================================================


class CampaignManager:
    """
    Manages campaign progression and state.

    Responsibilities:
    - Track campaign state (regions, missions, abilities)
    - Region unlock logic
    - Mission completion handling
    - Ability unlock progression
    - Campaign statistics
    """

    def __init__(self, world_seed: int):
        """
        Initialize campaign manager.

        Args:
            world_seed: Seed for campaign world generation
        """
        self.state = CampaignState(world_seed=world_seed)

        # Story manager (The Hollowed Ninja narrative)
        self.story_manager = StoryManager()

        # Region unlock requirements
        self.region_requirements = {
            Region.CENTRAL_HUB: {},  # Always unlocked
            Region.FOREST: {},  # Always unlocked at start
            Region.TOWN: {"missions_complete": ["forest_1", "forest_2", "forest_3"]},
            Region.CAVES: {"abilities": ["double_jump", "dash"]},
            Region.CASTLE: {
                "missions_complete": ["town_1", "town_2", "town_3", "town_4", "town_5"],
                "abilities": ["wall_jump"],
            },
            Region.SEWER: {"completion_percent": 0.5},  # 50% of all other regions
        }

    def start_new_campaign(self):
        """Start a new campaign from the beginning"""
        self.state = CampaignState(world_seed=self.state.world_seed)
        self.story_manager = StoryManager()  # Reset story state

    def is_region_unlocked(self, region: Region) -> bool:
        """Check if a region is unlocked"""
        return region.value in self.state.unlocked_regions

    def can_unlock_region(self, region: Region) -> tuple[bool, list[str]]:
        """
        Check if region can be unlocked.

        Args:
            region: Region to check

        Returns:
            (can_unlock, missing_requirements)
        """
        if self.is_region_unlocked(region):
            return True, []

        requirements = self.region_requirements.get(region, {})
        missing = []

        # Check mission requirements
        if "missions_complete" in requirements:
            required_missions = set(requirements["missions_complete"])
            completed = self.state.completed_missions
            missing_missions = required_missions - completed

            if missing_missions:
                missing.extend([f"Complete {m}" for m in missing_missions])

        # Check ability requirements
        if "abilities" in requirements:
            required_abilities = set(requirements["abilities"])
            unlocked = self.state.unlocked_abilities
            missing_abilities = required_abilities - unlocked

            if missing_abilities:
                missing.extend([f"Unlock {a}" for a in missing_abilities])

        # Check completion percent requirement
        if "completion_percent" in requirements:
            required_percent = requirements["completion_percent"]
            current_percent = self.get_overall_completion_percent()

            if current_percent < required_percent:
                missing.append(f"Complete {int(required_percent * 100)}% of game")

        return len(missing) == 0, missing

    def unlock_region(self, region: Region) -> bool:
        """
        Unlock a region.

        Args:
            region: Region to unlock

        Returns:
            True if newly unlocked, False if already unlocked
        """
        if region.value in self.state.unlocked_regions:
            return False

        self.state.unlocked_regions.add(region.value)
        return True

    def complete_mission(
        self,
        mission_id: str,
        completion_time: float,
        abilities_unlocked: list[str] | None = None,
        currency_reward: int = 0,
    ):
        """
        Mark mission as completed.

        Args:
            mission_id: Mission ID
            completion_time: Time taken to complete (seconds)
            abilities_unlocked: Abilities unlocked as reward
            currency_reward: Gold/currency reward

        Returns:
            Story events triggered (dict from story_manager)
        """
        # Mark as completed
        self.state.completed_missions.add(mission_id)

        # Update best time
        if mission_id not in self.state.mission_best_times:
            self.state.mission_best_times[mission_id] = completion_time
        else:
            self.state.mission_best_times[mission_id] = min(
                self.state.mission_best_times[mission_id], completion_time
            )

        # Unlock abilities
        if abilities_unlocked:
            for ability in abilities_unlocked:
                self.state.unlocked_abilities.add(ability)

        # Award currency
        self.state.currency += currency_reward

        # Trigger story events
        story_events = self.story_manager.on_mission_complete(mission_id, self)

        # Check for region unlocks
        self._check_region_unlocks()

        return story_events

    def attempt_mission(self, mission_id: str):
        """Record a mission attempt"""
        if mission_id not in self.state.mission_attempts:
            self.state.mission_attempts[mission_id] = 0

        self.state.mission_attempts[mission_id] += 1

    def has_completed_mission(self, mission_id: str) -> bool:
        """Check if mission has been completed"""
        return mission_id in self.state.completed_missions

    def has_ability(self, ability: str) -> bool:
        """Check if ability is unlocked"""
        return ability in self.state.unlocked_abilities

    def unlock_ability(self, ability: str):
        """Unlock an ability"""
        self.state.unlocked_abilities.add(ability)
        self._check_region_unlocks()

    def get_region_completion_percent(self, region: Region) -> float:
        """
        Get completion percentage for a region.

        Args:
            region: Region to check

        Returns:
            Completion percent (0.0 - 1.0)
        """
        # Get all missions for this region
        region_missions = self._get_region_missions(region)

        if not region_missions:
            return 0.0

        completed = len([m for m in region_missions if m in self.state.completed_missions])
        return completed / len(region_missions)

    def get_overall_completion_percent(self) -> float:
        """Get overall campaign completion percentage"""
        all_regions = [Region.FOREST, Region.TOWN, Region.CAVES, Region.CASTLE, Region.SEWER]

        total_completion = sum(self.get_region_completion_percent(r) for r in all_regions)
        return total_completion / len(all_regions)

    def get_unlocked_abilities(self) -> set[str]:
        """Get set of unlocked abilities"""
        return self.state.unlocked_abilities.copy()

    def get_completed_missions(self) -> set[str]:
        """Get set of completed missions"""
        return self.state.completed_missions.copy()

    def get_statistics(self) -> dict[str, any]:
        """Get campaign statistics"""
        return {
            "completed_missions": len(self.state.completed_missions),
            "total_attempts": sum(self.state.mission_attempts.values()),
            "total_deaths": self.state.total_deaths,
            "total_play_time": self.state.total_play_time,
            "currency": self.state.currency,
            "completion_percent": self.get_overall_completion_percent(),
            "unlocked_regions": len(self.state.unlocked_regions),
            "unlocked_abilities": len(self.state.unlocked_abilities),
        }

    def _check_region_unlocks(self):
        """Check and auto-unlock regions when requirements are met"""
        for region in Region:
            if not self.is_region_unlocked(region):
                can_unlock, _ = self.can_unlock_region(region)
                if can_unlock:
                    self.unlock_region(region)

    def _get_region_missions(self, region: Region) -> list[str]:
        """Get all missions for a region (placeholder)"""
        # In full implementation, this would query mission_system.py
        mission_counts = {
            Region.FOREST: ["forest_1", "forest_2", "forest_3", "forest_4", "forest_5"],
            Region.TOWN: ["town_1", "town_2", "town_3", "town_4", "town_5", "town_6"],
            Region.CAVES: ["caves_1", "caves_2", "caves_3", "caves_4", "caves_5"],
            Region.CASTLE: ["castle_1", "castle_2", "castle_3", "castle_4", "castle_5", "castle_6"],
            Region.SEWER: ["sewer_1", "sewer_2", "sewer_3"],
        }

        return mission_counts.get(region, [])

    def save_to_dict(self) -> dict:
        """Serialize campaign state to dictionary"""
        return {
            "world_seed": self.state.world_seed,
            "current_hub": self.state.current_hub,
            "current_region": self.state.current_region,
            "current_position": list(self.state.current_position),
            "unlocked_regions": list(self.state.unlocked_regions),
            "completed_missions": list(self.state.completed_missions),
            "unlocked_abilities": list(self.state.unlocked_abilities),
            "mission_attempts": self.state.mission_attempts,
            "mission_best_times": self.state.mission_best_times,
            "total_deaths": self.state.total_deaths,
            "total_play_time": self.state.total_play_time,
            "currency": self.state.currency,
            "collected_items": list(self.state.collected_items),
            "story_state": self.story_manager.to_dict(),  # Story progression
        }

    def load_from_dict(self, data: dict):
        """Load campaign state from dictionary"""
        self.state.world_seed = data.get("world_seed", 0)
        self.state.current_hub = data.get("current_hub", "central_hub")
        self.state.current_region = data.get("current_region")
        self.state.current_position = tuple(data.get("current_position", [0.0, 0.0]))
        self.state.unlocked_regions = set(data.get("unlocked_regions", ["central_hub", "forest"]))
        self.state.completed_missions = set(data.get("completed_missions", []))
        self.state.unlocked_abilities = set(
            data.get("unlocked_abilities", ["basic_movement", "jump"])
        )
        self.state.mission_attempts = data.get("mission_attempts", {})
        self.state.mission_best_times = data.get("mission_best_times", {})
        self.state.total_deaths = data.get("total_deaths", 0)
        self.state.total_play_time = data.get("total_play_time", 0.0)
        self.state.currency = data.get("currency", 0)
        self.state.collected_items = set(data.get("collected_items", []))

        # Load story state (backwards compatible with old saves)
        if "story_state" in data:
            self.story_manager = StoryManager.from_dict(data["story_state"])
        else:
            # Old save without story state - create new story manager
            self.story_manager = StoryManager()


# ============================================================
# Helper Functions
# ============================================================


def create_campaign(world_seed: int) -> CampaignManager:
    """Create a new campaign"""
    return CampaignManager(world_seed)


def get_region_display_name(region: Region) -> str:
    """Get display name for region"""
    names = {
        Region.CENTRAL_HUB: "Central Hub",
        Region.FOREST: "Whispering Forest",
        Region.TOWN: "Merchant Town",
        Region.CAVES: "Crystal Caves",
        Region.CASTLE: "Dark Castle",
        Region.SEWER: "Ancient Sewer",
    }
    return names.get(region, region.value.title())


def get_region_description(region: Region) -> str:
    """Get description for region"""
    descriptions = {
        Region.CENTRAL_HUB: "Safe haven connecting all regions",
        Region.FOREST: "Dense woodland filled with creatures",
        Region.TOWN: "Bustling marketplace and training grounds",
        Region.CAVES: "Treacherous vertical caverns",
        Region.CASTLE: "Fortress of the corrupted nobles",
        Region.SEWER: "Ancient depths beneath the castle",
        Region.HOLLOW_DEPTHS: "Empty void where light struggles to exist",
    }
    return descriptions.get(region, "Unknown region")
