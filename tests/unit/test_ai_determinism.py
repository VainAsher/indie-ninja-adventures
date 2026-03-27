"""
Unit Test: AI Determinism

Tests that AI timing decisions are deterministic and reproducible with the same seed.
This ensures replay accuracy and natural behavior variation between enemies.
"""

import sys
from pathlib import Path

# Add project root to path (two levels up from this file)
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame

from entities.ai_random import (
    AIRandom,
    derive_ai_seed,
    get_varied_attack_cooldown,
    get_varied_chase_interval,
    get_varied_idle_duration,
    get_varied_patrol_wait,
)
from entities.enemy import Enemy, EnemyAIState, EnemyType
from entities.enemy_ai import EnemyAI


def test_airandom_same_seed_produces_same_values():
    """Test that same seed produces identical random values"""
    seed = 12345

    # Create two RNGs with same seed
    rng1 = AIRandom(seed)
    rng2 = AIRandom(seed)

    # Generate values from both
    values1 = [rng1.uniform(0.0, 1.0) for _ in range(10)]
    values2 = [rng2.uniform(0.0, 1.0) for _ in range(10)]

    # Should be identical
    assert values1 == values2, "Same seed should produce identical values"
    print(f"[PASS] Same seed produces identical values: {values1[:3]}...")


def test_airandom_different_seeds_produce_different_values():
    """Test that different seeds produce different random values"""
    rng1 = AIRandom(12345)
    rng2 = AIRandom(54321)

    # Generate values
    values1 = [rng1.uniform(0.0, 1.0) for _ in range(10)]
    values2 = [rng2.uniform(0.0, 1.0) for _ in range(10)]

    # Should be different
    assert values1 != values2, "Different seeds should produce different values"
    print("[PASS] Different seeds produce different values")


def test_airandom_reset_restores_sequence():
    """Test that reset() restores the RNG to initial state"""
    rng = AIRandom(99999)

    # Generate some values
    first_values = [rng.uniform(0.0, 1.0) for _ in range(5)]

    # Reset
    rng.reset()

    # Generate same number of values
    second_values = [rng.uniform(0.0, 1.0) for _ in range(5)]

    # Should be identical to first sequence
    assert first_values == second_values, "Reset should restore sequence"
    print("[PASS] Reset restores RNG sequence")


def test_derive_ai_seed_is_deterministic():
    """Test that seed derivation is deterministic"""
    base_seed = 42
    enemy_id = "enemy_0"

    seed1 = derive_ai_seed(base_seed, enemy_id)
    seed2 = derive_ai_seed(base_seed, enemy_id)

    assert seed1 == seed2, "Seed derivation should be deterministic"
    print(f"[PASS] Seed derivation is deterministic: {seed1}")


def test_derive_ai_seed_different_ids_produce_different_seeds():
    """Test that different enemy IDs produce different seeds"""
    base_seed = 42

    seed1 = derive_ai_seed(base_seed, "enemy_0")
    seed2 = derive_ai_seed(base_seed, "enemy_1")

    assert seed1 != seed2, "Different enemy IDs should produce different seeds"
    print(f"[PASS] Different IDs produce different seeds: {seed1} vs {seed2}")


def test_timing_variations_within_expected_range():
    """Test that timing variations are within expected ranges"""
    rng = AIRandom(777)

    # Test patrol wait time (±30%)
    patrol_times = [get_varied_patrol_wait(rng, 1.0) for _ in range(100)]
    assert all(0.7 <= t <= 1.3 for t in patrol_times), "Patrol times should be in [0.7, 1.3]"

    # Test chase interval (±20%)
    chase_intervals = [get_varied_chase_interval(rng, 0.5) for _ in range(100)]
    assert all(0.4 <= t <= 0.6 for t in chase_intervals), "Chase intervals should be in [0.4, 0.6]"

    # Test attack cooldown (±15%)
    attack_cooldowns = [get_varied_attack_cooldown(rng, 1.0) for _ in range(100)]
    assert all(
        0.85 <= t <= 1.15 for t in attack_cooldowns
    ), "Attack cooldowns should be in [0.85, 1.15]"

    # Test idle duration (±40%)
    idle_durations = [get_varied_idle_duration(rng, 1.0) for _ in range(100)]
    assert all(0.6 <= t <= 1.4 for t in idle_durations), "Idle durations should be in [0.6, 1.4]"

    print("[PASS] All timing variations within expected ranges")


def test_timing_variations_without_rng_returns_base_values():
    """Test that timing functions return base values when ai_random is None"""
    # No RNG provided
    patrol_time = get_varied_patrol_wait(None, 1.0)
    chase_interval = get_varied_chase_interval(None, 0.5)
    attack_cooldown = get_varied_attack_cooldown(None, 1.0)
    idle_duration = get_varied_idle_duration(None, 1.0)

    # Should return exact base values
    assert patrol_time == 1.0, "Should return base patrol time"
    assert chase_interval == 0.5, "Should return base chase interval"
    assert attack_cooldown == 1.0, "Should return base attack cooldown"
    assert idle_duration == 1.0, "Should return base idle duration"

    print("[PASS] Timing functions return base values when RNG is None")


def test_enemy_ai_with_same_seed_produces_same_timing():
    """Test that EnemyAI with same seed produces identical timing"""
    pygame.init()

    # Create two enemies with same AI seed
    enemy1 = Enemy(enemy_id="test1", enemy_type=EnemyType.GOBLIN, x=100.0, y=100.0)

    enemy2 = Enemy(enemy_id="test2", enemy_type=EnemyType.GOBLIN, x=100.0, y=100.0)

    # Create AIs with same seed
    seed = 42
    ai1 = EnemyAI(enemy1, AIRandom(seed))
    ai2 = EnemyAI(enemy2, AIRandom(seed))

    # Check that timing parameters are identical
    assert ai1.idle_duration == ai2.idle_duration, "Idle duration should match"
    assert ai1.patrol_wait_time_base == ai2.patrol_wait_time_base, "Patrol wait time should match"
    assert ai1.chase_interval == ai2.chase_interval, "Chase interval should match"
    assert ai1.attack_cooldown_base == ai2.attack_cooldown_base, "Attack cooldown should match"

    print("[PASS] Same seed produces identical AI timing")
    print(f"  Idle: {ai1.idle_duration:.3f}s")
    print(f"  Patrol wait: {ai1.patrol_wait_time_base:.3f}s")
    print(f"  Chase interval: {ai1.chase_interval:.3f}s")
    print(f"  Attack cooldown: {ai1.attack_cooldown_base:.3f}s")


def test_enemy_ai_with_different_seeds_produces_different_timing():
    """Test that EnemyAI with different seeds produces varied timing"""
    pygame.init()

    # Create two enemies with different AI seeds
    enemy1 = Enemy(enemy_id="test1", enemy_type=EnemyType.GOBLIN, x=100.0, y=100.0)

    enemy2 = Enemy(enemy_id="test2", enemy_type=EnemyType.GOBLIN, x=100.0, y=100.0)

    # Create AIs with different seeds
    ai1 = EnemyAI(enemy1, AIRandom(111))
    ai2 = EnemyAI(enemy2, AIRandom(222))

    # At least one timing parameter should be different
    timing_matches = (
        ai1.idle_duration == ai2.idle_duration
        and ai1.patrol_wait_time_base == ai2.patrol_wait_time_base
        and ai1.chase_interval == ai2.chase_interval
        and ai1.attack_cooldown_base == ai2.attack_cooldown_base
    )

    assert not timing_matches, "Different seeds should produce at least some different timing"
    print("[PASS] Different seeds produce varied AI timing")


def test_enemy_ai_replay_consistency():
    """Test that AI behavior is consistent across multiple runs with same seed"""
    pygame.init()

    seed = 9999
    results = []

    # Run AI simulation 3 times with same seed
    for run in range(3):
        enemy = Enemy(
            enemy_id="test_replay",
            enemy_type=EnemyType.GOBLIN,
            x=100.0,
            y=100.0,
            ai_state=EnemyAIState.IDLE,
        )

        ai = EnemyAI(enemy, AIRandom(seed))

        # Simulate 10 frames of IDLE state
        state_transitions = []
        for frame in range(10):
            ai.update(
                dt=1 / 60,
                player_x=500.0,  # Player far away
                player_y=500.0,
                player_width=32,
                player_height=56,
            )
            state_transitions.append((frame, enemy.ai_state.name))

        results.append(state_transitions)

    # All runs should produce identical state transitions
    assert results[0] == results[1] == results[2], "Replay should be deterministic"
    print("[PASS] AI behavior is consistent across replays")


def test_enemy_ai_without_seed_still_works():
    """Test that AI works correctly without seeded random (backwards compatibility)"""
    pygame.init()

    enemy = Enemy(enemy_id="test_no_seed", enemy_type=EnemyType.GOBLIN, x=100.0, y=100.0)

    # Create AI without seed (None)
    ai = EnemyAI(enemy, ai_random=None)

    # Should have base timing values
    assert ai.idle_duration == 1.0, "Should use base idle duration"
    assert ai.patrol_wait_time_base == 1.0, "Should use base patrol wait"
    assert ai.chase_interval == 0.5, "Should use base chase interval"
    assert ai.attack_cooldown_base == 0.8, "Should use base attack cooldown"

    # Should still update correctly
    ai.update(dt=1 / 60, player_x=500.0, player_y=500.0, player_width=32, player_height=56)

    print("[PASS] AI works without seeded random (backwards compatible)")


def main():
    """Run all AI determinism tests"""
    print("\n" + "=" * 60)
    print("AI DETERMINISM TESTS")
    print("=" * 60 + "\n")

    test_airandom_same_seed_produces_same_values()
    test_airandom_different_seeds_produce_different_values()
    test_airandom_reset_restores_sequence()
    test_derive_ai_seed_is_deterministic()
    test_derive_ai_seed_different_ids_produce_different_seeds()
    test_timing_variations_within_expected_range()
    test_timing_variations_without_rng_returns_base_values()
    test_enemy_ai_with_same_seed_produces_same_timing()
    test_enemy_ai_with_different_seeds_produces_different_timing()
    test_enemy_ai_replay_consistency()
    test_enemy_ai_without_seed_still_works()

    print("\n" + "=" * 60)
    print("ALL AI DETERMINISM TESTS PASSED!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
