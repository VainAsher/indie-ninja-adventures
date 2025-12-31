"""
Tileset Extraction Tool

Extracts individual 8x8 tiles from TilesetTest.png and organizes them
by biome/theme for the game.
"""

from PIL import Image
from pathlib import Path
import os

# Source tileset
TILESET_PATH = r"C:\Users\asher\Downloads\TilesetTest.png"
OUTPUT_DIR = Path(__file__).parent / "assets" / "biomes"

# Tile dimensions
TILE_SIZE = 8

def extract_tiles(tileset_path: str, output_dir: Path):
    """
    Extract all 8x8 tiles from the tileset

    Args:
        tileset_path: Path to source tileset PNG
        output_dir: Directory to save extracted tiles
    """
    # Load tileset
    tileset = Image.open(tileset_path)
    width, height = tileset.size

    print(f"Tileset size: {width}x{height} pixels")
    print(f"Tile size: {TILE_SIZE}x{TILE_SIZE} pixels")

    # Calculate grid dimensions
    cols = width // TILE_SIZE
    rows = height // TILE_SIZE

    print(f"Grid: {cols} cols x {rows} rows = {cols * rows} tiles")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract each tile
    tiles = []
    for row in range(rows):
        for col in range(cols):
            # Calculate tile position
            x = col * TILE_SIZE
            y = row * TILE_SIZE

            # Extract tile
            tile = tileset.crop((x, y, x + TILE_SIZE, y + TILE_SIZE))

            # Check if tile is not empty (has non-transparent pixels)
            if tile.mode == 'RGBA':
                # Check for any non-transparent pixels
                pixels = list(tile.getdata())
                has_content = any(p[3] > 0 for p in pixels if len(p) == 4)
            else:
                # For non-RGBA, assume has content if not all same color
                pixels = list(tile.getdata())
                has_content = len(set(pixels)) > 1

            if has_content:
                tile_info = {
                    'row': row,
                    'col': col,
                    'image': tile,
                    'position': (x, y)
                }
                tiles.append(tile_info)

    print(f"\nFound {len(tiles)} non-empty tiles")

    # Save visual map
    print("\nTile Map (X = tile, . = empty):")
    for row in range(rows):
        line = ""
        for col in range(cols):
            has_tile = any(t['row'] == row and t['col'] == col for t in tiles)
            line += "X" if has_tile else "."
        print(f"Row {row:2d}: {line}")

    return tiles, cols, rows


def analyze_tileset_regions(tiles, cols, rows):
    """
    Analyze tileset to identify different regions/themes

    Based on visual inspection of TilesetTest.png:
    - Top rows: Dark/dungeon tiles (brown, dark gray)
    - Middle rows: Various terrain (grass, dirt, stone)
    - Bottom rows: Special tiles, decorative elements
    """
    print("\n" + "="*60)
    print("TILESET ANALYSIS")
    print("="*60)

    # Organize tiles by row groups
    regions = {
        'dungeon': [],      # Rows 0-3: Dark castle/dungeon tiles
        'cave': [],         # Rows 4-7: Earth/cave tiles
        'terrain': [],      # Rows 8-11: Grass/ground tiles
        'decorative': [],   # Rows 12+: Special/decorative tiles
    }

    for tile in tiles:
        row = tile['row']

        if row < 4:
            regions['dungeon'].append(tile)
        elif row < 8:
            regions['cave'].append(tile)
        elif row < 12:
            regions['terrain'].append(tile)
        else:
            regions['decorative'].append(tile)

    print("\nRegion distribution:")
    for region, region_tiles in regions.items():
        print(f"  {region:12s}: {len(region_tiles):3d} tiles")

    return regions


def save_tiles(regions, output_dir: Path):
    """
    Save extracted tiles organized by biome

    Args:
        regions: Dictionary of region tiles
        output_dir: Base output directory
    """
    print("\n" + "="*60)
    print("SAVING TILES")
    print("="*60)

    # Create biome directories
    biome_dirs = {
        'dungeon': output_dir / 'dungeon',
        'cave': output_dir / 'cave',
        'building': output_dir / 'building',  # Using terrain for building
    }

    for dir_path in biome_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    # Map regions to biomes
    biome_mapping = {
        'dungeon': 'dungeon',
        'cave': 'cave',
        'terrain': 'building',  # Grass/terrain tiles for building biome
    }

    saved_count = {}

    for region, biome in biome_mapping.items():
        if region not in regions:
            continue

        biome_dir = biome_dirs[biome]
        region_tiles = regions[region]

        print(f"\nSaving {biome} tiles ({len(region_tiles)} tiles)...")

        for i, tile_info in enumerate(region_tiles):
            row, col = tile_info['row'], tile_info['col']
            filename = f"tile_r{row}_c{col}.png"
            filepath = biome_dir / filename

            # Save tile
            tile_info['image'].save(filepath)

        saved_count[biome] = len(region_tiles)
        print(f"  Saved to: {biome_dir}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for biome, count in saved_count.items():
        print(f"  {biome:10s}: {count:3d} tiles")

    return saved_count


def main():
    """Main extraction process"""
    print("="*60)
    print("TILESET EXTRACTION TOOL")
    print("="*60)
    print(f"Source: {TILESET_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Extract tiles
    tiles, cols, rows = extract_tiles(TILESET_PATH, OUTPUT_DIR)

    # Analyze regions
    regions = analyze_tileset_regions(tiles, cols, rows)

    # Save organized tiles
    save_tiles(regions, OUTPUT_DIR)

    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
