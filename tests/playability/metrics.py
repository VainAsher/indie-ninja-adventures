"""
Playability Metrics - Collect and analyze playability statistics
"""

from dataclasses import dataclass, field
from typing import Any

from systems.world_generation import RoomNode, World


@dataclass
class RoomMetrics:
    """Metrics for a single room"""

    room_type: str
    biome_theme: str

    # Reachability
    total_walkable_tiles: int = 0
    reachable_tiles: int = 0
    unreachable_tiles: int = 0
    reachability_pct: float = 0.0

    # Density
    obstacle_density: float = 0.0
    platform_density: float = 0.0

    # Complexity
    num_platforms: int = 0
    num_gaps: int = 0
    num_doors: int = 0

    # Validation results
    validators_passed: list[str] = field(default_factory=list)
    validators_failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_playable(self) -> bool:
        """Room is playable if no validators failed"""
        return len(self.validators_failed) == 0


@dataclass
class WorldMetrics:
    """Metrics for entire world"""

    seed: int
    num_rooms: int
    num_biomes: int

    room_metrics: list[RoomMetrics] = field(default_factory=list)

    @property
    def playable_rooms(self) -> int:
        """Count of playable rooms"""
        return sum(1 for rm in self.room_metrics if rm.is_playable)

    @property
    def world_playability_pct(self) -> float:
        """Percentage of rooms that are playable"""
        if not self.room_metrics:
            return 0.0
        return (self.playable_rooms / len(self.room_metrics)) * 100.0

    @property
    def avg_reachability_pct(self) -> float:
        """Average reachability across all rooms"""
        if not self.room_metrics:
            return 0.0
        return sum(rm.reachability_pct for rm in self.room_metrics) / len(self.room_metrics)

    @property
    def avg_obstacle_density(self) -> float:
        """Average obstacle density across all rooms"""
        if not self.room_metrics:
            return 0.0
        return sum(rm.obstacle_density for rm in self.room_metrics) / len(self.room_metrics)

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics"""
        return {
            "seed": self.seed,
            "total_rooms": self.num_rooms,
            "playable_rooms": self.playable_rooms,
            "world_playability": f"{self.world_playability_pct:.1f}%",
            "avg_reachability": f"{self.avg_reachability_pct:.1f}%",
            "avg_obstacle_density": f"{self.avg_obstacle_density * 100:.1f}%",
            "total_warnings": sum(len(rm.warnings) for rm in self.room_metrics),
        }

    def get_failed_rooms(self) -> list[RoomMetrics]:
        """Get list of rooms that failed validation"""
        return [rm for rm in self.room_metrics if not rm.is_playable]


class PlayabilityMetrics:
    """
    Collects and analyzes playability metrics for rooms and worlds.
    """

    @staticmethod
    def analyze_room(room: RoomNode, validation_results: list[dict[str, Any]]) -> RoomMetrics:
        """
        Analyze a single room and collect metrics.

        Args:
            room: Room to analyze
            validation_results: Results from validators

        Returns:
            RoomMetrics with collected data
        """
        metrics = RoomMetrics(
            room_type=room.room_type.value if room.room_type else "unknown",
            biome_theme="unknown",  # Will be set by world analysis
        )

        # Process validation results
        for result in validation_results:
            if result["passed"]:
                metrics.validators_passed.append(result["validator"])
            else:
                metrics.validators_failed.append(result["validator"])

            metrics.warnings.extend(result.get("warnings", []))

        # Calculate densities
        tilemap = room.tilemap
        if tilemap:
            height = len(tilemap)
            width = len(tilemap[0]) if height > 0 else 0

            if width > 2 and height > 2:
                from systems.room_generation import TILE_PLATFORM, TILE_SOLID

                playable_area = (width - 2) * (height - 2)
                obstacle_count = 0
                platform_count = 0

                for y in range(1, height - 1):
                    for x in range(1, width - 1):
                        if tilemap[y][x] == TILE_SOLID:
                            obstacle_count += 1
                        elif tilemap[y][x] == TILE_PLATFORM:
                            platform_count += 1

                metrics.obstacle_density = obstacle_count / playable_area
                metrics.platform_density = platform_count / playable_area
                metrics.num_platforms = platform_count

        # Count doors
        if room.door_ports:
            metrics.num_doors = sum(len(ports) for ports in room.door_ports.values())

        return metrics

    @staticmethod
    def analyze_world(world: World, room_metrics: list[RoomMetrics]) -> WorldMetrics:
        """
        Analyze entire world.

        Args:
            world: World to analyze
            room_metrics: Metrics for each room

        Returns:
            WorldMetrics with aggregated data
        """
        metrics = WorldMetrics(
            seed=world.seed,
            num_rooms=len(world.all_rooms),
            num_biomes=len(world.biomes),
            room_metrics=room_metrics,
        )

        # Add biome theme to room metrics
        for biome in world.biomes:
            for room in biome.rooms:
                # Find corresponding room metric
                room_idx = world.all_rooms.index(room)
                if room_idx < len(room_metrics):
                    room_metrics[room_idx].biome_theme = biome.theme.value

        return metrics
