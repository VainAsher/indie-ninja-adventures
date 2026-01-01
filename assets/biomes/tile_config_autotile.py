"""
Autotile Configuration for Biomes

Maps autotile shapes to tile variants for each biome.
Since we have 197 extracted 8×8 tiles that aren't pre-organized by shape,
we'll use all tiles as variants for all shapes (creates natural variation).

Future: Manually categorize tiles by shape for more coherent autotiling.

Tile Types:
- solid: Solid ground/wall tiles (TILE_SOLID = 1)
- platform: One-way platforms (TILE_PLATFORM = 2)

Usage:
    from assets.biomes.tile_config_autotile import get_autotile_variants
    variants = get_autotile_variants('dungeon', 'solid', 'top_left')
"""

from pathlib import Path

# Tile sizes
ORIGINAL_TILE_SIZE = 8  # 8×8 pixels in tileset
GAME_TILE_SIZE = 32  # 32×32 pixels in game

# 9-slice autotile shapes
AUTOTILE_SHAPES = [
    "top_left",
    "top_mid",
    "top_right",
    "mid_left",
    "mid_mid",
    "mid_right",
    "bottom_left",
    "bottom_mid",
    "bottom_right",
]


def get_all_tiles_in_biome(biome: str) -> list[str]:
    """
    Get all tile filenames in a biome directory

    Args:
        biome: Biome name (dungeon, cave, building)

    Returns:
        List of tile filenames (sorted)
    """
    project_root = Path(__file__).parent.parent.parent
    biome_dir = project_root / "assets" / "biomes" / biome

    if not biome_dir.exists():
        return []

    # Get all PNG files
    tiles = sorted([f.name for f in biome_dir.glob("tile_*.png")])
    return tiles


def _build_autotile_config() -> dict[str, dict[str, dict[str, list[str]]]]:
    """
    Build autotile configuration from extracted tiles

    Since tiles aren't pre-organized by shape, we use all tiles
    as variants for all shapes. This creates natural variety.

    Structure:
        {biome: {tile_type: {shape: [variant1, variant2, ...]}}}

    Returns:
        Dictionary mapping biomes → tile types → shapes → variants
    """
    biomes = ["dungeon", "cave", "building"]
    config = {}

    for biome in biomes:
        all_tiles = get_all_tiles_in_biome(biome)

        if not all_tiles:
            config[biome] = {
                "solid": {shape: [] for shape in AUTOTILE_SHAPES},
                "platform": {shape: [] for shape in AUTOTILE_SHAPES},
            }
            continue

        # Split tiles between solid and platform
        # Use all tiles for solid, first 25% for platform
        solid_tiles = all_tiles
        platform_tiles = all_tiles[: len(all_tiles) // 4] if all_tiles else []

        # Assign all variants to all shapes
        config[biome] = {
            "solid": dict.fromkeys(AUTOTILE_SHAPES, solid_tiles),
            "platform": dict.fromkeys(AUTOTILE_SHAPES, platform_tiles),
        }

    return config


# Build configuration on import
AUTOTILE_CONFIG = _build_autotile_config()


def get_autotile_variants(biome: str, tile_type: str, shape: str) -> list[str]:
    """
    Get all tile variants for a specific autotile shape

    Args:
        biome: Biome name (dungeon, cave, building)
        tile_type: Tile type ('solid' or 'platform')
        shape: Autotile shape ('top_left', 'mid_mid', etc.)

    Returns:
        List of tile filenames for this shape
    """
    variants = AUTOTILE_CONFIG.get(biome, {}).get(tile_type, {}).get(shape, [])
    return variants


def get_autotile_path(
    biome: str, tile_type: str, shape: str, variant_index: int = 0
) -> Path | None:
    """
    Get path to a specific autotile variant

    Args:
        biome: Biome name
        tile_type: Tile type ('solid' or 'platform')
        shape: Autotile shape
        variant_index: Index in variant list (wraps around)

    Returns:
        Path to tile PNG, or None if not found
    """
    variants = get_autotile_variants(biome, tile_type, shape)

    if not variants:
        return None

    # Wrap index
    index = variant_index % len(variants)
    filename = variants[index]

    project_root = Path(__file__).parent.parent.parent
    return project_root / "assets" / "biomes" / biome / filename


def get_variant_count(biome: str, tile_type: str, shape: str) -> int:
    """Get number of variants available for a shape"""
    return len(get_autotile_variants(biome, tile_type, shape))


def deterministic_variant_index(x: int, y: int, seed: int, num_variants: int) -> int:
    """
    Calculate deterministic variant index from position and seed

    Uses large primes to create pseudo-random but stable selection.
    Same position + seed always returns same variant.

    Args:
        x, y: Tile position
        seed: World seed
        num_variants: Total number of variants available

    Returns:
        Variant index (0 to num_variants-1)
    """
    if num_variants == 0:
        return 0

    # Large prime numbers for good distribution
    hsh = (x * 73856093) ^ (y * 19349663) ^ (seed * 83492791)

    # Ensure positive and wrap to variant count
    return abs(hsh) % num_variants


# Print configuration stats
if __name__ == "__main__":
    print("=" * 60)
    print("AUTOTILE CONFIGURATION")
    print("=" * 60)
    print(f"Original tile size: {ORIGINAL_TILE_SIZE}×{ORIGINAL_TILE_SIZE}")
    print(f"Game tile size: {GAME_TILE_SIZE}×{GAME_TILE_SIZE}")
    print(f"Autotile shapes: {len(AUTOTILE_SHAPES)}")
    print()

    for biome in ["dungeon", "cave", "building"]:
        print(f"{biome.upper()}:")
        for tile_type in ["solid", "platform"]:
            for shape in AUTOTILE_SHAPES[:3]:  # Show first 3 shapes
                count = get_variant_count(biome, tile_type, shape)
                print(f"  {tile_type:8s} / {shape:12s}: {count:3d} variants")
            print("  ... (6 more shapes)")
        print()
