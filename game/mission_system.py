"""
Mission System - Mission Definitions and Progression

This module provides mission and region metadata for campaign mode:
- Mission definitions with objectives and rewards
- Region definitions with biome themes
- Ability unlock requirements and grants
- Progression tracking
- Deterministic mission generation

Version: v0.6.0
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from systems.world_generation import BiomeTheme


class ObjectiveType(Enum):
    """Types of mission objectives"""
    KILL_ALL_ENEMIES = "kill_all_enemies"
    COLLECT_ITEMS = "collect_items"
    ACTIVATE_SWITCHES = "activate_switches"
    REACH_LOCATION = "reach_location"
    TIME_CHALLENGE = "time_challenge"
    DEFEAT_BOSS = "defeat_boss"


@dataclass
class MissionObjective:
    """
    Single objective within a mission.

    Objectives must be completed to unlock the exit portal.
    """
    objective_type: ObjectiveType
    description: str
    target_count: int = 1  # For kill/collect/switch objectives
    target_location: Optional[str] = None  # For reach objectives (e.g., "shrine")
    time_limit: Optional[float] = None  # For time challenge (seconds)


@dataclass
class MissionDefinition:
    """
    Complete mission definition.

    Defines everything needed to generate and complete a mission.
    """
    mission_id: str
    region_id: str
    display_name: str
    description: str

    # World generation parameters
    room_count: int
    world_shape: str  # "blob", "snake", "branchy"

    # Objectives
    objectives: List[MissionObjective]

    # Ability requirements and unlocks
    required_abilities: List[str] = field(default_factory=list)
    unlock_abilities: List[str] = field(default_factory=list)

    # Rewards
    reward_loot_table: Optional[str] = None
    reward_currency: int = 0
    reward_items: List[str] = field(default_factory=list)

    # Difficulty
    difficulty: int = 1  # 1-5 scale
    recommended_level: int = 1

    def __post_init__(self):
        """Validate mission definition"""
        if self.room_count < 3:
            raise ValueError(f"Mission {self.mission_id}: room_count must be >= 3")
        if not self.objectives:
            raise ValueError(f"Mission {self.mission_id}: must have at least one objective")


@dataclass
class RegionDefinition:
    """
    Region metadata.

    Defines a region (hub + missions) in the campaign.
    """
    region_id: str
    display_name: str
    description: str
    biome_theme: BiomeTheme
    hub_room_count: int
    mission_ids: List[str]

    # Unlock requirements
    required_missions_completed: int = 0  # Number of missions from previous regions
    required_abilities: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate region definition"""
        if self.hub_room_count < 5:
            raise ValueError(f"Region {self.region_id}: hub_room_count must be >= 5")


REGION_METADATA = {
    "forest": {
        "display_name": "Whispering Forest",
        "description": "Ancient woodland full of secrets.",
        "biome_theme": BiomeTheme.DUNGEON,
        "hub_room_count": 8
    },
    "town": {
        "display_name": "Ashenvale Town",
        "description": "A troubled town under corruption.",
        "biome_theme": BiomeTheme.BUILDING,
        "hub_room_count": 8
    },
    "caves": {
        "display_name": "Crystal Caverns",
        "description": "Luminous caverns beneath the surface.",
        "biome_theme": BiomeTheme.CAVE,
        "hub_room_count": 8
    },
    "castle": {
        "display_name": "Obsidian Castle",
        "description": "A fortress of stone and shadow.",
        "biome_theme": BiomeTheme.BUILDING,
        "hub_room_count": 8
    },
    "sewer": {
        "display_name": "Shadow Sewers",
        "description": "Toxic tunnels beneath the city.",
        "biome_theme": BiomeTheme.DUNGEON,
        "hub_room_count": 8
    }
}


def _get_region_metadata(region_id: str) -> Dict[str, object]:
    metadata = REGION_METADATA.get(region_id)
    if metadata:
        return metadata

    display_name = region_id.replace("_", " ").title()
    return {
        "display_name": display_name,
        "description": f"A region known as {display_name}.",
        "biome_theme": BiomeTheme.DUNGEON,
        "hub_room_count": 8
    }


class MissionRegistry:
    """
    Registry of all missions and regions.

    Provides lookup and validation for campaign progression.
    """

    def __init__(self):
        self.missions: Dict[str, MissionDefinition] = {}
        self.regions: Dict[str, RegionDefinition] = {}
        self._register_default_content()

    def register_mission(self, mission: MissionDefinition):
        """Register a mission definition"""
        self.missions[mission.mission_id] = mission

    def register_region(self, region: RegionDefinition):
        """Register a region definition"""
        self.regions[region.region_id] = region

    def get_mission(self, mission_id: str) -> Optional[MissionDefinition]:
        """Get mission by ID"""
        return self.missions.get(mission_id)

    def get_region(self, region_id: str) -> Optional[RegionDefinition]:
        """Get region by ID"""
        return self.regions.get(region_id)

    def get_region_missions(self, region_id: str) -> List[MissionDefinition]:
        """Get all missions for a region"""
        region = self.get_region(region_id)
        if region is None:
            return []
        return [self.missions[mid] for mid in region.mission_ids if mid in self.missions]

    def is_mission_unlocked(self, mission_id: str, unlocked_abilities: Set[str]) -> bool:
        """
        Check if mission is unlocked.

        Args:
            mission_id: Mission to check
            unlocked_abilities: Set of abilities player has unlocked

        Returns:
            True if mission requirements met
        """
        mission = self.get_mission(mission_id)
        if mission is None:
            return False

        # Check ability requirements
        for ability in mission.required_abilities:
            if ability not in unlocked_abilities:
                return False

        return True

    def is_region_unlocked(self, region_id: str, completed_missions: Set[str],
                          unlocked_abilities: Set[str]) -> bool:
        """
        Check if region is unlocked.

        Args:
            region_id: Region to check
            completed_missions: Set of completed mission IDs
            unlocked_abilities: Set of unlocked abilities

        Returns:
            True if region requirements met
        """
        region = self.get_region(region_id)
        if region is None:
            return False

        # Check mission completion requirement
        if len(completed_missions) < region.required_missions_completed:
            return False

        # Check ability requirements
        for ability in region.required_abilities:
            if ability not in unlocked_abilities:
                return False

        return True

    def _register_default_content(self):
        """Register missions and regions from missions.json."""
        missions_path = Path(__file__).resolve().parent.parent / "data" / "missions.json"
        if not missions_path.exists():
            print(f"[MISSION] Warning: Missions file not found: {missions_path}")
            return

        try:
            data = json.loads(missions_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[MISSION] Error loading missions: {exc}")
            return

        region_map: Dict[str, List[str]] = {}
        for mission_data in data.get("missions", []):
            try:
                mission = self._mission_from_dict(mission_data)
            except Exception as exc:
                mission_id = mission_data.get("mission_id", "<unknown>")
                print(f"[MISSION] Skipping mission '{mission_id}': {exc}")
                continue
            self.register_mission(mission)
            region_map.setdefault(mission.region_id, []).append(mission.mission_id)

        regions_data = data.get("regions", {})
        self._register_regions_from_map(region_map, regions_data)

    def _mission_from_dict(self, data: Dict) -> MissionDefinition:
        objectives = []
        for obj_data in data.get("objectives", []):
            objectives.append(self._objective_from_dict(obj_data, data))

        reward_items = self._extract_reward_items(
            data.get("rewards", {}).get("items", [])
        )

        return MissionDefinition(
            mission_id=data["mission_id"],
            region_id=data.get("region", "unknown"),
            display_name=data.get("mission_name", data["mission_id"]),
            description=data.get("description", ""),
            room_count=data.get("room_count", 3),
            world_shape=data.get("shape", "blob"),
            objectives=objectives,
            required_abilities=data.get("required_abilities", []),
            unlock_abilities=data.get("unlock_abilities", []),
            reward_loot_table=data.get("reward_loot_table"),
            reward_currency=data.get("rewards", {}).get("currency", 0),
            reward_items=reward_items,
            difficulty=data.get("difficulty", 1),
            recommended_level=data.get("difficulty", 1)
        )

    def _objective_from_dict(self, data: Dict, mission_data: Dict) -> MissionObjective:
        obj_type = ObjectiveType(data["type"])
        target_count = data.get("count")
        if target_count is None:
            target_count = data.get("target")
        if target_count is None:
            target_count = 1

        time_limit = data.get("time_limit")
        if time_limit is None and obj_type == ObjectiveType.TIME_CHALLENGE:
            time_limit = mission_data.get("time_limit")

        return MissionObjective(
            objective_type=obj_type,
            description=data.get("description", ""),
            target_count=target_count,
            target_location=data.get("location"),
            time_limit=time_limit
        )

    def _extract_reward_items(self, rewards: List[object]) -> List[str]:
        items: List[str] = []
        for reward in rewards:
            if isinstance(reward, dict):
                item_id = reward.get("id") or reward.get("item_id")
            else:
                item_id = reward
            if item_id:
                items.append(item_id)
        return items

    def _normalize_region_metadata(self, region_id: str, data: Dict[str, object]) -> Dict[str, object]:
        display_name = data.get("display_name")
        if not display_name:
            display_name = region_id.replace("_", " ").title()

        description = data.get("description")
        if not description:
            description = f"A region known as {display_name}."

        biome_theme = self._parse_biome_theme(data.get("biome_theme"))
        hub_room_count = data.get("hub_room_count", 8)

        return {
            "display_name": display_name,
            "description": description,
            "biome_theme": biome_theme,
            "hub_room_count": hub_room_count,
            "required_missions_completed": data.get("required_missions_completed", 0),
            "required_abilities": data.get("required_abilities", []),
        }

    def _parse_biome_theme(self, value: object) -> BiomeTheme:
        if isinstance(value, BiomeTheme):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            for theme in BiomeTheme:
                if theme.value == lowered or theme.name.lower() == lowered:
                    return theme
        return BiomeTheme.DUNGEON

    def _register_regions_from_map(self, region_map: Dict[str, List[str]],
                                   regions_data: Optional[Dict[str, Dict[str, object]]] = None):
        region_metadata = regions_data or {}
        for region_id, mission_ids in region_map.items():
            if region_id in region_metadata:
                meta = self._normalize_region_metadata(region_id, region_metadata[region_id])
            else:
                meta = _get_region_metadata(region_id)
            region = RegionDefinition(
                region_id=region_id,
                display_name=meta["display_name"],
                description=meta["description"],
                biome_theme=meta["biome_theme"],
                hub_room_count=meta["hub_room_count"],
                mission_ids=mission_ids,
                required_missions_completed=meta.get("required_missions_completed", 0),
                required_abilities=meta.get("required_abilities", [])
            )
            self.register_region(region)


# Global registry instance
_mission_registry = MissionRegistry()


def get_mission_registry() -> MissionRegistry:
    """Get the global mission registry instance"""
    return _mission_registry
