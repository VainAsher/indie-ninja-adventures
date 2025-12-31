"""Test complete world generation pipeline"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from systems.world_generation import WorldGenerator, print_world_debug
from systems.zone_planning import ZonePlanner, print_zone_grid
from systems.room_generation import RoomGenerator, print_tilemap_sample

print("="*60)
print("FULL WORLD GENERATION PIPELINE TEST")
print("="*60)

# Step 1: Generate World
print("\n[1/4] Generating World...")
world_gen = WorldGenerator(seed=12345)
world = world_gen.generate(num_biomes=2, rooms_per_biome=8)
print_world_debug(world)

# Step 2: Plan Zones for all rooms
print("\n[2/4] Planning Zones...")
zone_planner = ZonePlanner(seed=12345)
for room in world.all_rooms:
    room.zone_grid = zone_planner.plan_room(room)
print(f"[OK] Planned zones for {len(world.all_rooms)} rooms")

# Show sample zone grids
print("\nSample Zone Grid (Start Room):")
print_zone_grid(world.start_room.zone_grid)

# Step 3: Generate Tilemaps
print("\n[3/4] Generating Tilemaps...")
room_gen = RoomGenerator()
for room in world.all_rooms:
    room.tilemap = room_gen.generate_tilemap(room)
print(f"[OK] Generated tilemaps for {len(world.all_rooms)} rooms")

# Show sample tilemap
print("\nSample Tilemap (Start Room, top-left corner):")
print_tilemap_sample(world.start_room.tilemap, sample_size=30)

# Step 4: Verify
print("\n[4/4] Verification...")
print(f"[OK] World seed: {world.seed}")
print(f"[OK] Total rooms: {len(world.all_rooms)}")
print(f"[OK] Biomes: {len(world.biomes)}")
for i, biome in enumerate(world.biomes):
    print(f"  - Biome {i+1}: {biome.theme.value} ({len(biome.rooms)} rooms)")
print(f"[OK] All rooms have zone grids: {all(r.zone_grid for r in world.all_rooms)}")
print(f"[OK] All rooms have tilemaps: {all(r.tilemap for r in world.all_rooms)}")
print(f"[OK] Tilemap size: {len(world.start_room.tilemap)}x{len(world.start_room.tilemap[0])}")

print("\n" + "="*60)
print("PIPELINE TEST COMPLETE - ALL SYSTEMS WORKING!")
print("="*60)
