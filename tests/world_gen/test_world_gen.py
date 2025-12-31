"""Quick test of world generation system"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from systems.world_generation import WorldGenerator, print_world_debug

# Generate a test world
generator = WorldGenerator(seed=42)
world = generator.generate(num_biomes=3, rooms_per_biome=10)

# Print debug view
print_world_debug(world)

# Print some stats
print(f"\nDetailed Stats:")
print(f"  Total Rooms: {len(world.all_rooms)}")
print(f"  Biomes: {len(world.biomes)}")
for i, biome in enumerate(world.biomes):
    print(f"    Biome {i+1}: {biome.theme.value} ({len(biome.rooms)} rooms)")
print(f"  Start Room: ({world.start_room.grid_x}, {world.start_room.grid_y})")
print(f"  Exit Room: ({world.exit_room.grid_x}, {world.exit_room.grid_y})")
print(f"  Bounds: {world.bounds}")
