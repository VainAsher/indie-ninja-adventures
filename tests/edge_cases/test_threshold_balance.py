"""Test to find the right threshold for corner collision"""
import pygame
from systems.collision_system import CollisionSystem
from core.entity_system import Entity, EntityType, EntityManager
from core.state import PhysicsState
from core.event_bus import EventBus

pygame.init()

def test_scenario(name, player_x, player_y, vx, vy, tile_rect):
    """Test a collision scenario"""
    event_bus = EventBus()
    entity_manager = EntityManager(event_bus)
    collision_system = CollisionSystem(event_bus, entity_manager)
    collision_system.set_tiles([tile_rect])

    player = Entity(
        entity_id=0,
        entity_type=EntityType.PLAYER,
        physics=PhysicsState(x=player_x, y=player_y, vx=vx, vy=vy, width=20, height=20)
    )

    player_rect = player.physics.get_rect()
    if player_rect.colliderect(tile_rect):
        overlap_x = min(player_rect.right, tile_rect.right) - max(player_rect.left, tile_rect.left)
        overlap_y = min(player_rect.bottom, tile_rect.bottom) - max(player_rect.top, tile_rect.top)
        diff = abs(overlap_x - overlap_y)

        # What should happen
        is_side_collision = overlap_x < 10  # Very small X overlap = side hit
        is_ground_collision = overlap_y < 10  # Very small Y overlap = ground/ceiling hit

        expected = "HORIZONTAL (wall)" if is_side_collision else "VERTICAL (ground)"

        print(f"\n{name}:")
        print(f"  Overlaps: X={overlap_x}, Y={overlap_y}, diff={diff}")
        print(f"  Expected: {expected}")

        old_vx = player.physics.vx
        collision_system.check_and_resolve(player)
        new_vx = player.physics.vx

        if is_side_collision and new_vx != 0:
            print(f"  FAIL: Should stop horizontal (wall), but vx={new_vx}")
            return False
        elif not is_side_collision and new_vx == 0:
            print(f"  FAIL: Should preserve horizontal (ground), but vx={new_vx}")
            return False
        else:
            print(f"  PASS: Collision handled correctly")
            return True
    else:
        print(f"\n{name}: No collision")
        return True

print("=" * 60)
print("Testing different collision scenarios")
print("=" * 60)

# Test 1: Clear wall collision (small X overlap, should stop)
test_scenario(
    "Wall collision (side approach)",
    85.0, 505.0, 3.0, 5.0,
    pygame.Rect(100, 500, 32, 32)
)

# Test 2: Landing on platform edge (moderate overlaps)
test_scenario(
    "Platform edge landing",
    50.0, 595.0, 5.0, 10.0,
    pygame.Rect(60, 600, 32, 32)
)

# Test 3: Landing flat on ground (large X overlap, small Y)
test_scenario(
    "Flat ground landing",
    100.0, 670.0, 5.0, 10.0,
    pygame.Rect(0, 688, 640, 32)
)

# Test 4: Very corner collision (equal overlaps)
test_scenario(
    "Perfect corner collision",
    92.0, 592.0, 5.0, 8.0,
    pygame.Rect(100, 600, 32, 32)
)
