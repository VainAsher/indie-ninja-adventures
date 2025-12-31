"""
Game entities for Vain Asher Gaming's: Indie Ninja Adventures

Entity definitions and management:
- Player entity
- Pickup entities (coins, health, collectibles)
- Hazard entities (spikes, voids)
"""

from .pickups import (
    CoinPickup,
    HealthPickup,
    CollectiblePickup,
    PickupManager,
    PickupCollectedEvent
)
from .hazards import (
    SpikeHazard,
    VoidHazard,
    HazardManager,
    PlayerDamageEvent,
    PlayerDeathEvent
)

__all__ = [
    'CoinPickup',
    'HealthPickup',
    'CollectiblePickup',
    'PickupManager',
    'PickupCollectedEvent',
    'SpikeHazard',
    'VoidHazard',
    'HazardManager',
    'PlayerDamageEvent',
    'PlayerDeathEvent',
]
