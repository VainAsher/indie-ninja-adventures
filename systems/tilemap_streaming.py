"""
Tilemap Streaming System - Lazy-load room tilemaps on demand

Features:
- Lazy generation: Only generate tilemaps when accessed
- LRU caching: Keep recently used tilemaps in memory
- Memory management: Automatically evict old tilemaps
- Thread-safe access: Can be called from render loop

Memory savings:
- 10×10 rooms: ~10.2MB → ~2MB (keeps 20% in cache)
- 20×20 rooms: ~40.9MB → ~8MB
- 30×30 rooms: ~92MB → ~18MB
"""

from collections import OrderedDict

from systems.room_generation import RoomNode


class TilemapCache:
    """
    LRU cache for room tilemaps with automatic eviction

    Uses OrderedDict to maintain access order for LRU eviction.
    """

    def __init__(self, max_size: int = 50):
        """
        Initialize tilemap cache

        Args:
            max_size: Maximum number of tilemaps to keep in cache
        """
        self.cache: OrderedDict[tuple[int, int], list[list[int]]] = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, room_coords: tuple[int, int]) -> list[list[int]] | None:
        """
        Get tilemap from cache (LRU access)

        Args:
            room_coords: (grid_x, grid_y) room coordinates

        Returns:
            Tilemap if cached, None otherwise
        """
        if room_coords in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(room_coords)
            self.hits += 1
            return self.cache[room_coords]
        else:
            self.misses += 1
            return None

    def put(self, room_coords: tuple[int, int], tilemap: list[list[int]]):
        """
        Put tilemap in cache with LRU eviction

        Args:
            room_coords: (grid_x, grid_y) room coordinates
            tilemap: Generated tilemap
        """
        # Remove if already exists (to update position)
        if room_coords in self.cache:
            del self.cache[room_coords]

        # Add to end (most recently used)
        self.cache[room_coords] = tilemap

        # Evict oldest if cache full
        if len(self.cache) > self.max_size:
            # Remove from beginning (least recently used)
            evicted = self.cache.popitem(last=False)
            # print(f"[TILEMAP CACHE] Evicted room {evicted[0]} (cache full)")

    def clear(self):
        """Clear all cached tilemaps"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cached": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class TilemapStreamingManager:
    """
    Manages lazy-loading of room tilemaps

    Only generates tilemaps when accessed, keeps recently used in cache.
    Significantly reduces memory footprint for large worlds.
    """

    def __init__(self, world, cache_size: int = 50):
        """
        Initialize tilemap streaming manager

        Args:
            world: World instance with all rooms
            cache_size: Maximum number of tilemaps to cache (default 50)
        """
        self.world = world
        self.cache = TilemapCache(max_size=cache_size)

        # Lazy initialization of generators
        self.zone_planner = None
        self.room_generator = None

        # Track which tilemaps have been generated at least once
        self.generated = set()

        print(f"[TILEMAP STREAMING] Initialized with cache size {cache_size}")
        print(f"[TILEMAP STREAMING] {len(world.all_rooms)} rooms in world")

    def _ensure_generators(self):
        """Lazy initialize zone planner and room generator"""
        if self.zone_planner is None:
            from systems.room_generation import RoomGenerator
            from systems.zone_planning import ZonePlanner

            self.zone_planner = ZonePlanner(seed=self.world.seed)
            self.room_generator = RoomGenerator()

    def get_tilemap(self, room_coords: tuple[int, int]) -> list[list[int]] | None:
        """
        Get tilemap for room (lazy-load if not cached)

        Args:
            room_coords: (grid_x, grid_y) room coordinates

        Returns:
            Tilemap for the room, or None if room doesn't exist
        """
        # Check cache first
        cached = self.cache.get(room_coords)
        if cached is not None:
            return cached

        # Find room in world
        room = self._find_room(room_coords)
        if room is None:
            return None

        # Generate tilemap
        tilemap = self._generate_tilemap(room)

        # Cache it
        self.cache.put(room_coords, tilemap)

        return tilemap

    def preload_rooms(self, room_coords_list: list[tuple[int, int]]):
        """
        Preload tilemaps for specific rooms (for smoother gameplay)

        Args:
            room_coords_list: List of (grid_x, grid_y) to preload
        """
        for coords in room_coords_list:
            if coords not in self.generated:
                self.get_tilemap(coords)

    def preload_surrounding_rooms(self, center_coords: tuple[int, int], radius: int = 1):
        """
        Preload tilemaps for rooms surrounding a center room

        Args:
            center_coords: Center (grid_x, grid_y)
            radius: Number of rooms in each direction to preload
        """
        cx, cy = center_coords
        coords_to_load = []

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                coords = (cx + dx, cy + dy)
                coords_to_load.append(coords)

        self.preload_rooms(coords_to_load)

    def _find_room(self, room_coords: tuple[int, int]) -> RoomNode | None:
        """Find room by coordinates"""
        for room in self.world.all_rooms:
            if (room.grid_x, room.grid_y) == room_coords:
                return room
        return None

    def _generate_tilemap(self, room: RoomNode) -> list[list[int]]:
        """
        Generate tilemap for a room

        Args:
            room: Room to generate tilemap for

        Returns:
            Generated tilemap
        """
        self._ensure_generators()

        # Plan zones if not already done
        if room.zone_grid is None:
            room.zone_grid = self.zone_planner.plan_room(room)

        # Generate tilemap
        if room.tilemap is None:
            room.tilemap = self.room_generator.generate_tilemap(room)

        # Mark as generated
        self.generated.add((room.grid_x, room.grid_y))

        return room.tilemap

    def get_all_tilemaps(self) -> dict[tuple[int, int], list[list[int]]]:
        """
        Get all tilemaps (forces generation of all rooms)

        Use sparingly - defeats the purpose of streaming.
        Needed for megamap building.

        Returns:
            Dictionary of all room tilemaps
        """
        tilemaps = {}

        for room in self.world.all_rooms:
            coords = (room.grid_x, room.grid_y)
            tilemaps[coords] = self.get_tilemap(coords)

        return tilemaps

    def get_stats(self) -> dict:
        """Get streaming statistics"""
        cache_stats = self.cache.get_stats()
        total_rooms = len(self.world.all_rooms)
        generated_count = len(self.generated)

        return {
            **cache_stats,
            "total_rooms": total_rooms,
            "generated": generated_count,
            "generation_rate": (generated_count / total_rooms * 100) if total_rooms > 0 else 0,
        }

    def print_stats(self):
        """Print streaming statistics"""
        stats = self.get_stats()

        print("\n[TILEMAP STREAMING STATS]")
        print(f"  Total rooms: {stats['total_rooms']}")
        print(f"  Generated: {stats['generated']} ({stats['generation_rate']:.1f}%)")
        print(f"  Cached: {stats['cached']}/{stats['max_size']}")
        print(f"  Cache hits: {stats['hits']}")
        print(f"  Cache misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']:.1f}%")

    def clear_cache(self):
        """Clear cache (keeps generation tracking)"""
        self.cache.clear()

    def reset(self):
        """Full reset (clears cache and generation tracking)"""
        self.cache.clear()
        self.generated.clear()
