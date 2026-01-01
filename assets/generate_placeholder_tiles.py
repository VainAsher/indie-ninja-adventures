"""
Placeholder Tile Sprite Generator

Generates simple colored 8x8 tile sprites for world generation testing.
These will be replaced with actual artwork in Phase C (Rendering).

Usage:
    python assets/generate_placeholder_tiles.py
"""

import os

import pygame


def generate_tile_sprite(color, size=8):
    """
    Generate a simple colored square tile sprite.

    Args:
        color: RGB tuple (r, g, b)
        size: Pixel size (default 8x8)

    Returns:
        pygame.Surface with the tile
    """
    surface = pygame.Surface((size, size))
    surface.fill(color)

    # Add subtle border for visibility
    border_color = tuple(max(0, c - 40) for c in color)
    pygame.draw.rect(surface, border_color, surface.get_rect(), 1)

    return surface


def save_tile(surface, filename):
    """Save tile surface to PNG file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    pygame.image.save(surface, filename)
    print(f"Generated: {filename}")


def generate_all_tiles(base_path="assets/biomes", size=8):
    """
    Generate all placeholder tiles.

    Tile Types:
    - terrain: Solid ground (brown)
    - wall: Solid walls (dark gray)
    - platform: Semi-solid platforms (light gray)
    - door: Door connections (blue)
    - shop: Shop location (gold)
    - treasure: Loot location (yellow)
    - void: Empty space (black)
    - spawn: Player spawn (green)
    """
    pygame.init()

    tiles = {
        "terrain.png": (64, 64, 64),  # Dark Gray
        "wall.png": (139, 69, 19),  # Brown
        "platform.png": (160, 160, 160),  # Light Gray
        "door.png": (0, 0, 255),  # Blue
        "shop.png": (255, 215, 0),  # Gold
        "treasure.png": (255, 255, 0),  # Yellow
        "void.png": (0, 0, 0),  # Black
        "spawn.png": (0, 255, 0),  # Green
        "save.png": (0, 255, 255),  # Cyan
        "exit.png": (255, 0, 255),  # Magenta
    }

    # Generate for each biome theme
    biomes = ["dungeon", "cave", "building"]

    for biome in biomes:
        biome_path = os.path.join(base_path, biome)

        for tile_name, color in tiles.items():
            # Vary color slightly per biome for visual distinction
            if biome == "cave":
                # Cave: darker, more earthy tones
                adjusted_color = tuple(max(0, int(c * 0.8)) for c in color)
            elif biome == "building":
                # Building: lighter, more stone-like
                adjusted_color = tuple(min(255, int(c * 1.1)) for c in color)
            else:
                # Dungeon: standard colors
                adjusted_color = color

            surface = generate_tile_sprite(adjusted_color, size)
            filename = os.path.join(biome_path, tile_name)
            save_tile(surface, filename)

    pygame.quit()
    print(f"\n[OK] Generated {len(tiles) * len(biomes)} placeholder tiles")
    print(f"[LOCATION] {base_path}/")
    print("\nBiomes generated:")
    for biome in biomes:
        print(f"  - {biome}/ ({len(tiles)} tiles)")


if __name__ == "__main__":
    # Get script directory and navigate to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Generate 8x8 tiles
    print("Generating 8x8 placeholder tile sprites...")
    print("=" * 60)

    base_path = os.path.join(project_root, "assets", "biomes")
    generate_all_tiles(base_path, size=8)

    print("\n" + "=" * 60)
    print("Placeholder tiles ready for world generation testing!")
    print("These will be replaced with proper artwork in Phase C.")
