"""
Zone Patterns - Multi-Zone Shape Templates

Defines reusable patterns that span multiple zones for creating:
- Chambers (enclosed arenas)
- Irregular platforms (L/T shapes)
- Vertical shafts (wall jump challenges)
- Fluid pools (water/lava cavities)

These patterns are stamped into the zone grid during room generation
to create more interesting and varied room shapes.
"""

from dataclasses import dataclass
from typing import List, Set, Tuple

# Import zone role constants
from systems.zone_planning import (
    Z_ALCOVE,
    Z_CHAMBER,
    Z_DIAGONAL,
    Z_FILL,
    Z_FLOATING,
    Z_FLUID_SURFACE,
    Z_L_PLATFORM,
    Z_LAVA_POOL,
    Z_PLAT,
    Z_SHAFT_DOWN,
    Z_SHAFT_UP,
    Z_T_PLATFORM,
    Z_TUNNEL,
    Z_VOID,
    Z_WALK,
    Z_WATER_POOL,
)


@dataclass
class ZonePattern:
    """Multi-zone shape pattern"""

    name: str
    pattern: List[List[str]]  # 2D grid of zone roles (top to bottom, left to right)
    width: int  # Pattern width in zones
    height: int  # Pattern height in zones
    anchor_zones: List[Tuple[int, int]]  # Where anchors can spawn (relative coords)
    tags: Set[str]  # Pattern tags for placement logic


# =============================================================================
# CHAMBER PATTERNS - Enclosed arenas for combat/puzzles
# =============================================================================

CHAMBER_3X3 = ZonePattern(
    name="chamber_3x3",
    pattern=[
        [Z_FILL, Z_FILL, Z_FILL],
        [Z_FILL, Z_VOID, Z_FILL],
        [Z_FILL, Z_WALK, Z_FILL],
    ],
    width=3,
    height=3,
    anchor_zones=[(1, 1)],  # Center void
    tags={"arena", "enclosed", "combat", "chamber"},
)

CHAMBER_4X3 = ZonePattern(
    name="chamber_4x3",
    pattern=[
        [Z_FILL, Z_FILL, Z_FILL, Z_FILL],
        [Z_FILL, Z_VOID, Z_VOID, Z_FILL],
        [Z_FILL, Z_WALK, Z_WALK, Z_FILL],
    ],
    width=4,
    height=3,
    anchor_zones=[(1, 1), (2, 1)],  # Center positions
    tags={"arena", "enclosed", "combat", "chamber"},
)

CHAMBER_5X5 = ZonePattern(
    name="chamber_5x5",
    pattern=[
        [Z_FILL, Z_FILL, Z_FILL, Z_FILL, Z_FILL],
        [Z_FILL, Z_VOID, Z_VOID, Z_VOID, Z_FILL],
        [Z_FILL, Z_VOID, Z_VOID, Z_VOID, Z_FILL],
        [Z_FILL, Z_VOID, Z_VOID, Z_VOID, Z_FILL],
        [Z_FILL, Z_WALK, Z_WALK, Z_WALK, Z_FILL],
    ],
    width=5,
    height=5,
    anchor_zones=[(2, 2)],  # Very center
    tags={"arena", "enclosed", "boss", "large", "chamber"},
)

# =============================================================================
# ALCOVE PATTERNS - Small niches for secrets/treasure
# =============================================================================

ALCOVE_SMALL = ZonePattern(
    name="alcove_small",
    pattern=[
        [Z_FILL, Z_VOID, Z_FILL],
        [Z_FILL, Z_WALK, Z_FILL],
    ],
    width=3,
    height=2,
    anchor_zones=[(1, 0)],  # Center of alcove
    tags={"secret", "treasure", "alcove"},
)

ALCOVE_DEEP = ZonePattern(
    name="alcove_deep",
    pattern=[
        [Z_FILL, Z_VOID, Z_FILL],
        [Z_FILL, Z_VOID, Z_FILL],
        [Z_FILL, Z_WALK, Z_FILL],
    ],
    width=3,
    height=3,
    anchor_zones=[(1, 1)],  # Middle of deep alcove
    tags={"secret", "treasure", "alcove"},
)

# =============================================================================
# IRREGULAR PLATFORM PATTERNS - L/T shaped platforms
# =============================================================================

L_PLATFORM_PATTERN = ZonePattern(
    name="l_platform",
    pattern=[
        [Z_PLAT, Z_VOID],
        [Z_PLAT, Z_PLAT],
    ],
    width=2,
    height=2,
    anchor_zones=[(0, 1), (1, 1)],
    tags={"irregular", "platforming", "l_shape"},
)

L_PLATFORM_FLIPPED = ZonePattern(
    name="l_platform_flipped",
    pattern=[
        [Z_VOID, Z_PLAT],
        [Z_PLAT, Z_PLAT],
    ],
    width=2,
    height=2,
    anchor_zones=[(0, 1), (1, 1)],
    tags={"irregular", "platforming", "l_shape"},
)

T_PLATFORM_PATTERN = ZonePattern(
    name="t_platform",
    pattern=[
        [Z_VOID, Z_PLAT, Z_VOID],
        [Z_PLAT, Z_PLAT, Z_PLAT],
    ],
    width=3,
    height=2,
    anchor_zones=[(1, 1)],  # Center of T
    tags={"irregular", "platforming", "t_shape"},
)

DIAGONAL_STAIRS_UP = ZonePattern(
    name="diagonal_stairs_up",
    pattern=[
        [Z_VOID, Z_VOID, Z_DIAGONAL],
        [Z_VOID, Z_DIAGONAL, Z_VOID],
        [Z_DIAGONAL, Z_VOID, Z_VOID],
    ],
    width=3,
    height=3,
    anchor_zones=[(1, 1)],
    tags={"platforming", "diagonal", "stairs"},
)

DIAGONAL_STAIRS_DOWN = ZonePattern(
    name="diagonal_stairs_down",
    pattern=[
        [Z_DIAGONAL, Z_VOID, Z_VOID],
        [Z_VOID, Z_DIAGONAL, Z_VOID],
        [Z_VOID, Z_VOID, Z_DIAGONAL],
    ],
    width=3,
    height=3,
    anchor_zones=[(1, 1)],
    tags={"platforming", "diagonal", "stairs"},
)

# =============================================================================
# FLOATING PLATFORM PATTERNS - Isolated platforms
# =============================================================================

FLOATING_PLATFORM_SINGLE = ZonePattern(
    name="floating_single",
    pattern=[[Z_FLOATING]],
    width=1,
    height=1,
    anchor_zones=[(0, 0)],
    tags={"platforming", "floating", "small"},
)

FLOATING_PLATFORM_DOUBLE = ZonePattern(
    name="floating_double",
    pattern=[[Z_FLOATING, Z_FLOATING]],
    width=2,
    height=1,
    anchor_zones=[(0, 0), (1, 0)],
    tags={"platforming", "floating", "medium"},
)

FLOATING_PLATFORM_CLUSTER = ZonePattern(
    name="floating_cluster",
    pattern=[
        [Z_VOID, Z_FLOATING, Z_VOID],
        [Z_FLOATING, Z_VOID, Z_FLOATING],
    ],
    width=3,
    height=2,
    anchor_zones=[(1, 0)],
    tags={"platforming", "floating", "cluster"},
)

# =============================================================================
# SHAFT PATTERNS - Vertical passages for wall jumping
# =============================================================================

SHAFT_VERTICAL_UP = ZonePattern(
    name="shaft_vertical_up",
    pattern=[
        [Z_SHAFT_UP, Z_SHAFT_UP],
        [Z_SHAFT_UP, Z_SHAFT_UP],
        [Z_SHAFT_UP, Z_SHAFT_UP],
    ],
    width=2,
    height=3,
    anchor_zones=[(0, 1), (1, 1)],
    tags={"vertical", "wall_jump", "shaft"},
)

SHAFT_VERTICAL_DOWN = ZonePattern(
    name="shaft_vertical_down",
    pattern=[
        [Z_SHAFT_DOWN, Z_SHAFT_DOWN],
        [Z_SHAFT_DOWN, Z_SHAFT_DOWN],
        [Z_SHAFT_DOWN, Z_SHAFT_DOWN],
    ],
    width=2,
    height=3,
    anchor_zones=[(0, 1), (1, 1)],
    tags={"vertical", "shaft", "downward"},
)

# =============================================================================
# TUNNEL PATTERNS - Horizontal narrow passages
# =============================================================================

TUNNEL_HORIZONTAL = ZonePattern(
    name="tunnel_horizontal",
    pattern=[[Z_TUNNEL, Z_TUNNEL, Z_TUNNEL]],
    width=3,
    height=1,
    anchor_zones=[(1, 0)],
    tags={"horizontal", "tunnel", "crouch"},
)

TUNNEL_LOW = ZonePattern(
    name="tunnel_low",
    pattern=[[Z_TUNNEL, Z_TUNNEL]],
    width=2,
    height=1,
    anchor_zones=[(0, 0), (1, 0)],
    tags={"horizontal", "tunnel", "crouch", "tutorial"},
)

# =============================================================================
# FLUID POOL PATTERNS - Water/lava hazards
# =============================================================================

WATER_POOL_2X2 = ZonePattern(
    name="water_pool_2x2",
    pattern=[
        [Z_FLUID_SURFACE, Z_FLUID_SURFACE],
        [Z_WATER_POOL, Z_WATER_POOL],
    ],
    width=2,
    height=2,
    anchor_zones=[(0, 0), (1, 0)],  # Surface level
    tags={"fluid", "water", "safe"},
)

WATER_POOL_3X2 = ZonePattern(
    name="water_pool_3x2",
    pattern=[
        [Z_FLUID_SURFACE, Z_FLUID_SURFACE, Z_FLUID_SURFACE],
        [Z_WATER_POOL, Z_WATER_POOL, Z_WATER_POOL],
    ],
    width=3,
    height=2,
    anchor_zones=[(1, 0)],
    tags={"fluid", "water", "safe", "large"},
)

LAVA_POOL_SMALL = ZonePattern(
    name="lava_pool_small",
    pattern=[
        [Z_FLUID_SURFACE, Z_FLUID_SURFACE],
        [Z_LAVA_POOL, Z_LAVA_POOL],
    ],
    width=2,
    height=2,
    anchor_zones=[],  # No anchors in lava
    tags={"fluid", "lava", "hazard", "danger"},
)

LAVA_MOAT = ZonePattern(
    name="lava_moat",
    pattern=[[Z_LAVA_POOL, Z_LAVA_POOL, Z_LAVA_POOL]],
    width=3,
    height=1,
    anchor_zones=[],
    tags={"fluid", "lava", "hazard", "moat"},
)

WATER_PIT_DEEP = ZonePattern(
    name="water_pit_deep",
    pattern=[
        [Z_FLUID_SURFACE, Z_FLUID_SURFACE],
        [Z_WATER_POOL, Z_WATER_POOL],
        [Z_WATER_POOL, Z_WATER_POOL],
    ],
    width=2,
    height=3,
    anchor_zones=[(0, 0), (1, 0)],
    tags={"fluid", "water", "pit", "deep"},
)

# =============================================================================
# ALL PATTERNS - Organized by category
# =============================================================================

CHAMBER_PATTERNS = [CHAMBER_3X3, CHAMBER_4X3, CHAMBER_5X5]

ALCOVE_PATTERNS = [ALCOVE_SMALL, ALCOVE_DEEP]

PLATFORM_PATTERNS = [
    L_PLATFORM_PATTERN,
    L_PLATFORM_FLIPPED,
    T_PLATFORM_PATTERN,
    DIAGONAL_STAIRS_UP,
    DIAGONAL_STAIRS_DOWN,
]

FLOATING_PATTERNS = [
    FLOATING_PLATFORM_SINGLE,
    FLOATING_PLATFORM_DOUBLE,
    FLOATING_PLATFORM_CLUSTER,
]

SHAFT_PATTERNS = [SHAFT_VERTICAL_UP, SHAFT_VERTICAL_DOWN]

TUNNEL_PATTERNS = [TUNNEL_HORIZONTAL, TUNNEL_LOW]

WATER_PATTERNS = [WATER_POOL_2X2, WATER_POOL_3X2, WATER_PIT_DEEP]

LAVA_PATTERNS = [LAVA_POOL_SMALL, LAVA_MOAT]

# All patterns combined
ALL_PATTERNS = (
    CHAMBER_PATTERNS
    + ALCOVE_PATTERNS
    + PLATFORM_PATTERNS
    + FLOATING_PATTERNS
    + SHAFT_PATTERNS
    + TUNNEL_PATTERNS
    + WATER_PATTERNS
    + LAVA_PATTERNS
)


def get_patterns_by_tag(tag: str) -> List[ZonePattern]:
    """
    Get all patterns with a specific tag

    Args:
        tag: Tag to search for

    Returns:
        List of patterns with that tag
    """
    return [p for p in ALL_PATTERNS if tag in p.tags]


def get_patterns_for_room_type(room_type: str) -> List[ZonePattern]:
    """
    Get recommended patterns for a room type

    Args:
        room_type: Room type name (e.g., "combat", "platform", "treasure")

    Returns:
        List of appropriate patterns for that room type
    """
    mappings = {
        "combat": CHAMBER_PATTERNS + FLOATING_PATTERNS + LAVA_PATTERNS,
        "platform": PLATFORM_PATTERNS + FLOATING_PATTERNS + SHAFT_PATTERNS,
        "treasure": ALCOVE_PATTERNS + LAVA_PATTERNS[:1],  # Just small lava pool
        "boss": [CHAMBER_5X5, CHAMBER_4X3] + FLOATING_PATTERNS + LAVA_PATTERNS,
        "start": WATER_PATTERNS + TUNNEL_PATTERNS,
        "shop": ALCOVE_PATTERNS + WATER_PATTERNS,
        "exit": SHAFT_PATTERNS + CHAMBER_PATTERNS[:2],  # Small/medium chambers
    }

    return mappings.get(room_type, [])
