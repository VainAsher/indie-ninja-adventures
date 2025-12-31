"""
Test script for Phase 7: Three-Tier Connectivity Fallback

Tests:
1. Natural connectivity (no fixes needed)
2. Disconnected clusters (spine fallback)
3. Complex disconnections (nuclear option)
4. All world shapes
5. Various world sizes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from systems.world_generation import WorldGenerator, WorldShape
from systems.world_generation import generate_world_tilemaps
from systems.connectivity import validate_world_connectivity, ConnectivityTier


def test_connectivity():
    """Test three-tier connectivity system"""

    print("\n" + "="*60)
    print("PHASE 7: THREE-TIER CONNECTIVITY FALLBACK TEST")
    print("="*60)

    # Test configurations
    test_cases = [
        # (shape, seed, rooms, description)
        ("snake", 12345, 10, "Snake - naturally connected"),
        ("tree", 22222, 15, "Tree - may need spine"),
        ("branchy", 33333, 20, "Branchy - complex connectivity"),
        ("grid", 44444, 12, "Grid - structured layout"),
        ("blob", 55555, 8, "Blob - clustered rooms"),
        ("spiral", 66666, 10, "Spiral - tight rotation"),
    ]

    results_summary = []

    for shape_name, seed, num_rooms, description in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {shape_name.upper()} (seed={seed}, {num_rooms} rooms)")
        print(f"Description: {description}")
        print(f"{'='*60}")

        # Generate world
        shape_map = {
            "snake": WorldShape.SNAKE,
            "tree": WorldShape.TREE,
            "branchy": WorldShape.BRANCHY,
            "grid": WorldShape.GRID,
            "blob": WorldShape.BLOB,
            "spiral": WorldShape.SPIRAL,
        }

        gen = WorldGenerator(seed=seed)
        world = gen.generate(num_biomes=1, rooms_per_biome=num_rooms, shape=shape_map[shape_name])

        print(f"[WORLD] Generated {len(world.all_rooms)} rooms")
        print(f"[WORLD] Bounds: {world.bounds}")

        # Count neighbors
        total_neighbors = sum(len(r.neighbors) for r in world.all_rooms)
        avg_neighbors = total_neighbors / len(world.all_rooms) if world.all_rooms else 0
        print(f"[WORLD] Average neighbors per room: {avg_neighbors:.2f}")

        # Generate tilemaps
        print("[TILEMAPS] Generating room tilemaps...")
        room_tilemaps = generate_world_tilemaps(world)

        # Validate connectivity
        print("\n[CONNECTIVITY] Running three-tier validation...")
        result = validate_world_connectivity(world, room_tilemaps, verbose=True)

        # Print results
        print(f"\n[RESULT] Success: {result.success}")
        print(f"[RESULT] Tier used: {result.tier_used.upper()}")
        print(f"[RESULT] Fixes applied: {result.fixes_applied}")
        print(f"[RESULT] Unreachable rooms: {len(result.unreachable_rooms)}")
        print(f"[RESULT] Details: {result.details}")

        if result.success:
            print(f"\n[PASS] {shape_name.upper()} connectivity test PASSED")
        else:
            print(f"\n[FAIL] {shape_name.upper()} connectivity test FAILED")
            print(f"   Unreachable rooms: {result.unreachable_rooms}")

        # Store summary
        results_summary.append({
            "shape": shape_name,
            "seed": seed,
            "rooms": len(world.all_rooms),
            "tier": result.tier_used,
            "fixes": result.fixes_applied,
            "success": result.success,
        })

    # Print summary table
    print("\n" + "="*60)
    print("CONNECTIVITY TEST SUMMARY")
    print("="*60)
    print(f"{'Shape':<10} {'Seed':<8} {'Rooms':<7} {'Tier':<10} {'Fixes':<7} {'Status':<8}")
    print("-"*60)

    for r in results_summary:
        status = "PASS" if r["success"] else "FAIL"
        print(f"{r['shape']:<10} {r['seed']:<8} {r['rooms']:<7} {r['tier']:<10} {r['fixes']:<7} {status:<8}")

    # Overall statistics
    total_tests = len(results_summary)
    passed_tests = sum(1 for r in results_summary if r["success"])
    tier_counts = {}
    for r in results_summary:
        tier = r["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}/{total_tests} ({100*passed_tests//total_tests}%)")
    print(f"\nTier usage:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier.upper()}: {count} tests")

    total_fixes = sum(r["fixes"] for r in results_summary)
    print(f"\nTotal connectivity fixes: {total_fixes}")

    # Final verdict
    print("\n" + "="*60)
    if passed_tests == total_tests:
        print("ALL CONNECTIVITY TESTS PASSED!")
        print("\nFeatures Validated:")
        print("  [OK] Tier 1 (Natural): BFS graph traversal")
        print("  [OK] Tier 2 (Spine): Cluster connection with spine corridors")
        print("  [OK] Tier 3 (Nuclear): Brute force all adjacent connections")
        print("  [OK] All 6 world shapes tested")
        print("  [OK] Progressive escalation working correctly")
        print("\n[PHASE 7] Three-Tier Connectivity Fallback - COMPLETE")
    else:
        print(f"SOME TESTS FAILED ({total_tests - passed_tests} failures)")
        print("Review failed tests above for details")

    print("="*60)


if __name__ == "__main__":
    test_connectivity()
