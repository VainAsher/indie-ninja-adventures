"""
Physics Capability Calculator

Calculates player movement capabilities from physics constants.
Used by level generation to ensure platforms are reachable.

This module provides dynamic calculations based on current physics values,
allowing level generation to adapt when physics constants are tweaked.
"""

import config.physics_constants as physics
from config.physics_constants import TILE_SIZE


def calculate_max_jump_height() -> float:
    """
    Calculate maximum jump height in tiles.

    Physics: v² = u² + 2as
    At apex: v=0, u=JUMP_POWER, a=-GRAVITY
    Height: h = JUMP_POWER² / (2 * GRAVITY)

    Returns:
        Max jump height in tiles
    """
    # Time to apex
    t_apex = physics.JUMP_POWER / physics.GRAVITY

    # Height (pixels): h = v*t - 0.5*g*t²
    h_pixels = physics.JUMP_POWER * t_apex - 0.5 * physics.GRAVITY * t_apex * t_apex

    # Convert to tiles
    return h_pixels / TILE_SIZE


def calculate_max_jump_distance() -> float:
    """
    Calculate maximum horizontal jump distance in tiles.

    Assumes running jump at max speed.

    Returns:
        Max jump distance in tiles (running jump)
    """
    # Total air time (up + down, symmetric for now)
    t_air = 2 * physics.JUMP_POWER / physics.GRAVITY

    # Horizontal distance = speed * time
    h_distance = physics.MAX_RUN_SPEED * t_air

    return h_distance / TILE_SIZE


def calculate_double_jump_height() -> float:
    """
    Calculate maximum height with double jump.

    Simplified calculation: first jump height + second jump from apex.

    Returns:
        Max height with double jump in tiles
    """
    # First jump height
    first_jump = calculate_max_jump_height()

    # Simplified: assume double jump from apex
    # Second jump adds additional height based on DOUBLE_JUMP_POWER
    second_jump = physics.DOUBLE_JUMP_POWER**2 / (2 * physics.GRAVITY * TILE_SIZE)

    return first_jump + second_jump


def calculate_dash_distance() -> float:
    """
    Calculate maximum dash distance in tiles.

    Returns:
        Max dash distance in tiles
    """
    return (physics.DASH_SPEED * physics.DASH_DURATION) / TILE_SIZE


def get_safe_vertical_gap() -> int:
    """
    Get safe vertical gap for platform placement (tiles).

    Includes 1-tile safety margin to ensure platforms are always reachable.

    Returns:
        Safe vertical gap in tiles (integer)
    """
    max_height = calculate_max_jump_height()
    return max(1, int(max_height) - 1)  # -1 for safety margin


def get_safe_horizontal_gap() -> int:
    """
    Get safe horizontal gap for platform placement (tiles).

    Includes 1-tile safety margin to ensure gaps are always jumpable.

    Returns:
        Safe horizontal gap in tiles (integer)
    """
    max_distance = calculate_max_jump_distance()
    return max(1, int(max_distance) - 1)  # -1 for safety margin


def validate_physics_for_generation() -> dict:
    """
    Validate current physics constants are reasonable for level generation.

    Checks if current physics allow for:
    - Minimum jump capabilities (at least 2 tiles vertical, 3 tiles horizontal)
    - Reasonable maximums (not so high that levels become trivial)

    Returns:
        Dictionary with validation results:
        {
            'valid': bool - True if no critical warnings
            'warnings': list of str - Warning messages
            'capabilities': dict - Calculated movement capabilities
        }
    """
    warnings = []

    max_jump = calculate_max_jump_height()
    max_distance = calculate_max_jump_distance()

    # Check minimums (critical for playability)
    if max_jump < 2.0:
        warnings.append(
            f"Jump height too low ({max_jump:.1f} tiles). Minimum 2.0 tiles recommended."
        )
    if max_distance < 3.0:
        warnings.append(
            f"Jump distance too low ({max_distance:.1f} tiles). Minimum 3.0 tiles recommended."
        )

    # Check maximums (balance concerns)
    if max_jump > 8.0:
        warnings.append(
            f"Jump height very high ({max_jump:.1f} tiles). May trivialize vertical challenges."
        )
    if max_distance > 12.0:
        warnings.append(
            f"Jump distance very far ({max_distance:.1f} tiles). May trivialize horizontal challenges."
        )

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "capabilities": {
            "max_jump_height": max_jump,
            "max_jump_distance": max_distance,
            "safe_vertical_gap": get_safe_vertical_gap(),
            "safe_horizontal_gap": get_safe_horizontal_gap(),
            "double_jump_height": calculate_double_jump_height(),
            "dash_distance": calculate_dash_distance(),
        },
    }


def get_physics_info_string() -> str:
    """
    Get formatted string with current physics capabilities.

    Useful for debugging and display.

    Returns:
        Formatted string with all capabilities
    """
    caps = validate_physics_for_generation()["capabilities"]

    return (
        f"Physics Capabilities:\n"
        f"  Max Jump Height: {caps['max_jump_height']:.2f} tiles\n"
        f"  Max Jump Distance: {caps['max_jump_distance']:.2f} tiles\n"
        f"  Double Jump Height: {caps['double_jump_height']:.2f} tiles\n"
        f"  Dash Distance: {caps['dash_distance']:.2f} tiles\n"
        f"  Safe Vertical Gap: {caps['safe_vertical_gap']} tiles\n"
        f"  Safe Horizontal Gap: {caps['safe_horizontal_gap']} tiles"
    )
