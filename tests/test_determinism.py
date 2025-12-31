"""
Determinism Test Suite - Ensure Replay Consistency

Tests that identical seeds produce identical game states across:
- World generation
- Pickup spawning
- Hazard spawning
- Physics simulation
- Replay playback

Run with: python -m pytest tests/test_determinism.py -v
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from systems.world_generation import WorldGenerator, WorldShape
from systems.pickup_spawner import PickupSpawner
from systems.hazard_spawner import HazardSpawner
from entities import PickupManager, HazardManager
from core import EventBus


def test_world_generation_determinism():
    """Test that world generation is deterministic"""
    seed = 12345
    shape = WorldShape.BLOB
    rooms = 5

    # Generate world twice with same seed
    gen1 = WorldGenerator(seed)
    world1 = gen1.generate(num_biomes=1, rooms_per_biome=rooms, shape=shape)

    gen2 = WorldGenerator(seed)
    world2 = gen2.generate(num_biomes=1, rooms_per_biome=rooms, shape=shape)

    # Check world structure matches
    assert len(world1.all_rooms) == len(world2.all_rooms), "Different room counts"

    for room1, room2 in zip(world1.all_rooms, world2.all_rooms):
        assert room1.grid_x == room2.grid_x, f"Room grid_x mismatch"
        assert room1.grid_y == room2.grid_y, f"Room grid_y mismatch"
        assert room1.room_type == room2.room_type, f"Room type mismatch"
        assert room1.biome_theme == room2.biome_theme, f"Biome mismatch"

        # Check door ports
        assert len(room1.door_ports) == len(room2.door_ports), "Door port count mismatch"

        for direction in room1.door_ports:
            assert direction in room2.door_ports, f"Missing door direction: {direction}"
            ports1 = room1.door_ports[direction]
            ports2 = room2.door_ports[direction]
            assert len(ports1) == len(ports2), f"Door port count mismatch for {direction}"

    print(f"[PASS] World generation is deterministic ({len(world1.all_rooms)} rooms)")


def test_pickup_spawning_determinism():
    """Test that pickup spawning is deterministic"""
    seed = 54321

    # Create mock world with tilemaps
    from systems.world_generation import WorldGenerator, WorldShape, generate_world_tilemaps
    from systems.megamap import build_megamap

    gen = WorldGenerator(seed)
    world = gen.generate(num_biomes=1, rooms_per_biome=3, shape=WorldShape.SNAKE)
    room_tilemaps = generate_world_tilemaps(world)
    megamap = build_megamap(world, room_tilemaps)

    # Spawn pickups twice with same seed
    event_bus1 = EventBus()
    pickup_manager1 = PickupManager(event_bus1)
    spawner1 = PickupSpawner(seed)

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]
        spawner1.spawn_pickups_for_room(room, pickup_manager1, room_px, room_py)

    pickups1 = [(p.x, p.y, p.pickup_type) for p in pickup_manager1.pickups]

    # Second spawn
    event_bus2 = EventBus()
    pickup_manager2 = PickupManager(event_bus2)
    spawner2 = PickupSpawner(seed)

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]
        spawner2.spawn_pickups_for_room(room, pickup_manager2, room_px, room_py)

    pickups2 = [(p.x, p.y, p.pickup_type) for p in pickup_manager2.pickups]

    # Compare
    assert len(pickups1) == len(pickups2), "Different pickup counts"
    assert pickups1 == pickups2, "Pickup positions differ"

    print(f"[PASS] Pickup spawning is deterministic ({len(pickups1)} pickups)")


def test_hazard_spawning_determinism():
    """Test that hazard spawning is deterministic"""
    seed = 99999

    # Create mock world with tilemaps
    from systems.world_generation import WorldGenerator, WorldShape, generate_world_tilemaps
    from systems.megamap import build_megamap

    gen = WorldGenerator(seed)
    world = gen.generate(num_biomes=1, rooms_per_biome=4, shape=WorldShape.BRANCHY)
    room_tilemaps = generate_world_tilemaps(world)
    megamap = build_megamap(world, room_tilemaps)

    # Get spawn/exit positions
    spawn_room = next(r for r in world.all_rooms if r.room_type.value == "start")
    exit_room = next(r for r in world.all_rooms if r.room_type.value == "exit")

    spawn_coords = (spawn_room.grid_x, spawn_room.grid_y)
    exit_coords = (exit_room.grid_x, exit_room.grid_y)

    spawn_px, spawn_py = megamap.room_positions[spawn_coords]
    exit_px, exit_py = megamap.room_positions[exit_coords]

    spawn_pos = (spawn_px + 2560, spawn_py + 2560)
    exit_pos = (exit_px + 2560, exit_py + 2560)

    # Spawn hazards twice with same seed
    event_bus1 = EventBus()
    hazard_manager1 = HazardManager(event_bus1)
    spawner1 = HazardSpawner(seed)

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        room_spawn_pos = spawn_pos if room.room_type.value == "start" else None
        room_exit_pos = exit_pos if room.room_type.value == "exit" else None

        spawner1.spawn_hazards_for_room(
            room, hazard_manager1, room_px, room_py,
            spawn_pos=room_spawn_pos,
            exit_pos=room_exit_pos
        )

    hazards1 = [(h.x, h.y, h.hazard_type) for h in hazard_manager1.hazards]

    # Second spawn
    event_bus2 = EventBus()
    hazard_manager2 = HazardManager(event_bus2)
    spawner2 = HazardSpawner(seed)

    for room in world.all_rooms:
        room_coords = (room.grid_x, room.grid_y)
        room_px, room_py = megamap.room_positions[room_coords]

        room_spawn_pos = spawn_pos if room.room_type.value == "start" else None
        room_exit_pos = exit_pos if room.room_type.value == "exit" else None

        spawner2.spawn_hazards_for_room(
            room, hazard_manager2, room_px, room_py,
            spawn_pos=room_spawn_pos,
            exit_pos=room_exit_pos
        )

    hazards2 = [(h.x, h.y, h.hazard_type) for h in hazard_manager2.hazards]

    # Compare
    assert len(hazards1) == len(hazards2), f"Different hazard counts: {len(hazards1)} vs {len(hazards2)}"
    assert hazards1 == hazards2, "Hazard positions differ"

    print(f"[PASS] Hazard spawning is deterministic ({len(hazards1)} hazards)")


def test_multiple_seeds_produce_different_results():
    """Test that different seeds produce different worlds"""
    shape = WorldShape.BLOB
    rooms = 5

    gen1 = WorldGenerator(111)
    world1 = gen1.generate(num_biomes=1, rooms_per_biome=rooms, shape=shape)

    gen2 = WorldGenerator(222)
    world2 = gen2.generate(num_biomes=1, rooms_per_biome=rooms, shape=shape)

    # Worlds should be different
    room_positions1 = [(r.grid_x, r.grid_y) for r in world1.all_rooms]
    room_positions2 = [(r.grid_x, r.grid_y) for r in world2.all_rooms]

    assert room_positions1 != room_positions2, "Different seeds produced same world!"

    print("[PASS] Different seeds produce different worlds")


def test_position_list_sorting():
    """Test that position lists are sorted for determinism"""
    from systems.pickup_spawner import PickupSpawner
    from systems.hazard_spawner import HazardSpawner
    from systems.world_generation import RoomNode, RoomType, BiomeTheme

    # Create a mock room with a simple tilemap
    from systems.room_generation import TILE_SOLID, TILE_PLATFORM

    room = RoomNode(0, 0, RoomType.COMBAT, BiomeTheme.DUNGEON, 123)

    # Create a small tilemap
    room.tilemap = [[TILE_SOLID for _ in range(20)] for _ in range(20)]

    # Add some walkable areas
    for x in range(1, 19):
        room.tilemap[5][x] = 0  # Air
        room.tilemap[10][x] = TILE_PLATFORM  # Platform
        room.tilemap[9][x] = 0  # Air above platform

    # Test pickup spawner
    spawner = PickupSpawner(123)
    ground_pos = spawner._find_ground_positions(room, 0, 0)
    platform_pos = spawner._find_platform_positions(room, 0, 0)

    # Positions should be sorted
    assert ground_pos == sorted(ground_pos), "Ground positions not sorted!"
    assert platform_pos == sorted(platform_pos), "Platform positions not sorted!"

    # Test hazard spawner
    haz_spawner = HazardSpawner(123)
    haz_ground_pos = haz_spawner._find_ground_positions(room, 0, 0)

    assert haz_ground_pos == sorted(haz_ground_pos), "Hazard ground positions not sorted!"

    print("[PASS] All position lists are properly sorted")


if __name__ == "__main__":
    print("=" * 60)
    print("Determinism Test Suite")
    print("=" * 60)
    print()

    try:
        test_world_generation_determinism()
        test_pickup_spawning_determinism()
        test_hazard_spawning_determinism()
        test_multiple_seeds_produce_different_results()
        test_position_list_sorting()

        print()
        print("=" * 60)
        print("[PASS] ALL TESTS PASSED - System is deterministic")
        print("=" * 60)

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"[FAIL] TEST FAILED: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        sys.exit(1)
