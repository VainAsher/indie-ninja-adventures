"""
Anchor Resolution System - Two-Phase Feature Placement

Phase 1: Zone generators emit weighted anchor candidates
Phase 2: World-level resolver makes global decisions (save point spacing, etc.)

This enables global constraints like:
- Save points spaced at least 2 rooms apart
- Loot distribution across world
- Boss spawn positioning

Based on: Dynamic dungeon platformer anchor system
"""

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systems.world_generation import RoomNode


@dataclass
class AnchorCandidate:
    """
    Potential anchor placement from zone generation

    Emitted during zone-to-tile conversion. Multiple candidates
    can exist for same anchor type, with different weights and positions.

    Attributes:
        kind: Anchor type ("shopkeeper", "save_point", "loot", "spawn", "exit", etc.)
        pos: Tile coordinates within room (x, y)
        weight: Higher weight = more likely to be resolved (0.0-1.0+)
        tags: Feature tags ({"chest", "npc", "healing", "secret"})
        metadata: Optional metadata dict for anchor-specific data
    """

    kind: str
    pos: tuple[int, int]
    weight: float
    tags: set[str]
    metadata: dict | None = None


@dataclass
class ResolvedAnchor:
    """
    Finalized anchor placement after world-level resolution

    Attributes:
        kind: Anchor type
        pos: Tile coordinates within room
        room_coords: Room position in world grid
    """

    kind: str
    pos: tuple[int, int]
    room_coords: tuple[int, int]


# Save point proximity constraint
SAVE_POINT_PROXIMITY = 2  # Room distance (Manhattan)

# NEW: Puzzle constraints
PUZZLE_PROXIMITY = 3  # Puzzle switches at least 3 rooms apart
PUZZLE_TARGET_DISTANCE = (1, 4)  # Target must be 1-4 rooms from switch

# NEW: Ability gate progression thresholds (room depth from start)
GATE_PROGRESSION = {
    "gate_high_ledge": 2,  # Early game - requires double jump
    "gate_wall_shaft": 5,  # Mid game - requires wall jump
    "gate_wide_gap": 8,  # Late game - requires dash
    "gate_low_passage": 2,  # Can appear early - requires crouch
}

# NEW: Trigger density
MAX_TRIGGERS_PER_ROOM = 2

# Anchor kinds that always resolve if candidate exists
ALWAYS_RESOLVE = {"shopkeeper", "secret_stash", "exit_portal", "spawn", "exit"}

# NEW: Anchor kinds for puzzles, gates, and triggers
PUZZLE_ANCHORS = {"puzzle_switch", "puzzle_button", "puzzle_lever", "puzzle_target"}
ABILITY_GATE_ANCHORS = {"gate_high_ledge", "gate_wall_shaft", "gate_wide_gap", "gate_low_passage"}
TRIGGER_ANCHORS = {"trigger_enemy", "trigger_hazard", "trigger_timed"}


def resolve_world_anchors(rooms: dict[tuple[int, int], "RoomNode"], seed: int) -> None:
    """
    Resolve anchor candidates globally with spacing constraints

    Modifies rooms in-place to set resolved_anchors dictionary.

    Args:
        rooms: Dictionary of room nodes (modified in-place)
        seed: World seed for deterministic resolution
    """
    # Priority order: START/SHOP first, COMBAT last
    priority_order = sorted(
        rooms.keys(),
        key=lambda rc: (
            rooms[rc].room_type.value not in ("start", "shop"),  # False sorts first
            rooms[rc].room_type.value == "combat",  # True sorts last
            rc[1],
            rc[0],  # Tiebreaker: top-left to bottom-right
        ),
    )

    # Track rooms with resolved save points
    chosen_save_rooms: set[tuple[int, int]] = set()

    print(f"\n[ANCHOR RESOLUTION] Resolving anchors for {len(rooms)} rooms")
    print(f"[ANCHOR RESOLUTION] Priority order: {len(priority_order)} rooms")

    for room_coords in priority_order:
        room = rooms[room_coords]

        # Initialize resolved_anchors if not exists
        if not hasattr(room, "resolved_anchors"):
            room.resolved_anchors = {}

        # Initialize anchor_candidates if not exists
        if not hasattr(room, "anchor_candidates"):
            room.anchor_candidates = []

        # Always resolve these if candidate exists
        for kind in ALWAYS_RESOLVE:
            _resolve_always(room, kind)

        # Save points with proximity check
        save_candidate = _best_candidate(room, "save_point")

        if save_candidate is None:
            continue

        # Check if any save within PROXIMITY rooms
        too_close = False
        for other_coords in chosen_save_rooms:
            distance = _bfs_room_distance(rooms, room_coords, other_coords)
            if distance <= SAVE_POINT_PROXIMITY:
                too_close = True
                print(
                    f"[ANCHOR] Room {room_coords}: Save too close to {other_coords} (distance={distance})"
                )
                break

        if not too_close:
            room.resolved_anchors["save_point"] = save_candidate.pos
            chosen_save_rooms.add(room_coords)
            print(f"[ANCHOR] Room {room_coords}: Placed SAVE at {save_candidate.pos}")
        else:
            # Too close to existing save → convert to loot
            loot_candidate = _best_candidate(room, "loot")
            if loot_candidate:
                room.resolved_anchors["loot"] = loot_candidate.pos
                print(f"[ANCHOR] Room {room_coords}: Converted SAVE → LOOT at {loot_candidate.pos}")
            else:
                # No loot candidate → use save position for loot
                room.resolved_anchors["loot"] = save_candidate.pos
                print(
                    f"[ANCHOR] Room {room_coords}: Converted SAVE → LOOT at {save_candidate.pos} (no loot candidate)"
                )

    print(f"[ANCHOR RESOLUTION] Placed {len(chosen_save_rooms)} save points")

    # NEW: Resolve ability gates based on room depth
    _resolve_ability_gates(rooms)

    # NEW: Resolve triggers (limit per room)
    _resolve_triggers(rooms)

    # NEW: Resolve puzzle anchors (optional for now)
    _resolve_puzzles(rooms)


def _best_candidate(room: "RoomNode", kind: str) -> AnchorCandidate | None:
    """
    Get highest-weight candidate of given kind

    Args:
        room: Room node
        kind: Anchor kind to search for

    Returns:
        AnchorCandidate with highest weight, or None
    """
    candidates = [c for c in room.anchor_candidates if c.kind == kind]

    if not candidates:
        return None

    return max(candidates, key=lambda c: c.weight)


def _resolve_always(room: "RoomNode", kind: str) -> None:
    """
    Always place anchor if candidate exists

    Args:
        room: Room node (modified in-place)
        kind: Anchor kind to resolve
    """
    candidate = _best_candidate(room, kind)

    if candidate:
        room.resolved_anchors[kind] = candidate.pos
        print(
            f"[ANCHOR] Room ({room.grid_x}, {room.grid_y}): Placed {kind.upper()} at {candidate.pos}"
        )


def _bfs_room_distance(
    rooms: dict[tuple[int, int], "RoomNode"], start: tuple[int, int], end: tuple[int, int]
) -> int:
    """
    Calculate room-to-room distance via BFS

    Args:
        rooms: Dictionary of room nodes
        start: Starting room coordinates
        end: Ending room coordinates

    Returns:
        Minimum room count distance, or float('inf') if unreachable
    """
    if start == end:
        return 0

    queue = deque([(start, 0)])
    visited = {start}

    while queue:
        current, dist = queue.popleft()

        # Check all neighbors
        current_room = rooms.get(current)
        if not current_room:
            continue

        for neighbor_coords in current_room.neighbors:
            if neighbor_coords == end:
                return dist + 1

            if neighbor_coords not in visited:
                visited.add(neighbor_coords)
                queue.append((neighbor_coords, dist + 1))

    return float("inf")  # Unreachable


def emit_anchor_candidate(
    candidates: list[AnchorCandidate],
    kind: str,
    pos: tuple[int, int],
    weight: float = 1.0,
    tags: set[str] | None = None,
    metadata: dict | None = None,
):
    """
    Helper to emit an anchor candidate

    Args:
        candidates: List to append to
        kind: Anchor kind
        pos: Tile position
        weight: Candidate weight (default: 1.0)
        tags: Feature tags (default: empty set)
        metadata: Optional metadata dict
    """
    candidates.append(
        AnchorCandidate(kind=kind, pos=pos, weight=weight, tags=tags or set(), metadata=metadata)
    )


def _resolve_ability_gates(rooms: dict[tuple[int, int], "RoomNode"]) -> None:
    """
    Resolve ability gate anchors based on room depth

    Gates are placed only if room is far enough from start to justify
    the ability requirement.

    Args:
        rooms: Dictionary of room nodes (modified in-place)
    """
    placed_gates = 0

    for room_coords, room in rooms.items():
        if not hasattr(room, "anchor_candidates"):
            continue

        # Check for gate candidates
        gate_candidates = [c for c in room.anchor_candidates if c.kind in ABILITY_GATE_ANCHORS]

        if not gate_candidates:
            continue

        # Calculate room depth (Manhattan distance from origin)
        room_depth = abs(room.grid_x) + abs(room.grid_y)

        # Resolve each gate candidate if depth is sufficient
        for candidate in gate_candidates:
            required_depth = GATE_PROGRESSION.get(candidate.kind, 0)

            if room_depth >= required_depth:
                room.resolved_anchors[candidate.kind] = candidate.pos
                placed_gates += 1
                print(
                    f"[ANCHOR] Room {room_coords}: Placed {candidate.kind.upper()} at {candidate.pos} (depth={room_depth})"
                )
            else:
                print(
                    f"[ANCHOR] Room {room_coords}: Skipped {candidate.kind} (depth {room_depth} < required {required_depth})"
                )

    print(f"[ANCHOR RESOLUTION] Placed {placed_gates} ability gates")


def _resolve_triggers(rooms: dict[tuple[int, int], "RoomNode"]) -> None:
    """
    Resolve environmental trigger anchors with density limit

    Args:
        rooms: Dictionary of room nodes (modified in-place)
    """
    placed_triggers = 0

    for room_coords, room in rooms.items():
        if not hasattr(room, "anchor_candidates"):
            continue

        # Check for trigger candidates
        trigger_candidates = [c for c in room.anchor_candidates if c.kind in TRIGGER_ANCHORS]

        if not trigger_candidates:
            continue

        # Sort by weight (highest first) and limit to MAX_TRIGGERS_PER_ROOM
        trigger_candidates.sort(key=lambda c: c.weight, reverse=True)
        triggers_to_place = trigger_candidates[:MAX_TRIGGERS_PER_ROOM]

        for candidate in triggers_to_place:
            room.resolved_anchors[candidate.kind] = candidate.pos
            placed_triggers += 1
            print(
                f"[ANCHOR] Room {room_coords}: Placed {candidate.kind.upper()} at {candidate.pos}"
            )

    print(f"[ANCHOR RESOLUTION] Placed {placed_triggers} triggers")


def _resolve_puzzles(rooms: dict[tuple[int, int], "RoomNode"]) -> None:
    """
    Resolve puzzle anchor candidates (switches, buttons, targets)

    For now, this is a simple implementation that just places puzzle
    elements without linking them. Full multi-room puzzle linking
    can be added in a future phase.

    Args:
        rooms: Dictionary of room nodes (modified in-place)
    """
    placed_puzzles = 0

    for room_coords, room in rooms.items():
        if not hasattr(room, "anchor_candidates"):
            continue

        # Check for puzzle candidates
        puzzle_candidates = [c for c in room.anchor_candidates if c.kind in PUZZLE_ANCHORS]

        if not puzzle_candidates:
            continue

        # For now, place all puzzle elements
        # TODO: Add multi-room puzzle linking logic
        for candidate in puzzle_candidates:
            room.resolved_anchors[candidate.kind] = candidate.pos
            placed_puzzles += 1
            print(
                f"[ANCHOR] Room {room_coords}: Placed {candidate.kind.upper()} at {candidate.pos}"
            )

    print(f"[ANCHOR RESOLUTION] Placed {placed_puzzles} puzzle elements")
