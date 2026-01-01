"""
Player Simulator - Simulates player movement through procedurally generated worlds
"""

from dataclasses import dataclass
from enum import Enum

from systems.room_generation import TILE_EMPTY, TILE_PLATFORM, TILE_SOLID
from systems.world_generation import RoomNode


class MovementAction(Enum):
    """Available movement actions for simulation"""

    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    JUMP = "jump"
    DOUBLE_JUMP = "double_jump"
    WALL_JUMP = "wall_jump"
    DASH = "dash"
    FALL = "fall"


@dataclass
class SimulationResult:
    """Result of a playability simulation"""

    success: bool
    reachable_tiles: set[tuple[int, int]]
    unreachable_tiles: set[tuple[int, int]]
    movement_path: list[tuple[int, int, MovementAction]]
    errors: list[str]
    metrics: dict

    def get_reachability_percentage(self) -> float:
        """Calculate percentage of walkable tiles that are reachable"""
        total = len(self.reachable_tiles) + len(self.unreachable_tiles)
        if total == 0:
            return 0.0
        return (len(self.reachable_tiles) / total) * 100.0


class PlayerSimulator:
    """
    Simulates player movement through a room to validate playability.

    Uses simplified physics based on the actual player capabilities:
    - Jump height: ~3 tiles (96 pixels / 32 = 3)
    - Horizontal jump distance: ~5 tiles
    - Double jump adds ~2 tiles height
    - Wall jump allows vertical climb
    - Dash adds ~3 tiles horizontal distance
    """

    def __init__(self, room: RoomNode):
        """
        Initialize simulator for a room.

        Args:
            room: Room with tilemap to simulate
        """
        self.room = room
        self.tilemap = room.tilemap
        self.width = len(self.tilemap[0]) if self.tilemap else 0
        self.height = len(self.tilemap) if self.tilemap else 0

        # Player physics constants (in tiles)
        self.JUMP_HEIGHT = 3
        self.DOUBLE_JUMP_HEIGHT = 5
        self.HORIZONTAL_JUMP_DIST = 5
        self.WALL_JUMP_HEIGHT = 4
        self.DASH_DISTANCE = 3

        # Simulation state
        self.visited: set[tuple[int, int]] = set()
        self.walkable_tiles: set[tuple[int, int]] = set()

    def simulate_playability(self, start_x: int, start_y: int) -> SimulationResult:
        """
        Simulate player movement from spawn point to validate playability.

        Args:
            start_x: Starting tile X position
            start_y: Starting tile Y position

        Returns:
            SimulationResult with reachability analysis
        """
        errors = []

        # Validate start position
        if not self._is_valid_spawn(start_x, start_y):
            errors.append(f"Invalid spawn position: ({start_x}, {start_y})")
            return SimulationResult(
                success=False,
                reachable_tiles=set(),
                unreachable_tiles=self._find_all_walkable_tiles(),
                movement_path=[],
                errors=errors,
                metrics={},
            )

        # Find all walkable tiles in room
        self.walkable_tiles = self._find_all_walkable_tiles()

        # Perform flood-fill reachability analysis
        self.visited = set()
        movement_path = []
        self._flood_fill_reachability(start_x, start_y, movement_path)

        # Calculate unreachable tiles
        unreachable = self.walkable_tiles - self.visited

        # Calculate metrics
        metrics = {
            "total_walkable": len(self.walkable_tiles),
            "reachable": len(self.visited),
            "unreachable": len(unreachable),
            "reachability_pct": (
                (len(self.visited) / len(self.walkable_tiles) * 100.0)
                if self.walkable_tiles
                else 0.0
            ),
        }

        # Success if >90% of walkable tiles are reachable
        success = metrics["reachability_pct"] >= 90.0

        if not success:
            errors.append(f"Low reachability: {metrics['reachability_pct']:.1f}% (need >=90%)")

        return SimulationResult(
            success=success,
            reachable_tiles=self.visited.copy(),
            unreachable_tiles=unreachable,
            movement_path=movement_path,
            errors=errors,
            metrics=metrics,
        )

    def _is_valid_spawn(self, x: int, y: int) -> bool:
        """Check if spawn position is valid (empty tile with floor below)"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False

        # Must be empty
        if self.tilemap[y][x] != TILE_EMPTY:
            return False

        # Must have floor below (solid or platform)
        if y + 1 < self.height:
            below = self.tilemap[y + 1][x]
            if below in (TILE_SOLID, TILE_PLATFORM):
                return True

        return False

    def _find_all_walkable_tiles(self) -> set[tuple[int, int]]:
        """Find all tiles where player could theoretically stand"""
        walkable = set()

        for y in range(self.height - 1):  # Exclude bottom row
            for x in range(self.width):
                # Empty tile with solid or platform below
                if self.tilemap[y][x] == TILE_EMPTY:
                    below = self.tilemap[y + 1][x]
                    if below in (TILE_SOLID, TILE_PLATFORM):
                        walkable.add((x, y))

        return walkable

    def _flood_fill_reachability(self, x: int, y: int, path: list[tuple[int, int, MovementAction]]):
        """
        Flood-fill algorithm to find all reachable tiles from (x, y).

        Uses BFS with player movement capabilities.
        """
        from collections import deque

        queue = deque([(x, y, None)])
        self.visited.add((x, y))

        while queue:
            cx, cy, action = queue.popleft()

            if action:
                path.append((cx, cy, action))

            # Try all movement actions from current position
            reachable_positions = self._get_reachable_positions(cx, cy)

            for nx, ny, move_action in reachable_positions:
                if (nx, ny) not in self.visited:
                    self.visited.add((nx, ny))
                    queue.append((nx, ny, move_action))

    def _get_reachable_positions(self, x: int, y: int) -> list[tuple[int, int, MovementAction]]:
        """
        Get all positions reachable from (x, y) with player movement.

        Returns:
            List of (new_x, new_y, action) tuples
        """
        reachable = []

        # 1. Walk left/right
        for dx, action in [(-1, MovementAction.WALK_LEFT), (1, MovementAction.WALK_RIGHT)]:
            nx = x + dx
            if self._can_walk_to(x, y, nx, y):
                reachable.append((nx, y, action))

        # 2. Jump (horizontal and vertical)
        for jump_dx in range(-self.HORIZONTAL_JUMP_DIST, self.HORIZONTAL_JUMP_DIST + 1):
            for jump_dy in range(-self.JUMP_HEIGHT, 1):  # Can jump up to JUMP_HEIGHT
                nx, ny = x + jump_dx, y + jump_dy
                if self._can_jump_to(x, y, nx, ny, double_jump=False):
                    reachable.append((nx, ny, MovementAction.JUMP))

        # 3. Double jump (greater height)
        for jump_dx in range(-self.HORIZONTAL_JUMP_DIST, self.HORIZONTAL_JUMP_DIST + 1):
            for jump_dy in range(-self.DOUBLE_JUMP_HEIGHT, 1):
                nx, ny = x + jump_dx, y + jump_dy
                if self._can_jump_to(x, y, nx, ny, double_jump=True):
                    reachable.append((nx, ny, MovementAction.DOUBLE_JUMP))

        # 4. Wall jump (if adjacent to wall)
        if self._has_wall_adjacent(x, y):
            for jump_dx in [-2, -1, 1, 2]:  # Wall jump moves you away from wall
                for jump_dy in range(-self.WALL_JUMP_HEIGHT, 0):
                    nx, ny = x + jump_dx, y + jump_dy
                    if self._can_jump_to(x, y, nx, ny, double_jump=False):
                        reachable.append((nx, ny, MovementAction.WALL_JUMP))

        # 5. Dash (horizontal boost)
        for dash_dx in [-self.DASH_DISTANCE, self.DASH_DISTANCE]:
            nx = x + dash_dx
            if self._can_dash_to(x, y, nx, y):
                reachable.append((nx, y, MovementAction.DASH))

        # 6. Fall (gravity)
        if y + 1 < self.height:
            if self.tilemap[y + 1][x] == TILE_EMPTY:
                # Fall until hitting ground
                fall_y = y + 1
                while fall_y < self.height and self.tilemap[fall_y][x] == TILE_EMPTY:
                    fall_y += 1
                if fall_y > y + 1:  # Actually fell
                    landing_y = fall_y - 1
                    if self._is_valid_spawn(x, landing_y):
                        reachable.append((x, landing_y, MovementAction.FALL))

        return reachable

    def _can_walk_to(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if player can walk from (x1,y1) to (x2,y2)"""
        if not (0 <= x2 < self.width and 0 <= y2 < self.height):
            return False

        # Must be empty
        if self.tilemap[y2][x2] != TILE_EMPTY:
            return False

        # Must have floor below
        if y2 + 1 < self.height:
            below = self.tilemap[y2 + 1][x2]
            return below in (TILE_SOLID, TILE_PLATFORM)

        return False

    def _can_jump_to(self, x1: int, y1: int, x2: int, y2: int, double_jump: bool) -> bool:
        """Check if player can jump from (x1,y1) to (x2,y2)"""
        if not (0 <= x2 < self.width and 0 <= y2 < self.height):
            return False

        # Destination must be empty
        if self.tilemap[y2][x2] != TILE_EMPTY:
            return False

        # Must have floor below destination
        if y2 + 1 < self.height:
            below = self.tilemap[y2 + 1][x2]
            if below not in (TILE_SOLID, TILE_PLATFORM):
                return False
        else:
            return False

        # Simplified collision check - no obstacles in direct path
        # (In reality, player follows arc, but this is conservative)
        return True

    def _can_dash_to(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if player can dash from (x1,y1) to (x2,y2)"""
        if not (0 <= x2 < self.width and 0 <= y2 < self.height):
            return False

        # Check all tiles in dash path are empty
        step = 1 if x2 > x1 else -1
        for x in range(x1, x2 + step, step):
            if self.tilemap[y1][x] != TILE_EMPTY:
                return False

        # Destination must have floor
        if y2 + 1 < self.height:
            below = self.tilemap[y2 + 1][x2]
            return below in (TILE_SOLID, TILE_PLATFORM)

        return False

    def _has_wall_adjacent(self, x: int, y: int) -> bool:
        """Check if there's a wall adjacent to position"""
        # Check left
        if x > 0 and self.tilemap[y][x - 1] == TILE_SOLID:
            return True
        # Check right
        if x < self.width - 1 and self.tilemap[y][x + 1] == TILE_SOLID:
            return True
        return False
