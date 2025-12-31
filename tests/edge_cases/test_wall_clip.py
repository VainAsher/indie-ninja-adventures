"""Test wall clipping - player getting stuck in walls"""
import pygame
from systems.collision_system import CollisionSystem
from core.entity_system import Entity, EntityType, EntityManager
from core.state import PhysicsState
from core.event_bus import EventBus

pygame.init()

# Create collision system
event_bus = EventBus()
entity_manager = EntityManager(event_bus)
collision_system = CollisionSystem(event_bus, entity_manager)

# Create a wall
wall_tiles = [pygame.Rect(100, 500, 32, 32)]
collision_system.set_tiles(wall_tiles)

# Scenario: Player falling and moving toward wall from the side
# This should be a horizontal collision, NOT vertical
player = Entity(
    entity_id=0,
    entity_type=EntityType.PLAYER,
    physics=PhysicsState(
        x=85.0,   # Approaching wall from left
        y=505.0,  # Vertically aligned with wall
        vx=3.0,   # Moving right slowly
        vy=5.0,   # Falling
        width=20,
        height=20
    )
)

print("\n=== Test: Player falling while approaching wall from side ===")
print(f"Wall tile: {wall_tiles[0]} (x: 100-132, y: 500-532)")

player_rect = player.physics.get_rect()
tile = wall_tiles[0]

print(f"\nPlayer rect: {player_rect} (x: {player_rect.left}-{player_rect.right}, y: {player_rect.top}-{player_rect.bottom})")

if player_rect.colliderect(tile):
    overlap_x = min(player_rect.right, tile.right) - max(player_rect.left, tile.left)
    overlap_y = min(player_rect.bottom, tile.bottom) - max(player_rect.top, tile.top)
    print(f"\nCollision detected!")
    print(f"  Overlap X: {overlap_x}")
    print(f"  Overlap Y: {overlap_y}")
    print(f"  Difference: {abs(overlap_x - overlap_y)}")
    print(f"  Entity height: {player_rect.height}")

    is_horiz_basic = overlap_x < overlap_y
    print(f"\n  Basic logic: horizontal={is_horiz_basic}")

    # Current (possibly buggy) logic
    is_horiz_current = overlap_x < overlap_y
    if player.physics.vy > 0 and abs(overlap_x - overlap_y) <= player_rect.height:
        is_horiz_current = False
    print(f"  Current logic: horizontal={is_horiz_current}")

    if is_horiz_basic != is_horiz_current:
        print(f"\n  WARNING: Current logic changed classification!")
        print(f"  This will cause player to clip into wall instead of being pushed away")

print(f"\nBefore: pos=({player.physics.x}, {player.physics.y}), vel=({player.physics.vx}, {player.physics.vy})")

collision_system.check_and_resolve(player)

print(f"After:  pos=({player.physics.x}, {player.physics.y}), vel=({player.physics.vx}, {player.physics.vy})")
print(f"On ground: {player.physics.on_ground}, On wall: {player.physics.on_wall}")

# Check if player clipped into wall
player_rect_after = player.physics.get_rect()
if player_rect_after.colliderect(tile):
    print(f"\nERROR: Player is still overlapping with wall!")
    print(f"Player clipped into wall instead of being pushed away")
else:
    print(f"\nSUCCESS: Player properly separated from wall")
