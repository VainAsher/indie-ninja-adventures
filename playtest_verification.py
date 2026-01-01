"""
Quick verification script for playtest readiness
"""

from systems.megamap import build_megamap
from systems.world_generation import RoomType, WorldGenerator, WorldShape, generate_world_tilemaps


def verify_world_generation():
    """Verify all world generation features"""

    print("=" * 70)
    print("PLAYTEST READINESS VERIFICATION")
    print("=" * 70)

    # Test configuration
    test_configs = [
        ("SNAKE", WorldShape.SNAKE, 10, 42),
        ("TREE", WorldShape.TREE, 10, 42),
        ("BLOB", WorldShape.BLOB, 10, 42),
    ]

    all_passed = True

    for shape_name, shape, rooms, seed in test_configs:
        print(f"\n[TEST] {shape_name} - {rooms} rooms (seed={seed})")
        print("-" * 70)

        # Generate world
        gen = WorldGenerator(seed=seed)
        world = gen.generate(num_biomes=1, rooms_per_biome=rooms, shape=shape)
        tilemaps = generate_world_tilemaps(world)
        megamap = build_megamap(world, tilemaps)

        # Find special rooms
        start_room = next((r for r in world.all_rooms if r.room_type == RoomType.START), None)
        exit_room = next((r for r in world.all_rooms if r.room_type == RoomType.EXIT), None)

        # Verify spawn anchor
        has_spawn = start_room and "spawn" in start_room.anchors
        if has_spawn:
            spawn_zone = start_room.anchors["spawn"][0]
            room_coords = (start_room.grid_x, start_room.grid_y)
            room_px, room_py = megamap.room_positions[room_coords]
            spawn_x = room_px + spawn_zone[0] * 320 + 160
            spawn_y = room_py + spawn_zone[1] * 320 + 160

            # Check if in bounds
            in_bounds = (room_px <= spawn_x < room_px + 5120) and (
                room_py <= spawn_y < room_py + 5120
            )

            print(f"  [OK] Spawn anchor: zone {spawn_zone} -> pixel ({spawn_x}, {spawn_y})")
            print(
                f"       Room bounds: x=[{room_px}, {room_px + 5120}], y=[{room_py}, {room_py + 5120}]"
            )
            print(f"       In bounds: {'YES' if in_bounds else 'NO'}")

            if not in_bounds:
                all_passed = False
        else:
            print("  [FAIL] No spawn anchor found!")
            all_passed = False

        # Verify exit anchor
        has_exit = exit_room and "exit" in exit_room.anchors
        if has_exit:
            exit_zone = exit_room.anchors["exit"][0]
            room_coords = (exit_room.grid_x, exit_room.grid_y)
            room_px, room_py = megamap.room_positions[room_coords]
            exit_x = room_px + exit_zone[0] * 320 + 160
            exit_y = room_py + exit_zone[1] * 320 + 160

            # Check if in bounds
            in_bounds = (room_px <= exit_x < room_px + 5120) and (
                room_py <= exit_y < room_py + 5120
            )

            print(f"  [OK] Exit anchor: zone {exit_zone} -> pixel ({exit_x}, {exit_y})")
            print(f"       In bounds: {'YES' if in_bounds else 'NO'}")

            if not in_bounds:
                all_passed = False
        else:
            print("  [FAIL] No exit anchor found!")
            all_passed = False

        # Verify megamap
        print(f"  [OK] Megamap: {megamap.width_tiles}x{megamap.height_tiles} tiles")
        print(f"  [OK] Rooms: {len(world.all_rooms)} generated")

        # Count room types
        type_counts = {}
        for room in world.all_rooms:
            room_type = room.room_type.value
            type_counts[room_type] = type_counts.get(room_type, 0) + 1

        print(f"  [OK] Room types: {', '.join(f'{k}={v}' for k, v in sorted(type_counts.items()))}")

    print("\n" + "=" * 70)
    if all_passed:
        print("[PASS] ALL TESTS PASSED - DEMO READY FOR PLAYTESTING")
    else:
        print("[FAIL] SOME TESTS FAILED - REVIEW ERRORS ABOVE")
    print("=" * 70)


if __name__ == "__main__":
    verify_world_generation()
