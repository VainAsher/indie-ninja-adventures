# Pre-Release Validation - Determinism & Testing

**Version**: v0.3.0
**Status**: PRE-RELEASE
**Core Tenet**: Deterministic, Reproducible, Debuggable

---

## Quick Validation Tests

### Test 1: Same Seed = Same World

```bash
# Run 1
python demo_game.py --procedural --seed 42 --headless
# Note the output: "Spawned: X coins, Y collectibles, Z spikes"

# Run 2 (should be IDENTICAL)
python demo_game.py --procedural --seed 42 --headless
# Output should match Run 1 exactly
```

**Expected Result**: Identical output for both runs
**If Different**: CRITICAL BUG - report immediately

### Test 2: Record and Replay

```bash
# Record a session
python demo_game.py --procedural --seed 123 --record test_replay

# Play it back
python demo_game.py --replay test_replay --show-replay
```

**Expected Result**: Replay shows exact same gameplay
**If Desynced**: Replay determinism broken - report with logs

### Test 3: Different Seeds = Different Worlds

```bash
# Seed 100
python demo_game.py --procedural --seed 100 --headless

# Seed 200
python demo_game.py --procedural --seed 200 --headless
```

**Expected Result**: Different spawn counts, different room layouts
**If Same**: RNG broken - report immediately

---

## What Gets Logged

Every session creates a log in `user_data/logs/` containing:

### 1. World Generation
```
[PROCEDURAL] World: 5 rooms, bounds: (5, 2, 7, 4)
[PROCEDURAL] Spawn point: (7840, 7840)
[PROCEDURAL] Exit point: (7840, 12960)
[PROCEDURAL] Room types: boss=1, combat=1, exit=1, platform=1, shop=1, start=1
```

### 2. Spawning (MUST be deterministic)
```
[PICKUPS] Spawned: 22 coins, 0 collectibles
[HAZARDS] Spawned: 15 spikes, 2 voids
```

### 3. Player Events
```
[INFO] player_0 | Player 0 initialized at (7840, 7840)
[INFO] player_0.jump | Executed ground_jump: vy 0.00 -> -14.50
[DEATH] Player died from spike, respawning at (7840, 7840)
```

### 4. Physics Warnings
```
[ERROR] clock | Physics falling behind! 11 ticks in one frame
[WARNING] clock | Frame time 301.4ms exceeds max 250.0ms
```

---

## Replay File Structure

Replays are stored in `user_data/replays/` as JSON:

```json
{
  "version": "0.3.0",
  "seed": 42,
  "procedural": true,
  "world_shape": "blob",
  "num_rooms": 5,
  "timestamp": "2025-12-14T21:44:36.123Z",
  "inputs": [
    {"frame": 0, "keys": []},
    {"frame": 60, "keys": ["jump"]},
    ...
  ]
}
```

All game state is derived from:
- **Seed** (determines world, pickups, hazards)
- **Inputs** (player actions)
- **Physics** (deterministic simulation)

---

## Bug Report Requirements

When reporting bugs, **ALWAYS include**:

### 1. Seed Number
```
Seed: 42
```

### 2. Spawn Information from Log
```
[PICKUPS] Spawned: 22 coins, 0 collectibles
[HAZARDS] Spawned: 15 spikes, 2 voids
```

### 3. Replay File
```
user_data/replays/bug_session.json
```

### 4. Log File
```
user_data/logs/VainAsherGamings_IndieNinjaAdventures_2025-12-14_HH-MM-SS.log
```

### 5. Can It Be Reproduced?
```
✓ YES - Same seed always triggers bug
✗ NO - Bug appears randomly
```

---

## Common Issues & Validation

### Issue: "Replay shows different pickups"
**Root Cause**: Spawn system not deterministic
**Validation**: Run same seed twice, compare spawn counts
**Status**: FIXED (v0.3.0) - positions now sorted

### Issue: "Physics falling behind"
**Root Cause**: Frame time exceeded, accumulator reset
**Validation**: Check logs for ERROR messages
**Status**: NORMAL on startup, ERROR if frequent

### Issue: "Coins in different places each run"
**Root Cause**: Non-sorted position lists before RNG
**Validation**: Check spawner code has `.sort()` calls
**Status**: FIXED (v0.3.0)

---

## Pre-Release Checklist

Before sending to playtesters:

- [ ] Run Test 1 (same seed = same world)
- [ ] Run Test 2 (record and replay works)
- [ ] Run Test 3 (different seeds = different worlds)
- [ ] Check logs directory exists and is writable
- [ ] Check replays directory exists and is writable
- [ ] Verify all spawning has `.sort()` for determinism
- [ ] Test headless mode (no graphics)
- [ ] Test with various seeds (42, 123, 999, 12345)
- [ ] Test with various world shapes (blob, snake, branchy)
- [ ] Test with various room counts (3, 5, 8, 10)

---

## Determinism Guarantees

### What IS Guaranteed Deterministic:
✓ World structure (same seed = same rooms)
✓ Pickup placement (coins, collectibles, health)
✓ Hazard placement (spikes, fire pits)
✓ Physics simulation (gravity, collisions)
✓ Platform positions
✓ Zone layouts
✓ Door placements

### What is NOT Deterministic (By Design):
✗ Frame rate (varies by system)
✗ Render timing (vsync, display lag)
✗ Log file timestamps
✗ User input timing (that's why we record it!)

---

## For Developers: Adding New Systems

If you add new procedural generation:

1. **Use explicit seeds**: Derive from world seed
   ```python
   spawner_seed = world_seed + room.grid_x * 1000 + room.grid_y
   ```

2. **Sort position lists**:
   ```python
   positions.sort()  # CRITICAL for determinism
   ```

3. **Test with same seed twice**:
   ```python
   # Must produce identical results
   assert run1_output == run2_output
   ```

4. **Document RNG usage**:
   ```python
   # Uses room-specific RNG for spawn positions
   self.rng = random.Random(room_seed)
   ```

---

## Emergency Validation Script

If determinism is suspected broken:

```bash
# Run automated test suite
python tests/test_determinism.py
```

**Expected Output:**
```
============================================================
Determinism Test Suite
============================================================

[PASS] World generation is deterministic (5 rooms)
[PASS] Pickup spawning is deterministic (X pickups)
[PASS] Hazard spawning is deterministic (Y hazards)
[PASS] Different seeds produce different worlds
[PASS] All position lists are properly sorted

============================================================
[PASS] ALL TESTS PASSED - System is deterministic
============================================================
```

**If tests fail**, the system will show which specific test failed and why.

---

## Version History

### v0.3.0 (2025-12-14)
- ✓ Fixed replay determinism (sorted position lists)
- ✓ Added intelligent spawning systems
- ✓ Enhanced HUD with navigation compass
- ✓ Comprehensive logging system
- ✓ Playtester documentation

### Future (v0.4.0+)
- [ ] Automated determinism CI tests
- [ ] Replay comparison tools
- [ ] Bug report auto-submission
- [ ] Determinism dashboard

---

## Contact & Support

**For Bug Reports**: Include seed + replay + logs
**For Questions**: Check `PLAYTESTER_GUIDE.md`
**For Technical Details**: Check `ARCHITECTURE.md`

**Remember**: Determinism = Debuggability!
