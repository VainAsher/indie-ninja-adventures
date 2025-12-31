"""Test equal overlap collision - when overlap_x ≈ overlap_y"""
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

# Create a platform
platform_tiles = [pygame.Rect(200, 500, 32, 32)]
collision_system.set_tiles(platform_tiles)

# Create player with EQUAL overlaps (corner collision)
# Player needs to have overlap_x ≈ overlap_y to trigger the issue
player = Entity(
    entity_id=0,
    entity_type=EntityType.PLAYER,
    physics=PhysicsState(
        x=192.0,  # Carefully positioned for equal overlap
        y=492.0,
        vx=5.0,   # Moving right
        vy=5.0,   # Falling
        width=20,
        height=20
    )
)

print("\n=== Test: Player with EQUAL overlaps (corner collision) ===")
print("Platform tile:", platform_tiles[0])

player_rect = player.physics.get_rect()
tile = platform_tiles[0]

if player_rect.colliderect(tile):
    overlap_x = min(player_rect.right, tile.right) - max(player_rect.left, tile.left)
    overlap_y = min(player_rect.bottom, tile.bottom) - max(player_rect.top, tile.top)
    print(f"\nCollision detected!")
    print(f"  Overlap X: {overlap_x}")
    print(f"  Overlap Y: {overlap_y}")
    print(f"  Difference: {abs(overlap_x - overlap_y)}")
    is_horiz = overlap_x < overlap_y
    print(f"  Is horizontal collision: {is_horiz}")

    if abs(overlap_x - overlap_y) < 2:
        print(f"  CORNER COLLISION: Overlaps are nearly equal!")
        print(f"  This could cause ambiguous collision resolution")

print(f"\nBefore: pos=({player.physics.x}, {player.physics.y}), vel=({player.physics.vx}, {player.physics.vy})")

# Check collision
collision_system.check_and_resolve(player)

print(f"After:  pos=({player.physics.x}, {player.physics.y}), vel=({player.physics.vx}, {player.physics.vy})")
print(f"On ground: {player.physics.on_ground}")

if player.physics.vx != 5.0:
    print(f"\nJITTER: Horizontal velocity was zeroed!")
