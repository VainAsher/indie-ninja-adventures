"""
Hazard Spawning System - Intelligent hazard placement

Features:
- Room-type-specific hazard rules
- Zone-aware placement (avoid WALK zones, prefer PLAT/VOID)
- Density controls per room type
- Multiple hazard types with varied behavior
- Balanced difficulty progression

Hazard Types:
- Spikes: Ground-based contact damage
- Ceiling Spikes: Overhead threats
- Fire Pits: Area denial hazards
- Saw Blades: Moving hazards (future)
"""

import random

from entities.hazards import HazardManager
from systems.room_generation import (
    TILE_PLATFORM,
    TILE_PLATFORM_FALLING,
    TILE_PLATFORM_MOVING,
    TILE_SOLID,
    TILES_PER_ZONE,
)
from systems.world_generation import RoomNode


class HazardSpawnConfig:
    """Configuration for hazard spawning in a room type"""

    def __init__(
        self,
        spike_density: tuple[int, int] = (0, 0),  # Min/max spikes
        ceiling_spike_density: tuple[int, int] = (0, 0),  # Min/max ceiling spikes
        fire_pit_density: tuple[int, int] = (0, 0),  # Min/max fire pits
        avoid_spawn_radius: int = 320,  # Pixels to avoid spawn point
        avoid_exit_radius: int = 160,  # Pixels to avoid exit (≈5 tiles)
        platform_spike_chance: float = 0.0,  # Chance to put spike on platform
        ground_spike_chance: float = 0.0,  # Chance to put spike on ground
        ceiling_spike_chance: float = 0.0,  # Chance for ceiling spikes
        clustering: bool = False,  # Whether to cluster hazards
    ):
        self.spike_density = spike_density
        self.ceiling_spike_density = ceiling_spike_density
        self.fire_pit_density = fire_pit_density
        self.avoid_spawn_radius = avoid_spawn_radius
        self.avoid_exit_radius = avoid_exit_radius
        self.platform_spike_chance = platform_spike_chance
        self.ground_spike_chance = ground_spike_chance
        self.ceiling_spike_chance = ceiling_spike_chance
        self.clustering = clustering


# Room type -> hazard configuration
HAZARD_CONFIGS: dict[str, HazardSpawnConfig] = {
    "start": HazardSpawnConfig(
        spike_density=(0, 1),  # Very safe, maybe 1 tutorial spike
        avoid_spawn_radius=640,  # Large safe zone
    ),
    "combat": HazardSpawnConfig(
        spike_density=(4, 8),
        ceiling_spike_density=(1, 3),
        fire_pit_density=(1, 2),
        platform_spike_chance=0.15,
        ground_spike_chance=0.25,
        ceiling_spike_chance=0.10,
        clustering=True,
    ),
    "platform": HazardSpawnConfig(
        spike_density=(3, 6),
        platform_spike_chance=0.20,  # More platform hazards
        ground_spike_chance=0.15,
        ceiling_spike_chance=0.05,
        fire_pit_density=(1, 2),
    ),
    "treasure": HazardSpawnConfig(
        spike_density=(2, 5),
        fire_pit_density=(1, 2),
        ground_spike_chance=0.20,
        clustering=True,  # Protect treasure with clustered hazards
    ),
    "boss": HazardSpawnConfig(
        spike_density=(6, 12),
        ceiling_spike_density=(2, 4),
        fire_pit_density=(2, 3),
        platform_spike_chance=0.10,
        ground_spike_chance=0.30,
        ceiling_spike_chance=0.15,
        avoid_spawn_radius=480,  # Give player room to move
        avoid_exit_radius=320,
    ),
    "shop": HazardSpawnConfig(
        spike_density=(0, 0),  # Shops are safe zones
    ),
    "exit": HazardSpawnConfig(
        spike_density=(1, 3),
        ground_spike_chance=0.10,
        fire_pit_density=(0, 1),
        avoid_exit_radius=320,  # Keep exit area safe
    ),
}


class HazardSpawner:
    """
    Intelligent hazard spawning system.

    Responsibilities:
    - Analyze room layout and zone grid
    - Place hazards according to room type rules
    - Respect safe zones (spawn, exit)
    - Create interesting hazard patterns
    """

    def __init__(self, seed: int):
        """
        Initialize hazard spawner

        Args:
            seed: Random seed for deterministic spawning
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def spawn_hazards_for_room(
        self,
        room: RoomNode,
        hazard_manager: HazardManager,
        room_px: float,
        room_py: float,
        spawn_pos: tuple[float, float] | None = None,
        exit_pos: tuple[float, float] | None = None,
    ):
        """
        Spawn hazards for a room based on its type and layout.

        Args:
            room: Room node with zone grid
            hazard_manager: Hazard manager to spawn into
            room_px, room_py: Room position in world pixels
            spawn_pos: Player spawn position (to avoid)
            exit_pos: Exit position (to avoid)
        """
        # Get config for this room type
        config = HAZARD_CONFIGS.get(room.room_type.value, HazardSpawnConfig())

        # Reseed RNG for this room
        self.rng = random.Random(self.seed + room.grid_x * 1000 + room.grid_y)

        # Spawn different hazard types
        self._spawn_ground_spikes(
            room, hazard_manager, room_px, room_py, config, spawn_pos, exit_pos
        )
        self._spawn_ceiling_spikes(
            room, hazard_manager, room_px, room_py, config, spawn_pos, exit_pos
        )
        self._spawn_fire_pits(room, hazard_manager, room_px, room_py, config, spawn_pos, exit_pos)

    def _spawn_ground_spikes(
        self,
        room: RoomNode,
        hazard_manager: HazardManager,
        room_px: float,
        room_py: float,
        config: HazardSpawnConfig,
        spawn_pos: tuple[float, float] | None,
        exit_pos: tuple[float, float] | None,
    ):
        """Spawn ground-based spike hazards"""
        if config.spike_density == (0, 0):
            return

        num_spikes = self.rng.randint(*config.spike_density)
        from config.physics_constants import ROOM_HEIGHT_TILES, ROOM_WIDTH_TILES, TILE_SIZE

        room_width = ROOM_WIDTH_TILES * TILE_SIZE
        room_height = ROOM_HEIGHT_TILES * TILE_SIZE

        # Find valid ground positions
        ground_positions = self._find_ground_positions(room, room_px, room_py)

        if not ground_positions:
            return

        # Spawn spikes
        spawned = 0
        attempts = 0
        max_attempts = num_spikes * 10

        while spawned < num_spikes and attempts < max_attempts:
            attempts += 1

            # Pick random ground position
            x, y = self.rng.choice(ground_positions)

            # Check safe zones
            if not self._is_safe_position(x, y, spawn_pos, exit_pos, config):
                continue

            # Spawn spike
            hazard_manager.spawn_spike(x, y)
            spawned += 1

            # If clustering, spawn nearby spikes
            if config.clustering and spawned < num_spikes and self.rng.random() < 0.4:
                cluster_x = x + self.rng.randint(-64, 64)
                cluster_y = y
                if self._is_safe_position(cluster_x, cluster_y, spawn_pos, exit_pos, config):
                    hazard_manager.spawn_spike(cluster_x, cluster_y)
                    spawned += 1

    def _spawn_ceiling_spikes(
        self,
        room: RoomNode,
        hazard_manager: HazardManager,
        room_px: float,
        room_py: float,
        config: HazardSpawnConfig,
        spawn_pos: tuple[float, float] | None,
        exit_pos: tuple[float, float] | None,
    ):
        """Spawn ceiling spike hazards (inverted spikes)"""
        if config.ceiling_spike_density == (0, 0):
            return

        num_spikes = self.rng.randint(*config.ceiling_spike_density)
        from config.physics_constants import ROOM_HEIGHT_TILES, ROOM_WIDTH_TILES, TILE_SIZE

        room_width = ROOM_WIDTH_TILES * TILE_SIZE
        room_height = ROOM_HEIGHT_TILES * TILE_SIZE

        # Find ceiling positions (tiles with solid above and air below)
        ceiling_positions = self._find_ceiling_positions(room, room_px, room_py)

        if not ceiling_positions:
            return

        # Spawn ceiling spikes
        spawned = 0
        attempts = 0
        max_attempts = num_spikes * 10

        while spawned < num_spikes and attempts < max_attempts:
            attempts += 1

            x, y = self.rng.choice(ceiling_positions)

            if not self._is_safe_position(x, y, spawn_pos, exit_pos, config):
                continue

            # Spawn ceiling spike (we'll need to add this to HazardManager)
            # For now, just spawn regular spike
            hazard_manager.spawn_spike(x, y)
            spawned += 1

    def _spawn_fire_pits(
        self,
        room: RoomNode,
        hazard_manager: HazardManager,
        room_px: float,
        room_py: float,
        config: HazardSpawnConfig,
        spawn_pos: tuple[float, float] | None,
        exit_pos: tuple[float, float] | None,
    ):
        """Spawn fire pit hazards"""
        if config.fire_pit_density == (0, 0):
            return

        num_pits = self.rng.randint(*config.fire_pit_density)

        # Find VOID zones (pits) to convert to poison
        void_positions = self._find_void_positions(room, room_px, room_py)

        if not void_positions:
            return

        for x, y in void_positions:
            if not self._is_safe_position(x, y, spawn_pos, exit_pos, config):
                continue
            # Span entire zone (8x8 tiles)
            size_px = TILES_PER_ZONE * 32
            hazard_manager.spawn_poison(x, y, size_px, size_px)

    def _find_ground_positions(
        self, room: RoomNode, room_px: float, room_py: float
    ) -> list[tuple[float, float]]:
        """Find valid ground positions for spike placement"""
        positions = []

        if not room.tilemap:
            return positions

        # Scan tilemap for ground tiles (solid with air above)
        for ty in range(1, len(room.tilemap) - 1):
            for tx in range(1, len(room.tilemap[0]) - 1):
                tile = room.tilemap[ty][tx]
                tile_above = room.tilemap[ty - 1][tx]

                # Ground tile: solid with air/platform above
                if tile == TILE_SOLID and tile_above in (
                    0,
                    TILE_PLATFORM,
                    TILE_PLATFORM_FALLING,
                    TILE_PLATFORM_MOVING,
                ):
                    x = room_px + tx * 32
                    # Place spike on top of the ground tile (not inside it)
                    y = room_py + ty * 32 - 32
                    positions.append((x, y))

        # Sort positions for determinism (always same order)
        positions.sort()
        return positions

    def _find_ceiling_positions(
        self, room: RoomNode, room_px: float, room_py: float
    ) -> list[tuple[float, float]]:
        """Find valid ceiling positions for ceiling spikes"""
        positions = []

        if not room.tilemap:
            return positions

        # Scan tilemap for ceiling tiles (solid with air below)
        for ty in range(1, len(room.tilemap) - 1):
            for tx in range(1, len(room.tilemap[0]) - 1):
                tile = room.tilemap[ty][tx]
                tile_below = room.tilemap[ty + 1][tx]

                # Ceiling tile: solid with air below
                if tile == TILE_SOLID and tile_below == 0:
                    x = room_px + tx * 32
                    # Hang ceiling spike from the bottom of the ceiling tile
                    y = room_py + (ty + 1) * 32
                    positions.append((x, y))

        # Sort positions for determinism (always same order)
        positions.sort()
        return positions

    def _find_void_positions(
        self, room: RoomNode, room_px: float, room_py: float
    ) -> list[tuple[float, float]]:
        """Find void/pit areas for fire pits"""
        positions = []

        if not room.zone_grid:
            return positions

        # Scan zone grid for VOID zones
        for zy in range(len(room.zone_grid)):
            for zx in range(len(room.zone_grid[0])):
                zone_role = room.zone_grid[zy][zx]

                if zone_role == "void":
                    # Convert zone coords to world pixels
                    x = room_px + zx * TILES_PER_ZONE * 32
                    y = room_py + zy * TILES_PER_ZONE * 32
                    positions.append((x, y))

        # Sort positions for determinism (always same order)
        positions.sort()
        return positions

    def _is_safe_position(
        self,
        x: float,
        y: float,
        spawn_pos: tuple[float, float] | None,
        exit_pos: tuple[float, float] | None,
        config: HazardSpawnConfig,
    ) -> bool:
        """Check if position is safe for hazard placement (not too close to spawn/exit)"""

        # Check spawn distance
        if spawn_pos:
            spawn_x, spawn_y = spawn_pos
            dist_to_spawn = ((x - spawn_x) ** 2 + (y - spawn_y) ** 2) ** 0.5
            if dist_to_spawn < config.avoid_spawn_radius:
                return False

        # Check exit distance
        if exit_pos:
            exit_x, exit_y = exit_pos
            dist_to_exit = ((x - exit_x) ** 2 + (y - exit_y) ** 2) ** 0.5
            if dist_to_exit < config.avoid_exit_radius:
                return False

        return True
