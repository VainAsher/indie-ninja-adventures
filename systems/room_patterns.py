"""
Room Patterns - Room Type to Zone Pattern Mapping

Defines which zone patterns are used for each room type,
with probabilities for procedural variety.

This system allows different room types to have distinct visual
and gameplay characteristics through pattern-based generation.
"""

from systems.world_generation import RoomType
from systems.zone_patterns import (
    ALCOVE_DEEP,
    ALCOVE_SMALL,
    CHAMBER_3X3,
    CHAMBER_4X3,
    CHAMBER_5X5,
    DIAGONAL_STAIRS_DOWN,
    DIAGONAL_STAIRS_UP,
    FLOATING_PLATFORM_CLUSTER,
    FLOATING_PLATFORM_DOUBLE,
    FLOATING_PLATFORM_SINGLE,
    L_PLATFORM_FLIPPED,
    L_PLATFORM_PATTERN,
    LAVA_MOAT,
    LAVA_POOL_SMALL,
    SHAFT_VERTICAL_DOWN,
    SHAFT_VERTICAL_UP,
    T_PLATFORM_PATTERN,
    TUNNEL_HORIZONTAL,
    TUNNEL_LOW,
    WATER_PIT_DEEP,
    WATER_POOL_2X2,
    WATER_POOL_3X2,
    ZonePattern,
)

# Room type -> [(pattern, probability)]
# Probabilities can exceed 1.0 since multiple patterns can be placed per room
ROOM_ZONE_PATTERNS: dict[RoomType, list[tuple[ZonePattern, float]]] = {
    # Combat rooms: Arenas, floating platforms for dodging, lava hazards
    RoomType.COMBAT: [
        (CHAMBER_3X3, 0.30),  # Combat arenas
        (CHAMBER_4X3, 0.15),  # Larger arenas
        (FLOATING_PLATFORM_SINGLE, 0.40),  # Platforming during combat
        (FLOATING_PLATFORM_DOUBLE, 0.25),  # More platforms
        (LAVA_POOL_SMALL, 0.10),  # Hazard challenge
        (LAVA_MOAT, 0.08),  # Area denial
    ],
    # Platform rooms: Lots of irregular platforms, shafts, stairs
    RoomType.PLATFORM: [
        (L_PLATFORM_PATTERN, 0.20),
        (L_PLATFORM_FLIPPED, 0.20),
        (T_PLATFORM_PATTERN, 0.20),
        (DIAGONAL_STAIRS_UP, 0.30),
        (DIAGONAL_STAIRS_DOWN, 0.20),
        (SHAFT_VERTICAL_UP, 0.20),
        (SHAFT_VERTICAL_DOWN, 0.15),
        (FLOATING_PLATFORM_CLUSTER, 0.30),
        (FLOATING_PLATFORM_DOUBLE, 0.25),
    ],
    # Treasure rooms: Alcoves for secrets, lava moats for protection
    RoomType.TREASURE: [
        (ALCOVE_SMALL, 0.60),  # Hidden treasure nook
        (ALCOVE_DEEP, 0.40),  # Deeper secret
        (LAVA_MOAT, 0.20),  # Protection hazard
        (LAVA_POOL_SMALL, 0.10),  # Small hazard
        (WATER_POOL_2X2, 0.15),  # Safe fluid (aesthetic)
    ],
    # Boss rooms: Large arenas, floating platforms for dodging, hazards
    RoomType.BOSS: [
        (CHAMBER_5X5, 1.0),  # Large arena (always)
        (CHAMBER_4X3, 0.30),  # Additional structure
        (FLOATING_PLATFORM_DOUBLE, 0.50),  # Dodging platforms
        (FLOATING_PLATFORM_CLUSTER, 0.40),  # More dodging space
        (LAVA_POOL_SMALL, 0.30),  # Arena hazards
        (LAVA_MOAT, 0.20),  # Perimeter hazard
    ],
    # Start rooms: Safe aesthetic features, tutorial elements
    RoomType.START: [
        (WATER_POOL_2X2, 0.20),  # Safe aesthetic
        (WATER_POOL_3X2, 0.10),  # Larger pool
        (TUNNEL_LOW, 0.15),  # Tutorial crouch
        (FLOATING_PLATFORM_SINGLE, 0.20),  # Tutorial jump
    ],
    # Shop rooms: Alcoves for booth, safe water features
    RoomType.SHOP: [
        (ALCOVE_SMALL, 0.60),  # Shop booth
        (WATER_POOL_2X2, 0.10),  # Decoration
        (FLOATING_PLATFORM_SINGLE, 0.15),  # Display platforms
    ],
    # Exit rooms: Shafts to climb, chambers for final room feel
    RoomType.EXIT: [
        (SHAFT_VERTICAL_UP, 0.50),  # Climb to exit
        (CHAMBER_3X3, 0.40),  # Final room chamber
        (DIAGONAL_STAIRS_UP, 0.30),  # Ascension
        (FLOATING_PLATFORM_DOUBLE, 0.20),  # Final platforming
    ],
}


def get_patterns_for_room(room_type: RoomType) -> list[tuple[ZonePattern, float]]:
    """
    Get zone patterns and probabilities for a room type

    Args:
        room_type: The type of room

    Returns:
        List of (pattern, probability) tuples
    """
    return ROOM_ZONE_PATTERNS.get(room_type, [])


def should_place_pattern(probability: float, rng) -> bool:
    """
    Determine if pattern should be placed based on probability

    Args:
        probability: Placement probability (0.0-1.0+)
        rng: Random number generator

    Returns:
        True if pattern should be placed
    """
    return rng.random() < probability
