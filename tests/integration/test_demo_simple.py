"""
Minimal test to debug collision issues
"""
import pygame
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core import EventBus, GameLogger, EntityManager, EntityType, PhysicsState
from systems import CollisionSystem

# Init pygame
pygame.init()

# Create systems
bus = EventBus()
logger = GameLogger()
entity_manager = EntityManager(bus, logger.get_logger("entity"))
collision_system = CollisionSystem(bus, entity_manager, logger.get_logger("collision"))

# Create ground
ground = pygame.Rect(0, 688, 1280, 32)
collision_system.set_tiles([ground])

# Create player entity
physics = PhysicsState(x=640, y=680, vx=5.0, vy=0.0, width=20, height=20)
entity = entity_manager.create_entity(EntityType.PLAYER, physics)

print(f"\nBefore collision:")
print(f"  Position: ({entity.physics.x}, {entity.physics.y})")
print(f"  Velocity: ({entity.physics.vx}, {entity.physics.vy})")
print(f"  Bottom: {entity.physics.y + entity.physics.height}")
print(f"  On ground: {entity.physics.on_ground}")

# Simulate movement
entity.physics.x += entity.physics.vx
entity.physics.y += entity.physics.vy

print(f"\nAfter movement:")
print(f"  Position: ({entity.physics.x}, {entity.physics.y})")
print(f"  Bottom: {entity.physics.y + entity.physics.height}")

# Check collision
collision_system.check_and_resolve(entity)

print(f"\nAfter collision:")
print(f"  Position: ({entity.physics.x}, {entity.physics.y})")
print(f"  Velocity: ({entity.physics.vx}, {entity.physics.vy})")
print(f"  Bottom: {entity.physics.y + entity.physics.height}")
print(f"  On ground: {entity.physics.on_ground}")

pygame.quit()
