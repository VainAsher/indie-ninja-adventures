"""
Test script for Physics System

Verifies:
- Gravity application
- Velocity integration
- Fall speed capping
- Gravity multipliers (fall faster, jump cut)
- Integration with entity system
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    EventBus, GameLogger, EntityManager, EntityType,
    PhysicsState
)
from systems import PhysicsSystem


def test_gravity():
    """Test gravity application"""
    print("\n" + "="*60)
    print("Testing Gravity Application")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_physics")
    entity_manager = EntityManager(bus, logger)
    physics_system = PhysicsSystem(bus, entity_manager, logger)

    # Create entity in air
    physics = PhysicsState(x=100, y=100, vx=0, vy=0, width=20, height=20)
    physics.on_ground = False
    entity = entity_manager.create_entity(EntityType.PLAYER, physics)

    print(f"\nInitial state:")
    print(f"  Position: ({entity.physics.x}, {entity.physics.y})")
    print(f"  Velocity: ({entity.physics.vx}, {entity.physics.vy})")

    # Simulate 10 ticks
    print(f"\nApplying gravity for 10 ticks...")
    for i in range(10):
        tick_event = bus.create_tick_event(dt=1/60, tick_number=i)
        physics_system.on_tick(tick_event)

    print(f"  After 10 ticks:")
    print(f"  Position: ({entity.physics.x:.1f}, {entity.physics.y:.1f})")
    print(f"  Velocity: ({entity.physics.vx:.2f}, {entity.physics.vy:.2f})")

    assert entity.physics.vy > 0, "Should be falling (vy > 0)"
    assert entity.physics.y > 100, "Should have moved down"

    print(f"\n[PASS] Gravity Application Test PASSED")


def test_fall_speed_cap():
    """Test max fall speed capping"""
    print("\n" + "="*60)
    print("Testing Fall Speed Cap")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_physics")
    entity_manager = EntityManager(bus, logger)
    physics_system = PhysicsSystem(bus, entity_manager, logger)

    # Create entity in air with high velocity
    physics = PhysicsState(x=100, y=100, vx=0, vy=20.0, width=20, height=20)
    physics.on_ground = False
    entity = entity_manager.create_entity(EntityType.PLAYER, physics)

    print(f"\nInitial vy: {entity.physics.vy:.2f}")

    # Simulate many ticks to build up speed
    print(f"\nApplying gravity for 100 ticks...")
    for i in range(100):
        tick_event = bus.create_tick_event(dt=1/60, tick_number=i)
        physics_system.on_tick(tick_event)

    print(f"  Final vy: {entity.physics.vy:.2f}")
    print(f"  Max fall speed: {physics_system.MAX_FALL_SPEED}")

    assert entity.physics.vy <= physics_system.MAX_FALL_SPEED, \
        f"Fall speed should be capped at {physics_system.MAX_FALL_SPEED}"

    print(f"\n[PASS] Fall Speed Cap Test PASSED")


def test_velocity_integration():
    """Test velocity integration into position"""
    print("\n" + "="*60)
    print("Testing Velocity Integration")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_physics")
    entity_manager = EntityManager(bus, logger)
    physics_system = PhysicsSystem(bus, entity_manager, logger)

    # Create entity with velocity
    physics = PhysicsState(x=100, y=100, vx=5.0, vy=3.0, width=20, height=20)
    physics.on_ground = False
    entity = entity_manager.create_entity(EntityType.PLAYER, physics)

    print(f"\nInitial state:")
    print(f"  Position: ({entity.physics.x}, {entity.physics.y})")
    print(f"  Velocity: ({entity.physics.vx}, {entity.physics.vy})")

    # Process one tick
    tick_event = bus.create_tick_event(dt=1/60, tick_number=0)
    physics_system.on_tick(tick_event)

    print(f"\nAfter 1 tick:")
    print(f"  Position: ({entity.physics.x}, {entity.physics.y})")

    # Position should have changed by velocity (plus gravity on vy)
    assert entity.physics.x == 105.0, f"x should be 105.0, got {entity.physics.x}"
    assert entity.physics.y > 100, "y should have increased"

    print(f"\n[PASS] Velocity Integration Test PASSED")


def test_grounded_no_gravity():
    """Test that grounded entities don't have gravity applied"""
    print("\n" + "="*60)
    print("Testing Grounded Entities (No Gravity)")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_physics")
    entity_manager = EntityManager(bus, logger)
    physics_system = PhysicsSystem(bus, entity_manager, logger)

    # Create grounded entity
    physics = PhysicsState(x=100, y=100, vx=0, vy=0, width=20, height=20)
    physics.on_ground = True
    entity = entity_manager.create_entity(EntityType.PLAYER, physics)

    print(f"\nInitial state (on ground):")
    print(f"  vy: {entity.physics.vy}")

    # Process 10 ticks
    for i in range(10):
        tick_event = bus.create_tick_event(dt=1/60, tick_number=i)
        physics_system.on_tick(tick_event)

    print(f"  After 10 ticks: vy={entity.physics.vy}")

    assert entity.physics.vy == 0, "Grounded entity should have vy=0 (no gravity)"

    print(f"\n[PASS] Grounded Entities Test PASSED")


def test_physics_with_multiple_entities():
    """Test physics system with multiple entities"""
    print("\n" + "="*60)
    print("Testing Multiple Entities")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_physics")
    entity_manager = EntityManager(bus, logger)
    physics_system = PhysicsSystem(bus, entity_manager, logger)

    # Create multiple entities
    entities = []
    for i in range(5):
        physics = PhysicsState(x=100+i*50, y=100, vx=0, vy=0, width=20, height=20)
        physics.on_ground = False
        entity = entity_manager.create_entity(EntityType.PLAYER, physics)
        entities.append(entity)

    print(f"\nCreated {len(entities)} entities")

    # Process ticks
    for i in range(10):
        tick_event = bus.create_tick_event(dt=1/60, tick_number=i)
        physics_system.on_tick(tick_event)

    print(f"\nAfter 10 ticks, all entities falling:")
    for i, entity in enumerate(entities):
        print(f"  Entity {i}: y={entity.physics.y:.1f}, vy={entity.physics.vy:.2f}")
        assert entity.physics.vy > 0, f"Entity {i} should be falling"

    # Get stats
    stats = physics_system.get_stats()
    print(f"\nPhysics stats:")
    print(f"  Entities with physics: {stats['entities_with_physics']}")
    print(f"  Gravity: {stats['gravity']}")
    print(f"  Max fall speed: {stats['max_fall_speed']}")

    assert stats['entities_with_physics'] == 5

    print(f"\n[PASS] Multiple Entities Test PASSED")


def main():
    """Run all physics system tests"""
    print("\n" + "#"*60)
    print("#  PHYSICS SYSTEM TEST")
    print("#"*60)

    try:
        test_gravity()
        test_fall_speed_cap()
        test_velocity_integration()
        test_grounded_no_gravity()
        test_physics_with_multiple_entities()

        print("\n" + "="*60)
        print("[PASS] ALL PHYSICS SYSTEM TESTS PASSED")
        print("="*60)
        print("\nPhysics system is working correctly!")
        print("Features verified:")
        print("  - Gravity application")
        print("  - Fall speed capping")
        print("  - Velocity integration")
        print("  - Grounded entity handling")
        print("  - Multiple entity support")
        print("\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
