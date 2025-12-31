# Test Suite Documentation
**Vain Asher Gaming's: Indie Ninja Adventures**

This directory contains all automated tests for the project, organized by test type.

---

## Test Organization

```
tests/
 unit/                  # Unit tests (individual components)
 integration/           # Integration tests (systems working together)
 edge_cases/            # Edge case and regression tests
 playability/           # Simulation utilities for playability validation
 README.md              # This file
```

---

## Test Categories

### Unit Tests (`unit/`)

Tests individual components in isolation without dependencies.

**Current Tests**:
- `test_core_infrastructure.py` - Event bus, logger, clock, state
- `test_collision_system.py` - AABB collision detection
- `test_jump_mechanic.py` - Jump mechanic all types
- `test_physics_system.py` - Gravity and velocity integration

**Purpose**:
- Verify individual components work correctly
- Fast execution (< 1 second each)
- No external dependencies
- High code coverage

**When to Add**:
- Creating new mechanic or system
- Fixing a bug in specific component
- Refactoring existing code

### Integration Tests (`integration/`)

Tests multiple systems working together.

**Current Tests**:
- `test_player_integration.py` - Player with all mechanics
- `test_demo_simple.py` - Simple demo scenario

**Purpose**:
- Verify systems integrate correctly
- Test realistic game scenarios
- Catch integration bugs
- Validate game loop

**When to Add**:
- Adding new system that interacts with others
- Creating new entity types
- Testing complete gameplay flows

### Edge Cases (`edge_cases/`)

Tests corner cases, boundary conditions, and regressions.

**Current Tests**:
- `test_wall_collision.py` - Wall boundary testing
- `test_corner_collision.py` - Platform edge landing
- `test_crouch_jump.py` - Crouch + jump interaction
- `test_falling_collision.py` - Falling + horizontal movement
- `test_falling_corner.py` - Jitter scenario
- `test_wall_clip.py` - Wall clipping prevention
- `test_equal_overlap.py` - Equal overlap cases
- `test_threshold_balance.py` - Collision threshold tuning

**Purpose**:
- Prevent regressions
- Test unusual situations
- Validate bug fixes
- Stress test edge conditions

**When to Add**:
- Fixing a bug (add regression test)
- Finding edge case during testing
- User reports unusual behavior

### Additional Validation

Quick validations:
- World generation scripts: `tests/world_gen/test_world_gen.py`, `tests/world_gen/test_zone_planning.py`, `tests/world_gen/test_zone_complexity.py`, `tests/world_gen/test_full_generation.py`
- Playability validation: `test_playability_validation.py`
- `tests/legacy/test_wall_collision_legacy.py` (legacy regression)

---

## Running Tests

### Run All Tests

```bash
# From project root
python -m pytest tests/

# Or run manually
python tests/unit/test_core_infrastructure.py
python tests/unit/test_collision_system.py
# ... etc
```

### Run by Category

```bash
# Unit tests only
python -m pytest tests/unit/

# Integration tests only
python -m pytest tests/integration/

# Edge cases only
python -m pytest tests/edge_cases/
```

### Run Specific Test

```bash
# By file
python tests/unit/test_jump_mechanic.py

# By test function (with pytest)
python -m pytest tests/unit/test_jump_mechanic.py::test_ground_jump
```

---

## Writing New Tests

### Test Structure

```python
"""
Test module for [component name]

Tests:
- Test case 1
- Test case 2
- Test case 3
"""

import pygame
# Import component to test
from systems.my_system import MySystem

pygame.init()

# Test functions
def test_basic_functionality():
    """Test basic [component] functionality"""
    # Arrange
    system = MySystem()

    # Act
    result = system.do_something()

    # Assert
    assert result == expected_value
    print("[PASS] Basic functionality")

def test_edge_case():
    """Test edge case [description]"""
    # Test code
    pass

# Main execution
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Testing [Component Name]")
    print(f"{'='*60}\n")

    test_basic_functionality()
    test_edge_case()

    print(f"\n{'='*60}")
    print("[PASS] ALL TESTS PASSED")
    print(f"{'='*60}\n")
```

### Best Practices

1. **Naming**:
   - Test files: `test_<component_name>.py`
   - Test functions: `test_<what_is_being_tested>()`
   - Descriptive names that explain what's tested

2. **Organization**:
   - One test file per component/system
   - Group related tests together
   - Use clear section comments

3. **Assertions**:
   - Use descriptive assertion messages
   - Test one concept per test function
   - Print results clearly

4. **Documentation**:
   - Module docstring explaining what's tested
   - Function docstrings for complex tests
   - Inline comments for tricky logic

5. **Independence**:
   - Each test should be independent
   - No shared state between tests
   - Clean up after tests if needed

---

## Test Coverage

### Current Coverage

- **Core systems & mechanics**: High coverage through unit + integration suites (event bus, logger, clock, state, collision, jump, physics, movement/dash/wall slide/crouch via integration).
- **World generation**: Moderate coverage via quick validations; comprehensive per-biome/per-room tests still pending.
- **Playability/regression**: Edge-case collision suites plus `test_playability_validation.py`.
- **Overall**: Broad coverage of critical systems; world-gen and rendering/UI remain the largest gaps. Formal percentage not yet measured.

### Coverage Goals

- **Unit Tests**: 95% code coverage
- **Integration Tests**: All major systems combinations
- **Edge Cases**: All known bugs have regression tests

---

## Test Results Format

### Expected Output

```
============================================================
Testing [Component Name]
============================================================

[PASS] Test case 1
[PASS] Test case 2
[PASS] Test case 3
...

============================================================
[PASS] ALL TESTS PASSED
============================================================
```

### Failure Output

```
[FAIL] Test case name
  Expected: X
  Actual: Y

Traceback:
  ...
```

---

## Continuous Integration

### Pre-Commit Checklist

Before committing code:

- [ ] Run all affected tests
- [ ] All tests pass
- [ ] Add tests for new features
- [ ] Add regression tests for bug fixes
- [ ] Update test documentation if needed

### Automation (Future)

- [ ] Set up GitHub Actions
- [ ] Run tests on every commit
- [ ] Generate coverage reports
- [ ] Automated test reports

---

## Test Data & Fixtures

### Common Test Fixtures

Located in `tests/fixtures/` (to be created):

- Level layouts for testing
- Player states
- Entity configurations
- Mock event buses

### Using Fixtures

```python
from tests.fixtures.player_states import default_player_state

def test_with_fixture():
    state = default_player_state()
    # Test with state
```

---

## Performance Testing

### Benchmarks

Located in `tests/benchmarks/` (to be created):

- Collision detection speed
- Event bus throughput
- Physics simulation performance
- Render loop timing

### Running Benchmarks

```bash
python tests/benchmarks/benchmark_collision.py
```

---

## Debugging Tests

### Verbose Output

```bash
# Enable verbose logging
python test_file.py --verbose

# Or set log level
LOG_LEVEL=DEBUG python test_file.py
```

### Debugging Single Test

```python
if __name__ == "__main__":
    # Comment out other tests
    test_specific_case()
```

### Using Pygame's Debug Mode

```python
import pygame
pygame.init()

# Create window for visual debugging
screen = pygame.display.set_mode((800, 600))

# Run test with visualization
```

---

## Known Issues

### Test Environment

- Some tests require pygame display (may fail in headless environments)
- Timing-sensitive tests may be flaky on slow hardware
- Windows-specific path handling in some tests

### Solutions

```python
# Skip tests requiring display
import os
if os.environ.get('CI'):
    pytest.skip("Skipping in CI environment")

# Add timeouts for flaky tests
import time
time.sleep(0.1)  # Give system time to settle
```

---

## Contributing Tests

### Adding New Tests

1. Determine test category (unit/integration/edge)
2. Create test file in appropriate directory
3. Follow naming conventions
4. Include docstrings
5. Ensure all tests pass
6. Update this README

### Test Review Checklist

- [ ] Tests are independent
- [ ] Tests are repeatable
- [ ] Tests have clear names
- [ ] Tests include docstrings
- [ ] Tests print clear output
- [ ] Tests follow project style
- [ ] Tests actually test what they claim to test

---

## Test Metrics

### Current Stats

- **Total Tests**: 14 test files
- **Test Functions**: ~50+ individual tests
- **Total Assertions**: ~200+
- **Average Run Time**: < 5 seconds (all tests)
- **Code Coverage**: ~85%

### Goals

- **Total Tests**: 25+ test files
- **Test Functions**: 100+ individual tests
- **Code Coverage**: 95%+
- **Run Time**: < 10 seconds (all tests)

---

## Resources

### Testing Documentation

- [Python unittest](https://docs.python.org/3/library/unittest.html)
- [pytest documentation](https://docs.pytest.org/)
- [Pygame testing](https://www.pygame.org/wiki/UnitTest)

### Project-Specific

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Understanding systems
- [SYSTEM_OVERVIEW.md](../SYSTEM_OVERVIEW.md) - API reference
- [docs/DEVLOG.md](../docs/DEVLOG.md) - Known issues and fixes

---

**Last Updated**: 2025-12-12
**Test Suite Version**: 0.4.0-dev
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
