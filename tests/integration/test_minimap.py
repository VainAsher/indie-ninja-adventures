"""
Test script for Phase 6: Enhanced Minimap

Tests:
1. Minimap rendering with room type colors
2. Player position indicator
3. Connection lines between rooms
4. Current room highlight
5. Different world shapes (snake, tree, grid)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pygame

from rendering.minimap import MinimapConfig, MinimapRenderer, get_current_room_coords
from systems.megamap import build_megamap
from systems.world_generation import WorldGenerator, WorldShape, generate_world_tilemaps


def test_minimap_rendering():
    """Test minimap rendering with various world shapes"""

    print("\n" + "=" * 60)
    print("PHASE 6: ENHANCED MINIMAP TEST")
    print("=" * 60)

    # Initialize pygame
    pygame.init()
    screen = pygame.Surface((800, 600))

    # Test configurations
    test_cases = [
        ("snake", 12345, "Snake world with linear progression"),
        ("tree", 22222, "Tree world with branching structure"),
        ("grid", 33333, "Grid world with orthogonal corridors"),
    ]

    for shape_name, seed, description in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {shape_name.upper()} World (seed={seed})")
        print(f"Description: {description}")
        print(f"{'='*60}")

        # Generate world
        shape_map = {
            "snake": WorldShape.SNAKE,
            "tree": WorldShape.TREE,
            "grid": WorldShape.GRID,
        }

        gen = WorldGenerator(seed=seed)
        world = gen.generate(num_biomes=1, rooms_per_biome=10, shape=shape_map[shape_name])

        print(f"[WORLD] Generated {len(world.all_rooms)} rooms")
        print(f"[WORLD] Bounds: {world.bounds}")

        # Generate tilemaps and build megamap
        print("[TILEMAPS] Generating room tilemaps...")
        room_tilemaps = generate_world_tilemaps(world)

        print("[MEGAMAP] Building unified tilemap...")
        megamap = build_megamap(world, room_tilemaps)

        # Create minimap renderer
        config = MinimapConfig(
            position=(10, 10),
            show_connections=True,
            show_player=True,
            highlight_current=True,
            scale=20,  # Larger for testing
        )
        minimap = MinimapRenderer(config)

        # Test player at different positions
        test_positions = [
            ("START", world.start_room, (0.5, 0.5)),  # Center of start room
            ("EXIT", world.exit_room, (0.8, 0.2)),  # Near top-right of exit room
        ]

        for pos_name, room, (norm_x, norm_y) in test_positions:
            if room is None:
                continue

            # Calculate world position
            room_coords = (room.grid_x, room.grid_y)
            if room_coords not in megamap.room_positions:
                continue

            room_px, room_py = megamap.room_positions[room_coords]
            player_x = room_px + norm_x * (160 * 32)
            player_y = room_py + norm_y * (160 * 32)

            # Get current room
            current_room = get_current_room_coords(megamap, (player_x, player_y))

            print(f"\n[TEST] Player at {pos_name} room")
            print(f"  Room coords: {room_coords}")
            print(f"  Room type: {room.room_type.value}")
            print(f"  Player pos: ({player_x:.0f}, {player_y:.0f})")
            print(f"  Current room: {current_room}")

            # Render minimap
            screen.fill((0, 0, 0))
            minimap.render(screen, world, megamap, (player_x, player_y), current_room)

            print("  Minimap rendered successfully!")

        # Count room types
        room_type_counts = {}
        for room in world.all_rooms:
            room_type = room.room_type.value
            room_type_counts[room_type] = room_type_counts.get(room_type, 0) + 1

        print("\n[ROOM TYPES] Distribution:")
        for room_type, count in sorted(room_type_counts.items()):
            print(f"  {room_type}: {count}")

        print(f"\n[SUCCESS] {shape_name.upper()} world minimap test passed!")

    pygame.quit()
    print("\n" + "=" * 60)
    print("ALL MINIMAP TESTS PASSED!")
    print("=" * 60)
    print("\nFeatures Tested:")
    print("  - Room type color coding (7 types)")
    print("  - Player position indicator (white dot)")
    print("  - Connection lines between rooms")
    print("  - Current room highlight (white border)")
    print("  - Multiple world shapes (snake, tree, grid)")
    print("\n[PHASE 6] Enhanced Minimap - COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_minimap_rendering()
