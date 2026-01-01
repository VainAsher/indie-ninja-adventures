"""
Game entities for Vain Asher Gaming's: Indie Ninja Adventures

Entity definitions and management:
- Player entity
- Pickup entities (coins, health, collectibles)
- Hazard entities (spikes, voids)
"""

from .hazards import HazardManager, PlayerDamageEvent, PlayerDeathEvent, SpikeHazard, VoidHazard
from .pickups import (
    CoinPickup,
    CollectiblePickup,
    HealthPickup,
    PickupCollectedEvent,
    PickupManager,
)

__all__ = [
    "CoinPickup",
    "HealthPickup",
    "CollectiblePickup",
    "PickupManager",
    "PickupCollectedEvent",
    "SpikeHazard",
    "VoidHazard",
    "HazardManager",
    "PlayerDamageEvent",
    "PlayerDeathEvent",
]
