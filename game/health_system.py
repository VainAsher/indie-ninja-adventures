"""
Health System - HP, Damage, and Invincibility Frames

This module provides health management for entities with:
- Current and maximum HP tracking
- Damage calculation with defense
- Healing mechanics
- Invincibility frames (i-frames) after taking damage
- Deterministic behavior for replays

Version: v0.6.0
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HealthState:
    """
    Tracks health points, max HP, and invincibility frames.

    Invincibility frames (i-frames) prevent damage spam - after taking damage,
    the entity becomes temporarily invincible for a short duration.
    """
    current_hp: int
    max_hp: int
    invincibility_frames: int = 0  # Damage immunity after getting hit
    invincibility_duration: int = 60  # frames (~1 second at 60fps)

    def take_damage(self, damage: int, defense: int = 0) -> bool:
        """
        Apply damage to health.

        Args:
            damage: Raw damage amount
            defense: Defense stat to reduce damage

        Returns:
            True if entity died (hp reached 0), False otherwise
        """
        if self.invincibility_frames > 0:
            return False  # Invincible, no damage taken

        # Calculate effective damage (minimum 1 damage)
        effective_damage = max(1, damage - defense)
        self.current_hp = max(0, self.current_hp - effective_damage)

        # Activate invincibility frames (only if still alive)
        if self.current_hp > 0:
            self.invincibility_frames = self.invincibility_duration

        return self.current_hp == 0

    def heal(self, amount: int) -> int:
        """
        Restore health (capped at max_hp).

        Args:
            amount: HP to restore

        Returns:
            Actual amount healed (may be less if already at/near max)
        """
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp

    def increase_max_hp(self, amount: int):
        """
        Permanently increase maximum HP.
        Also restores current HP by the same amount.

        Args:
            amount: How much to increase max HP by
        """
        self.max_hp += amount
        self.current_hp += amount

    def update(self):
        """
        Update invincibility frames (call once per frame).
        """
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1

    def is_invincible(self) -> bool:
        """
        Check if currently invincible.

        Returns:
            True if invincibility frames active
        """
        return self.invincibility_frames > 0

    def is_alive(self) -> bool:
        """
        Check if entity is alive.

        Returns:
            True if current_hp > 0
        """
        return self.current_hp > 0

    def is_dead(self) -> bool:
        """
        Check if entity is dead.

        Returns:
            True if current_hp == 0
        """
        return self.current_hp == 0

    def is_full_health(self) -> bool:
        """
        Check if at maximum health.

        Returns:
            True if current_hp == max_hp
        """
        return self.current_hp >= self.max_hp

    def is_low_health(self, threshold: float = 0.25) -> bool:
        """
        Check if health is below threshold (for UI warnings).

        Args:
            threshold: Health percentage threshold (0.0-1.0)

        Returns:
            True if health below threshold
        """
        if self.max_hp == 0:
            return False
        return (self.current_hp / self.max_hp) <= threshold

    def get_health_percentage(self) -> float:
        """
        Get current health as a percentage.

        Returns:
            Health percentage (0.0-1.0)
        """
        if self.max_hp == 0:
            return 0.0
        return self.current_hp / self.max_hp

    def reset_to_full(self):
        """
        Restore to full health and clear i-frames.
        """
        self.current_hp = self.max_hp
        self.invincibility_frames = 0

    def __str__(self) -> str:
        """String representation for debugging."""
        invincible_str = " (INVINCIBLE)" if self.is_invincible() else ""
        return f"HP: {self.current_hp}/{self.max_hp}{invincible_str}"
