"""Test corner collision - player landing on platform edge"""
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

# Create a platform tile (not full width, so has edges)
platform_tiles = [pygame.Rect(200, 500, 32, 32)]  # Single tile platform
collision_system.set_tiles(platform_tiles)

# Create player falling onto the LEFT edge of platform while moving right
player = Entity(
    entity_id=0,
    entity_type=EntityType.PLAYER,
    physics=PhysicsState(
        x=195.0,  # Slightly overlapping left edge (platform is 200-232)
        y=490.0,  # Above platform, about to land
        vx=5.0,   # Moving right
        vy=5.0,   # Falling slowly
        width=20,
        height=20
    )
)

print("\n=== Test: Player landing on platform LEFT edge while moving right ===")
print("Platform tile:", platform_tiles[0])
print(f"\nBefore collision:")
print(f"  Position: ({player.physics.x}, {player.physics.y})")
print(f"  Velocity: ({player.physics.vx}, {player.physics.vy})")
player_rect = player.physics.get_rect()
print(f"  Player rect: {player_rect}")
print(f"  Player spans X: {player_rect.left} to {player_rect.right}")

# Calculate overlaps manually
tile = platform_tiles[0]

if player_rect.colliderect(tile):
    overlap_x = min(player_rect.right, tile.right) - max(player_rect.left, tile.left)
    overlap_y = min(player_rect.bottom, tile.bottom) - max(player_rect.top, tile.top)
    print(f"\nCollision detected!")
    print(f"  Overlap X: {overlap_x}")
    print(f"  Overlap Y: {overlap_y}")
    is_horiz = overlap_x < overlap_y
    print(f"  Is horizontal collision (overlap_x < overlap_y): {is_horiz}")
    if is_horiz:
        print(f"  WARNING: Will be treated as HORIZONTAL collision (should be vertical!)")
else:
    print("\nNo collision yet")

# Check collision
collision_system.check_and_resolve(player)

print(f"\nAfter collision:")
print(f"  Position: ({player.physics.x}, {player.physics.y})")
print(f"  Velocity: ({player.physics.vx}, {player.physics.vy})")
print(f"  On ground: {player.physics.on_ground}")

# Check if horizontal velocity was preserved
if player.physics.vx == 5.0:
    print(f"\nSUCCESS: Horizontal velocity preserved")
else:
    print(f"\nJITTER DETECTED: vx changed from 5.0 to {player.physics.vx}")
    print(f"This happens when landing on platform edge - overlap_x is small")
