"""Test falling player collision - check for jitter"""

import pygame

from core.entity_system import Entity, EntityManager, EntityType
from core.event_bus import EventBus
from core.state import PhysicsState
from systems.collision_system import CollisionSystem

pygame.init()

# Create collision system
event_bus = EventBus()
entity_manager = EntityManager(event_bus)
collision_system = CollisionSystem(event_bus, entity_manager)

# Create a ground tile
ground_tiles = [pygame.Rect(0, 688, 640, 32)]  # Ground at y=688
collision_system.set_tiles(ground_tiles)

# Create player falling and moving right
player = Entity(
    entity_id=0,
    entity_type=EntityType.PLAYER,
    physics=PhysicsState(
        x=100.0,
        y=670.0,  # Above ground, about to land
        vx=5.0,  # Moving right
        vy=10.0,  # Falling
        width=20,
        height=20,
    ),
)

print("\n=== Test: Player falling while moving horizontally ===")
print("Ground tile:", ground_tiles[0])
print("\nBefore collision:")
print(f"  Position: ({player.physics.x}, {player.physics.y})")
print(f"  Velocity: ({player.physics.vx}, {player.physics.vy})")
print(f"  Player rect: {player.physics.get_rect()}")

# Calculate overlaps manually
player_rect = player.physics.get_rect()
tile = ground_tiles[0]

if player_rect.colliderect(tile):
    overlap_x = min(player_rect.right, tile.right) - max(player_rect.left, tile.left)
    overlap_y = min(player_rect.bottom, tile.bottom) - max(player_rect.top, tile.top)
    print("\nCollision detected!")
    print(f"  Overlap X: {overlap_x}")
    print(f"  Overlap Y: {overlap_y}")
    print(f"  Is horizontal collision (overlap_x < overlap_y): {overlap_x < overlap_y}")
else:
    print("\nNo collision yet")

# Check collision
collision_system.check_and_resolve(player)

print("\nAfter collision:")
print(f"  Position: ({player.physics.x}, {player.physics.y})")
print(f"  Velocity: ({player.physics.vx}, {player.physics.vy})")
print(f"  On ground: {player.physics.on_ground}")

# Check if horizontal velocity was preserved
if player.physics.vx == 5.0:
    print("\nSUCCESS: Horizontal velocity preserved (no jitter)")
else:
    print(
        f"\nFAILURE: Horizontal velocity changed from 5.0 to {player.physics.vx} (jitter detected!)"
    )
