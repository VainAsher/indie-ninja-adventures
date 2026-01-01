"""
Seed Hierarchy System - Deterministic 6-Level Seed Derivation

This module provides hierarchical seed generation for deterministic world creation:

Level 1: worldSeed (user input)
Level 2: regionSeed = hash(worldSeed, regionId)
Level 3: missionSeed = hash(regionSeed, missionId)
Level 4: roomSeed = hash(missionSeed, roomNodeId)
Level 5: subroomSeed = hash(roomSeed, subroomIndex)
Level 6: featureSeed = hash(subroomSeed, featureType)

Features:
- Deterministic hashing using SHA256
- Reproducible generation with same inputs
- Support for replay and network sync
- Easy to debug and trace seed origins

Version: v0.6.0
"""

import hashlib
from dataclasses import dataclass


class SeedDerivation:
    """
    Deterministic seed derivation using cryptographic hashing.

    Uses SHA256 to derive child seeds from parent seeds and identifiers,
    ensuring the same inputs always produce the same outputs.
    """

    @staticmethod
    def derive_seed(parent_seed: int, identifier: str) -> int:
        """
        Derive child seed from parent seed and identifier.

        Args:
            parent_seed: Parent seed value
            identifier: String identifier for this derivation

        Returns:
            32-bit integer seed value

        Example:
            >>> SeedDerivation.derive_seed(12345, "forest_region")
            2847561923
        """
        # Combine parent seed and identifier
        combined = f"{parent_seed}:{identifier}"

        # Hash using SHA256
        hash_digest = hashlib.sha256(combined.encode("utf-8")).digest()

        # Convert first 4 bytes to 32-bit integer
        seed_value = int.from_bytes(hash_digest[:4], byteorder="big")

        # Ensure positive 32-bit range
        return seed_value & 0x7FFFFFFF

    @staticmethod
    def derive_region_seed(world_seed: int, region_id: str) -> int:
        """
        Level 2: Derive region seed from world seed.

        Args:
            world_seed: Level 1 world seed
            region_id: Region identifier (e.g., "forest", "town", "caves")

        Returns:
            Region seed
        """
        return SeedDerivation.derive_seed(world_seed, f"region:{region_id}")

    @staticmethod
    def derive_mission_seed(region_seed: int, mission_id: str) -> int:
        """
        Level 3: Derive mission seed from region seed.

        Args:
            region_seed: Level 2 region seed
            mission_id: Mission identifier (e.g., "mission_01", "boss_forest")

        Returns:
            Mission seed
        """
        return SeedDerivation.derive_seed(region_seed, f"mission:{mission_id}")

    @staticmethod
    def derive_room_seed(mission_seed: int, room_node_id: str) -> int:
        """
        Level 4: Derive room seed from mission seed.

        Args:
            mission_seed: Level 3 mission seed
            room_node_id: Room node identifier (e.g., "room_0_0", "room_3_5")

        Returns:
            Room seed
        """
        return SeedDerivation.derive_seed(mission_seed, f"room:{room_node_id}")

    @staticmethod
    def derive_room_seed_from_coords(mission_seed: int, grid_x: int, grid_y: int) -> int:
        """
        Level 4: Derive room seed from mission seed using grid coordinates.

        Args:
            mission_seed: Level 3 mission seed
            grid_x: Room grid X coordinate
            grid_y: Room grid Y coordinate

        Returns:
            Room seed
        """
        room_node_id = f"{grid_x}_{grid_y}"
        return SeedDerivation.derive_room_seed(mission_seed, room_node_id)

    @staticmethod
    def derive_subroom_seed(room_seed: int, subroom_index: int) -> int:
        """
        Level 5: Derive subroom seed from room seed.

        Args:
            room_seed: Level 4 room seed
            subroom_index: Subroom index within room (0-based)

        Returns:
            Subroom seed
        """
        return SeedDerivation.derive_seed(room_seed, f"subroom:{subroom_index}")

    @staticmethod
    def derive_feature_seed(subroom_seed: int, feature_type: str) -> int:
        """
        Level 6: Derive feature seed from subroom seed.

        Args:
            subroom_seed: Level 5 subroom seed
            feature_type: Feature type (e.g., "hazards", "pickups", "enemies", "loot", "decor")

        Returns:
            Feature seed
        """
        return SeedDerivation.derive_seed(subroom_seed, f"feature:{feature_type}")


@dataclass
class SeedContext:
    """
    Tracks position in seed hierarchy.

    Provides convenient access to all seed levels and automatic
    child seed derivation.
    """

    world_seed: int
    region_id: str | None = None
    mission_id: str | None = None
    room_coords: tuple[int, int] | None = None
    subroom_index: int | None = None

    def get_region_seed(self) -> int | None:
        """Get Level 2 region seed (if region_id set)"""
        if self.region_id is None:
            return None
        return SeedDerivation.derive_region_seed(self.world_seed, self.region_id)

    def get_mission_seed(self) -> int | None:
        """Get Level 3 mission seed (if region_id and mission_id set)"""
        region_seed = self.get_region_seed()
        if region_seed is None or self.mission_id is None:
            return None
        return SeedDerivation.derive_mission_seed(region_seed, self.mission_id)

    def get_room_seed(self) -> int | None:
        """Get Level 4 room seed (if mission_seed and room_coords set)"""
        mission_seed = self.get_mission_seed()
        if mission_seed is None or self.room_coords is None:
            return None
        grid_x, grid_y = self.room_coords
        return SeedDerivation.derive_room_seed_from_coords(mission_seed, grid_x, grid_y)

    def get_subroom_seed(self) -> int | None:
        """Get Level 5 subroom seed (if room_seed and subroom_index set)"""
        room_seed = self.get_room_seed()
        if room_seed is None or self.subroom_index is None:
            return None
        return SeedDerivation.derive_subroom_seed(room_seed, self.subroom_index)

    def get_feature_seed(self, feature_type: str) -> int | None:
        """
        Get Level 6 feature seed.

        Args:
            feature_type: Type of feature to generate seed for

        Returns:
            Feature seed if context is complete enough, otherwise None
        """
        # Try subroom-level features first
        subroom_seed = self.get_subroom_seed()
        if subroom_seed is not None:
            return SeedDerivation.derive_feature_seed(subroom_seed, feature_type)

        # Fall back to room-level features
        room_seed = self.get_room_seed()
        if room_seed is not None:
            return SeedDerivation.derive_feature_seed(room_seed, feature_type)

        # Fall back to mission-level features
        mission_seed = self.get_mission_seed()
        if mission_seed is not None:
            return SeedDerivation.derive_seed(mission_seed, f"feature:{feature_type}")

        return None

    def with_region(self, region_id: str) -> "SeedContext":
        """Create new context with region set"""
        return SeedContext(
            world_seed=self.world_seed,
            region_id=region_id,
            mission_id=self.mission_id,
            room_coords=self.room_coords,
            subroom_index=self.subroom_index,
        )

    def with_mission(self, mission_id: str) -> "SeedContext":
        """Create new context with mission set"""
        return SeedContext(
            world_seed=self.world_seed,
            region_id=self.region_id,
            mission_id=mission_id,
            room_coords=self.room_coords,
            subroom_index=self.subroom_index,
        )

    def with_room(self, grid_x: int, grid_y: int) -> "SeedContext":
        """Create new context with room coordinates set"""
        return SeedContext(
            world_seed=self.world_seed,
            region_id=self.region_id,
            mission_id=self.mission_id,
            room_coords=(grid_x, grid_y),
            subroom_index=self.subroom_index,
        )

    def with_subroom(self, subroom_index: int) -> "SeedContext":
        """Create new context with subroom index set"""
        return SeedContext(
            world_seed=self.world_seed,
            region_id=self.region_id,
            mission_id=self.mission_id,
            room_coords=self.room_coords,
            subroom_index=subroom_index,
        )

    def __str__(self) -> str:
        """String representation for debugging"""
        parts = [f"world={self.world_seed}"]
        if self.region_id:
            parts.append(f"region={self.region_id}")
        if self.mission_id:
            parts.append(f"mission={self.mission_id}")
        if self.room_coords:
            parts.append(f"room={self.room_coords}")
        if self.subroom_index is not None:
            parts.append(f"subroom={self.subroom_index}")
        return f"SeedContext({', '.join(parts)})"


class SeedHierarchyValidator:
    """
    Validation utilities for seed hierarchy.

    Ensures determinism and reproducibility.
    """

    @staticmethod
    def validate_determinism(
        world_seed: int, region_id: str, mission_id: str, grid_x: int, grid_y: int
    ) -> bool:
        """
        Test that seed hierarchy is deterministic.

        Args:
            world_seed: Test world seed
            region_id: Test region ID
            mission_id: Test mission ID
            grid_x: Test room X coordinate
            grid_y: Test room Y coordinate

        Returns:
            True if deterministic (same seeds on multiple calls)
        """
        # Generate seeds twice
        ctx1 = SeedContext(world_seed=world_seed)
        ctx1 = ctx1.with_region(region_id).with_mission(mission_id).with_room(grid_x, grid_y)

        ctx2 = SeedContext(world_seed=world_seed)
        ctx2 = ctx2.with_region(region_id).with_mission(mission_id).with_room(grid_x, grid_y)

        # Compare all levels
        checks = [
            ctx1.get_region_seed() == ctx2.get_region_seed(),
            ctx1.get_mission_seed() == ctx2.get_mission_seed(),
            ctx1.get_room_seed() == ctx2.get_room_seed(),
            ctx1.get_feature_seed("hazards") == ctx2.get_feature_seed("hazards"),
            ctx1.get_feature_seed("pickups") == ctx2.get_feature_seed("pickups"),
        ]

        return all(checks)

    @staticmethod
    def validate_uniqueness(world_seed: int, region_ids: list, mission_ids: list) -> bool:
        """
        Test that different identifiers produce different seeds.

        Args:
            world_seed: Test world seed
            region_ids: List of region IDs to test
            mission_ids: List of mission IDs to test

        Returns:
            True if all seeds are unique
        """
        seeds = set()

        for region_id in region_ids:
            region_seed = SeedDerivation.derive_region_seed(world_seed, region_id)
            if region_seed in seeds:
                return False
            seeds.add(region_seed)

            for mission_id in mission_ids:
                mission_seed = SeedDerivation.derive_mission_seed(region_seed, mission_id)
                if mission_seed in seeds:
                    return False
                seeds.add(mission_seed)

        return True


# Convenience function for backward compatibility with existing arcade mode
def get_arcade_world_seed(base_seed: int, level_number: int) -> int:
    """
    Generate world seed for arcade mode.

    Maintains backward compatibility with existing arcade mode where
    world seed increments for each level.

    Args:
        base_seed: User-provided base seed
        level_number: Current level number (0-based)

    Returns:
        World seed for this level
    """
    if level_number == 0:
        return base_seed
    return SeedDerivation.derive_seed(base_seed, f"arcade_level:{level_number}")
