"""
Zone Planning System - 16x16 Grid Layout Planning

Each room is divided into a 16x16 grid of zones. Each zone has a role (WALK, FILL, PLAT, DOOR, etc.)
that determines how it will be converted to tiles.

Features:
- Intelligent feature placement (shops, treasures, save points)
- Connectivity validation (BFS ensures all features reachable)
- Shape patterns for different room types
- Door zone placement based on connections

Source: Dynamic dungeon platformer project (originally 5×5)
Enhanced: Increased to 16×16 for finer granularity and more complex layouts
"""

import random
from collections.abc import Callable
from dataclasses import dataclass

from config.physics_constants import TILES_PER_ZONE
from systems.anchor_resolution import AnchorCandidate
from systems.world_generation import (
    ZONES_H,
    ZONES_W,
    RoomNode,
    RoomType,
)

# Simplified zone role constants (matching source)
Z_WALK = "walk"  # Walkable floor
Z_FILL = "fill"  # Solid terrain
Z_PLAT = "platform"  # Platform (jump through)
Z_DOOR = "door"  # Door connection
Z_SAVE = "save"  # Save point
Z_SHOP = "shop"  # Shop NPC
Z_LOOT = "loot"  # Treasure
Z_VOID = "void"  # Empty space (pit)
Z_DECOR = "decor"  # Unassigned (will become walkable or platform)

# Additional zone roles for context-aware rules
Z_CHUTE = "chute"  # Vertical shaft for down movement
Z_CLIMB = "climb"  # Stepped platforms for up movement
Z_CONNECTOR = "connector"  # Horizontal platform for hub rooms

# NEW: Enclosed room zones
Z_CHAMBER = "chamber"  # 3×3 walled box (arena/puzzle)
Z_ALCOVE = "alcove"  # 2×1 wall indent (secret nook)

# NEW: Irregular platform zones
Z_L_PLATFORM = "l_platform"  # L-shaped platform
Z_T_PLATFORM = "t_platform"  # T-shaped platform
Z_DIAGONAL = "diagonal"  # Diagonal staircase
Z_FLOATING = "floating"  # Isolated floating platform

# NEW: Vertical passage zones
Z_SHAFT_UP = "shaft_up"  # Narrow vertical shaft (2 zones wide)
Z_SHAFT_DOWN = "shaft_down"  # Downward shaft with walls
Z_TUNNEL = "tunnel"  # Horizontal narrow tunnel (1 zone tall)

# NEW: Fluid zones
Z_WATER_POOL = "water_pool"  # Water-filled cavity
Z_LAVA_POOL = "lava_pool"  # Lava-filled cavity
Z_FLUID_SURFACE = "fluid_surface"  # Top layer of fluid


@dataclass
class RoomContext:
    """
    Context information for logic rules

    Attributes:
        room: The room being planned
        zone_grid: Current zone grid (modifiable by rules)
        neighbor_dirs: Set of door directions ("up", "down", "left", "right")
        degree: Number of doors (connectivity degree)
        door_zones: List of door zone coordinates
    """

    room: RoomNode
    zone_grid: list[list[str]]
    neighbor_dirs: set[str]
    degree: int
    door_zones: list[tuple[int, int]]


# Logic rule function signature
ZoneRuleFn = Callable[[RoomContext], None]


def rule_force_down_chute(ctx: RoomContext):
    """
    If DOWN door exists, force bottom-center zone to CHUTE

    Ensures vertical drop path when room has downward connection.
    """
    if "down" not in ctx.neighbor_dirs:
        return

    # Force bottom-center to CHUTE for vertical drop
    bottom_row = ZONES_H - 1
    center_col = ZONES_W // 2

    ctx.zone_grid[bottom_row][center_col] = Z_CHUTE
    print(f"[LOGIC RULE] Applied rule_force_down_chute at ({center_col}, {bottom_row})")


def rule_force_up_climb(ctx: RoomContext):
    """
    If UP door exists, force top-center zone to CLIMB

    Ensures vertical ascent path when room has upward connection.
    """
    if "up" not in ctx.neighbor_dirs:
        return

    # Force top-center to CLIMB for vertical ascent
    top_row = 0
    center_col = ZONES_W // 2

    ctx.zone_grid[top_row][center_col] = Z_CLIMB
    print(f"[LOGIC RULE] Applied rule_force_up_climb at ({center_col}, {top_row})")


def rule_high_degree_connector(ctx: RoomContext):
    """
    If 3+ doors, force center to CONNECTOR (hub room)

    Hub rooms need strong horizontal connectivity.
    """
    if ctx.degree < 3:
        return

    # Force center to CONNECTOR for hub rooms
    center_x = ZONES_W // 2
    center_y = ZONES_H // 2

    ctx.zone_grid[center_y][center_x] = Z_CONNECTOR
    print(f"[LOGIC RULE] Applied rule_high_degree_connector at ({center_x}, {center_y})")


def rule_dead_end_bonus_corner(ctx: RoomContext):
    """
    If degree==1 (dead end), add bonus loot in random corner

    Rewards exploration of dead-end rooms.
    """
    if ctx.degree != 1:
        return

    import random

    rng = random.Random(ctx.room.seed)

    # Pick random corner (avoid edges to prevent door conflicts)
    corners = [
        (1, 1),  # Top-left
        (ZONES_W - 2, 1),  # Top-right
        (1, ZONES_H - 2),  # Bottom-left
        (ZONES_W - 2, ZONES_H - 2),  # Bottom-right
    ]

    cx, cy = rng.choice(corners)

    # Avoid overwriting door zones
    if (cx, cy) in ctx.door_zones:
        return

    # Place bonus loot in corner
    ctx.zone_grid[cy][cx] = Z_LOOT
    print(f"[LOGIC RULE] Applied rule_dead_end_bonus_corner at ({cx}, {cy})")


def rule_place_ability_gate(ctx: RoomContext):
    """
    Place ability gate if room depth warrants it

    Creates optional paths requiring specific abilities:
    - High ledges require double jump
    - Wall shafts require wall jump
    - Wide gaps require dash
    - Low passages require crouch

    Args:
        ctx: Room context with zone grid and room info
    """
    import random

    # Calculate room depth from start (Manhattan distance from origin)
    depth = abs(ctx.room.grid_x) + abs(ctx.room.grid_y)

    # Determine available gate types based on depth
    available_gates = []
    if depth >= 2:
        available_gates.extend(["gate_high_ledge", "gate_low_passage"])
    if depth >= 5:
        available_gates.append("gate_wall_shaft")
    if depth >= 8:
        available_gates.append("gate_wide_gap")

    if not available_gates:
        return

    # 30% chance to place gate
    rng = random.Random(ctx.room.seed + 1000)  # Different seed for gate placement
    if rng.random() > 0.3:
        return

    gate_type = rng.choice(available_gates)

    # Find edge zones (not on critical path - near room edges)
    edge_zones = [
        (x, y)
        for x in range(ZONES_W)
        for y in range(ZONES_H)
        if (x < 2 or x >= ZONES_W - 2 or y < 2 or y >= ZONES_H - 2)
        and (x, y) not in ctx.door_zones
        and ctx.zone_grid[y][x] == Z_DECOR  # Only place in unassigned zones
    ]

    if not edge_zones:
        return

    zx, zy = rng.choice(edge_zones)

    # Emit anchor candidate
    ctx.room.anchor_candidates.append(
        AnchorCandidate(
            kind=gate_type,
            pos=(zx * 10 + 5, zy * 10 + 5),
            weight=0.7,
            tags={"ability_gate", "optional"},
            metadata={"required_ability": gate_type.replace("gate_", "")},
        )
    )

    print(f"[LOGIC RULE] Placed {gate_type} candidate at ({zx}, {zy}) (depth={depth})")


# Room type to logic rules mapping
ROOM_LOGIC_RULES: dict[str, list[ZoneRuleFn]] = {
    "start": [
        rule_force_down_chute,
        rule_force_up_climb,
    ],
    "shop": [
        rule_high_degree_connector,
    ],
    "treasure": [
        rule_dead_end_bonus_corner,
        rule_place_ability_gate,  # NEW: Ability gates in treasure rooms
    ],
    "combat": [
        rule_force_down_chute,
        rule_force_up_climb,
    ],
    "platform": [
        rule_force_down_chute,
        rule_force_up_climb,
        rule_place_ability_gate,  # NEW: Ability gates in platform rooms
    ],
    "boss": [],  # No rules for boss rooms (they're special)
    "exit": [
        rule_force_down_chute,
        rule_force_up_climb,
    ],
}


class ZonePlanner:
    """
    Plans 16x16 zone grid layout for a room.

    Assigns zone roles based on room type, biome theme, and connections.
    Ensures connectivity between important features.
    """

    def __init__(self, seed: int):
        """
        Initialize zone planner.

        Args:
            seed: Random seed for deterministic planning
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def plan_room(self, room: RoomNode) -> list[list[str]]:
        """
        Plan zone grid for a room.

        Args:
            room: Room to plan zones for

        Returns:
            5x5 grid of zone role strings
        """
        # Initialize grid with DECOR (unassigned)
        roles = [[Z_DECOR for _ in range(ZONES_W)] for _ in range(ZONES_H)]

        # Step 1: Place door zones (at edges where connections exist)
        door_zones = self._place_door_zones(room, roles)

        # Step 2: Place feature zones (shop, save, loot, etc.)
        feature_zones = self._place_features(room, roles, door_zones)

        # Step 3: Ensure connectivity (create paths between doors and features)
        must_connect = door_zones + feature_zones
        if must_connect:
            self._ensure_connectivity(roles, must_connect)

        # Step 4: Apply context-aware logic rules
        self._apply_logic_rules(room, roles, door_zones)

        # Step 5: Add solid fill zones (obstacles, platforms)
        self._add_fill_zones(room, roles, must_connect)

        # Step 6: Convert remaining DECOR to WALK or PLAT
        self._finalize_zones(roles, room)

        return roles

    def _place_door_zones(self, room: RoomNode, roles: list[list[str]]) -> list[tuple[int, int]]:
        """
        Place door zones at room edges based on connections.

        Returns list of door zone coordinates.
        """
        door_zones = []

        for direction, ports in room.door_ports.items():
            for port in ports:
                # Get edge zones for this direction
                edge_zones = self._get_edge_zones(direction)

                # Convert tile index to zone index using the configured tiles-per-zone
                zone_index = min(len(edge_zones) - 1, port.center_tile // TILES_PER_ZONE)
                zx, zy = edge_zones[zone_index]

                if (zx, zy) not in door_zones:
                    door_zones.append((zx, zy))
                    roles[zy][zx] = Z_DOOR

        return door_zones

    def _place_features(
        self, room: RoomNode, roles: list[list[str]], door_zones: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """
        Place feature zones (shop, save, loot) based on room type.

        Returns list of feature zone coordinates.
        """
        features = []

        # Interior zones (exclude only zones with doors, not all edges)
        # This maximizes available space for features
        interior = [
            (x, y) for y in range(ZONES_H) for x in range(ZONES_W) if (x, y) not in door_zones
        ]

        if not interior:
            interior = [(ZONES_W // 2, ZONES_H // 2)]  # Fallback to center

        # Center zones for important features (sorted by distance from room center)
        center_x, center_y = ZONES_W // 2, ZONES_H // 2
        center_zones = sorted(interior, key=lambda z: abs(z[0] - center_x) + abs(z[1] - center_y))[
            :3
        ]

        # Initialize anchor_candidates if not present
        if not hasattr(room, "anchor_candidates") or room.anchor_candidates is None:
            room.anchor_candidates = []

        # Place features based on room type
        if room.room_type == RoomType.SHOP:
            # Shop NPC in center
            if center_zones:
                zx, zy = center_zones[0]
                roles[zy][zx] = Z_SHOP
                features.append((zx, zy))
                # Emit shop anchor candidate
                room.anchor_candidates.append(
                    AnchorCandidate(
                        kind="shopkeeper",
                        pos=(
                            zx * 10 + 5,
                            zy * 10 + 5,
                        ),  # Convert zone to tile coords (center of zone)
                        weight=1.0,
                        tags={"npc", "shop"},
                    )
                )

            # Loot in corner
            if len(interior) > 1:
                zx, zy = interior[-1]
                roles[zy][zx] = Z_LOOT
                features.append((zx, zy))
                # Emit loot anchor candidate
                room.anchor_candidates.append(
                    AnchorCandidate(
                        kind="loot",
                        pos=(zx * 10 + 5, zy * 10 + 5),
                        weight=0.8,
                        tags={"chest", "shop"},
                    )
                )

        elif room.room_type == RoomType.TREASURE:
            # Loot in center
            if center_zones:
                zx, zy = center_zones[0]
                roles[zy][zx] = Z_LOOT
                features.append((zx, zy))
                # Emit treasure anchor candidate
                room.anchor_candidates.append(
                    AnchorCandidate(
                        kind="loot",
                        pos=(zx * 10 + 5, zy * 10 + 5),
                        weight=1.0,
                        tags={"chest", "treasure"},
                    )
                )

        elif room.room_type == RoomType.BOSS:
            # Boss spawn in center (no special zone role, just mark)
            # Will be converted to WALK for boss to stand on
            pass

        elif room.room_type == RoomType.START:
            # Spawn point in center/safe area
            if center_zones:
                zx, zy = center_zones[0]
                # Emit spawn anchor
                if not room.anchors:
                    room.anchors = {}
                if "spawn" not in room.anchors:
                    room.anchors["spawn"] = []
                room.anchors["spawn"].append((zx, zy))
                features.append((zx, zy))
                # Emit spawn anchor candidate
                room.anchor_candidates.append(
                    AnchorCandidate(
                        kind="spawn",
                        pos=(zx * 10 + 5, zy * 10 + 5),
                        weight=1.0,
                        tags={"spawn", "start"},
                    )
                )

            # Save point near entry (optional)
            if door_zones and interior and len(center_zones) > 1:
                # Closest interior to first door
                door = door_zones[0]
                closest = min(interior, key=lambda z: abs(z[0] - door[0]) + abs(z[1] - door[1]))
                zx, zy = closest
                if (zx, zy) not in features:  # Avoid overlap with spawn
                    roles[zy][zx] = Z_SAVE
                    features.append((zx, zy))
                    # Emit save point anchor candidate
                    room.anchor_candidates.append(
                        AnchorCandidate(
                            kind="save_point",
                            pos=(zx * 10 + 5, zy * 10 + 5),
                            weight=0.9,
                            tags={"checkpoint", "healing"},
                        )
                    )

        elif room.room_type == RoomType.EXIT:
            # Exit portal in center
            if center_zones:
                zx, zy = center_zones[0]
                # Emit exit anchor
                if not room.anchors:
                    room.anchors = {}
                if "exit" not in room.anchors:
                    room.anchors["exit"] = []
                room.anchors["exit"].append((zx, zy))
                # Emit exit anchor candidate
                room.anchor_candidates.append(
                    AnchorCandidate(
                        kind="exit",
                        pos=(zx * 10 + 5, zy * 10 + 5),
                        weight=1.0,
                        tags={"exit", "portal"},
                    )
                )
                # Use LOOT role for exit portal (will be rendered differently)
                roles[zy][zx] = Z_LOOT
                features.append((zx, zy))

        elif room.room_type == RoomType.COMBAT:
            # NEW: Enemy trigger anchor for combat rooms
            if self.rng.random() < 0.4:  # 40% chance
                # Place trigger near edge (room entry)
                edge_zones = [
                    z
                    for z in interior
                    if (z[0] < 3 or z[0] >= ZONES_W - 3 or z[1] < 3 or z[1] >= ZONES_H - 3)
                ]
                if edge_zones:
                    zx, zy = self.rng.choice(edge_zones)
                    room.anchor_candidates.append(
                        AnchorCandidate(
                            kind="trigger_enemy",
                            pos=(zx * 10 + 5, zy * 10 + 5),
                            weight=0.7,
                            tags={"trigger", "combat"},
                            metadata={"enemy_count": self.rng.randint(2, 4)},
                        )
                    )
                    print(f"[ZONE PLANNING] Room {room.room_type}: Added enemy trigger candidate")

        else:
            # Random loot chance for other rooms
            if self.rng.random() < 0.25 and interior:
                zx, zy = self.rng.choice(interior)
                roles[zy][zx] = Z_LOOT
                features.append((zx, zy))

        # NEW: Add puzzle switch for TREASURE rooms (50% chance)
        if room.room_type == RoomType.TREASURE and self.rng.random() < 0.5:
            # Find zones away from treasure
            non_treasure_zones = [z for z in interior if z not in features]
            if non_treasure_zones:
                zx, zy = non_treasure_zones[0]
                room.anchor_candidates.append(
                    AnchorCandidate(
                        kind="puzzle_switch",
                        pos=(zx * 10 + 5, zy * 10 + 5),
                        weight=0.9,
                        tags={"puzzle", "treasure"},
                        metadata={"target_room": (room.grid_x, room.grid_y)},
                    )
                )
                print(f"[ZONE PLANNING] Room {room.room_type}: Added puzzle switch candidate")

        return features

    def _ensure_connectivity(self, roles: list[list[str]], must_connect: list[tuple[int, int]]):
        """
        Ensure all critical zones are connected by walkable paths.

        Uses BFS to create paths between doors and features.
        """
        if len(must_connect) < 2:
            return

        # Start from first zone, connect to all others
        start = must_connect[0]

        for target in must_connect[1:]:
            path = self._bfs_path(roles, start, target)
            if path:
                # Mark path zones as walkable
                for zx, zy in path:
                    if roles[zy][zx] == Z_DECOR:
                        roles[zy][zx] = Z_WALK

    def _bfs_path(
        self, roles: list[list[str]], start: tuple[int, int], goal: tuple[int, int]
    ) -> list[tuple[int, int]] | None:
        """
        Find shortest path between two zones using BFS.

        Returns list of (x, y) coordinates, or None if no path.
        """
        queue = [(start, [start])]
        visited = {start}

        while queue:
            (x, y), path = queue.pop(0)

            if (x, y) == goal:
                return path

            # Check neighbors (4-directional)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy

                # Bounds check
                if not (0 <= nx < ZONES_W and 0 <= ny < ZONES_H):
                    continue

                # Skip visited
                if (nx, ny) in visited:
                    continue

                # Skip solid zones and voids (not walkable)
                if roles[ny][nx] in (Z_FILL, Z_VOID):
                    continue

                visited.add((nx, ny))
                queue.append(((nx, ny), path + [(nx, ny)]))

        return None

    def _add_fill_zones(
        self, room: RoomNode, roles: list[list[str]], must_connect: list[tuple[int, int]]
    ):
        """
        Add solid fill zones (obstacles) AND zone patterns based on room type.

        More combat/platform rooms = more obstacles.
        NEW: Also tries to place zone patterns for room variety.
        """
        # NEW: Try to place zone patterns first
        from systems.room_patterns import get_patterns_for_room, should_place_pattern

        patterns_to_try = get_patterns_for_room(room.room_type)

        for pattern, probability in patterns_to_try:
            if should_place_pattern(probability, self.rng):
                placed = self._try_place_pattern(pattern, roles, must_connect)
                if placed:
                    print(f"[PATTERN] Placed {pattern.name} in {room.room_type.value} room")

        # Determine fill budget (obstacles)
        if room.room_type in (RoomType.COMBAT, RoomType.PLATFORM):
            fill_count = self.rng.randint(2, 4)
        elif room.room_type in (RoomType.TREASURE, RoomType.SHOP):
            fill_count = self.rng.randint(1, 2)
        else:
            fill_count = self.rng.randint(0, 2)

        # Candidate zones (DECOR zones not critical)
        candidates = [
            (x, y)
            for y in range(ZONES_H)
            for x in range(ZONES_W)
            if roles[y][x] == Z_DECOR and (x, y) not in must_connect
        ]

        self.rng.shuffle(candidates)

        # Add fill zones, ensuring connectivity isn't broken
        for x, y in candidates[:fill_count]:
            roles[y][x] = Z_FILL

            # Check if connectivity is maintained
            if not self._check_connectivity(roles, must_connect):
                # Revert if connectivity broken
                roles[y][x] = Z_DECOR

    def _check_connectivity(
        self, roles: list[list[str]], must_connect: list[tuple[int, int]]
    ) -> bool:
        """
        Check if all critical zones are still connected.

        Returns True if connected, False otherwise.
        """
        if len(must_connect) < 2:
            return True

        start = must_connect[0]

        for target in must_connect[1:]:
            if not self._bfs_path(roles, start, target):
                return False

        return True

    def _try_place_pattern(
        self, pattern, roles: list[list[str]], must_connect: list[tuple[int, int]]
    ) -> bool:
        """
        Try to place a zone pattern in available space

        Args:
            pattern: ZonePattern to place
            roles: Current zone grid
            must_connect: Critical zones that must stay connected

        Returns:
            True if pattern was placed successfully
        """
        # Find available positions (where pattern fits)
        for y in range(ZONES_H - pattern.height + 1):
            for x in range(ZONES_W - pattern.width + 1):
                # Check if space is available (all zones are DECOR)
                available = all(
                    roles[y + py][x + px] == Z_DECOR
                    for py in range(pattern.height)
                    for px in range(pattern.width)
                )

                if not available:
                    continue

                # Save original state for rollback
                original_zones = [
                    [roles[y + py][x + px] for px in range(pattern.width)]
                    for py in range(pattern.height)
                ]

                # Stamp pattern
                for py in range(pattern.height):
                    for px in range(pattern.width):
                        roles[y + py][x + px] = pattern.pattern[py][px]

                # Verify connectivity still valid
                if self._check_connectivity(roles, must_connect):
                    return True
                else:
                    # Revert pattern
                    for py in range(pattern.height):
                        for px in range(pattern.width):
                            roles[y + py][x + px] = original_zones[py][px]

        return False

    def _apply_logic_rules(
        self, room: RoomNode, zone_grid: list[list[str]], door_zones: list[tuple[int, int]]
    ):
        """
        Apply context-aware logic rules based on room type and connectivity

        Rules modify zone grid to ensure intelligent layouts:
        - DOWN doors get CHUTE zones for vertical drops
        - UP doors get CLIMB zones for vertical ascent
        - Hub rooms (3+ doors) get CONNECTOR zones
        - Dead-end rooms get bonus loot in corners

        Args:
            room: Room being planned
            zone_grid: Current zone grid (modified in-place)
            door_zones: List of door zone coordinates
        """
        # Get neighbor directions from door ports
        neighbor_dirs = set(room.door_ports.keys())

        # Build context
        ctx = RoomContext(
            room=room,
            zone_grid=zone_grid,
            neighbor_dirs=neighbor_dirs,
            degree=len(neighbor_dirs),
            door_zones=door_zones,
        )

        # Get rules for this room type
        room_type_key = (
            room.room_type.value if hasattr(room.room_type, "value") else str(room.room_type)
        )
        rules = ROOM_LOGIC_RULES.get(room_type_key, [])

        # Execute rules
        if rules:
            print(f"[LOGIC RULES] Applying {len(rules)} rules for {room_type_key} room")
            for rule in rules:
                rule(ctx)
        else:
            print(f"[LOGIC RULES] No rules defined for {room_type_key} room")

    def _finalize_zones(self, roles: list[list[str]], room: RoomNode):
        """
        Convert remaining DECOR zones to WALK, PLAT, or FILL based on room type.

        Creates interesting platforming layouts with room-specific probabilities.
        Uses probabilities from source project for better variety.
        """
        # Room-type-specific probabilities (from source)
        if room.room_type == RoomType.PLATFORM:
            plat_prob = 0.55  # High platform density for platforming challenges
            fill_prob = 0.22  # Some obstacles
            walk_prob = 0.22  # Less floor
        elif room.room_type == RoomType.COMBAT:
            plat_prob = 0.45  # Medium platforms for combat arenas
            fill_prob = 0.14  # Some cover
            walk_prob = 0.22  # Some floor space
        elif room.room_type == RoomType.TREASURE:
            plat_prob = 0.35  # Moderate platforms
            fill_prob = 0.10  # Minimal obstacles
            walk_prob = 0.22  # Open space
        elif room.room_type == RoomType.BOSS:
            plat_prob = 0.30  # Some platforms for dodging
            fill_prob = 0.12  # Light obstacles
            walk_prob = 0.22  # More arena space
        else:
            # Default probabilities (start, exit, shop rooms)
            plat_prob = 0.25  # Low platform density
            fill_prob = 0.08  # Minimal obstacles
            walk_prob = 0.22  # Mostly open

        for y in range(ZONES_H):
            for x in range(ZONES_W):
                if roles[y][x] == Z_DECOR:
                    r = self.rng.random()
                    if r < fill_prob:
                        # Solid obstacle
                        roles[y][x] = Z_FILL
                    elif r < fill_prob + plat_prob:
                        # Platform
                        roles[y][x] = Z_PLAT
                    elif r < fill_prob + plat_prob + walk_prob:
                        # Walkable floor
                        roles[y][x] = Z_WALK
                    else:
                        # Void/empty space
                        roles[y][x] = Z_VOID

    def _get_edge_zones(self, direction: str) -> list[tuple[int, int]]:
        """
        Get list of edge zones for a direction.

        Args:
            direction: "up", "down", "left", or "right"

        Returns:
            List of (x, y) zone coordinates on that edge
        """
        if direction == "left":
            return [(0, zy) for zy in range(ZONES_H)]
        elif direction == "right":
            return [(ZONES_W - 1, zy) for zy in range(ZONES_H)]
        elif direction == "up":
            return [(zx, 0) for zx in range(ZONES_W)]
        elif direction == "down":
            return [(zx, ZONES_H - 1) for zx in range(ZONES_W)]
        return []


def print_zone_grid(roles: list[list[str]]) -> None:
    """
    Print ASCII visualization of zone grid (for debugging).

    Args:
        roles: 16x16 zone grid
    """
    # Zone symbols
    symbols = {
        Z_WALK: ".",
        Z_FILL: "#",
        Z_PLAT: "-",
        Z_DOOR: "D",
        Z_SAVE: "S",
        Z_SHOP: "$",
        Z_LOOT: "T",
        Z_VOID: " ",
        Z_DECOR: "?",
    }

    height = len(roles)
    width = len(roles[0]) if height > 0 else 0

    print(f"\nZone Grid ({width}x{height}):")
    for row in roles:
        print(" ".join(symbols.get(role, role[0]) for role in row))
    print()
