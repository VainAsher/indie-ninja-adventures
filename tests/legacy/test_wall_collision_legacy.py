"""
Test Wall Collision Fix - Verify player doesn't clip through walls

This test validates that the collision system properly prevents wall clipping
with the scaled tile system (4x4 pixel tiles with 20x20 pixel player).
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pygame

from core import EntityManager, EntityType, EventBus, GameLogger, PhysicsState
from systems import CollisionSystem, PhysicsSystem


def test_horizontal_wall_collision():
    """Test that player cannot clip through vertical walls when moving horizontally"""

    print("\n" + "=" * 60)
    print("WALL COLLISION TEST - Horizontal Movement")
    print("=" * 60)

    # Initialize systems
    bus = EventBus()
    logger = GameLogger()
    entity_manager = EntityManager(bus, logger.get_logger("entity_manager"))
    physics_system = PhysicsSystem(bus, entity_manager, logger.get_logger("physics"))
    collision_system = CollisionSystem(bus, entity_manager, logger.get_logger("collision"))

    # Create a simple wall layout
    # Player at (50, 50), wall at x=100
    wall = pygame.Rect(100, 0, 8, 200)  # 8-pixel wide wall (scaled tile)
    tiles = [wall]
    collision_system.set_tiles(tiles, [])

    # Create player entity
    player_physics = PhysicsState(
        x=50.0, y=50.0, vx=0.0, vy=0.0, width=20, height=20  # 20x20 player
    )

    entity = entity_manager.create_entity(entity_type=EntityType.PLAYER, physics=player_physics)

    print("Initial state:")
    print(f"  Player: x={player_physics.x}, y={player_physics.y}")
    print(f"  Wall: x={wall.x}, width={wall.width}")
    print(f"  Player width: {player_physics.width}")

    # Test 1: Move player towards wall with high velocity
    print("\nTest 1: High velocity horizontal collision")
    player_physics.vx = 10.0  # Fast horizontal movement
    player_physics.x = 75.0  # Close to wall

    # Simulate movement
    player_physics.x += player_physics.vx

    print(f"  Before collision: x={player_physics.x}, vx={player_physics.vx}")

    # Check collision
    collision_system.check_and_resolve(entity)

    print(f"  After collision: x={player_physics.x}, vx={player_physics.vx}")
    print(f"  On wall: {player_physics.on_wall}, wall_dir={player_physics.wall_dir}")

    # Verify player stopped at wall
    player_rect = player_physics.get_rect()
    assert (
        player_rect.right <= wall.left
    ), f"Player clipped through wall! Player right={player_rect.right}, wall left={wall.left}"
    assert player_physics.vx == 0.0, "Velocity should be zeroed"
    assert player_physics.on_wall, "Should detect wall collision"
    assert player_physics.wall_dir == 1, "Should detect right wall"

    print("  [OK] Player stopped at wall correctly")

    # Test 2: Try to push through wall with continuous force
    print("\nTest 2: Continuous pressure against wall")
    for i in range(10):
        player_physics.vx = 5.0  # Keep trying to move right
        player_physics.x += player_physics.vx
        collision_system.check_and_resolve(entity)

    player_rect = player_physics.get_rect()
    print(f"  After 10 frames: x={player_physics.x}")
    assert (
        player_rect.right <= wall.left
    ), f"Player penetrated wall over time! Player right={player_rect.right}, wall left={wall.left}"

    print("  [OK] Player cannot push through wall")

    # Test 3: Small movements near wall
    print("\nTest 3: Small movements at wall boundary")
    player_physics.x = wall.left - player_physics.width - 1.0  # 1 pixel away

    for i in range(5):
        player_physics.vx = 0.5  # Small movement
        player_physics.x += player_physics.vx
        collision_system.check_and_resolve(entity)

    player_rect = player_physics.get_rect()
    print(f"  After small movements: x={player_physics.x}")
    assert (
        player_rect.right <= wall.left
    ), f"Player clipped with small movements! Player right={player_rect.right}, wall left={wall.left}"

    print("  [OK] Small movements handled correctly")

    print("\n" + "=" * 60)
    print("HORIZONTAL WALL COLLISION: PASS")
    print("=" * 60)

    return True


def test_corner_collision():
    """Test that corner collision doesn't cause clipping"""

    print("\n" + "=" * 60)
    print("CORNER COLLISION TEST")
    print("=" * 60)

    # Initialize systems
    bus = EventBus()
    logger = GameLogger()
    entity_manager = EntityManager(bus, logger.get_logger("entity_manager"))
    physics_system = PhysicsSystem(bus, entity_manager, logger.get_logger("physics"))
    collision_system = CollisionSystem(bus, entity_manager, logger.get_logger("collision"))

    # Create corner: wall and floor meeting
    wall = pygame.Rect(100, 0, 4, 100)
    floor = pygame.Rect(0, 100, 200, 4)
    tiles = [wall, floor]
    collision_system.set_tiles(tiles, [])

    # Create player falling towards corner
    player_physics = PhysicsState(
        x=85.0, y=70.0, vx=0.0, vy=0.0, width=20, height=20  # Will hit corner
    )

    entity = entity_manager.create_entity(entity_type=EntityType.PLAYER, physics=player_physics)

    print("Initial state:")
    print(f"  Player: x={player_physics.x}, y={player_physics.y}")
    print(f"  Corner at: ({wall.x}, {floor.y})")

    # Simulate falling towards corner
    print("\nSimulating fall towards corner...")
    player_physics.vx = 2.0
    player_physics.vy = 5.0

    for i in range(10):
        player_physics.x += player_physics.vx
        player_physics.y += player_physics.vy

        collision_system.check_and_resolve(entity)

        # Check no clipping
        player_rect = player_physics.get_rect()
        assert not (
            player_rect.right > wall.left
            and player_rect.left < wall.right
            and player_rect.bottom > floor.top
            and player_rect.top < floor.bottom
        ), "Player clipped into corner!"

        if player_physics.on_ground or player_physics.on_wall:
            print(
                f"  Frame {i}: Collision detected (ground={player_physics.on_ground}, wall={player_physics.on_wall})"
            )
            break

    print(f"  Final position: x={player_physics.x}, y={player_physics.y}")
    print("  [OK] No corner clipping detected")

    print("\n" + "=" * 60)
    print("CORNER COLLISION: PASS")
    print("=" * 60)

    return True


def test_thin_wall_collision():
    """Test collision with 8-pixel walls (scaled tiles)"""

    print("\n" + "=" * 60)
    print("THIN WALL COLLISION TEST (8-pixel walls)")
    print("=" * 60)

    # Initialize systems
    bus = EventBus()
    logger = GameLogger()
    entity_manager = EntityManager(bus, logger.get_logger("entity_manager"))
    physics_system = PhysicsSystem(bus, entity_manager, logger.get_logger("physics"))
    collision_system = CollisionSystem(bus, entity_manager, logger.get_logger("collision"))

    # Create series of walls
    walls = [
        pygame.Rect(100, 0, 8, 200),
        pygame.Rect(200, 0, 8, 200),
        pygame.Rect(300, 0, 8, 200),
    ]
    collision_system.set_tiles(walls, [])

    # Create player
    player_physics = PhysicsState(x=50.0, y=50.0, vx=0.0, vy=0.0, width=20, height=20)

    entity = entity_manager.create_entity(entity_type=EntityType.PLAYER, physics=player_physics)

    print(f"Testing collision with {len(walls)} walls (8px each)")

    # Test high-speed collision with each wall
    for i, wall in enumerate(walls):
        print(f"\nWall {i+1}: x={wall.x}, width={wall.width}")

        # Position player before wall
        player_physics.x = wall.x - 30.0
        player_physics.vx = 15.0  # High speed

        # Move and collide
        player_physics.x += player_physics.vx
        collision_system.check_and_resolve(entity)

        player_rect = player_physics.get_rect()
        print(f"  Player stopped at x={player_physics.x}")
        print(f"  Distance from wall: {wall.left - player_rect.right:.2f}px")

        # Verify no clipping
        assert (
            player_rect.right <= wall.left
        ), f"Clipped through thin wall! Player right={player_rect.right}, wall left={wall.left}"

        print("  [OK] No clipping through wall")

    print("\n" + "=" * 60)
    print("WALL COLLISION TEST: PASS")
    print("=" * 60)

    return True


if __name__ == "__main__":
    pygame.init()  # Initialize pygame for Rect operations

    try:
        # Run all tests
        test_horizontal_wall_collision()
        test_corner_collision()
        test_thin_wall_collision()

        print("\n" + "=" * 60)
        print("ALL WALL COLLISION TESTS PASSED")
        print("=" * 60)
        print("\nThe wall clipping fix is working correctly:")
        print("  - Players cannot clip through vertical walls")
        print("  - Corner collisions work properly")
        print("  - 8-pixel walls are detected correctly")
        print("  - Continuous pressure doesn't cause penetration")
        print("\n")

        sys.exit(0)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
