# Playability Testing Framework

**Modular, extensible framework for validating that procedurally generated worlds are actually playable**

## Overview

The playability testing system validates procedurally generated worlds by simulating player movement and analyzing reachability, jump distances, navigation flow, and safety. It's designed to be:

- **Modular**: Each validator tests a specific aspect (reachability, jumpability, etc.)
- **Extensible**: Easy to add new validators for specific game mechanics
- **Automated**: Runs as part of test suite to catch generation issues early
- **Metrics-driven**: Collects quantitative data about world quality

## Architecture

```
tests/playability/
├── __init__.py           # Package exports
├── simulator.py          # Player movement simulation
├── validators.py         # Modular validation components
└── metrics.py            # Metrics collection & analysis

tests/
└── test_playability_validation.py  # Test suite
```

## Core Components

### 1. Player Simulator ([simulator.py](../tests/playability/simulator.py))

Simulates player movement through rooms using realistic physics:

```python
from tests.playability import PlayerSimulator

simulator = PlayerSimulator(room)
result = simulator.simulate_playability(spawn_x, spawn_y)

print(f"Reachability: {result.get_reachability_percentage():.1f}%")
print(f"Reachable tiles: {len(result.reachable_tiles)}")
print(f"Unreachable tiles: {len(result.unreachable_tiles)}")
```

**Player Capabilities (in tiles)**:
- Jump height: 3 tiles (~96 pixels)
- Double jump height: 5 tiles
- Horizontal jump distance: 5 tiles
- Wall jump height: 4 tiles
- Dash distance: 3 tiles

**Movement Actions**:
- `WALK_LEFT`, `WALK_RIGHT`: Basic movement
- `JUMP`, `DOUBLE_JUMP`: Vertical traversal
- `WALL_JUMP`: Climb walls
- `DASH`: Horizontal boost
- `FALL`: Gravity simulation

**Algorithm**: Breadth-first flood fill from spawn point, exploring all positions reachable with player movement capabilities.

### 2. Validators ([validators.py](../tests/playability/validators.py))

Modular validators for different playability aspects:

#### ReachabilityValidator

Validates that all walkable areas are reachable from spawn.

```python
validator = ReachabilityValidator(min_reachability_pct=90.0)
passed = validator.validate(room)

if not passed:
    print(validator.errors)  # List of validation errors
    print(validator.warnings)  # Non-critical warnings
```

**Checks**:
- >=90% of walkable tiles reachable from spawn
- All doors accessible
- Features (shops, save points) reachable

**Fails if**:
- Reachability < 90%
- Doors unreachable
- No valid spawn point

#### JumpabilityValidator

Validates that jumps are possible with player physics.

```python
validator = JumpabilityValidator(
    max_jump_height=3,
    max_jump_distance=5
)
passed = validator.validate(room)
```

**Checks**:
- No gaps wider than max jump distance
- No platforms higher than max jump height
- Jump sequences are possible

**Reports warnings** (not failures):
- Wide gaps that require dash/double jump
- High platforms requiring double jump or wall jump

#### NavigabilityValidator

Validates good room flow and navigation.

```python
validator = NavigabilityValidator()
passed = validator.validate(room)
```

**Checks**:
- Obstacle density (5-60% is good)
- Not too cramped (>60% obstacles)
- Not too empty (<5% obstacles)

**Reports warnings**:
- High obstacle density (cramped)
- Low obstacle density (boring)

#### SafetyValidator

Validates no player traps or softlocks.

```python
validator = SafetyValidator()
passed = validator.validate(room)
```

**Checks**:
- No inescapable pits
- No areas player can get stuck
- No deep pits (>8 tiles) without escape

**Reports warnings**:
- Deep pits that could trap player
- Potential softlock areas

### 3. Metrics ([metrics.py](../tests/playability/metrics.py))

Collects quantitative data about world quality.

```python
from tests.playability import PlayabilityMetrics

# Analyze single room
room_metrics = PlayabilityMetrics.analyze_room(room, validation_results)

print(f"Reachability: {room_metrics.reachability_pct:.1f}%")
print(f"Obstacle density: {room_metrics.obstacle_density * 100:.1f}%")
print(f"Validators passed: {len(room_metrics.validators_passed)}")

# Analyze entire world
world_metrics = PlayabilityMetrics.analyze_world(world, room_metrics_list)

print(f"World playability: {world_metrics.world_playability_pct:.1f}%")
print(f"Playable rooms: {world_metrics.playable_rooms}/{world_metrics.num_rooms}")
```

**RoomMetrics**:
- `reachability_pct`: Percentage of walkable tiles reachable
- `obstacle_density`: Percentage of solid obstacles
- `platform_density`: Percentage of platforms
- `num_platforms`, `num_gaps`, `num_doors`: Complexity metrics
- `validators_passed`, `validators_failed`: Validation results
- `warnings`: List of warnings

**WorldMetrics**:
- `world_playability_pct`: Percentage of rooms that pass validation
- `playable_rooms`: Count of playable rooms
- `avg_reachability_pct`: Average reachability across rooms
- `avg_obstacle_density`: Average obstacle density
- `get_failed_rooms()`: List of rooms with issues

## Usage Examples

### Test Single Room

```bash
python tests/test_playability_validation.py --test room --seed 12345
```

Output:
```
============================================================
SINGLE ROOM PLAYABILITY TEST
============================================================
Seed: 12345

Room Type: platform
Neighbors: ['up', 'down']
Doors: 2

[OK] ReachabilityValidator
[OK] JumpabilityValidator
[OK] NavigabilityValidator
[OK] SafetyValidator

------------------------------------------------------------
METRICS:
  Obstacle Density: 15.2%
  Platform Density: 8.3%
  Platforms: 124
  Doors: 2
  Validators Passed: 4/4
  Warnings: 12

[OK] ROOM IS PLAYABLE!
============================================================
```

### Test Full World

```bash
python tests/test_playability_validation.py --test world --seed 12345 --rooms 16
```

Output:
```
============================================================
WORLD PLAYABILITY TEST
============================================================
Seed: 12345
Rooms: 16

[OK] Room  1 (start   ) - 4/4 validators passed
[OK] Room  2 (platform) - 4/4 validators passed
[FAIL] Room  3 (combat ) - 3/4 validators passed
[OK] Room  4 (shop    ) - 4/4 validators passed
...

------------------------------------------------------------
WORLD SUMMARY:
  seed: 12345
  total_rooms: 16
  playable_rooms: 14
  world_playability: 87.5%
  avg_reachability: 92.3%
  avg_obstacle_density: 18.2%
  total_warnings: 45

Result: 14/16 rooms are playable

FAILED ROOMS:
  Room 3 (combat):
    - ReachabilityValidator
  Room 9 (boss):
    - ReachabilityValidator
============================================================
```

### Test Multiple Seeds

```bash
python tests/test_playability_validation.py --test multi --count 10 --rooms 16
```

Output:
```
============================================================
MULTI-SEED PLAYABILITY TEST
============================================================
Testing 10 different seeds with 16 rooms each

Testing seed 425819... [OK] (93.8% playable)
Testing seed 738291... [OK] (100.0% playable)
Testing seed 192847... [FAIL] (81.3% playable)
...

------------------------------------------------------------
SUMMARY:
  Seeds Tested: 10
  Seeds Passed: 8/10 (80.0%)
  Avg World Playability: 91.2%
  Avg Room Reachability: 94.5%

WORST PERFORMING SEEDS:
  Seed 192847: 81.3% playable
  Seed 556421: 85.7% playable
  Seed 394028: 87.5% playable
============================================================
```

## Adding Custom Validators

The framework is designed to be extended with custom validators:

```python
from tests.playability.validators import PlayabilityValidator

class MyCustomValidator(PlayabilityValidator):
    """Validates custom game mechanic"""

    def __init__(self, custom_param: float = 1.0):
        super().__init__("MyCustomValidator")
        self.custom_param = custom_param

    def validate(self, room: RoomNode) -> bool:
        """Validate room for custom mechanic"""
        self.reset()

        # Your validation logic here
        tilemap = room.tilemap

        if some_condition_fails:
            self.errors.append("Validation failed because...")
            return False

        if some_warning_condition:
            self.warnings.append("Warning: ...")

        return True  # Passed
```

Then use it in tests:

```python
validators = [
    ReachabilityValidator(),
    JumpabilityValidator(),
    MyCustomValidator(custom_param=2.0),  # Your validator
]

for validator in validators:
    validator.validate(room)
```

## Integration with World Generation

### During Development

Run tests after making changes to zone planning or room generation:

```bash
# Quick single-room test
python tests/test_playability_validation.py --test room

# Full world test
python tests/test_playability_validation.py --test world --rooms 16

# Comprehensive multi-seed test
python tests/test_playability_validation.py --test multi --count 20
```

### As Unit Tests

Integrate into pytest suite:

```python
# tests/unit/test_world_generation_playability.py
def test_world_generation_is_playable():
    """Test that generated worlds are playable"""
    from tests.test_playability_validation import test_world_playability

    passed, metrics = test_world_playability(seed=12345, num_rooms=16, verbose=False)

    assert passed, f"World not playable: {metrics.world_playability_pct:.1f}%"
    assert metrics.world_playability_pct >= 90.0
    assert metrics.avg_reachability_pct >= 85.0
```

### CI/CD Integration

Add to continuous integration pipeline:

```yaml
# .github/workflows/test.yml
- name: Test World Playability
  run: |
    python tests/test_playability_validation.py --test multi --count 5
```

## Performance

- **Single room validation**: ~50-200ms (depending on room complexity)
- **16-room world validation**: ~1-3 seconds
- **Multi-seed test (10 seeds × 16 rooms)**: ~20-30 seconds

Simulation uses BFS flood-fill which is O(n) where n = number of walkable tiles.

## Limitations & Future Enhancements

### Current Limitations

1. **Simplified physics**: Uses conservative tile-based movement, not pixel-perfect physics
2. **No advanced mechanics**: Doesn't test grappling hooks, teleporters, etc.
3. **Single-room only**: Doesn't validate multi-room navigation (yet)
4. **No AI simulation**: Doesn't test enemy placements or combat scenarios

### Planned Enhancements

1. **Advanced Mechanics Validators**:
   - Grappling hook points validator
   - Dash sequence validator
   - Wall-run chain validator

2. **Multi-Room Navigation**:
   - Door transition validator
   - World graph connectivity validator
   - Critical path analyzer

3. **Combat Validators**:
   - Enemy spawn point validator
   - Cover/line-of-sight validator
   - Arena balance validator

4. **Visual Debugging**:
   - Generate HTML reports with tilemap visualizations
   - Highlight unreachable areas in red
   - Show simulated movement paths

5. **Performance Optimization**:
   - Caching for repeated validations
   - Parallel validation of multiple rooms
   - Incremental validation during generation

## API Reference

### PlayerSimulator

```python
class PlayerSimulator:
    def __init__(self, room: RoomNode)
    def simulate_playability(self, start_x: int, start_y: int) -> SimulationResult
```

### SimulationResult

```python
@dataclass
class SimulationResult:
    success: bool
    reachable_tiles: Set[Tuple[int, int]]
    unreachable_tiles: Set[Tuple[int, int]]
    movement_path: List[Tuple[int, int, MovementAction]]
    errors: List[str]
    metrics: dict

    def get_reachability_percentage() -> float
```

### PlayabilityValidator (Base Class)

```python
class PlayabilityValidator(ABC):
    def __init__(self, name: str)
    @abstractmethod
    def validate(self, room: RoomNode) -> bool
    def get_report(self) -> Dict[str, Any]
    def reset(self)
```

### PlayabilityMetrics

```python
class PlayabilityMetrics:
    @staticmethod
    def analyze_room(room: RoomNode, validation_results: List[Dict]) -> RoomMetrics

    @staticmethod
    def analyze_world(world: World, room_metrics: List[RoomMetrics]) -> WorldMetrics
```

## Conclusion

The playability testing framework ensures that procedurally generated worlds are not just visually interesting, but actually playable. By catching issues early in development and providing quantitative metrics, it helps maintain high quality generation across all seeds and configurations.

The modular design makes it easy to extend for new game mechanics, and the automated testing ensures no regressions when modifying world generation algorithms.
