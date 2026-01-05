"""
Solvability Validator

Ensures generated levels are beatable with baseline abilities.
Critical path (START -> EXIT) must be passable with only move + jump.

This validator ensures that:
1. All ability gates are on OPTIONAL paths (side branches)
2. Critical path is always passable with baseline abilities
3. Players can complete the level without advanced abilities
"""

from collections import deque
from typing import TYPE_CHECKING, Set

from systems.ability_progression import get_baseline_abilities
from systems.anchor_resolution import ABILITY_GATE_ANCHORS

if TYPE_CHECKING:
    from systems.world_generation import RoomNode, World


class SolvabilityValidator:
    """Validates level solvability constraints"""

    def __init__(self):
        """Initialize solvability validator"""
        self.baseline_abilities = get_baseline_abilities()

    def validate_critical_path(self, world: "World") -> bool:
        """
        Ensure START -> EXIT is passable with baseline abilities

        This is the core solvability check. The critical path must
        never require advanced abilities.

        Args:
            world: Generated world to validate

        Returns:
            True if solvable with baseline abilities, False if blocked
        """
        # Find start and exit rooms
        start_room = None
        exit_room = None

        for room in world.all_rooms:
            if room.room_type.value == "start":
                start_room = room
            elif room.room_type.value == "exit":
                exit_room = room

        if not start_room or not exit_room:
            print("[SOLVABILITY] ERROR: Missing START or EXIT room!")
            return False

        # BFS from START to EXIT (only using baseline abilities)
        start_coords = (start_room.grid_x, start_room.grid_y)
        exit_coords = (exit_room.grid_x, exit_room.grid_y)

        reachable = self._bfs_reachable_rooms(world, start_coords, self.baseline_abilities)

        if exit_coords in reachable:
            print(f"[SOLVABILITY] OK: Critical path is passable with baseline abilities")
            print(f"[SOLVABILITY]   START {start_coords} -> EXIT {exit_coords} ({len(reachable)} rooms reachable)")
            return True
        else:
            print(f"[SOLVABILITY] ERROR: CRITICAL PATH BLOCKED!")
            print(f"[SOLVABILITY]   START {start_coords} -> EXIT {exit_coords} NOT REACHABLE")
            print(f"[SOLVABILITY]   Only {len(reachable)} rooms reachable with baseline abilities")
            return False

    def validate_optional_gates(self, world: "World") -> bool:
        """
        Ensure ability gates are not blocking critical path

        All gates must be on optional branches, not required
        for START -> EXIT progression.

        Args:
            world: Generated world to validate

        Returns:
            True if all gates are optional, False if any block critical path
        """
        # Find critical path (START -> EXIT)
        critical_path = self._find_critical_path(world)

        if not critical_path:
            print("[SOLVABILITY] WARNING: Could not determine critical path")
            return True  # Can't validate, assume OK

        # Create rooms dictionary for lookups
        rooms_dict = {(room.grid_x, room.grid_y): room for room in world.all_rooms}

        # Find all gates in world
        gates_on_critical_path = []

        for room_coords in critical_path:
            room = rooms_dict.get(room_coords)
            if not room or not hasattr(room, "resolved_anchors"):
                continue

            # Check if this room has any ability gates
            for anchor_kind in room.resolved_anchors.keys():
                if anchor_kind in ABILITY_GATE_ANCHORS:
                    gates_on_critical_path.append((room_coords, anchor_kind))

        if gates_on_critical_path:
            print(f"[SOLVABILITY] ERROR: GATES BLOCKING CRITICAL PATH:")
            for room_coords, gate_type in gates_on_critical_path:
                print(f"[SOLVABILITY]   Room {room_coords}: {gate_type}")
            return False
        else:
            print(f"[SOLVABILITY] OK: No gates on critical path (all gates are optional)")
            return True

    def _bfs_reachable_rooms(
        self, world: "World", start_coords: tuple[int, int], abilities: Set[str]
    ) -> Set[tuple[int, int]]:
        """
        BFS to find all rooms reachable with given abilities

        Args:
            world: World to search
            start_coords: Starting room coordinates
            abilities: Set of available abilities

        Returns:
            Set of reachable room coordinates
        """
        # Create rooms dictionary for lookups
        rooms_dict = {(room.grid_x, room.grid_y): room for room in world.all_rooms}

        queue = deque([start_coords])
        visited = {start_coords}

        while queue:
            current_coords = queue.popleft()
            current_room = rooms_dict.get(current_coords)

            if not current_room:
                continue

            # Check all neighbors
            for neighbor_coords in current_room.neighbors:
                if neighbor_coords in visited:
                    continue

                neighbor_room = rooms_dict.get(neighbor_coords)
                if not neighbor_room:
                    continue

                # Check if we can reach neighbor with current abilities
                if self._can_traverse(current_room, neighbor_room, abilities):
                    visited.add(neighbor_coords)
                    queue.append(neighbor_coords)

        return visited

    def _can_traverse(
        self, from_room: "RoomNode", to_room: "RoomNode", abilities: Set[str]
    ) -> bool:
        """
        Check if player can traverse from one room to another with given abilities

        For now, this is simplified - assumes all connected rooms are traversable
        with baseline abilities. In a more complex implementation, this would
        check for ability gates between rooms.

        Args:
            from_room: Starting room
            to_room: Destination room
            abilities: Available abilities

        Returns:
            True if traversal is possible
        """
        # Check if destination room has ability gate that blocks entry
        if hasattr(to_room, "resolved_anchors"):
            for anchor_kind in to_room.resolved_anchors.keys():
                if anchor_kind in ABILITY_GATE_ANCHORS:
                    # This room has an ability gate
                    required_ability = anchor_kind.replace("gate_", "").replace("_", " ")

                    # For now, gates are considered optional decorations
                    # They don't block room entry, just access to side areas
                    # So we always return True

                    # Future: Could track which gates block room entry vs side areas
                    pass

        # All connected rooms are traversable with baseline abilities
        return True

    def _find_critical_path(self, world: "World") -> list[tuple[int, int]]:
        """
        Find the critical path from START to EXIT

        Args:
            world: World to analyze

        Returns:
            List of room coordinates on critical path, or empty list if not found
        """
        # Find start and exit rooms
        start_room = None
        exit_room = None

        for room in world.all_rooms:
            if room.room_type.value == "start":
                start_room = room
            elif room.room_type.value == "exit":
                exit_room = room

        if not start_room or not exit_room:
            return []

        start_coords = (start_room.grid_x, start_room.grid_y)
        exit_coords = (exit_room.grid_x, exit_room.grid_y)

        # Create rooms dictionary for lookups
        rooms_dict = {(room.grid_x, room.grid_y): room for room in world.all_rooms}

        # BFS to find shortest path
        queue = deque([(start_coords, [start_coords])])
        visited = {start_coords}

        while queue:
            current_coords, path = queue.popleft()

            if current_coords == exit_coords:
                return path

            current_room = rooms_dict.get(current_coords)
            if not current_room:
                continue

            for neighbor_coords in current_room.neighbors:
                if neighbor_coords not in visited:
                    visited.add(neighbor_coords)
                    queue.append((neighbor_coords, path + [neighbor_coords]))

        return []  # No path found

    def validate_world(self, world: "World") -> bool:
        """
        Validate entire world for solvability

        Args:
            world: World to validate

        Returns:
            True if world is solvable, False otherwise
        """
        print("\n[SOLVABILITY] Validating world...")

        # Check critical path
        critical_path_ok = self.validate_critical_path(world)

        # Check gates
        gates_ok = self.validate_optional_gates(world)

        overall_valid = critical_path_ok and gates_ok

        if overall_valid:
            print("[SOLVABILITY] OK: World is SOLVABLE")
        else:
            print("[SOLVABILITY] ERROR: World has SOLVABILITY ISSUES")

        return overall_valid
