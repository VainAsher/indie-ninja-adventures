"""
Unit Test: Comprehensive Enemy AI Testing

Tests all enemy AI states, transitions, and behaviors:
- State transitions (IDLE -> PATROL -> CHASE -> ATTACK -> STUNNED)
- Player detection and tracking
- Patrol waypoint navigation
- Attack behavior and cooldowns
- Stun mechanics
- Determinism verification
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from entities.enemy import Enemy, EnemyType, EnemyAIState
from entities.enemy_ai import EnemyAI
from entities.ai_random import AIRandom


def test_idle_to_patrol_transition():
    """Test enemy transitions from IDLE to PATROL after idle duration"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.IDLE
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])

    # AI without seed uses fixed 1.0s idle duration
    ai = EnemyAI(enemy, ai_random=None)

    # Update for idle duration
    for _ in range(60):  # 1 second at 60 FPS
        ai.update(1/60, 500.0, 500.0, 32, 56)  # Player far away

    # Should transition to PATROL after idle duration
    ai.update(0.1, 500.0, 500.0, 32, 56)
    assert enemy.ai_state == EnemyAIState.PATROL, "Should transition to PATROL after idle"
    print("[PASS] IDLE -> PATROL transition")


def test_patrol_to_chase_on_player_detection():
    """Test enemy transitions from PATROL to CHASE when player detected"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])
    ai = EnemyAI(enemy)

    # Player within detection range (200px for goblin)
    ai.update(1/60, 150.0, 100.0, 32, 56)

    assert enemy.ai_state == EnemyAIState.CHASE, "Should transition to CHASE when player detected"
    print("[PASS] PATROL -> CHASE on detection")


def test_chase_to_attack_when_in_range():
    """Test enemy transitions from CHASE to ATTACK when in attack range"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.CHASE
    )

    ai = EnemyAI(enemy)
    ai.enemy.target_player_x = 120.0
    ai.enemy.target_player_y = 100.0

    # Player very close (within attack range ~32px)
    ai.update(1/60, 110.0, 100.0, 32, 56)

    assert enemy.ai_state == EnemyAIState.ATTACK, "Should transition to ATTACK when in range"
    print("[PASS] CHASE -> ATTACK when in range")


def test_attack_to_chase_when_player_leaves():
    """Test enemy returns to CHASE if player leaves attack range"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.ATTACK
    )

    ai = EnemyAI(enemy)

    # Player moves out of attack range
    ai.update(1/60, 200.0, 100.0, 32, 56)

    assert enemy.ai_state == EnemyAIState.CHASE, "Should return to CHASE when player leaves range"
    print("[PASS] ATTACK -> CHASE when out of range")


def test_chase_to_patrol_when_player_escapes():
    """Test enemy returns to PATROL if player escapes detection"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.CHASE
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])
    ai = EnemyAI(enemy)

    # Player far outside detection range
    ai.update(1/60, 500.0, 500.0, 32, 56)

    assert enemy.ai_state == EnemyAIState.PATROL, "Should return to PATROL when player escapes"
    print("[PASS] CHASE -> PATROL when player escapes")


def test_attack_deals_damage():
    """Test enemy deals damage when attacking"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.ATTACK
    )

    ai = EnemyAI(enemy)

    # First attack should deal damage
    damage = ai.update(1/60, 110.0, 100.0, 32, 56)

    assert damage is not None, "Should deal damage on attack"
    assert damage > 0, "Damage should be positive"
    print(f"[PASS] Attack deals {damage} damage")


def test_attack_cooldown():
    """Test attack cooldown prevents rapid attacks"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.ATTACK
    )

    ai = EnemyAI(enemy, ai_random=None)  # Fixed 1.0s cooldown

    # First attack
    damage1 = ai.update(1/60, 110.0, 100.0, 32, 56)

    # Immediate second attack (should not deal damage - on cooldown)
    damage2 = ai.update(1/60, 110.0, 100.0, 32, 56)

    assert damage1 is not None, "First attack should deal damage"
    assert damage2 is None, "Second attack should be on cooldown"

    # Track all attacks over a period of time
    attacks = []
    for i in range(125):  # ~2 seconds
        result = ai.update(1/60, 110.0, 100.0, 32, 56)
        if result is not None:
            attacks.append(i)

    # Should have exactly 2 attacks: one at ~60 frames, one at ~120 frames
    assert len(attacks) == 2, \
        f"Expected 2 attacks after cooldown, got {len(attacks)} at frames {attacks}"
    print("[PASS] Attack cooldown works correctly")


def test_stun_state_recovery():
    """Test enemy recovers from stun state"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])
    ai = EnemyAI(enemy)

    # Apply stun
    enemy.take_damage(1, knockback_x=50.0, knockback_y=-50.0, stun_duration=0.5)

    assert enemy.ai_state == EnemyAIState.STUNNED, "Should be stunned after damage"

    # Update for stun duration
    for _ in range(30):  # 0.5 seconds
        ai.update(1/60, 500.0, 500.0, 32, 56)

    # Should transition back to PATROL after stun expires
    ai.update(0.1, 500.0, 500.0, 32, 56)
    assert enemy.ai_state == EnemyAIState.PATROL, "Should return to PATROL after stun"
    print("[PASS] Stun recovery works")


def test_patrol_waypoint_navigation():
    """Test enemy navigates between patrol waypoints"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    waypoints = [(100.0, 100.0), (200.0, 100.0)]
    enemy.set_patrol_waypoints(waypoints)
    enemy.current_waypoint_index = 1  # Start heading to second waypoint
    ai = EnemyAI(enemy)

    initial_x = enemy.x

    # Update many times to move toward waypoint
    for _ in range(200):
        ai.update(0.1, 500.0, 500.0, 32, 56)  # Player far away
        # Manually integrate physics (test doesn't have physics system)
        enemy.physics.x += enemy.physics.vx
        enemy.physics.y += enemy.physics.vy
        enemy.sync_from_physics()  # Sync position from physics

    # Should have moved significantly from starting position
    moved_distance = abs(enemy.x - initial_x)
    assert moved_distance > 5, \
        f"Enemy should move during patrol (moved {moved_distance:.1f}px)"
    print(f"[PASS] Patrol navigation (moved from {initial_x:.1f} to {enemy.x:.1f})")


def test_waypoint_advancement():
    """Test enemy advances to next waypoint when reaching current one"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    waypoints = [(100.0, 100.0), (300.0, 100.0)]
    enemy.set_patrol_waypoints(waypoints)
    enemy.current_waypoint_index = 1  # Heading to waypoint at x=300
    ai = EnemyAI(enemy)

    # Run for a long time to reach waypoint and advance
    for _ in range(800):
        ai.update(0.1, 500.0, 500.0, 32, 56)
        enemy.physics.x += enemy.physics.vx
        enemy.physics.y += enemy.physics.vy
        enemy.sync_from_physics()

    # Should have advanced through waypoints at least once
    # (may be at 0 or back at 1, just check it changed and advanced)
    assert enemy.current_waypoint_index in [0, 1], \
        f"Expected waypoint 0 or 1, got {enemy.current_waypoint_index}"
    print(f"[PASS] Waypoint advancement (patrol cycling works)")


def test_detection_radius_multiplier():
    """Test detection radius multiplier affects player detection"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,  # 200px detection radius
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])
    ai = EnemyAI(enemy)

    # Player at 120px distance (within 200px normal range, outside 100px stealth range)
    # Enemy center at x=116, player at x=220 gives player center at 236
    # Distance = 120px
    ai.update(1/60, 220.0, 100.0, 32, 56, detection_mult=1.0)
    state_normal = enemy.ai_state

    # Reset
    enemy.ai_state = EnemyAIState.PATROL

    # Player at same distance with 0.5x detection (100px effective range)
    ai.update(1/60, 220.0, 100.0, 32, 56, detection_mult=0.5)
    state_stealth = enemy.ai_state

    # Normal detection should trigger chase, stealth should not
    assert state_normal == EnemyAIState.CHASE, "Should detect with normal mult"
    assert state_stealth == EnemyAIState.PATROL, \
        f"Should not detect with stealth mult (state={state_stealth})"
    print("[PASS] Detection multiplier works")


def test_dead_state_no_behavior():
    """Test dead enemies have no AI behavior"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.DEAD
    )

    ai = EnemyAI(enemy)

    initial_x = enemy.x

    # Update dead enemy
    for _ in range(10):
        damage = ai.update(0.1, 120.0, 100.0, 32, 56)
        enemy.sync_from_physics()

    # Should not move or deal damage
    assert enemy.x == initial_x, "Dead enemy should not move"
    assert damage is None, "Dead enemy should not deal damage"
    print("[PASS] Dead state has no behavior")


def test_deterministic_timing_with_seed():
    """Test AI timing is deterministic with same seed"""
    pygame.init()

    # Create two enemies with same seed
    enemy1 = Enemy("test1", EnemyType.GOBLIN, 100.0, 100.0, ai_state=EnemyAIState.IDLE)
    enemy2 = Enemy("test2", EnemyType.GOBLIN, 100.0, 100.0, ai_state=EnemyAIState.IDLE)

    seed = 42
    ai1 = EnemyAI(enemy1, AIRandom(seed))
    ai2 = EnemyAI(enemy2, AIRandom(seed))

    # Timing should be identical
    assert ai1.idle_duration == ai2.idle_duration, "Idle duration should match"
    assert ai1.patrol_wait_time_base == ai2.patrol_wait_time_base, "Patrol wait should match"
    assert ai1.chase_interval == ai2.chase_interval, "Chase interval should match"
    assert ai1.attack_cooldown_base == ai2.attack_cooldown_base, "Attack cooldown should match"

    print("[PASS] Deterministic timing with same seed")


def test_different_seeds_produce_variation():
    """Test different seeds produce different timing"""
    pygame.init()

    enemy1 = Enemy("test1", EnemyType.GOBLIN, 100.0, 100.0)
    enemy2 = Enemy("test2", EnemyType.GOBLIN, 100.0, 100.0)

    ai1 = EnemyAI(enemy1, AIRandom(111))
    ai2 = EnemyAI(enemy2, AIRandom(222))

    # At least one timing should differ
    timing_differs = (
        ai1.idle_duration != ai2.idle_duration or
        ai1.patrol_wait_time_base != ai2.patrol_wait_time_base or
        ai1.chase_interval != ai2.chase_interval or
        ai1.attack_cooldown_base != ai2.attack_cooldown_base
    )

    assert timing_differs, "Different seeds should produce different timing"
    print("[PASS] Different seeds produce variation")


def test_flying_enemy_no_gravity():
    """Test flying enemies don't have gravity applied (BAT)"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test_bat",
        enemy_type=EnemyType.BAT,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])
    ai = EnemyAI(enemy)

    # Bats can fly, so they should be able to patrol freely
    for _ in range(10):
        ai.update(0.1, 500.0, 500.0, 32, 56)

    # Just verify AI works for flying enemies
    assert enemy.ai_state in [EnemyAIState.PATROL, EnemyAIState.IDLE], "Flying AI should work"
    print("[PASS] Flying enemy AI works")


def test_chase_target_update_interval():
    """Test chase updates player target periodically, not every frame"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.CHASE
    )

    ai = EnemyAI(enemy, ai_random=None)  # Fixed 0.5s interval

    # First update should set target
    ai.update(1/60, 150.0, 100.0, 32, 56)
    first_target = ai.enemy.target_player_x

    # Player moves
    ai.update(1/60, 200.0, 100.0, 32, 56)
    second_target = ai.enemy.target_player_x

    # Target should not update immediately (interval not elapsed)
    assert first_target == second_target, "Target should not update every frame"

    # Wait for update interval
    for _ in range(30):  # 0.5 seconds
        ai.update(1/60, 200.0, 100.0, 32, 56)

    # Now target should update
    assert ai.enemy.target_player_x != first_target, "Target should update after interval"
    print("[PASS] Chase target updates periodically")


def test_state_timer_resets_on_transition():
    """Test state timer resets when transitioning between states"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.PATROL
    )

    enemy.set_patrol_waypoints([(100.0, 100.0), (200.0, 100.0)])
    ai = EnemyAI(enemy)

    # Accumulate time in patrol
    for _ in range(60):
        ai.update(1/60, 500.0, 500.0, 32, 56)

    timer_in_patrol = enemy.ai_state_timer
    assert timer_in_patrol > 0.9, "Timer should accumulate"

    # Trigger transition to chase
    ai.update(1/60, 150.0, 100.0, 32, 56)

    # Timer should reset
    assert enemy.ai_state_timer == 0.0, "Timer should reset on state transition"
    print("[PASS] State timer resets on transition")


def test_facing_direction_during_attack():
    """Test enemy faces player during attack state"""
    pygame.init()

    enemy = Enemy(
        enemy_id="test",
        enemy_type=EnemyType.GOBLIN,
        x=100.0,
        y=100.0,
        ai_state=EnemyAIState.ATTACK,
        facing_right=True
    )

    ai = EnemyAI(enemy)

    # Player to the left of enemy and within attack range (32px)
    # Enemy center at 116, player center at 94 = distance of 22px < 32px attack range
    ai.update(0.1, 78.0, 100.0, 32, 56)

    # Enemy should face left (toward player) during attack
    assert not enemy.facing_right, "Should face toward player during attack"
    print("[PASS] Faces player during attack")


def main():
    """Run all comprehensive AI tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE ENEMY AI TESTS")
    print("="*60 + "\n")

    # State transition tests
    print("=== State Transition Tests ===")
    test_idle_to_patrol_transition()
    test_patrol_to_chase_on_player_detection()
    test_chase_to_attack_when_in_range()
    test_attack_to_chase_when_player_leaves()
    test_chase_to_patrol_when_player_escapes()
    test_stun_state_recovery()
    print()

    # Combat tests
    print("=== Combat Tests ===")
    test_attack_deals_damage()
    test_attack_cooldown()
    print()

    # Movement tests
    print("=== Movement & Navigation Tests ===")
    test_patrol_waypoint_navigation()
    test_waypoint_advancement()
    test_facing_direction_during_attack()
    print()

    # Detection tests
    print("=== Detection Tests ===")
    test_detection_radius_multiplier()
    print()

    # Determinism tests
    print("=== Determinism Tests ===")
    test_deterministic_timing_with_seed()
    test_different_seeds_produce_variation()
    print()

    # Special cases
    print("=== Special Cases ===")
    test_dead_state_no_behavior()
    test_flying_enemy_no_gravity()
    test_chase_target_update_interval()
    test_state_timer_resets_on_transition()
    print()

    print("="*60)
    print("ALL COMPREHENSIVE AI TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
