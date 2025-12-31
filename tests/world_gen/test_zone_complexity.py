"""Test zone generation complexity with room-type-specific probabilities"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from systems.world_generation import WorldGenerator, RoomType
from systems.zone_planning import ZonePlanner, print_zone_grid, Z_PLAT, Z_FILL, Z_WALK, Z_VOID
from systems.room_generation import RoomGenerator, print_tilemap_ascii

print("="*60)
print("ZONE COMPLEXITY TEST - Room-Type-Specific Probabilities")
print("="*60)

# Generate a small world
world_gen = WorldGenerator(seed=99999)
world = world_gen.generate(num_biomes=1, rooms_per_biome=8)

# Plan zones
zone_planner = ZonePlanner(seed=99999)
for room in world.all_rooms:
    room.zone_grid = zone_planner.plan_room(room)

# Generate tilemaps
room_gen = RoomGenerator()
for room in world.all_rooms:
    room.tilemap = room_gen.generate_tilemap(room)

# Analyze zone distribution by room type
def analyze_zone_grid(grid):
    """Count zone types in grid"""
    counts = {Z_PLAT: 0, Z_FILL: 0, Z_WALK: 0, Z_VOID: 0}
    total_decor = 0

    for row in grid:
        for cell in row:
            if cell in counts:
                counts[cell] += 1
            # Count all cells for percentage
            total_decor += 1

    return counts, total_decor

print("\nROOM-TYPE ANALYSIS:")
print("-" * 60)

room_types_analyzed = set()

for room in world.all_rooms:
    if room.room_type not in room_types_analyzed:
        room_types_analyzed.add(room.room_type)

        counts, total = analyze_zone_grid(room.zone_grid)

        print(f"\n{room.room_type.value.upper()} Room:")
        print_zone_grid(room.zone_grid)

        print(f"Zone Distribution (out of 25 zones):")
        print(f"  PLATFORM: {counts[Z_PLAT]:2d} ({counts[Z_PLAT]/25*100:5.1f}%)")
        print(f"  FILL:     {counts[Z_FILL]:2d} ({counts[Z_FILL]/25*100:5.1f}%)")
        print(f"  WALK:     {counts[Z_WALK]:2d} ({counts[Z_WALK]/25*100:5.1f}%)")
        print(f"  VOID:     {counts[Z_VOID]:2d} ({counts[Z_VOID]/25*100:5.1f}%)")

        # Show tilemap preview
        print("\nTilemap Preview:")
        print_tilemap_ascii(room.tilemap, scale=4)

print("\n" + "="*60)
print("EXPECTED PROBABILITIES (from source):")
print("-" * 60)
print("PLATFORM rooms: 55% plat, 22% fill, 22% walk")
print("COMBAT rooms:   45% plat, 14% fill, 22% walk")
print("TREASURE rooms: 35% plat, 10% fill, 22% walk")
print("BOSS rooms:     30% plat, 12% fill, 22% walk")
print("Default rooms:  25% plat,  8% fill, 22% walk")
print("="*60)
