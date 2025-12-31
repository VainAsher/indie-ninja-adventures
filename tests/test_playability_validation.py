"""
Playability Validation Test Suite

Tests that procedurally generated worlds are playable using the
modular playability testing framework.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from systems.world_generation import WorldGenerator
from systems.zone_planning import ZonePlanner
from systems.room_generation import RoomGenerator

from tests.playability.validators import (
    ReachabilityValidator,
    JumpabilityValidator,
    NavigabilityValidator,
    SafetyValidator,
)
from tests.playability.metrics import PlayabilityMetrics, RoomMetrics, WorldMetrics


def test_single_room_playability(seed: int = 12345, verbose: bool = True):
    """Test playability of a single generated room"""

    if verbose:
        print("=" * 60)
        print("SINGLE ROOM PLAYABILITY TEST")
        print("=" * 60)
        print(f"Seed: {seed}\n")

    # Generate a single room
    world_gen = WorldGenerator(seed=seed)
    world = world_gen.generate(num_biomes=1, rooms_per_biome=1)

    # Plan zones
    zone_planner = ZonePlanner(seed=seed)
    for room in world.all_rooms:
        room.zone_grid = zone_planner.plan_room(room)

    # Generate tilemaps
    room_gen = RoomGenerator()
    for room in world.all_rooms:
        room.tilemap = room_gen.generate_tilemap(room)

    # Get the room
    room = world.all_rooms[0]

    if verbose:
        print(f"Room Type: {room.room_type.value}")
        print(f"Neighbors: {list(room.neighbor_dirs.keys())}")
        print(f"Doors: {sum(len(ports) for ports in room.door_ports.values())}")
        print()

    # Create validators
    validators = [
        ReachabilityValidator(min_reachability_pct=90.0),
        JumpabilityValidator(max_jump_height=3, max_jump_distance=5),
        NavigabilityValidator(),
        SafetyValidator(),
    ]

    # Run validation
    validation_results = []
    all_passed = True

    for validator in validators:
        passed = validator.validate(room)
        result = validator.get_report()
        validation_results.append(result)

        if verbose:
            status = "[OK]" if passed else "[FAIL]"
            print(f"{status} {validator.name}")

            if result['errors']:
                for error in result['errors']:
                    print(f"  ERROR: {error}")

            if result['warnings']:
                for warning in result['warnings']:
                    print(f"  WARN: {warning}")

        if not passed:
            all_passed = False

    # Collect metrics
    metrics = PlayabilityMetrics.analyze_room(room, validation_results)

    if verbose:
        print()
        print("-" * 60)
        print("METRICS:")
        print(f"  Obstacle Density: {metrics.obstacle_density * 100:.1f}%")
        print(f"  Platform Density: {metrics.platform_density * 100:.1f}%")
        print(f"  Platforms: {metrics.num_platforms}")
        print(f"  Doors: {metrics.num_doors}")
        print(f"  Validators Passed: {len(metrics.validators_passed)}/{len(validators)}")
        print(f"  Warnings: {len(metrics.warnings)}")
        print()

        if all_passed:
            print("[OK] ROOM IS PLAYABLE!")
        else:
            print("[FAIL] ROOM HAS PLAYABILITY ISSUES")

        print("=" * 60)

    return all_passed, metrics


def test_world_playability(seed: int = 12345, num_rooms: int = 16, verbose: bool = True):
    """Test playability of entire generated world"""

    if verbose:
        print("=" * 60)
        print("WORLD PLAYABILITY TEST")
        print("=" * 60)
        print(f"Seed: {seed}")
        print(f"Rooms: {num_rooms}\n")

    # Generate world
    world_gen = WorldGenerator(seed=seed)
    world = world_gen.generate(num_biomes=2, rooms_per_biome=num_rooms // 2)

    # Plan zones
    zone_planner = ZonePlanner(seed=seed)
    for room in world.all_rooms:
        room.zone_grid = zone_planner.plan_room(room)

    # Generate tilemaps
    room_gen = RoomGenerator()
    for room in world.all_rooms:
        room.tilemap = room_gen.generate_tilemap(room)

    if verbose:
        print(f"Generated {len(world.all_rooms)} rooms across {len(world.biomes)} biomes")
        print()

    # Create validators
    validators = [
        ReachabilityValidator(min_reachability_pct=90.0),
        JumpabilityValidator(max_jump_height=3, max_jump_distance=5),
        NavigabilityValidator(),
        SafetyValidator(),
    ]

    # Validate each room
    room_metrics_list = []
    playable_count = 0

    for i, room in enumerate(world.all_rooms):
        # Run all validators
        validation_results = []
        room_passed = True

        for validator in validators:
            validator.reset()
            passed = validator.validate(room)
            result = validator.get_report()
            validation_results.append(result)

            if not passed:
                room_passed = False

        # Collect metrics
        metrics = PlayabilityMetrics.analyze_room(room, validation_results)
        room_metrics_list.append(metrics)

        if room_passed:
            playable_count += 1

        if verbose:
            status = "[OK]" if room_passed else "[FAIL]"
            print(f"{status} Room {i + 1:2d} ({room.room_type.value:8s}) - "
                  f"{len(metrics.validators_passed)}/{len(validators)} validators passed")

    # Analyze world
    world_metrics = PlayabilityMetrics.analyze_world(world, room_metrics_list)

    if verbose:
        print()
        print("-" * 60)
        print("WORLD SUMMARY:")
        summary = world_metrics.get_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")

        print()
        print(f"Result: {playable_count}/{len(world.all_rooms)} rooms are playable")

        # Show failed rooms
        failed_rooms = world_metrics.get_failed_rooms()
        if failed_rooms:
            print()
            print("FAILED ROOMS:")
            for i, room_metric in enumerate(failed_rooms):
                room_idx = room_metrics_list.index(room_metric)
                print(f"  Room {room_idx + 1} ({room_metric.room_type}):")
                for failed_validator in room_metric.validators_failed:
                    print(f"    - {failed_validator}")

        print("=" * 60)

    world_passed = world_metrics.world_playability_pct >= 90.0

    return world_passed, world_metrics


def test_multiple_seeds(num_seeds: int = 10, rooms_per_world: int = 16):
    """Test playability across multiple random seeds"""

    print("=" * 60)
    print("MULTI-SEED PLAYABILITY TEST")
    print("=" * 60)
    print(f"Testing {num_seeds} different seeds with {rooms_per_world} rooms each\n")

    import random

    results = []

    for i in range(num_seeds):
        seed = random.randint(1, 999999)
        print(f"Testing seed {seed}... ", end="", flush=True)

        passed, world_metrics = test_world_playability(seed, rooms_per_world, verbose=False)

        results.append({
            'seed': seed,
            'passed': passed,
            'playability_pct': world_metrics.world_playability_pct,
            'avg_reachability': world_metrics.avg_reachability_pct,
        })

        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} ({world_metrics.world_playability_pct:.1f}% playable)")

    # Summary
    passed_count = sum(1 for r in results if r['passed'])
    avg_playability = sum(r['playability_pct'] for r in results) / len(results)
    avg_reachability = sum(r['avg_reachability'] for r in results) / len(results)

    print()
    print("-" * 60)
    print("SUMMARY:")
    print(f"  Seeds Tested: {num_seeds}")
    print(f"  Seeds Passed: {passed_count}/{num_seeds} ({passed_count / num_seeds * 100:.1f}%)")
    print(f"  Avg World Playability: {avg_playability:.1f}%")
    print(f"  Avg Room Reachability: {avg_reachability:.1f}%")

    # Show worst seeds
    worst_seeds = sorted(results, key=lambda r: r['playability_pct'])[:3]
    print()
    print("WORST PERFORMING SEEDS:")
    for r in worst_seeds:
        print(f"  Seed {r['seed']}: {r['playability_pct']:.1f}% playable")

    print("=" * 60)

    return passed_count == num_seeds


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test procedural world playability")
    parser.add_argument("--test", choices=["room", "world", "multi"], default="world",
                        help="Test type: single room, full world, or multiple seeds")
    parser.add_argument("--seed", type=int, default=12345,
                        help="Random seed for generation")
    parser.add_argument("--rooms", type=int, default=16,
                        help="Number of rooms for world test")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of seeds for multi-seed test")

    args = parser.parse_args()

    try:
        if args.test == "room":
            passed, _ = test_single_room_playability(seed=args.seed)
            sys.exit(0 if passed else 1)

        elif args.test == "world":
            passed, _ = test_world_playability(seed=args.seed, num_rooms=args.rooms)
            sys.exit(0 if passed else 1)

        elif args.test == "multi":
            passed = test_multiple_seeds(num_seeds=args.count, rooms_per_world=args.rooms)
            sys.exit(0 if passed else 1)

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
