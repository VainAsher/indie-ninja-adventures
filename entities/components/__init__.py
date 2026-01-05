"""
Components package exports.

Provides access to reusable components implemented in entity_components.py and
helper modules inside this package.
"""

# Re-export core components defined in entity_components.py
from ..entity_components import (
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
