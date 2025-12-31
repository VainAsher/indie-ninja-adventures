"""
Test Runner for Vain Asher Gaming's: Indie Ninja Adventures

Runs all test suites in organized categories.
Can run all tests, specific categories, or individual test files.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run unit tests only
    python run_tests.py --integration      # Run integration tests only
    python run_tests.py --edge             # Run edge case tests only
    python run_tests.py --verbose          # Run with verbose output
"""

import sys
import subprocess
import os

# Add project root to Python path so tests can find modules
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Test categories
TEST_CATEGORIES = {
    "unit": [
        "tests/unit/test_core_infrastructure.py",
        "tests/unit/test_collision_system.py",
        "tests/unit/test_jump_mechanic.py",
        "tests/unit/test_physics_system.py",
        "tests/unit/test_input_pipeline.py",
    ],
    "integration": [
        "tests/integration/test_player_integration.py",
        "tests/integration/test_demo_simple.py",
        "tests/integration/test_play_modes.py",
        "tests/integration/test_objective_coin_run.py",
    ],
    "edge": [
        "tests/edge_cases/test_wall_collision.py",
        "tests/edge_cases/test_corner_collision.py",
        "tests/edge_cases/test_crouch_jump.py",
        "tests/edge_cases/test_falling_collision.py",
        "tests/edge_cases/test_falling_corner.py",
        "tests/edge_cases/test_wall_clip.py",
        "tests/edge_cases/test_equal_overlap.py",
        "tests/edge_cases/test_threshold_balance.py",
    ]
}


def run_test_file(test_path: str, verbose: bool = False) -> bool:
    """
    Run a single test file.

    Args:
        test_path: Path to test file
        verbose: Whether to show detailed output

    Returns:
        True if tests passed, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Running: {test_path}")
    print(f"{'='*60}")

    try:
        # Run the test file with project root in PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = PROJECT_ROOT

        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=not verbose,
            text=True,
            timeout=30,
            env=env
        )

        if result.returncode == 0:
            print(f"[PASS] {test_path}")
            if verbose and result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"[FAIL] {test_path}")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {test_path} (exceeded 30 seconds)")
        return False
    except Exception as e:
        print(f"[ERROR] {test_path} - {e}")
        return False


def run_category(category: str, verbose: bool = False) -> tuple[int, int]:
    """
    Run all tests in a category.

    Args:
        category: Category name (unit, integration, edge)
        verbose: Whether to show detailed output

    Returns:
        Tuple of (passed_count, total_count)
    """
    if category not in TEST_CATEGORIES:
        print(f"❌ Unknown category: {category}")
        return 0, 0

    tests = TEST_CATEGORIES[category]
    passed = 0
    total = len(tests)

    print(f"\n{'#'*60}")
    print(f"# Running {category.upper()} Tests ({total} files)")
    print(f"{'#'*60}")

    for test_path in tests:
        if run_test_file(test_path, verbose):
            passed += 1

    return passed, total


def run_all_tests(verbose: bool = False) -> bool:
    """
    Run all test categories.

    Args:
        verbose: Whether to show detailed output

    Returns:
        True if all tests passed, False otherwise
    """
    print(f"\n{'#'*60}")
    print("# VAIN ASHER GAMING'S: INDIE NINJA ADVENTURES")
    print("# Test Suite Runner")
    print(f"{'#'*60}")

    total_passed = 0
    total_tests = 0

    # Run each category
    for category in ["unit", "integration", "edge"]:
        passed, total = run_category(category, verbose)
        total_passed += passed
        total_tests += total

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
    print(f"{'='*60}")

    if total_passed == total_tests:
        print("[PASS] ALL TESTS PASSED!")
        return True

    print(f"[FAIL] {total_tests - total_passed} TEST(S) FAILED")
    return False


def main():
    """Main entry point."""
    args = sys.argv[1:]
    verbose = "--verbose" in args or "-v" in args

    # Remove verbose flag from args
    args = [arg for arg in args if arg not in ["--verbose", "-v"]]

    # Determine what to run
    if not args:
        # Run all tests
        success = run_all_tests(verbose)
        sys.exit(0 if success else 1)

    elif "--unit" in args:
        passed, total = run_category("unit", verbose)
        sys.exit(0 if passed == total else 1)

    elif "--integration" in args:
        passed, total = run_category("integration", verbose)
        sys.exit(0 if passed == total else 1)

    elif "--edge" in args:
        passed, total = run_category("edge", verbose)
        sys.exit(0 if passed == total else 1)

    elif "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    else:
        print(f"Unknown argument: {args[0]}")
        print("Use --help for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
