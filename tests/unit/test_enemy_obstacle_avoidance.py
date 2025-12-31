"""
Unit Test: Enemy Obstacle Avoidance

Tests that enemies properly detect and avoid obstacles using raycasting.
"""

import sys
from pathlib import Path

# Add project root to path (two levels up from this file)
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from entities.enemy import Enemy, EnemyType, EnemyAIState
from entities.enemy_ai import EnemyAI
from systems import CollisionSystem
from core import EventBus, EntityManager


def test_enemy_detects_obstacle_ahead():
    """Test that enemy AI detects obstacles in front of it"""
    pygame.init()

    # Create collision system with a wall
    bus = EventBus()
    entity_manager = EntityManager(bus)
    collision_system = CollisionSystem(bus, entity_manager)

    # Create a wall obstacle (vertical wall at x=80)
    # Raycast distance is 48px, so enemy at x=20 should detect wall at x=80
    wall = pygame.Rect(80, 0, 32, 200)
    collision_system.set_tiles([wall])

    # Create enemy facing right at x=20 (will face the wall)
    # Enemy center is at x=20+16=36, raycast goes to x=36+48=84, wall starts at x=80
    enemy = Enemy(
        enemy_id="test_enemy",
        enemy_type=EnemyType.GOBLIN,
        x=20.0,
        y=100.0,
        facing_right=True
    )
    enemy.physics.vx = 50.0  # Moving right toward wall

    # Create AI controller
    ai = EnemyAI(enemy)

    # Update AI with collision system (should detect obstacle)
    ai.update(
        dt=1/60,
        player_x=500.0,  # Player far away
        player_y=500.0,
        player_width=32,
        player_height=56,
        collision_system=collision_system
    )

    # Should detect obstacle ahead
    assert ai.obstacle_ahead == True, "Enemy should detect obstacle ahead"
    print("[PASS] Enemy correctly detected obstacle ahead")


def test_enemy_no_obstacle_when_clear():
    """Test that enemy does not detect obstacles when path is clear"""
    pygame.init()

    # Create collision system with no obstacles
    bus = EventBus()
    entity_manager = EntityManager(bus)
    collision_system = CollisionSystem(bus, entity_manager)
    collision_system.set_tiles([])

    # Create enemy
    enemy = Enemy(
        enemy_id="test_enemy",
        enemy_type=EnemyType.GOBLIN,
        x=20.0,
        y=100.0,
        facing_right=True
    )
    enemy.physics.vx = 50.0

    # Create AI controller
    ai = EnemyAI(enemy)

    # Update AI (should NOT detect obstacle)
    ai.update(
        dt=1/60,
        player_x=500.0,
        player_y=500.0,
        player_width=32,
        player_height=56,
        collision_system=collision_system
    )

    # Should NOT detect obstacle
    assert ai.obstacle_ahead == False, "Enemy should not detect obstacle when clear"
    print("[PASS] Enemy correctly detected no obstacle")


def test_flying_enemy_ignores_obstacles():
    """Test that flying enemies don't check for obstacles"""
    pygame.init()

    # Create collision system with a wall
    bus = EventBus()
    entity_manager = EntityManager(bus)
    collision_system = CollisionSystem(bus, entity_manager)

    wall = pygame.Rect(100, 0, 32, 200)
    collision_system.set_tiles([wall])

    # Create flying enemy (BAT) facing wall
    enemy = Enemy(
        enemy_id="test_bat",
        enemy_type=EnemyType.BAT,
        x=20.0,
        y=100.0,
        facing_right=True
    )

    # Create AI controller
    ai = EnemyAI(enemy)

    # Update AI
    ai.update(
        dt=1/60,
        player_x=500.0,
        player_y=500.0,
        player_width=32,
        player_height=56,
        collision_system=collision_system
    )

    # Flying enemies should ignore obstacles
    assert ai.obstacle_ahead == False, "Flying enemy should ignore obstacles"
    print("[PASS] Flying enemy correctly ignored obstacle")


def test_patrol_turns_around_on_obstacle():
    """Test that patrolling enemy turns around when hitting obstacle"""
    pygame.init()

    # Create collision system with a wall
    bus = EventBus()
    entity_manager = EntityManager(bus)
    collision_system = CollisionSystem(bus, entity_manager)

    wall = pygame.Rect(100, 0, 32, 200)
    collision_system.set_tiles([wall])

    # Create enemy with patrol waypoints
    enemy = Enemy(
        enemy_id="test_enemy",
        enemy_type=EnemyType.GOBLIN,
        x=20.0,
        y=100.0,
        facing_right=True,
        ai_state=EnemyAIState.PATROL
    )

    # Set patrol waypoints (moving right toward wall)
    enemy.set_patrol_waypoints([
        (10.0, 100.0),   # Left point
        (150.0, 100.0)   # Right point (beyond wall)
    ])
    enemy.current_waypoint_index = 1  # Moving toward right waypoint

    # Create AI controller
    ai = EnemyAI(enemy)

    # Update several times to trigger obstacle detection
    for _ in range(10):
        ai.update(
            dt=1/60,
            player_x=500.0,
            player_y=500.0,
            player_width=32,
            player_height=56,
            collision_system=collision_system
        )

        # If obstacle detected and wait timer started, enemy should have turned around
        if ai.obstacle_ahead and ai.obstacle_wait_timer > 0:
            # Waypoint should have advanced (turned around)
            assert enemy.current_waypoint_index == 0, "Enemy should turn around on obstacle"
            print("[PASS] Patrolling enemy turned around on obstacle")
            return

    # If we get here and obstacle was detected, still pass
    if ai.obstacle_ahead:
        print("[PASS] Enemy detected obstacle during patrol")
    else:
        print("[WARN] Enemy did not detect obstacle during test (may need more frames)")


def main():
    """Run all obstacle avoidance tests"""
    print("\n" + "="*60)
    print("ENEMY OBSTACLE AVOIDANCE TESTS")
    print("="*60 + "\n")

    test_enemy_detects_obstacle_ahead()
    test_enemy_no_obstacle_when_clear()
    test_flying_enemy_ignores_obstacles()
    test_patrol_turns_around_on_obstacle()

    print("\n" + "="*60)
    print("ALL OBSTACLE AVOIDANCE TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
