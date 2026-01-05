"""
Ability Progression System

Tracks expected player abilities by room depth and enforces
solvability constraints (critical path passable with baseline abilities).

This system ensures that:
1. Ability gates appear at appropriate depths
2. Critical path is always beatable with baseline abilities
3. Optional paths require advanced abilities
"""

from dataclasses import dataclass
from typing import Set


@dataclass
class AbilityTier:
    """Ability availability tier based on world progress"""

    tier: int
    min_room_depth: int  # Minimum Manhattan distance from start
    abilities: Set[str]  # Expected abilities at this tier
    gates_allowed: Set[str]  # Gate types allowed at this tier
    description: str  # Human-readable description


# Ability progression tiers
ABILITY_TIERS = [
    AbilityTier(
        tier=0,
        min_room_depth=0,
        abilities={"move", "jump"},
        gates_allowed=set(),
        description="Baseline - Start of game",
    ),
    AbilityTier(
        tier=1,
        min_room_depth=2,
        abilities={"move", "jump", "crouch"},
        gates_allowed={"gate_low_passage"},
        description="Early game - Crouch unlocked",
    ),
    AbilityTier(
        tier=2,
        min_room_depth=5,
        abilities={"move", "jump", "crouch", "double_jump"},
        gates_allowed={"gate_high_ledge", "gate_low_passage"},
        description="Mid game - Double jump unlocked",
    ),
    AbilityTier(
        tier=3,
        min_room_depth=8,
        abilities={"move", "jump", "crouch", "double_jump", "wall_jump"},
        gates_allowed={"gate_wall_shaft", "gate_high_ledge", "gate_low_passage"},
        description="Late game - Wall jump unlocked",
    ),
    AbilityTier(
        tier=4,
        min_room_depth=12,
        abilities={"move", "jump", "crouch", "double_jump", "wall_jump", "dash"},
        gates_allowed={"gate_wide_gap", "gate_wall_shaft", "gate_high_ledge", "gate_low_passage"},
        description="End game - All abilities",
    ),
]


def get_ability_tier(room_depth: int) -> AbilityTier:
    """
    Get ability tier for given room depth (Manhattan distance from origin)

    Args:
        room_depth: Distance from start room (abs(x) + abs(y))

    Returns:
        Appropriate AbilityTier for this depth
    """
    # Find highest tier where room_depth >= min_room_depth
    for tier in reversed(ABILITY_TIERS):
        if room_depth >= tier.min_room_depth:
            return tier

    # Fallback to tier 0
    return ABILITY_TIERS[0]


def can_place_gate(gate_type: str, room_depth: int) -> bool:
    """
    Check if gate type can be placed at given room depth

    Args:
        gate_type: Type of ability gate (e.g., "gate_high_ledge")
        room_depth: Distance from start room

    Returns:
        True if gate is appropriate for this depth
    """
    tier = get_ability_tier(room_depth)
    return gate_type in tier.gates_allowed


def get_required_ability(gate_type: str) -> str:
    """
    Get the ability required to pass a gate

    Args:
        gate_type: Type of ability gate

    Returns:
        Required ability name
    """
    gate_to_ability = {
        "gate_high_ledge": "double_jump",
        "gate_wall_shaft": "wall_jump",
        "gate_wide_gap": "dash",
        "gate_low_passage": "crouch",
    }

    return gate_to_ability.get(gate_type, "unknown")


def get_baseline_abilities() -> Set[str]:
    """
    Get the baseline abilities (always available)

    Returns:
        Set of baseline ability names
    """
    return ABILITY_TIERS[0].abilities.copy()


def print_progression_info():
    """Print ability progression information for debugging"""
    print("\n[ABILITY PROGRESSION] Tier Information:")
    for tier in ABILITY_TIERS:
        print(f"  Tier {tier.tier} (depth >={tier.min_room_depth}): {tier.description}")
        print(f"    Abilities: {', '.join(sorted(tier.abilities))}")
        if tier.gates_allowed:
            print(f"    Gates: {', '.join(sorted(tier.gates_allowed))}")
        else:
            print("    Gates: None (baseline)")
