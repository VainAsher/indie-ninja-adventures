"""Test zone planning system"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from systems.world_generation import WorldGenerator
from systems.zone_planning import ZonePlanner, print_zone_grid

# Generate a test world
print("Generating test world...")
generator = WorldGenerator(seed=42)
world = generator.generate(num_biomes=2, rooms_per_biome=5)

# Plan zones for first few rooms
planner = ZonePlanner(seed=42)

print("\n" + "=" * 60)
print("Testing Zone Planning for Different Room Types")
print("=" * 60)

# Test different room types
test_rooms = []
for room in world.all_rooms[:5]:  # First 5 rooms
    test_rooms.append(room)

for i, room in enumerate(test_rooms):
    print(f"\n--- Room {i+1}: {room.room_type.value} ({room.biome_theme.value}) ---")
    print(f"Position: ({room.grid_x}, {room.grid_y})")
    print(f"Connections: {list(room.neighbor_dirs.keys())}")
    print(f"Door Ports: {list(room.door_ports.keys())}")

    # Plan zones
    zone_grid = planner.plan_room(room)
    room.zone_grid = zone_grid  # Store it

    # Print visualization
    print_zone_grid(zone_grid)

print("\n" + "=" * 60)
print("Zone Planning Test Complete!")
print("=" * 60)
