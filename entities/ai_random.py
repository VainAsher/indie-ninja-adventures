"""
Deterministic Random Number Generation for AI

Provides seeded random number generation for enemy AI timing decisions.
This ensures replay accuracy while allowing natural variations between enemies.

Version: v1.0.0
"""

import random
from typing import Optional


class AIRandom:
    """
    Seeded random number generator for AI timing decisions.

    Uses Python's built-in random.Random() with deterministic seeding
    to ensure replay accuracy.
    """

    def __init__(self, seed: int):
        """
        Initialize AI random generator with seed.

        Args:
            seed: Deterministic seed for RNG
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def reset(self):
        """Reset RNG to initial seed state"""
        self.rng.seed(self.seed)

    def uniform(self, low: float, high: float) -> float:
        """
        Generate random float in range [low, high].

        Args:
            low: Minimum value (inclusive)
            high: Maximum value (inclusive)

        Returns:
            Random float in range
        """
        return self.rng.uniform(low, high)

    def randint(self, low: int, high: int) -> int:
        """
        Generate random integer in range [low, high].

        Args:
            low: Minimum value (inclusive)
            high: Maximum value (inclusive)

        Returns:
            Random integer in range
        """
        return self.rng.randint(low, high)

    def choice(self, sequence: list):
        """
        Choose random element from sequence.

        Args:
            sequence: List to choose from

        Returns:
            Random element from list
        """
        return self.rng.choice(sequence)

    def random(self) -> float:
        """
        Generate random float in range [0.0, 1.0).

        Returns:
            Random float
        """
        return self.rng.random()


# ============================================================
# AI Timing Helper Functions
# ============================================================

def get_varied_patrol_wait(ai_random: Optional[AIRandom], base_time: float = 1.0) -> float:
    """
    Get varied patrol wait time for natural behavior.

    Args:
        ai_random: AI random generator (None uses fixed time)
        base_time: Base wait time in seconds

    Returns:
        Wait time with ±30% variation
    """
    if ai_random is None:
        return base_time

    # Vary wait time by ±30%
    return ai_random.uniform(base_time * 0.7, base_time * 1.3)


def get_varied_chase_interval(ai_random: Optional[AIRandom], base_interval: float = 0.5) -> float:
    """
    Get varied chase update interval for natural tracking.

    Args:
        ai_random: AI random generator (None uses fixed interval)
        base_interval: Base interval in seconds

    Returns:
        Interval with ±20% variation
    """
    if ai_random is None:
        return base_interval

    # Vary interval by ±20%
    return ai_random.uniform(base_interval * 0.8, base_interval * 1.2)


def get_varied_attack_cooldown(ai_random: Optional[AIRandom], base_cooldown: float = 1.0) -> float:
    """
    Get varied attack cooldown for natural combat rhythm.

    Args:
        ai_random: AI random generator (None uses fixed cooldown)
        base_cooldown: Base cooldown in seconds

    Returns:
        Cooldown with ±15% variation
    """
    if ai_random is None:
        return base_cooldown

    # Vary cooldown by ±15%
    return ai_random.uniform(base_cooldown * 0.85, base_cooldown * 1.15)


def get_varied_idle_duration(ai_random: Optional[AIRandom], base_duration: float = 1.0) -> float:
    """
    Get varied idle duration before patrol starts.

    Args:
        ai_random: AI random generator (None uses fixed duration)
        base_duration: Base idle duration in seconds

    Returns:
        Duration with ±40% variation
    """
    if ai_random is None:
        return base_duration

    # Vary duration by ±40% (wider range for more variety)
    return ai_random.uniform(base_duration * 0.6, base_duration * 1.4)


# ============================================================
# Seed Derivation
# ============================================================

def derive_ai_seed(base_seed: int, enemy_id: str) -> int:
    """
    Derive deterministic AI seed from base seed and enemy ID.

    Args:
        base_seed: Level or world seed
        enemy_id: Unique enemy identifier

    Returns:
        Deterministic AI seed
    """
    import hashlib

    # Combine base seed and enemy ID
    seed_string = f"{base_seed}:ai:{enemy_id}"
    hash_bytes = hashlib.sha256(seed_string.encode()).digest()

    # Convert first 4 bytes to int
    return int.from_bytes(hash_bytes[:4], byteorder='big', signed=False)
