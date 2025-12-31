"""
Unit Test: NPC Movement and Facing

Tests that NPCs can patrol waypoints and face the player when nearby.
"""

import sys
from pathlib import Path

# Add project root to path (two levels up from this file)
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from entities.npc import NPC, NPCType, NPCManager
from core import EventBus


def test_npc_static_by_default():
    """Test that NPCs are static by default (no patrol)"""
    pygame.init()

    npc = NPC(
        npc_id="test_npc",
        npc_type=NPCType.SHOP,
        x=100.0,
        y=100.0
    )

    # Should not have patrol by default
    assert npc.has_patrol == False
    assert len(npc.patrol_waypoints) == 0

    # Update NPC (should stay in place)
    initial_x = npc.x
    npc.update(0.1)

    assert npc.x == initial_x, "Static NPC should not move"
    print("[PASS] NPC is static by default")


def test_npc_patrol_movement():
    """Test that NPC moves between patrol waypoints"""
    pygame.init()

    npc = NPC(
        npc_id="test_npc",
        npc_type=NPCType.MISSION_GIVER,
        x=100.0,
        y=100.0
    )

    # Set patrol waypoints
    waypoints = [
        (100.0, 100.0),  # Start position
        (200.0, 100.0)   # End position (100 pixels right)
    ]
    npc.set_patrol_waypoints(waypoints)

    assert npc.has_patrol == True
    assert len(npc.patrol_waypoints) == 2

    # Update NPC multiple times (should move toward waypoint)
    for _ in range(100):
        npc.update(0.1)  # 10 seconds total

    # NPC should have moved right toward waypoint[1]
    assert npc.x > 100.0, "NPC should have moved from starting position"
    print(f"[PASS] NPC moved from x=100 to x={npc.x:.1f}")


def test_npc_faces_movement_direction():
    """Test that NPC faces the direction it's moving"""
    pygame.init()

    npc = NPC(
        npc_id="test_npc",
        npc_type=NPCType.SHOP,
        x=100.0,
        y=100.0
    )

    # Set patrol waypoints (moving left then right)
    waypoints = [
        (100.0, 100.0),  # Start
        (50.0, 100.0),   # Move left
        (150.0, 100.0)   # Move right
    ]
    npc.set_patrol_waypoints(waypoints)
    npc.current_waypoint_index = 1  # Start moving to left waypoint

    # Update NPC (should move left and face left)
    for _ in range(10):
        npc.update(0.1)

    # Should be facing left (moving toward x=50)
    assert npc.facing == -1, "NPC should face left when moving left"
    print("[PASS] NPC faces movement direction")


def test_npc_faces_player_when_nearby():
    """Test that NPC faces player when player is nearby"""
    pygame.init()

    npc = NPC(
        npc_id="test_npc",
        npc_type=NPCType.SHOP,
        x=100.0,
        y=100.0
    )

    # Initially facing right
    npc.facing = 1

    # Player approaches from the left (close enough to be within interaction radius)
    # NPC center is at ~x=116, player needs to be within 48 pixels
    player_x = 80.0  # Player to the left of NPC, within interaction radius
    player_y = 100.0

    # Update NPC with player position
    npc.update(0.1, player_x, player_y)

    # NPC should now face left (toward player)
    assert npc.facing == -1, "NPC should face left toward player on the left"
    print("[PASS] NPC faces player when nearby (left)")

    # Player moves to the right (still within interaction radius)
    player_x = 130.0  # Player to the right of NPC

    npc.update(0.1, player_x, player_y)

    # NPC should now face right (toward player)
    assert npc.facing == 1, "NPC should face right toward player on the right"
    print("[PASS] NPC faces player when nearby (right)")


def test_npc_ignores_distant_player():
    """Test that NPC doesn't face player if player is far away"""
    pygame.init()

    npc = NPC(
        npc_id="test_npc",
        npc_type=NPCType.SHOP,
        x=100.0,
        y=100.0,
        interaction_radius=48.0
    )

    # Initially facing right
    npc.facing = 1

    # Player very far away (200 pixels away, > interaction_radius)
    player_x = 300.0
    player_y = 100.0

    # Update NPC with player position
    npc.update(0.1, player_x, player_y)

    # NPC should still face right (player too far)
    assert npc.facing == 1, "NPC should not change facing when player is distant"
    print("[PASS] NPC ignores distant player")


def test_npc_manager_patrol_setup():
    """Test that NPCManager can set up NPC patrol"""
    pygame.init()

    bus = EventBus()
    manager = NPCManager(bus)

    # Spawn an NPC (using a default registered NPC)
    npc = manager.spawn_npc("forest_merchant", 100.0, 100.0)
    assert npc is not None

    # Set patrol waypoints through manager
    waypoints = [(100.0, 100.0), (200.0, 100.0)]
    manager.set_npc_patrol("forest_merchant", waypoints)

    # Check NPC has patrol
    assert npc.has_patrol == True
    assert len(npc.patrol_waypoints) == 2
    print("[PASS] NPCManager can set up NPC patrol")


def test_npc_manager_updates_with_player_position():
    """Test that NPCManager passes player position to NPCs"""
    pygame.init()

    bus = EventBus()
    manager = NPCManager(bus)

    # Spawn an NPC (using a default registered NPC)
    npc = manager.spawn_npc("town_blacksmith", 100.0, 100.0)
    npc.facing = 1  # Initially facing right

    # Update manager with player to the left (within interaction radius)
    player_x = 80.0  # Close enough to NPC
    player_y = 100.0
    manager.update(0.1, player_x, player_y)

    # NPC should have faced player
    assert npc.facing == -1, "NPC should face player after manager update"
    print("[PASS] NPCManager updates NPCs with player position")


def main():
    """Run all NPC movement tests"""
    print("\n" + "="*60)
    print("NPC MOVEMENT AND FACING TESTS")
    print("="*60 + "\n")

    test_npc_static_by_default()
    test_npc_patrol_movement()
    test_npc_faces_movement_direction()
    test_npc_faces_player_when_nearby()
    test_npc_ignores_distant_player()
    test_npc_manager_patrol_setup()
    test_npc_manager_updates_with_player_position()

    print("\n" + "="*60)
    print("ALL NPC MOVEMENT TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
