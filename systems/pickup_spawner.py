"""
Pickup Spawning System - Intelligent coin and collectible placement

Features:
- Room-type-specific pickup densities
- Zone-aware placement (favor walkable areas)
- Breadcrumb trails between important locations
- Risk/reward positioning (near hazards)
- Collectible placement in challenging spots

Pickup Types:
- Coins: Common currency/score
- Collectibles: Optional 100% completion items
- Health: Rare health restoration
"""

import random

from entities.pickups import PickupManager
from systems.room_generation import (
    TILE_PLATFORM,
    TILE_PLATFORM_FALLING,
    TILE_PLATFORM_MOVING,
    TILE_SOLID,
)
from systems.world_generation import RoomNode


class PickupSpawnConfig:
    """Configuration for pickup spawning in a room type"""

    def __init__(
        self,
        coin_density: tuple[int, int] = (0, 0),  # Min/max coins
        collectible_count: tuple[int, int] = (0, 0),  # Min/max collectibles
        health_count: tuple[int, int] = (0, 0),  # Min/max health pickups
        coin_trail_chance: float = 0.0,  # Chance to create coin trails
        high_placement_bias: float = 0.0,  # Bias toward platforms (0.0-1.0)
        hazard_proximity_bonus: float = 0.0,  # Bonus coins near hazards
        collectible_difficulty: str = "medium",  # easy/medium/hard placement
    ):
        self.coin_density = coin_density
        self.collectible_count = collectible_count
        self.health_count = health_count
        self.coin_trail_chance = coin_trail_chance
        self.high_placement_bias = high_placement_bias
        self.hazard_proximity_bonus = hazard_proximity_bonus
        self.collectible_difficulty = collectible_difficulty


# Room type -> pickup configuration
PICKUP_CONFIGS: dict[str, PickupSpawnConfig] = {
    "start": PickupSpawnConfig(
        coin_density=(5, 10),
        coin_trail_chance=0.3,
        high_placement_bias=0.2,  # Mostly ground level
        collectible_difficulty="easy",
    ),
    "combat": PickupSpawnConfig(
        coin_density=(8, 15),
        collectible_count=(0, 1),
        health_count=(0, 1),
        high_placement_bias=0.5,  # Mixed placement
        hazard_proximity_bonus=0.3,  # Reward risk-taking
        collectible_difficulty="hard",
    ),
    "platform": PickupSpawnConfig(
        coin_density=(10, 20),
        collectible_count=(1, 2),
        coin_trail_chance=0.5,  # Guide player along platforms
        high_placement_bias=0.7,  # Favor platforms
        collectible_difficulty="medium",
    ),
    "treasure": PickupSpawnConfig(
        coin_density=(20, 35),
        collectible_count=(1, 3),
        health_count=(0, 1),
        hazard_proximity_bonus=0.4,  # High risk, high reward
        collectible_difficulty="easy",  # Reward is reaching the room
    ),
    "boss": PickupSpawnConfig(
        coin_density=(10, 15),
        health_count=(1, 2),  # More health for boss fights
        high_placement_bias=0.3,
        collectible_difficulty="medium",
    ),
    "shop": PickupSpawnConfig(
        coin_density=(3, 8),  # Some coins but not overwhelming
    ),
    "exit": PickupSpawnConfig(
        coin_density=(5, 10),
        collectible_count=(0, 1),
        collectible_difficulty="easy",
    ),
}


class PickupSpawner:
    """
    Intelligent pickup spawning system.

    Responsibilities:
    - Analyze room layout and zone grid
    - Place pickups according to room type rules
    - Create coin trails and patterns
    - Position collectibles in challenging locations
    """

    def __init__(self, seed: int):
        """
        Initialize pickup spawner

        Args:
            seed: Random seed for deterministic spawning
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def spawn_pickups_for_room(
        self,
        room: RoomNode,
        pickup_manager: PickupManager,
        room_px: float,
        room_py: float,
    ):
        """
        Spawn pickups for a room based on its type and layout.

        Args:
            room: Room node with zone grid and tilemap
            pickup_manager: Pickup manager to spawn into
            room_px, room_py: Room position in world pixels
        """
        # Get config for this room type
        config = PICKUP_CONFIGS.get(room.room_type.value, PickupSpawnConfig())

        # Reseed RNG for this room
        self.rng = random.Random(self.seed + room.grid_x * 1000 + room.grid_y)

        # Find valid spawn positions
        ground_positions = self._find_ground_positions(room, room_px, room_py)
        platform_positions = self._find_platform_positions(room, room_px, room_py)
        all_positions = ground_positions + platform_positions

        if not all_positions:
            return

        # Spawn coins
        self._spawn_coins(room, pickup_manager, config, ground_positions, platform_positions)

        # Spawn collectibles
        self._spawn_collectibles(room, pickup_manager, config, ground_positions, platform_positions)

        # Spawn health pickups
        self._spawn_health(room, pickup_manager, config, ground_positions, platform_positions)

    def _spawn_coins(
        self,
        room: RoomNode,
        pickup_manager: PickupManager,
        config: PickupSpawnConfig,
        ground_positions: list[tuple[float, float]],
        platform_positions: list[tuple[float, float]],
    ):
        """Spawn coin pickups"""
        if config.coin_density == (0, 0):
            return

        num_coins = self.rng.randint(*config.coin_density)

        # Decide position pool based on high placement bias
        if self.rng.random() < config.high_placement_bias and platform_positions:
            position_pool = platform_positions
        else:
            position_pool = ground_positions + platform_positions

        if not position_pool:
            return

        # Spawn coins
        spawned_positions = []
        for _ in range(num_coins):
            if not position_pool:
                break

            # Pick random position
            x, y = self.rng.choice(position_pool)

            # Add some variation
            x += self.rng.randint(-16, 16)
            y += self.rng.randint(-8, 8)

            pickup_manager.spawn_coin(x, y)
            spawned_positions.append((x, y))

            # Coin trails: spawn nearby coins
            if self.rng.random() < config.coin_trail_chance:
                for i in range(1, 4):
                    trail_x = x + i * 48
                    trail_y = y
                    pickup_manager.spawn_coin(trail_x, trail_y)

    def _spawn_collectibles(
        self,
        room: RoomNode,
        pickup_manager: PickupManager,
        config: PickupSpawnConfig,
        ground_positions: list[tuple[float, float]],
        platform_positions: list[tuple[float, float]],
    ):
        """Spawn collectible pickups in challenging positions"""
        if config.collectible_count == (0, 0):
            return

        num_collectibles = self.rng.randint(*config.collectible_count)

        # Choose positions based on difficulty
        if config.collectible_difficulty == "easy":
            # Ground level, safe positions
            position_pool = ground_positions
        elif config.collectible_difficulty == "medium":
            # Mix of ground and platforms
            position_pool = ground_positions + platform_positions
        else:  # hard
            # Favor platforms and high positions
            position_pool = platform_positions if platform_positions else ground_positions

        if not position_pool:
            return

        # Spawn collectibles
        for _ in range(num_collectibles):
            if not position_pool:
                break

            # Pick position from pool
            x, y = self.rng.choice(position_pool)

            # Add variation
            x += self.rng.randint(-8, 8)
            y += self.rng.randint(-8, 8)

            pickup_manager.spawn_collectible(x, y)

    def _spawn_health(
        self,
        room: RoomNode,
        pickup_manager: PickupManager,
        config: PickupSpawnConfig,
        ground_positions: list[tuple[float, float]],
        platform_positions: list[tuple[float, float]],
    ):
        """Spawn health pickups"""
        if config.health_count == (0, 0):
            return

        num_health = self.rng.randint(*config.health_count)

        # Health pickups are valuable - place in safe ground positions
        position_pool = ground_positions if ground_positions else platform_positions

        if not position_pool:
            return

        for _ in range(num_health):
            if not position_pool:
                break

            x, y = self.rng.choice(position_pool)
            pickup_manager.spawn_health(x, y)

    def _find_ground_positions(
        self, room: RoomNode, room_px: float, room_py: float
    ) -> list[tuple[float, float]]:
        """Find valid ground positions for pickup placement"""
        positions = []

        if not room.tilemap:
            return positions

        # Scan tilemap for ground tiles (solid with air above)
        # Sample every few tiles to avoid too many positions
        for ty in range(1, len(room.tilemap) - 1, 5):
            for tx in range(1, len(room.tilemap[0]) - 1, 5):
                tile = room.tilemap[ty][tx]
                tile_above = room.tilemap[ty - 1][tx]

                # Ground tile: solid with air above
                if tile == TILE_SOLID and tile_above == 0:
                    x = room_px + tx * 32
                    y = room_py + (ty - 1) * 32  # Spawn above ground
                    positions.append((x, y))

        # Sort positions for determinism (always same order)
        positions.sort()
        return positions

    def _find_platform_positions(
        self, room: RoomNode, room_px: float, room_py: float
    ) -> list[tuple[float, float]]:
        """Find valid platform positions for pickup placement"""
        positions = []

        if not room.tilemap:
            return positions

        # Scan tilemap for platforms
        for ty in range(1, len(room.tilemap) - 1, 5):
            for tx in range(1, len(room.tilemap[0]) - 1, 5):
                tile = room.tilemap[ty][tx]
                tile_above = room.tilemap[ty - 1][tx]

                # Platform with air above
                if tile in (TILE_PLATFORM, TILE_PLATFORM_FALLING, TILE_PLATFORM_MOVING) and tile_above == 0:
                    x = room_px + tx * 32
                    y = room_py + (ty - 1) * 32  # Spawn above platform
                    positions.append((x, y))

        # Sort positions for determinism (always same order)
        positions.sort()
        return positions
