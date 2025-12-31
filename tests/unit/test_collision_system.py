"""
Test script for Collision System

Verifies:
- Entity-tile collision detection
- Collision resolution (penetration correction)
- Collision event emission
- Ground/wall/ceiling detection
- Entity-entity collision
- Radius queries
- Raycast
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pygame
from core import (
    EventBus, GameLogger, EntityManager, EntityType,
    PhysicsState, CollisionEvent
)
from systems import CollisionSystem


def test_tile_collision():
    """Test entity-tile collision detection"""
    print("\n" + "="*60)
    print("Testing Tile Collision Detection")
    print("="*60)

    # Initialize pygame (needed for Rect)
    pygame.init()

    # Create systems
    bus = EventBus()
    logger = GameLogger().get_logger("test_collision")
    entity_manager = EntityManager(bus, logger)
    collision_system = CollisionSystem(bus, entity_manager, logger)

    # Create tile
    tile = pygame.Rect(100, 100, 32, 32)
    collision_system.set_tiles([tile])

    # Create entity that will collide with tile
    physics = PhysicsState(x=80, y=90, vx=5.0, vy=0.0, width=20, height=20)
    entity = entity_manager.create_entity(EntityType.PLAYER, physics)

    print(f"\nInitial state:")
    print(f"  Entity: x={entity.physics.x}, vx={entity.physics.vx}")
    print(f"  Tile: x={tile.x}, width={tile.width}")

    # Track collision events
    collisions = []
    def on_collision(event: CollisionEvent):
        collisions.append(event)
        print(f"  [COLLISION] Entity {event.entity_id} hit {event.collision_type}")

    bus.subscribe(CollisionEvent, on_collision)

    # Move entity into tile (simulating one frame of movement)
    entity.physics.x += entity.physics.vx  # x=95

    # Check collision
    print(f"\nAfter movement: x={entity.physics.x}")
    collision_system.check_and_resolve(entity)
    bus.process()

    print(f"After collision resolution: x={entity.physics.x}, vx={entity.physics.vx}")
    print(f"On wall: {entity.physics.on_wall}, Wall dir: {entity.physics.wall_dir}")

    # Verify collision was detected and resolved
    assert len(collisions) == 1, f"Expected 1 collision, got {len(collisions)}"
    assert collisions[0].collision_type == 'wall_right', \
        f"Expected wall_right, got {collisions[0].collision_type}"
    assert entity.physics.vx == 0.0, "Velocity should be zero after collision"
    assert entity.physics.on_wall, "Entity should be on wall"
    assert entity.physics.x < 100, "Entity should be pushed out of tile"

    print(f"\n[PASS] Tile Collision Test PASSED")
    print(f"   - Collision detected: OK")
    print(f"   - Penetration resolved: OK")
    print(f"   - Event emitted: OK")
    print(f"   - Flags updated: OK")


def test_ground_collision():
    """Test ground landing"""
    print("\n" + "="*60)
    print("Testing Ground Collision")
    print("="*60)

    pygame.init()

    bus = EventBus()
    logger = GameLogger().get_logger("test_collision")
    entity_manager = EntityManager(bus, logger)
    collision_system = CollisionSystem(bus, entity_manager, logger)

    # Create ground tile
    ground = pygame.Rect(0, 150, 200, 32)
    collision_system.set_tiles([ground])

    # Create falling entity (positioned to collide after movement)
    physics = PhysicsState(x=50, y=125, vx=0.0, vy=10.0, width=20, height=20)
    entity = entity_manager.create_entity(EntityType.PLAYER, physics)

    print(f"\nInitial state:")
    print(f"  Entity: y={entity.physics.y}, bottom={entity.physics.y + entity.physics.height}, vy={entity.physics.vy}")
    print(f"  Ground: y={ground.y}")

    # Track collisions
    collisions = []
    bus.subscribe(CollisionEvent, lambda e: collisions.append(e))

    # Move entity down (bottom will be 135+20=155, overlapping ground at 150)
    entity.physics.y += entity.physics.vy  # y=135

    # Check collision
    collision_system.check_and_resolve(entity)
    bus.process()

    print(f"\nAfter collision resolution:")
    print(f"  Entity: y={entity.physics.y}, vy={entity.physics.vy}")
    print(f"  On ground: {entity.physics.on_ground}")

    # Verify landing
    assert len(collisions) == 1, f"Expected 1 collision, got {len(collisions)}"
    assert collisions[0].collision_type == 'ground'
    assert entity.physics.vy == 0.0, "Vertical velocity should be zero"
    assert entity.physics.on_ground, "Entity should be on ground"
    assert entity.physics.y == ground.y - entity.physics.height, \
        "Entity should be on top of ground"

    print(f"\n[PASS] Ground Collision Test PASSED")


def test_entity_entity_collision():
    """Test collision between two entities"""
    print("\n" + "="*60)
    print("Testing Entity-Entity Collision")
    print("="*60)

    pygame.init()

    bus = EventBus()
    logger = GameLogger().get_logger("test_collision")
    entity_manager = EntityManager(bus, logger)
    collision_system = CollisionSystem(bus, entity_manager, logger)

    # Create two entities
    physics_a = PhysicsState(x=50, y=50, vx=0, vy=0, width=20, height=20)
    entity_a = entity_manager.create_entity(EntityType.PLAYER, physics_a)

    physics_b = PhysicsState(x=60, y=60, vx=0, vy=0, width=20, height=20)
    entity_b = entity_manager.create_entity(EntityType.ENEMY, physics_b)

    print(f"\nEntity A: ({entity_a.physics.x}, {entity_a.physics.y})")
    print(f"Entity B: ({entity_b.physics.x}, {entity_b.physics.y})")

    # Check collision
    is_colliding = collision_system.check_entity_collision(entity_a, entity_b)
    print(f"Colliding: {is_colliding}")

    assert is_colliding, "Entities should be colliding"

    # Move entity_b away
    entity_b.physics.x = 100
    is_colliding = collision_system.check_entity_collision(entity_a, entity_b)
    print(f"After moving B: Colliding: {is_colliding}")

    assert not is_colliding, "Entities should not be colliding after separation"

    print(f"\n[PASS] Entity-Entity Collision Test PASSED")


def test_radius_query():
    """Test radius query for entities"""
    print("\n" + "="*60)
    print("Testing Radius Query")
    print("="*60)

    pygame.init()

    bus = EventBus()
    logger = GameLogger().get_logger("test_collision")
    entity_manager = EntityManager(bus, logger)
    collision_system = CollisionSystem(bus, entity_manager, logger)

    # Create entities at various distances
    entities = []
    positions = [(50, 50), (100, 50), (150, 50), (200, 50)]
    for x, y in positions:
        physics = PhysicsState(x=x, y=y, vx=0, vy=0, width=10, height=10)
        entity = entity_manager.create_entity(EntityType.ENEMY, physics)
        entities.append(entity)

    print(f"\nCreated {len(entities)} entities")
    for i, (x, y) in enumerate(positions):
        print(f"  Entity {i}: ({x}, {y})")

    # Query entities within radius of (50, 50)
    center_x, center_y = 50, 50
    radius = 60

    nearby = collision_system.get_entities_in_radius(center_x, center_y, radius)

    print(f"\nEntities within {radius} pixels of ({center_x}, {center_y}):")
    for entity in nearby:
        print(f"  Entity {entity.entity_id}: ({entity.physics.x}, {entity.physics.y})")

    # Should find 2 entities (at 50 and 100)
    assert len(nearby) == 2, f"Expected 2 entities, found {len(nearby)}"

    print(f"\n[PASS] Radius Query Test PASSED")


def test_raycast():
    """Test raycast collision"""
    print("\n" + "="*60)
    print("Testing Raycast")
    print("="*60)

    pygame.init()

    bus = EventBus()
    logger = GameLogger().get_logger("test_collision")
    entity_manager = EntityManager(bus, logger)
    collision_system = CollisionSystem(bus, entity_manager, logger)

    # Create wall
    wall = pygame.Rect(100, 50, 32, 100)
    collision_system.set_tiles([wall])

    print(f"\nWall at x={wall.x}, y={wall.y}, w={wall.width}, h={wall.height}")

    # Raycast that hits wall
    start_x, start_y = 50, 75
    end_x, end_y = 150, 75

    print(f"\nRaycast from ({start_x}, {start_y}) to ({end_x}, {end_y})")

    hit = collision_system.raycast(start_x, start_y, end_x, end_y)

    if hit:
        hit_x, hit_y, hit_tile = hit
        print(f"Hit at ({hit_x:.1f}, {hit_y:.1f})")
        assert hit_x >= wall.x, "Should hit wall"
    else:
        print("No hit")
        assert False, "Raycast should hit wall"

    # Raycast that misses
    start_x, start_y = 50, 200
    end_x, end_y = 150, 200

    print(f"\nRaycast from ({start_x}, {start_y}) to ({end_x}, {end_y})")

    hit = collision_system.raycast(start_x, start_y, end_x, end_y)
    print(f"Hit: {hit}")

    assert hit is None, "Raycast should miss"

    print(f"\n[PASS] Raycast Test PASSED")


def main():
    """Run all collision tests"""
    print("\n" + "#"*60)
    print("#  COLLISION SYSTEM TEST")
    print("#"*60)

    try:
        test_tile_collision()
        test_ground_collision()
        test_entity_entity_collision()
        test_radius_query()
        test_raycast()

        print("\n" + "="*60)
        print("[PASS] ALL COLLISION TESTS PASSED")
        print("="*60)
        print("\nCollision system is working correctly!")
        print("Features verified:")
        print("  - Tile collision detection")
        print("  - Collision resolution")
        print("  - Collision events")
        print("  - Ground/wall detection")
        print("  - Entity-entity collision")
        print("  - Radius queries")
        print("  - Raycasting")
        print("\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
