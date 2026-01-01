"""Test wall collision - player shouldn't go off left edge."""

import pygame

from core.entity_system import Entity, EntityManager, EntityType
from core.event_bus import EventBus
from core.state import PhysicsState
from systems.collision_system import CollisionSystem


def main():
    pygame.init()

    # Create collision system with left wall tiles
    event_bus = EventBus()
    entity_manager = EntityManager(event_bus)
    collision_system = CollisionSystem(event_bus, entity_manager)

    left_wall_tiles = [pygame.Rect(0, y, 32, 32) for y in range(0, 720, 32)]
    collision_system.set_tiles(left_wall_tiles)

    # Create player overlapping the wall and moving left
    player = Entity(
        entity_id=0,
        entity_type=EntityType.PLAYER,
        physics=PhysicsState(
            x=20.0,  # Overlaps wall (0-32)
            y=100.0,
            vx=-5.0,
            vy=0.0,
            width=20,
            height=20,
        ),
    )

    print("\n=== Test: Player moving left toward wall ===")
    print("Before collision:")
    print(f"  Position: ({player.physics.x}, {player.physics.y})")
    print(f"  Velocity: ({player.physics.vx}, {player.physics.vy})")
    print(f"  Player rect: {player.physics.get_rect()}")
    print(f"  Wall tiles count: {len(left_wall_tiles)}")
    print(f"  First wall tile: {left_wall_tiles[0]}")

    player_rect = player.physics.get_rect()
    for i, tile in enumerate(left_wall_tiles):
        if player_rect.colliderect(tile):
            print(f"  Player DOES collide with wall tile {i}: {tile}")
            break
    else:
        print("  Player does NOT collide with any wall tiles")

    collision_system.check_and_resolve(player)

    print("\nAfter collision:")
    print(f"  Position: ({player.physics.x}, {player.physics.y})")
    print(f"  Velocity: ({player.physics.vx}, {player.physics.vy})")
    print(f"  On wall: {player.physics.on_wall}")
    print(f"  Wall dir: {player.physics.wall_dir}")

    # Player should be pushed to x=32 (wall.right)
    if player.physics.x >= 32:
        print(f"\n[OK] SUCCESS: Player blocked by wall at x={player.physics.x}")
    else:
        print(f"\n[FAIL] Player went through wall to x={player.physics.x} (should be >= 32)")


if __name__ == "__main__":
    main()
