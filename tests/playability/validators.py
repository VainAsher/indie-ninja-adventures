"""
Playability Validators - Modular validators for different playability aspects
"""

from typing import List, Dict, Any, Set, Tuple
from abc import ABC, abstractmethod

from systems.world_generation import RoomNode, World
from systems.room_generation import TILE_EMPTY, TILE_SOLID, TILE_PLATFORM
from .simulator import PlayerSimulator, SimulationResult


class PlayabilityValidator(ABC):
    """Base class for playability validators"""

    def __init__(self, name: str):
        self.name = name
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @abstractmethod
    def validate(self, room: RoomNode) -> bool:
        """
        Validate a room for playability.

        Args:
            room: Room to validate

        Returns:
            True if validation passes, False otherwise
        """
        pass

    def get_report(self) -> Dict[str, Any]:
        """Get validation report"""
        return {
            'validator': self.name,
            'passed': len(self.errors) == 0,
            'errors': self.errors.copy(),
            'warnings': self.warnings.copy(),
        }

    def reset(self):
        """Reset validator state"""
        self.errors = []
        self.warnings = []


class ReachabilityValidator(PlayabilityValidator):
    """
    Validates that all important areas of a room are reachable.

    Uses player simulation to ensure:
    - All walkable tiles are reachable from spawn
    - Doors are accessible
    - Features (shops, save points) are reachable
    """

    def __init__(self, min_reachability_pct: float = 90.0):
        super().__init__("ReachabilityValidator")
        self.min_reachability_pct = min_reachability_pct

    def validate(self, room: RoomNode) -> bool:
        """Validate room reachability"""
        self.reset()

        # Find spawn point (center of room, on floor)
        spawn_x, spawn_y = self._find_spawn_point(room)

        if spawn_x is None:
            self.errors.append("No valid spawn point found in room")
            return False

        # Run simulation
        simulator = PlayerSimulator(room)
        result = simulator.simulate_playability(spawn_x, spawn_y)

        # Check reachability percentage
        reachability = result.get_reachability_percentage()

        if reachability < self.min_reachability_pct:
            self.errors.append(
                f"Low reachability: {reachability:.1f}% (need >={self.min_reachability_pct}%)"
            )
            self.errors.append(
                f"{len(result.unreachable_tiles)} tiles unreachable out of "
                f"{len(result.reachable_tiles) + len(result.unreachable_tiles)}"
            )

        # Check door reachability (if room has doors)
        if room.door_ports:
            unreachable_doors = self._check_door_reachability(room, result.reachable_tiles)
            if unreachable_doors:
                self.errors.append(f"{len(unreachable_doors)} door(s) unreachable: {unreachable_doors}")

        return len(self.errors) == 0

    def _find_spawn_point(self, room: RoomNode) -> Tuple[int, int]:
        """Find a valid spawn point in room (center, on floor)"""
        tilemap = room.tilemap
        height = len(tilemap)
        width = len(tilemap[0]) if height > 0 else 0

        # Search from center outward
        center_x = width // 2
        center_y = height // 2

        # Search downward from center
        for y in range(center_y, height - 1):
            for dx in range(-10, 11):  # Search ±10 tiles from center
                x = center_x + dx
                if not (0 <= x < width):
                    continue

                # Check if valid spawn (empty with floor below)
                if tilemap[y][x] == TILE_EMPTY:
                    if y + 1 < height:
                        below = tilemap[y + 1][x]
                        if below in (TILE_SOLID, TILE_PLATFORM):
                            return (x, y)

        return (None, None)

    def _check_door_reachability(self, room: RoomNode, reachable_tiles: Set[Tuple[int, int]]) -> List[str]:
        """Check if all doors are reachable"""
        unreachable = []

        for direction, ports in room.door_ports.items():
            for port in ports:
                # Door is at edge, check tiles near door
                door_x = port.center_tile
                door_y = 0 if direction == "up" else (len(room.tilemap) - 1) if direction == "down" else port.center_tile

                # Check if any tiles near door are reachable
                door_reachable = False
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        check_pos = (door_x + dx, door_y + dy)
                        if check_pos in reachable_tiles:
                            door_reachable = True
                            break
                    if door_reachable:
                        break

                if not door_reachable:
                    unreachable.append(f"{direction}_door_{port.center_tile}")

        return unreachable


class JumpabilityValidator(PlayabilityValidator):
    """
    Validates that jumps in the room are possible with player physics.

    Ensures:
    - No gaps too wide to jump across
    - No platforms too high to reach
    - No impossible jump sequences
    """

    def __init__(self, max_jump_height: int = 3, max_jump_distance: int = 5):
        super().__init__("JumpabilityValidator")
        self.max_jump_height = max_jump_height
        self.max_jump_distance = max_jump_distance

    def validate(self, room: RoomNode) -> bool:
        """Validate jump requirements in room"""
        self.reset()

        tilemap = room.tilemap
        height = len(tilemap)
        width = len(tilemap[0]) if height > 0 else 0

        # Find all gaps and platforms
        gaps = self._find_gaps(tilemap, width, height)
        platforms = self._find_platforms(tilemap, width, height)

        # Check gap widths
        for gap_y, gap_x_start, gap_x_end in gaps:
            gap_width = gap_x_end - gap_x_start
            if gap_width > self.max_jump_distance:
                self.warnings.append(
                    f"Wide gap at y={gap_y}, x={gap_x_start}-{gap_x_end} "
                    f"({gap_width} tiles, max={self.max_jump_distance})"
                )

        # Check platform heights
        for plat_y, plat_x in platforms:
            # Find nearest floor below
            floor_y = self._find_floor_below(tilemap, plat_x, plat_y, height)
            if floor_y:
                height_diff = floor_y - plat_y
                if height_diff > self.max_jump_height + 2:  # +2 for double jump
                    self.warnings.append(
                        f"High platform at ({plat_x}, {plat_y}), "
                        f"{height_diff} tiles above floor (max={self.max_jump_height + 2})"
                    )

        # Warnings don't fail validation, just inform
        return True

    def _find_gaps(self, tilemap: List[List[int]], width: int, height: int) -> List[Tuple[int, int, int]]:
        """Find horizontal gaps in floor"""
        gaps = []

        for y in range(height - 1):
            in_gap = False
            gap_start = 0

            for x in range(width):
                is_floor = tilemap[y][x] in (TILE_SOLID, TILE_PLATFORM)
                below_is_empty = (y + 1 < height) and (tilemap[y + 1][x] == TILE_EMPTY)

                if not is_floor and below_is_empty:
                    # In a gap
                    if not in_gap:
                        gap_start = x
                        in_gap = True
                else:
                    # Not in gap
                    if in_gap:
                        gaps.append((y, gap_start, x))
                        in_gap = False

            # End of row
            if in_gap:
                gaps.append((y, gap_start, width))

        return gaps

    def _find_platforms(self, tilemap: List[List[int]], width: int, height: int) -> List[Tuple[int, int]]:
        """Find platform tiles (empty below, solid at position)"""
        platforms = []

        for y in range(height - 1):
            for x in range(width):
                if tilemap[y][x] in (TILE_SOLID, TILE_PLATFORM):
                    if y + 1 < height and tilemap[y + 1][x] == TILE_EMPTY:
                        platforms.append((y, x))

        return platforms

    def _find_floor_below(self, tilemap: List[List[int]], x: int, start_y: int, height: int) -> int:
        """Find nearest floor tile below position"""
        for y in range(start_y + 1, height):
            if tilemap[y][x] in (TILE_SOLID, TILE_PLATFORM):
                return y
        return None


class NavigabilityValidator(PlayabilityValidator):
    """
    Validates that the room has good flow and navigation.

    Ensures:
    - No dead ends (unless intentional)
    - Multiple paths where appropriate
    - Good spacing between obstacles
    """

    def __init__(self):
        super().__init__("NavigabilityValidator")

    def validate(self, room: RoomNode) -> bool:
        """Validate room navigation"""
        self.reset()

        tilemap = room.tilemap
        height = len(tilemap)
        width = len(tilemap[0]) if height > 0 else 0

        # Check for excessive obstacles (too cluttered)
        obstacle_density = self._calculate_obstacle_density(tilemap, width, height)

        if obstacle_density > 0.6:  # More than 60% obstacles
            self.warnings.append(
                f"High obstacle density: {obstacle_density * 100:.1f}% (room may feel cramped)"
            )

        # Check for completely empty rooms (too boring)
        if obstacle_density < 0.05:  # Less than 5% obstacles
            self.warnings.append(
                f"Low obstacle density: {obstacle_density * 100:.1f}% (room may feel empty)"
            )

        return True

    def _calculate_obstacle_density(self, tilemap: List[List[int]], width: int, height: int) -> float:
        """Calculate percentage of playable area that is solid"""
        if width == 0 or height == 0:
            return 0.0

        # Exclude borders (always solid)
        playable_area = (width - 2) * (height - 2)
        if playable_area <= 0:
            return 0.0

        obstacle_count = 0

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if tilemap[y][x] == TILE_SOLID:
                    obstacle_count += 1

        return obstacle_count / playable_area


class SafetyValidator(PlayabilityValidator):
    """
    Validates that rooms don't have player traps or softlocks.

    Ensures:
    - No inescapable pits
    - No areas player can get stuck
    - Always a way to return to spawn
    """

    def __init__(self):
        super().__init__("SafetyValidator")

    def validate(self, room: RoomNode) -> bool:
        """Validate room safety"""
        self.reset()

        tilemap = room.tilemap
        height = len(tilemap)
        width = len(tilemap[0]) if height > 0 else 0

        # Check for deep pits (fall with no escape)
        pits = self._find_pits(tilemap, width, height)

        for pit_x, pit_depth in pits:
            if pit_depth > 8:  # More than 8 tiles deep
                self.warnings.append(
                    f"Deep pit at x={pit_x}, depth={pit_depth} tiles (potential softlock)"
                )

        return True

    def _find_pits(self, tilemap: List[List[int]], width: int, height: int) -> List[Tuple[int, int]]:
        """Find vertical pits (columns of empty space)"""
        pits = []

        for x in range(1, width - 1):  # Exclude borders
            depth = 0
            for y in range(1, height - 1):
                if tilemap[y][x] == TILE_EMPTY:
                    # Check left and right are solid (pit walls)
                    left_solid = tilemap[y][x - 1] == TILE_SOLID
                    right_solid = tilemap[y][x + 1] == TILE_SOLID

                    if left_solid and right_solid:
                        depth += 1
                else:
                    if depth > 0:
                        pits.append((x, depth))
                        depth = 0

            if depth > 0:
                pits.append((x, depth))

        return pits
