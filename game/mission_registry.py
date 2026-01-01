"""
Mission Registry - Load and manage mission definitions

Loads mission data from missions.json and provides lookup functionality.

Version: v0.6.0 (Phase 7)
"""

import json
import os
from dataclasses import dataclass
from enum import Enum

# ============================================================
# Objective Types
# ============================================================


class ObjectiveType(Enum):
    """Mission objective types"""

    KILL_ALL_ENEMIES = "kill_all_enemies"
    COLLECT_ITEMS = "collect_items"
    ACTIVATE_SWITCHES = "activate_switches"
    REACH_LOCATION = "reach_location"
    TIME_CHALLENGE = "time_challenge"
    DEFEAT_BOSS = "defeat_boss"


# ============================================================
# Mission Data Structures
# ============================================================


@dataclass
class MissionObjective:
    """Single mission objective"""

    objective_type: ObjectiveType
    description: str
    target: int | None = None
    item: str | None = None
    count: int | None = None
    location: str | None = None
    boss: str | None = None
    time_limit: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "MissionObjective":
        """Create objective from dictionary"""
        obj_type = ObjectiveType(data["type"])
        return cls(
            objective_type=obj_type,
            description=data.get("description", ""),
            target=data.get("target"),
            item=data.get("item"),
            count=data.get("count"),
            location=data.get("location"),
            boss=data.get("boss"),
            time_limit=data.get("time_limit"),
        )


@dataclass
class MissionRewards:
    """Mission completion rewards"""

    currency: int = 0
    items: list[dict[str, any]] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []

    @classmethod
    def from_dict(cls, data: dict) -> "MissionRewards":
        """Create rewards from dictionary"""
        return cls(currency=data.get("currency", 0), items=data.get("items", []))


@dataclass
class MissionDefinition:
    """Complete mission definition"""

    mission_id: str
    mission_name: str
    region: str
    difficulty: int
    room_count: int
    shape: str
    description: str
    objectives: list[MissionObjective]
    required_abilities: list[str]
    unlock_abilities: list[str]
    rewards: MissionRewards
    enemy_types: list[str]
    hazards: list[str]
    time_limit: float | None
    unlock_requirements: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "MissionDefinition":
        """Create mission definition from dictionary"""
        return cls(
            mission_id=data["mission_id"],
            mission_name=data["mission_name"],
            region=data["region"],
            difficulty=data["difficulty"],
            room_count=data["room_count"],
            shape=data["shape"],
            description=data["description"],
            objectives=[MissionObjective.from_dict(obj) for obj in data["objectives"]],
            required_abilities=data.get("required_abilities", []),
            unlock_abilities=data.get("unlock_abilities", []),
            rewards=MissionRewards.from_dict(data.get("rewards", {})),
            enemy_types=data.get("enemy_types", []),
            hazards=data.get("hazards", []),
            time_limit=data.get("time_limit"),
            unlock_requirements=data.get("unlock_requirements", []),
        )

    def has_boss(self) -> bool:
        """Check if mission has a boss objective"""
        return any(obj.objective_type == ObjectiveType.DEFEAT_BOSS for obj in self.objectives)

    def is_timed(self) -> bool:
        """Check if mission has a time limit"""
        return self.time_limit is not None

    def get_total_currency_reward(self) -> int:
        """Get total currency reward"""
        return self.rewards.currency

    def get_item_rewards(self) -> list[dict]:
        """Get list of item rewards"""
        return self.rewards.items


# ============================================================
# Mission Registry
# ============================================================


class MissionRegistry:
    """
    Mission registry for loading and managing mission definitions.

    Responsibilities:
    - Load missions from JSON file
    - Provide mission lookup by ID
    - Query missions by region
    - Filter missions by requirements
    """

    def __init__(self, missions_file: str = None):
        """
        Initialize mission registry

        Args:
            missions_file: Path to missions.json file
        """
        if missions_file is None:
            # Default to data/missions.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            missions_file = os.path.join(base_dir, "data", "missions.json")

        self.missions_file = missions_file
        self.missions: dict[str, MissionDefinition] = {}
        self.missions_by_region: dict[str, list[str]] = {}

        self._load_missions()

    def _load_missions(self):
        """Load missions from JSON file"""
        if not os.path.exists(self.missions_file):
            print(f"[MISSION] Warning: Missions file not found: {self.missions_file}")
            return

        try:
            with open(self.missions_file) as f:
                data = json.load(f)

            mission_count = 0
            for mission_data in data.get("missions", []):
                mission = MissionDefinition.from_dict(mission_data)
                self.missions[mission.mission_id] = mission

                # Index by region
                if mission.region not in self.missions_by_region:
                    self.missions_by_region[mission.region] = []
                self.missions_by_region[mission.region].append(mission.mission_id)

                mission_count += 1

            print(f"[MISSION] Loaded {mission_count} missions from {self.missions_file}")

        except Exception as e:
            print(f"[MISSION] Error loading missions: {e}")

    def get_mission(self, mission_id: str) -> MissionDefinition | None:
        """
        Get mission definition by ID

        Args:
            mission_id: Mission identifier

        Returns:
            Mission definition or None if not found
        """
        return self.missions.get(mission_id)

    def get_missions_in_region(self, region: str) -> list[MissionDefinition]:
        """
        Get all missions in a region

        Args:
            region: Region identifier

        Returns:
            List of mission definitions
        """
        mission_ids = self.missions_by_region.get(region, [])
        return [self.missions[mid] for mid in mission_ids]

    def get_available_missions(
        self, unlocked_abilities: set[str], completed_missions: set[str]
    ) -> list[MissionDefinition]:
        """
        Get missions that are currently available

        Args:
            unlocked_abilities: Set of unlocked ability IDs
            completed_missions: Set of completed mission IDs

        Returns:
            List of available missions
        """
        available = []

        for mission in self.missions.values():
            # Skip if already completed
            if mission.mission_id in completed_missions:
                continue

            # Check ability requirements
            has_abilities = all(
                ability in unlocked_abilities for ability in mission.required_abilities
            )

            if not has_abilities:
                continue

            # Check mission unlock requirements
            has_prereqs = all(
                prereq in completed_missions for prereq in mission.unlock_requirements
            )

            if not has_prereqs:
                continue

            available.append(mission)

        return available

    def is_mission_unlocked(
        self,
        mission_id: str,
        unlocked_abilities: set[str],
        completed_missions: set[str] | None = None,
    ) -> bool:
        """
        Check if a specific mission is unlocked.

        Args:
            mission_id: Mission identifier
            unlocked_abilities: Set of unlocked ability IDs
            completed_missions: Optional set of completed mission IDs

        Returns:
            True if mission requirements are met
        """
        mission = self.get_mission(mission_id)
        if not mission:
            return False

        completed = completed_missions or set()

        has_abilities = all(ability in unlocked_abilities for ability in mission.required_abilities)
        if not has_abilities:
            return False

        has_prereqs = all(prereq in completed for prereq in mission.unlock_requirements)
        return has_prereqs

    def get_locked_missions(
        self, unlocked_abilities: set[str], completed_missions: set[str]
    ) -> list[MissionDefinition]:
        """
        Get missions that are locked

        Args:
            unlocked_abilities: Set of unlocked ability IDs
            completed_missions: Set of completed mission IDs

        Returns:
            List of locked missions with reasons
        """
        locked = []

        for mission in self.missions.values():
            # Skip if already completed
            if mission.mission_id in completed_missions:
                continue

            # Check if locked
            has_abilities = all(
                ability in unlocked_abilities for ability in mission.required_abilities
            )

            has_prereqs = all(
                prereq in completed_missions for prereq in mission.unlock_requirements
            )

            if not has_abilities or not has_prereqs:
                locked.append(mission)

        return locked

    def get_boss_missions(self) -> list[MissionDefinition]:
        """Get all missions with boss encounters"""
        return [m for m in self.missions.values() if m.has_boss()]

    def get_timed_missions(self) -> list[MissionDefinition]:
        """Get all missions with time limits"""
        return [m for m in self.missions.values() if m.is_timed()]

    def get_mission_count(self) -> int:
        """Get total number of missions"""
        return len(self.missions)

    def get_mission_count_by_region(self, region: str) -> int:
        """Get number of missions in a region"""
        return len(self.missions_by_region.get(region, []))

    def get_all_regions(self) -> list[str]:
        """Get list of all regions"""
        return list(self.missions_by_region.keys())

    def get_mission_unlock_requirements(self, mission_id: str) -> dict[str, list[str]]:
        """
        Get requirements to unlock a mission

        Args:
            mission_id: Mission identifier

        Returns:
            Dictionary with 'abilities' and 'missions' keys
        """
        mission = self.get_mission(mission_id)
        if not mission:
            return {"abilities": [], "missions": []}

        return {"abilities": mission.required_abilities, "missions": mission.unlock_requirements}

    def get_missions_by_pool(self, pool_ids: list[str]) -> list[MissionDefinition]:
        """
        Get missions matching a list of IDs (pool).

        Args:
            pool_ids: List of mission IDs

        Returns:
            List of mission definitions in the provided order
        """
        missions = []
        for mission_id in pool_ids:
            mission = self.get_mission(mission_id)
            if mission:
                missions.append(mission)
        return missions


# ============================================================
# Global Registry Instance
# ============================================================

_global_registry: MissionRegistry | None = None


def get_mission_registry() -> MissionRegistry:
    """Get global mission registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = MissionRegistry()
    return _global_registry


def load_missions(missions_file: str = None) -> MissionRegistry:
    """
    Load missions and return registry

    Args:
        missions_file: Optional path to missions.json

    Returns:
        Mission registry instance
    """
    global _global_registry
    _global_registry = MissionRegistry(missions_file)
    return _global_registry


# ============================================================
# Helper Functions
# ============================================================


def get_mission(mission_id: str) -> MissionDefinition | None:
    """Get mission by ID from global registry"""
    return get_mission_registry().get_mission(mission_id)


def get_missions_for_region(region: str) -> list[MissionDefinition]:
    """Get all missions for a region"""
    return get_mission_registry().get_missions_in_region(region)


def count_missions_by_region() -> dict[str, int]:
    """Get mission count for each region"""
    registry = get_mission_registry()
    return {
        region: registry.get_mission_count_by_region(region)
        for region in registry.get_all_regions()
    }
