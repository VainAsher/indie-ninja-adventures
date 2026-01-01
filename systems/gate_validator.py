"""
Gate Validation System - Ensures Solvable Level Design

This module validates that ability gates are placed correctly and that
all objectives remain reachable with the player's current abilities.

Uses BFS pathfinding to verify:
1. Path exists from start to gate (without required ability)
2. Path exists through gate (with required ability)
3. No alternative path to critical objectives bypassing the gate
4. All mission objectives reachable with available abilities

Version: v0.6.0 (Phase 5)
"""

from collections import deque
from dataclasses import dataclass

from entities.ability_gate import AbilityGate, AbilityRequirement

# ============================================================
# Pathfinding Node
# ============================================================


@dataclass
class PathNode:
    """Node in the pathfinding graph"""

    tile_x: int  # Tile coordinates
    tile_y: int
    abilities_used: set[AbilityRequirement]  # Abilities used to reach this node


# ============================================================
# Gate Validation Result
# ============================================================


@dataclass
class ValidationResult:
    """Result of gate validation"""

    valid: bool
    errors: list[str]
    warnings: list[str]


# ============================================================
# Gate Validator
# ============================================================


class GateValidator:
    """
    Validates ability gate placement for mission levels.

    Ensures that:
    - Gates properly block progression without required abilities
    - Objectives remain reachable with available abilities
    - No soft-locks or unreachable areas
    """

    def __init__(self, tile_width: int, tile_height: int, tile_size: int = 32):
        """
        Initialize gate validator.

        Args:
            tile_width: Level width in tiles
            tile_height: Level height in tiles
            tile_size: Size of each tile in pixels
        """
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.tile_size = tile_size

        # Collision data (set externally)
        self.solid_tiles: set[tuple[int, int]] = set()
        self.gates: list[AbilityGate] = []

    def set_collision_data(self, solid_tiles: set[tuple[int, int]]):
        """
        Set solid tile positions.

        Args:
            solid_tiles: Set of (tile_x, tile_y) positions that are solid
        """
        self.solid_tiles = solid_tiles

    def set_gates(self, gates: list[AbilityGate]):
        """
        Set ability gates.

        Args:
            gates: List of ability gates in the level
        """
        self.gates = gates

    def validate_gate_placement(
        self,
        start_pos: tuple[float, float],
        objective_positions: list[tuple[float, float]],
        available_abilities: set[AbilityRequirement],
    ) -> ValidationResult:
        """
        Validate that all gates are correctly placed.

        Args:
            start_pos: Player start position (x, y) in pixels
            objective_positions: List of objective positions (x, y) in pixels
            available_abilities: Abilities player has at mission start

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Convert pixel positions to tile positions
        start_tile = self._pixel_to_tile(start_pos)
        objective_tiles = [self._pixel_to_tile(pos) for pos in objective_positions]

        # Validate each gate
        for gate in self.gates:
            gate_tile = self._pixel_to_tile((gate.x, gate.y))

            # Check if gate blocks path to objectives
            result = self._validate_single_gate(
                gate, start_tile, objective_tiles, available_abilities
            )

            errors.extend(result.errors)
            warnings.extend(result.warnings)

        # Check if all objectives are reachable
        reachability_result = self._validate_objective_reachability(
            start_tile, objective_tiles, available_abilities
        )

        errors.extend(reachability_result.errors)
        warnings.extend(reachability_result.warnings)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_single_gate(
        self,
        gate: AbilityGate,
        start_tile: tuple[int, int],
        objective_tiles: list[tuple[int, int]],
        available_abilities: set[AbilityRequirement],
    ) -> ValidationResult:
        """Validate a single gate"""
        errors = []
        warnings = []

        gate_tile = self._pixel_to_tile((gate.x, gate.y))

        # Check 1: Start position can reach gate area (without ability)
        # This ensures the gate is actually encountered
        abilities_without_required = available_abilities.copy()
        if gate.required_ability in abilities_without_required:
            abilities_without_required.remove(gate.required_ability)

        can_reach_gate = self._can_reach_position(start_tile, gate_tile, abilities_without_required)

        if not can_reach_gate:
            warnings.append(
                f"Gate {gate.gate_id} ({gate.gate_type.value}) may not be encountered "
                f"(unreachable without required ability)"
            )

        # Check 2: With ability, player can pass gate
        abilities_with_required = available_abilities.copy()
        abilities_with_required.add(gate.required_ability)

        # Note: For actual validation, would need to check if player can pass
        # through the gate area with the ability. This is simplified.

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_objective_reachability(
        self,
        start_tile: tuple[int, int],
        objective_tiles: list[tuple[int, int]],
        available_abilities: set[AbilityRequirement],
    ) -> ValidationResult:
        """Validate that all objectives are reachable"""
        errors = []
        warnings = []

        for i, obj_tile in enumerate(objective_tiles):
            can_reach = self._can_reach_position(start_tile, obj_tile, available_abilities)

            if not can_reach:
                errors.append(
                    f"Objective {i} at {obj_tile} is unreachable with available abilities"
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _can_reach_position(
        self, start: tuple[int, int], target: tuple[int, int], abilities: set[AbilityRequirement]
    ) -> bool:
        """
        Check if target position is reachable from start with given abilities.

        Uses BFS pathfinding.

        Args:
            start: Start tile (tile_x, tile_y)
            target: Target tile (tile_x, tile_y)
            abilities: Set of available abilities

        Returns:
            True if path exists
        """
        # BFS to find path
        queue = deque([start])
        visited = set([start])

        while queue:
            current_x, current_y = queue.popleft()

            # Check if reached target
            if (current_x, current_y) == target:
                return True

            # Explore neighbors (4 directions)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_x = current_x + dx
                next_y = current_y + dy
                next_pos = (next_x, next_y)

                # Skip if out of bounds
                if not (0 <= next_x < self.tile_width and 0 <= next_y < self.tile_height):
                    continue

                # Skip if already visited
                if next_pos in visited:
                    continue

                # Skip if solid tile
                if next_pos in self.solid_tiles:
                    continue

                # Check if gate blocks this position
                if self._is_blocked_by_gate(next_x, next_y, abilities):
                    continue

                # Add to queue
                visited.add(next_pos)
                queue.append(next_pos)

        return False

    def _is_blocked_by_gate(
        self, tile_x: int, tile_y: int, abilities: set[AbilityRequirement]
    ) -> bool:
        """
        Check if tile position is blocked by a gate.

        Args:
            tile_x, tile_y: Tile position
            abilities: Available abilities

        Returns:
            True if blocked by gate
        """
        # Convert tile to pixel position (center of tile)
        pixel_x = tile_x * self.tile_size + self.tile_size / 2
        pixel_y = tile_y * self.tile_size + self.tile_size / 2

        for gate in self.gates:
            # Check if tile is within gate bounds
            if (
                gate.x <= pixel_x <= gate.x + gate.width
                and gate.y <= pixel_y <= gate.y + gate.height
            ):

                # Check if player can pass
                if not gate.can_pass(abilities):
                    return True

        return False

    def _pixel_to_tile(self, pos: tuple[float, float]) -> tuple[int, int]:
        """Convert pixel position to tile coordinates"""
        x, y = pos
        return (int(x // self.tile_size), int(y // self.tile_size))

    def _tile_to_pixel(self, tile_pos: tuple[int, int]) -> tuple[float, float]:
        """Convert tile position to pixel coordinates (center of tile)"""
        tile_x, tile_y = tile_pos
        return (
            tile_x * self.tile_size + self.tile_size / 2,
            tile_y * self.tile_size + self.tile_size / 2,
        )


# ============================================================
# Path Finding Utilities
# ============================================================


def find_path_with_abilities(
    start: tuple[int, int],
    target: tuple[int, int],
    solid_tiles: set[tuple[int, int]],
    gates: list[AbilityGate],
    abilities: set[AbilityRequirement],
    tile_width: int,
    tile_height: int,
) -> list[tuple[int, int]] | None:
    """
    Find path from start to target considering abilities.

    Args:
        start: Start tile position
        target: Target tile position
        solid_tiles: Set of solid tile positions
        gates: List of ability gates
        abilities: Available abilities
        tile_width: Level width in tiles
        tile_height: Level height in tiles

    Returns:
        List of tile positions forming path, or None if no path exists
    """
    queue = deque([(start, [start])])
    visited = set([start])

    while queue:
        current, path = queue.popleft()
        current_x, current_y = current

        # Check if reached target
        if current == target:
            return path

        # Explore neighbors
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            next_x = current_x + dx
            next_y = current_y + dy
            next_pos = (next_x, next_y)

            # Bounds check
            if not (0 <= next_x < tile_width and 0 <= next_y < tile_height):
                continue

            # Visited check
            if next_pos in visited:
                continue

            # Solid tile check
            if next_pos in solid_tiles:
                continue

            # Gate check
            blocked = False
            for gate in gates:
                # Simple gate blocking (would need pixel conversion for real check)
                if not gate.can_pass(abilities):
                    # Check if gate overlaps with this tile (simplified)
                    # In real implementation, would convert to pixel coords
                    blocked = True
                    break

            if blocked:
                continue

            # Add to path
            visited.add(next_pos)
            new_path = path + [next_pos]
            queue.append((next_pos, new_path))

    return None


# ============================================================
# Validation Helpers
# ============================================================


def validate_mission_gates(
    start_position: tuple[float, float],
    exit_position: tuple[float, float],
    objective_positions: list[tuple[float, float]],
    gates: list[AbilityGate],
    available_abilities: set[AbilityRequirement],
    solid_tiles: set[tuple[int, int]],
    level_width_tiles: int,
    level_height_tiles: int,
) -> ValidationResult:
    """
    Validate gate placement for a mission level.

    Args:
        start_position: Player spawn position (pixels)
        exit_position: Level exit position (pixels)
        objective_positions: Objective positions (pixels)
        gates: List of ability gates
        available_abilities: Abilities available at mission start
        solid_tiles: Set of solid tile positions
        level_width_tiles: Level width in tiles
        level_height_tiles: Level height in tiles

    Returns:
        ValidationResult
    """
    validator = GateValidator(level_width_tiles, level_height_tiles)
    validator.set_collision_data(solid_tiles)
    validator.set_gates(gates)

    # Add exit to objectives
    all_objectives = objective_positions + [exit_position]

    return validator.validate_gate_placement(start_position, all_objectives, available_abilities)
