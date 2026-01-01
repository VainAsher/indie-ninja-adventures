"""
Components package exports.

Provides access to reusable components implemented in components_core.py and
helper modules inside this package.
"""

# Re-export core components defined in components_core.py
from ..components_core import (
    AIComponent,
    FollowComponent,
    HealthComponent,
    PatrolComponent,
    PickupComponent,
    ProjectileComponent,
)

# Local helpers
from .enemy_movement import EnemyMovementComponent

__all__ = [
    "PickupComponent",
    "HealthComponent",
    "AIComponent",
    "PatrolComponent",
    "FollowComponent",
    "ProjectileComponent",
    "EnemyMovementComponent",
]
