"""
Tile Loader and Renderer

Loads tile assets from biomes, scales them from 70x70 to 32x32,
and provides cached access for rendering.

Usage:
    loader = TileLoader()
    tile_surface = loader.get_tile('dungeon', 'solid', 0)
    screen.blit(tile_surface, (x * 32, y * 32))
"""

import logging

# Import tile configuration
import sys
from pathlib import Path

import pygame
from PIL import Image

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from assets.biomes.tile_config import BIOME_TILES, GAME_TILE_SIZE, ORIGINAL_TILE_SIZE, get_tile_path
from assets.biomes.tile_config_autotile import (
    AUTOTILE_SHAPES,
    deterministic_variant_index,
    get_autotile_path,
    get_variant_count,
)
from systems.autotiling import autotile_key

logger = logging.getLogger(__name__)
# Debug info emitted at debug level to avoid noisy stdout during tests
logger.debug(
    "[TileLoader] Original=%sx%s Game=%sx%s Scale=%.3fx AutotileShapes=%s",
    ORIGINAL_TILE_SIZE,
    ORIGINAL_TILE_SIZE,
    GAME_TILE_SIZE,
    GAME_TILE_SIZE,
    GAME_TILE_SIZE / ORIGINAL_TILE_SIZE,
    len(AUTOTILE_SHAPES),
)


class TileLoader:
    """
    Tile loader with automatic scaling and caching

    Loads tiles from assets/biomes/, scales from 70x70 to 32x32,
    and caches the results for performance.

    Usage:
        loader = TileLoader()
        tile = loader.get_tile('dungeon', 'solid', 0)
        screen.blit(tile, (x * 32, y * 32))
    """

    def __init__(self, target_tile_size: int = GAME_TILE_SIZE):
        """
        Initialize tile loader

        Args:
            target_tile_size: Target size for scaled tiles (default: 32)
        """
        self.target_tile_size = target_tile_size
        self.cache: dict[tuple[str, str, int], pygame.Surface] = {}
        self.fallback_tiles: dict[tuple[str, str], pygame.Surface] = {}

        # Ensure pygame is initialized for surface creation
        if not pygame.get_init():
            pygame.init()

        # Detect headless mode (no video display initialized)
        self.headless_mode = pygame.display.get_surface() is None

    def get_tile(self, biome: str, tile_type: str, index: int = 0) -> pygame.Surface:
        """
        Get a tile surface, loading and scaling as needed

        Args:
            biome: Biome name (dungeon, cave, building)
            tile_type: Tile type (solid, platform, decorative, liquid)
            index: Index in tile list for variation

        Returns:
            pygame.Surface of the tile (scaled to target_tile_size)
        """
        # In headless mode, skip tile loading and return fallback
        if self.headless_mode:
            return self._get_fallback_tile(biome, tile_type)

        # Check cache first
        cache_key = (biome, tile_type, index)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Get tile path from config
        tile_path = get_tile_path(biome, tile_type, index)

        if tile_path is None or not tile_path.exists():
            # Create fallback tile
            return self._get_fallback_tile(biome, tile_type)

        try:
            # Load and scale tile
            tile_surface = self._load_and_scale_tile(tile_path)

            # Cache the result
            self.cache[cache_key] = tile_surface

            return tile_surface

        except Exception as e:
            print(f"Error loading tile {tile_path}: {e}")
            return self._get_fallback_tile(biome, tile_type)

    def _load_and_scale_tile(self, tile_path: Path) -> pygame.Surface:
        """
        Load PNG and scale from 70x70 to target size

        Args:
            tile_path: Path to tile PNG file

        Returns:
            Scaled pygame.Surface
        """
        # Load with PIL for high-quality scaling
        pil_image = Image.open(tile_path)

        # Scale using LANCZOS for quality
        scaled_image = pil_image.resize(
            (self.target_tile_size, self.target_tile_size), Image.LANCZOS
        )

        # Convert PIL image to pygame surface
        mode = scaled_image.mode
        size = scaled_image.size
        data = scaled_image.tobytes()

        # Create pygame surface with alpha channel
        if mode == "RGBA":
            surface = pygame.image.fromstring(data, size, mode)
        else:
            # Convert to RGBA if needed
            scaled_rgba = scaled_image.convert("RGBA")
            surface = pygame.image.fromstring(scaled_rgba.tobytes(), scaled_rgba.size, "RGBA")

        return surface.convert_alpha()

    def _get_fallback_tile(self, biome: str, tile_type: str) -> pygame.Surface:
        """
        Create colored fallback tile if asset missing

        Args:
            biome: Biome name
            tile_type: Tile type

        Returns:
            Colored pygame.Surface
        """
        fallback_key = (biome, tile_type)

        if fallback_key in self.fallback_tiles:
            return self.fallback_tiles[fallback_key]

        # Define colors by biome and type
        biome_colors = {
            "dungeon": {
                "solid": (100, 100, 120),  # Gray stone
                "platform": (139, 69, 19),  # Brown
                "decorative": (150, 100, 50),  # Bronze
                # NEW: Fluid tiles
                "water": (50, 150, 255),  # Blue water
                "lava": (255, 100, 0),  # Orange lava
                # NEW: Hazard tiles
                "ice": (150, 200, 255),  # Light blue ice
                "mud": (101, 67, 33),  # Dark brown mud
                # NEW: Interactive tiles
                "breakable": (120, 120, 120),  # Gray breakable
                "cracked": (140, 140, 140),  # Light gray cracked
                "pushable": (139, 90, 43),  # Brown wood
                "sticky": (128, 0, 128),  # Purple sticky
            },
            "cave": {
                "solid": (101, 67, 33),  # Brown earth
                "platform": (121, 87, 53),  # Light brown
                "liquid": (255, 100, 0),  # Orange lava
                # NEW: Fluid tiles
                "water": (30, 100, 180),  # Darker blue water
                "lava": (255, 100, 0),  # Orange lava
                # NEW: Hazard tiles
                "ice": (120, 180, 220),  # Cave ice
                "mud": (80, 50, 25),  # Dark mud
                # NEW: Interactive tiles
                "breakable": (90, 60, 30),  # Cave rock
                "cracked": (100, 70, 40),  # Cracked cave
                "pushable": (110, 80, 50),  # Stone block
                "sticky": (100, 50, 100),  # Cave fungus
            },
            "building": {
                "solid": (64, 64, 64),  # Dark Gray
                "platform": (160, 120, 80),  # Light wood
                "decorative": (180, 150, 100),  # Pale wood
                # NEW: Fluid tiles
                "water": (40, 120, 200),  # Clear water
                "lava": (255, 80, 20),  # Bright lava
                # NEW: Hazard tiles
                "ice": (180, 220, 255),  # Clean ice
                "mud": (90, 60, 30),  # Dirt floor
                # NEW: Interactive tiles
                "breakable": (100, 100, 100),  # Concrete
                "cracked": (120, 120, 120),  # Damaged concrete
                "pushable": (150, 120, 90),  # Wooden crate
                "sticky": (110, 70, 110),  # Tar/resin
            },
        }

        # Get color or default to gray
        color = biome_colors.get(biome, {}).get(tile_type, (128, 128, 128))

        # Create colored tile
        surface = pygame.Surface((self.target_tile_size, self.target_tile_size))
        surface.fill(color)

        # Add border for visual distinction
        border_color = tuple(min(c + 30, 255) for c in color)
        pygame.draw.rect(
            surface, border_color, (0, 0, self.target_tile_size, self.target_tile_size), 1
        )

        # Cache fallback
        self.fallback_tiles[fallback_key] = surface

        return surface

    def get_autotiled_tile(
        self,
        biome: str,
        tile_type: str,
        tilemap: list[list[int]],
        x: int,
        y: int,
        tile_id: int,
        seed: int = 0,
    ) -> pygame.Surface:
        """
        Get tile with 3×3 autotiling based on neighbors

        This is the main autotiling method that:
        1. Determines autotile shape from neighbors (top_left, mid_mid, etc.)
        2. Selects variant deterministically from position + seed
        3. Loads and caches the tile

        Args:
            biome: Biome name (dungeon, cave, building)
            tile_type: Tile type ('solid' or 'platform')
            tilemap: Full room tilemap for neighbor detection
            x, y: Tile position in tilemap
            tile_id: Tile ID (TILE_SOLID or TILE_PLATFORM)
            seed: World seed for deterministic variant selection

        Returns:
            Scaled and autotiled pygame.Surface (32×32)

        Example:
            tile = loader.get_autotiled_tile(
                biome='dungeon',
                tile_type='solid',
                tilemap=room.tilemap,
                x=10, y=5,
                tile_id=TILE_SOLID,
                seed=12345
            )
            screen.blit(tile, (x*32, y*32))
        """
        # In headless mode, skip tile loading and return fallback
        if self.headless_mode:
            return self._get_fallback_tile(biome, tile_type)

        # Determine autotile shape from neighbors
        shape = autotile_key(tilemap, x, y, tile_id)

        # Get number of variants available
        num_variants = get_variant_count(biome, tile_type, shape)

        if num_variants == 0:
            # No variants available, use fallback
            return self._get_fallback_tile(biome, tile_type)

        # Calculate deterministic variant index
        variant_idx = deterministic_variant_index(x, y, seed, num_variants)

        # Check cache
        cache_key = (biome, tile_type, shape, variant_idx, "autotile")
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Get tile path
        tile_path = get_autotile_path(biome, tile_type, shape, variant_idx)

        if tile_path is None or not tile_path.exists():
            return self._get_fallback_tile(biome, tile_type)

        try:
            # Load and scale tile
            tile_surface = self._load_and_scale_tile(tile_path)

            # Cache the result
            self.cache[cache_key] = tile_surface

            return tile_surface

        except Exception as e:
            print(f"Error loading autotile {tile_path}: {e}")
            return self._get_fallback_tile(biome, tile_type)

    def preload_biome(self, biome: str):
        """
        Preload all tiles for a biome into cache

        Args:
            biome: Biome name to preload
        """
        biome_tiles = BIOME_TILES.get(biome, {})

        for tile_type, tile_list in biome_tiles.items():
            for index in range(len(tile_list)):
                # This will load and cache the tile
                self.get_tile(biome, tile_type, index)

    def clear_cache(self):
        """Clear the tile cache to free memory"""
        self.cache.clear()
        self.fallback_tiles.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache info
        """
        return {
            "cached_tiles": len(self.cache),
            "fallback_tiles": len(self.fallback_tiles),
            "total_cached": len(self.cache) + len(self.fallback_tiles),
        }
