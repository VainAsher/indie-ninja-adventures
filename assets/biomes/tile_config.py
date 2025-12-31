"""
Tile Configuration for Biomes

Maps tile types to specific PNG files for each biome.
Original tiles are 8x8px, will be scaled to game tile size (32x32px).

Tile Types:
- TILE_SOLID (1): Solid ground/wall tiles
- TILE_PLATFORM (2): One-way platforms

Usage:
    from assets.biomes.tile_config import BIOME_TILES
    dungeon_solid = BIOME_TILES['dungeon']['solid']
"""

from pathlib import Path
from typing import List, Dict

# Tile size in original tileset
ORIGINAL_TILE_SIZE = 8

# Game tile size (used in world generation)
GAME_TILE_SIZE = 32


def get_all_tiles_in_biome(biome: str) -> List[str]:
    """
    Get all tile filenames in a biome directory

    Args:
        biome: Biome name (dungeon, cave, building)

    Returns:
        List of tile filenames
    """
    project_root = Path(__file__).parent.parent.parent
    biome_dir = project_root / 'assets' / 'biomes' / biome

    if not biome_dir.exists():
        return []

    # Get all PNG files in the biome directory
    tiles = sorted([f.name for f in biome_dir.glob('tile_*.png')])
    return tiles


# Auto-generate tile lists from extracted tiles
# Since we have 247 tiles automatically extracted and organized,
# we'll use all available tiles for each biome

def _build_biome_tiles() -> Dict[str, Dict[str, List[str]]]:
    """Build BIOME_TILES dictionary from extracted tiles"""
    biomes = ['dungeon', 'cave', 'building']
    biome_tiles = {}

    for biome in biomes:
        all_tiles = get_all_tiles_in_biome(biome)

        if not all_tiles:
            # Fallback empty lists
            biome_tiles[biome] = {
                'solid': [],
                'platform': [],
            }
            continue

        # For now, use all tiles as solid tiles
        # Can be manually categorized later if needed
        biome_tiles[biome] = {
            'solid': all_tiles,
            'platform': all_tiles[:len(all_tiles)//4] if all_tiles else [],  # Use first 25% as platforms
        }

    return biome_tiles


# Build the tile configuration
BIOME_TILES = _build_biome_tiles()

# Tile variations for visual diversity
# These will be automatically varied based on position
TILE_VARIATIONS = {
    biome: {
        'solid_var': tiles['solid'][:10] if len(tiles['solid']) >= 10 else tiles['solid'],
        'platform_var': tiles['platform'][:5] if len(tiles['platform']) >= 5 else tiles['platform'],
    }
    for biome, tiles in BIOME_TILES.items()
}


def get_tile_path(biome: str, tile_type: str, index: int = 0) -> Path:
    """
    Get path to a specific tile

    Args:
        biome: Biome name (dungeon, cave, building)
        tile_type: Type of tile (solid, platform)
        index: Index in the tile list (for variation)

    Returns:
        Path to the tile PNG file
    """
    project_root = Path(__file__).parent.parent.parent
    tiles = BIOME_TILES.get(biome, {}).get(tile_type, [])

    if not tiles:
        return None

    # Wrap index if out of bounds
    index = index % len(tiles)
    filename = tiles[index]

    return project_root / 'assets' / 'biomes' / biome / filename


def get_random_tile(biome: str, tile_type: str) -> Path:
    """Get a random tile for variety"""
    import random
    tiles = BIOME_TILES.get(biome, {}).get(tile_type, [])
    if not tiles:
        return None
    return get_tile_path(biome, tile_type, random.randint(0, len(tiles) - 1))


def list_available_tiles(biome: str) -> dict:
    """List all available tile types for a biome"""
    return BIOME_TILES.get(biome, {})


# Print tile counts on import (for debugging)
if __name__ == "__main__":
    print("="*60)
    print("TILE CONFIGURATION")
    print("="*60)
    print(f"Original tile size: {ORIGINAL_TILE_SIZE}x{ORIGINAL_TILE_SIZE}")
    print(f"Game tile size: {GAME_TILE_SIZE}x{GAME_TILE_SIZE}")
    print()

    for biome, tiles in BIOME_TILES.items():
        print(f"{biome.upper()}:")
        for tile_type, tile_list in tiles.items():
            print(f"  {tile_type:12s}: {len(tile_list):3d} tiles")
        print()
