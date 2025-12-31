"""Test falling into wall corner - should not jitter"""
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

# Create a wall tile
wall_tiles = [pygame.Rect(60, 600, 32, 32)]
collision_system.set_tiles(wall_tiles)

# Create player falling onto the TOP-LEFT corner of wall while moving right
# This is the scenario that would cause jitter
player = Entity(
    entity_id=0,
    entity_type=EntityType.PLAYER,
    physics=PhysicsState(
        x=50.0,   # Moving toward wall
        y=595.0,  # Above wall top
        vx=5.0,   # Moving right
        vy=10.0,  # Falling fast
        width=20,
        height=20
    )
)

print("\n=== Test: Falling onto wall corner (jitter scenario) ===")
print("Wall tile:", wall_tiles[0])

player_rect = player.physics.get_rect()
tile = wall_tiles[0]

print(f"\nPlayer rect: {player_rect} (x: {player_rect.left}-{player_rect.right}, y: {player_rect.top}-{player_rect.bottom})")
print(f"Wall tile:   {tile} (x: {tile.left}-{tile.right}, y: {tile.top}-{tile.bottom})")

if player_rect.colliderect(tile):
    overlap_x = min(player_rect.right, tile.right) - max(player_rect.left, tile.left)
    overlap_y = min(player_rect.bottom, tile.bottom) - max(player_rect.top, tile.top)
    print(f"\nCollision detected!")
    print(f"  Overlap X: {overlap_x}")
    print(f"  Overlap Y: {overlap_y}")
    print(f"  Difference: {abs(overlap_x - overlap_y)}")

    is_horiz_old = overlap_x < overlap_y
    print(f"  Old logic would treat as horizontal: {is_horiz_old}")

    # New logic
    is_horiz_new = overlap_x < overlap_y
    if player.physics.vy > 0 and abs(overlap_x - overlap_y) < 5:
        is_horiz_new = False
    print(f"  New logic treats as horizontal: {is_horiz_new}")

    if is_horiz_old and not is_horiz_new:
        print(f"  FIX APPLIED: Changed from horizontal to vertical!")

print(f"\nBefore: pos=({player.physics.x}, {player.physics.y}), vel=({player.physics.vx}, {player.physics.vy})")

# Check collision
collision_system.check_and_resolve(player)

print(f"After:  pos=({player.physics.x}, {player.physics.y}), vel=({player.physics.vx}, {player.physics.vy})")
print(f"On ground: {player.physics.on_ground}")

if player.physics.vx == 5.0:
    print(f"\nSUCCESS: No jitter - horizontal velocity preserved!")
else:
    print(f"\nFAILED: Horizontal velocity changed to {player.physics.vx}")
