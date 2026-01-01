"""
Autotiling System - 3×3 Edge Detection

Determines which tile variant to use based on neighboring tiles.
Implements 9-slice autotiling for seamless terrain rendering.

Usage:
    from systems.autotiling import autotile_key
    shape = autotile_key(tilemap, x, y, TILE_SOLID)
    # Returns: "top_left", "mid_mid", "bottom_right", etc.
"""

# 9-slice shape names (matches asset structure)
SHAPES_3X3 = [
    "top_left",
    "top_mid",
    "top_right",
    "mid_left",
    "mid_mid",
    "mid_right",
    "bottom_left",
    "bottom_mid",
    "bottom_right",
]


def get_neighbors(tilemap: list[list[int]], x: int, y: int) -> tuple[int, int, int, int]:
    """
    Get tile IDs of 4-directional neighbors

    Args:
        tilemap: 2D tile array
        x, y: Tile position

    Returns:
        Tuple of (up, down, left, right) tile IDs
        Out-of-bounds returns -1 (treated as different tile)
    """
    h = len(tilemap)
    w = len(tilemap[0]) if h > 0 else 0

    # Check bounds and get neighbors
    up = tilemap[y - 1][x] if y > 0 else -1
    down = tilemap[y + 1][x] if y < h - 1 else -1
    left = tilemap[y][x - 1] if x > 0 else -1
    right = tilemap[y][x + 1] if x < w - 1 else -1

    return up, down, left, right


def autotile_key(tilemap: list[list[int]], x: int, y: int, tile_id: int) -> str:
    """
    Determine which 3×3 autotile shape to use based on neighbors

    Algorithm:
    - Check 4-directional neighbors
    - If neighbor is different tile type → edge
    - Out-of-bounds counts as different (creates edges at borders)

    Args:
        tilemap: 2D tile array
        x, y: Tile position
        tile_id: Current tile type to match against

    Returns:
        Shape key: "top_left", "mid_mid", "bottom_right", etc.

    Examples:
        # Interior tile (all neighbors same type)
        >>> autotile_key(tilemap, 5, 5, TILE_SOLID)
        "mid_mid"

        # Top-left corner (no up/left neighbors)
        >>> autotile_key(tilemap, 0, 0, TILE_SOLID)
        "top_left"

        # Top edge (no up neighbor)
        >>> autotile_key(tilemap, 5, 0, TILE_SOLID)
        "top_mid"
    """
    up, down, left, right = get_neighbors(tilemap, x, y)

    # Determine row (vertical edge detection)
    if up != tile_id:
        row = "top"
    elif down != tile_id:
        row = "bottom"
    else:
        row = "mid"

    # Determine column (horizontal edge detection)
    if left != tile_id:
        col = "left"
    elif right != tile_id:
        col = "right"
    else:
        col = "mid"

    return f"{row}_{col}"


def get_all_autotile_neighbors(tilemap: list[list[int]], x: int, y: int) -> dict:
    """
    Get detailed neighbor information for advanced autotiling

    Returns dictionary with neighbor tiles and diagonal corners.
    Useful for 47-tile autotiling or inner/outer corners.

    Args:
        tilemap: 2D tile array
        x, y: Tile position

    Returns:
        Dictionary with keys: up, down, left, right,
                             top_left, top_right, bottom_left, bottom_right
    """
    h = len(tilemap)
    w = len(tilemap[0]) if h > 0 else 0

    def safe_get(tx: int, ty: int) -> int:
        """Get tile with bounds checking"""
        if 0 <= ty < h and 0 <= tx < w:
            return tilemap[ty][tx]
        return -1  # Out of bounds

    return {
        # Cardinal directions
        "up": safe_get(x, y - 1),
        "down": safe_get(x, y + 1),
        "left": safe_get(x - 1, y),
        "right": safe_get(x + 1, y),
        # Diagonals (for advanced autotiling)
        "top_left": safe_get(x - 1, y - 1),
        "top_right": safe_get(x + 1, y - 1),
        "bottom_left": safe_get(x - 1, y + 1),
        "bottom_right": safe_get(x + 1, y + 1),
    }


def validate_shape_key(shape: str) -> bool:
    """
    Validate that a shape key is valid

    Args:
        shape: Shape key to validate

    Returns:
        True if valid shape key
    """
    return shape in SHAPES_3X3


# Mapping for tile type names
TILE_TYPE_NAMES = {
    1: "solid",  # TILE_SOLID
    2: "platform",  # TILE_PLATFORM
}


def get_tile_type_name(tile_id: int) -> str:
    """
    Get human-readable tile type name

    Args:
        tile_id: Tile ID (TILE_SOLID, TILE_PLATFORM, etc.)

    Returns:
        Tile type name for asset lookup
    """
    return TILE_TYPE_NAMES.get(tile_id, "solid")
