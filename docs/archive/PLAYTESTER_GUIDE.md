# Playtester Guide - Vain Asher Gaming's Indie Ninja Adventures

**Version**: Pre-release (v0.3.0)
**Date**: 2025-12-14

Thank you for helping test Indie Ninja Adventures! This guide explains how to properly report bugs and issues so we can reproduce and fix them.

---

## Why Determinism Matters

This game is **fully deterministic** - the same seed always produces the same level, pickups, hazards, and physics. This means:

✓ **We can reproduce any bug** you encounter
✓ **Your replays show us exactly what happened**
✓ **Logs contain all the information we need**

---

## How to Report a Bug

### Step 1: Record Your Session

When you encounter a bug, the game should already be recording. If not, start recording:

```bash
# Record your gameplay
python demo_game.py --procedural --record bug_session
```

The recording captures:
- All your inputs (keypresses, timing)
- The world seed used
- Game version and settings
- Exact frame-by-frame state

### Step 2: Note the Details

When the bug occurs, note:
1. **What you were doing** (jumping, dashing, collecting coins, etc.)
2. **What you expected** to happen
3. **What actually happened**
4. **The seed number** (shown in top-left of screen)
5. **The room you were in** (shown in navigation panel)

### Step 3: Gather the Files

After experiencing the bug, collect these files:

1. **Replay file**: `user_data/replays/bug_session.json`
2. **Log file**: `user_data/logs/VainAsherGamings_IndieNinjaAdventures_YYYY-MM-DD_HH-MM-SS.log`
3. **Screenshot** (if visual bug): Press F12 or use system screenshot

### Step 4: Create a Bug Report

Create a text file called `bug_report.txt` with this format:

```
BUG REPORT
==========

Date: 2025-12-14
Game Version: v0.3.0

SUMMARY:
(Brief description - e.g., "Player fell through platform")

SEED: 42
ROOM TYPE: platform
APPROXIMATE TIME: 30 seconds into run

STEPS TO REPRODUCE:
1. Start game with seed 42
2. Jump to second platform
3. Dash mid-air
4. Player clips through platform

EXPECTED:
Player should land on platform

ACTUAL:
Player fell through platform into void below

FILES ATTACHED:
- bug_session.json (replay)
- VainAsherGamings_IndieNinjaAdventures_2025-12-14_15-30-45.log
- screenshot.png
```

### Step 5: Send the Report

Email or send via Discord:
- `bug_report.txt`
- `bug_session.json`
- Log file
- Screenshot (if applicable)

---

## Verifying Replays Work

Before sending a bug report, verify the replay works:

```bash
# Play back your recording
python demo_game.py --replay bug_session --show-replay
```

**The bug should reproduce exactly**. If it doesn't:
1. Note that in your bug report
2. Try recording again with `--record bug_session_2`
3. Send both recordings

---

## Understanding Determinism

### What IS Deterministic:
✓ World generation (same seed = same rooms)
✓ Pickup placement (coins, collectibles, health)
✓ Hazard placement (spikes, fire pits)
✓ Physics simulation (movement, collisions, falling)
✓ Enemy behavior (when implemented)

### What is NOT Deterministic:
✗ Your input timing (that's why we record it!)
✗ Frame rate (logs show if physics fell behind)
✗ Random test data you add manually

---

## Common Testing Scenarios

### Testing a Specific Seed

```bash
# Always test with explicit seeds for reproducibility
python demo_game.py --procedural --seed 12345 --record seed_12345_test
```

### Testing Different World Shapes

```bash
# Snake layout (long corridors)
python demo_game.py --procedural --shape snake --rooms 10 --seed 100

# Branchy layout (maze-like)
python demo_game.py --procedural --shape branchy --rooms 15 --seed 200

# Blob layout (clustered)
python demo_game.py --procedural --shape blob --rooms 8 --seed 300
```

### Headless Testing (for performance)

```bash
# Run without graphics for faster testing
python demo_game.py --procedural --seed 42 --headless --record headless_test
```

---

## Reading Log Files

Log files are in `user_data/logs/` and contain:

```
[TIMESTAMP] [LEVEL] [SYSTEM] Message
```

**Important sections to include in bug reports:**

### World Generation
```
[PROCEDURAL] World: 5 rooms, bounds: (5, 2, 7, 4)
[PICKUPS] Spawned: 22 coins, 0 collectibles
[HAZARDS] Spawned: 15 spikes, 2 voids
```

### Physics Errors
```
[ERROR] Physics falling behind! 11 ticks in one frame
```

### Collision Issues
```
[INFO] collision | Loaded 17147 tile colliders, 3915 platforms
```

### Player Deaths
```
[DEATH] Player died from spike, respawning at (7840, 7840)
```

---

## Testing Checklist

Before submitting a bug, verify:

- [ ] Can you reproduce it consistently?
- [ ] Did you record the session?
- [ ] Do you have the seed number?
- [ ] Does the replay show the bug?
- [ ] Did you attach the log file?
- [ ] Did you describe expected vs actual behavior?

---

## Known Limitations (Not Bugs)

These are **expected behavior** in pre-release:

1. **Physics warning on startup**: "Physics falling behind" on first frame is normal
2. **Shop rooms have no shops yet**: Placeholder for future NPC implementation
3. **Some rooms have no coins**: Shop rooms intentionally sparse
4. **Tutorial messages**: May appear multiple times (save system handles this)
5. **No enemies yet**: Combat rooms test hazard placement only

---

## Advanced: Manual Testing

### Determinism Verification

Run the test suite to verify determinism:

```bash
python tests/test_determinism.py
```

Should output:
```
✓ World generation is deterministic (5 rooms)
✓ Pickup spawning is deterministic (22 pickups)
✓ Hazard spawning is deterministic (15 hazards)
✓ Different seeds produce different worlds
✓ All position lists are properly sorted
✓ ALL TESTS PASSED - System is deterministic
```

### Comparing Two Runs

To verify exact determinism:

```bash
# Run 1
python demo_game.py --procedural --seed 999 --record run1 --headless

# Run 2 (same seed)
python demo_game.py --procedural --seed 999 --record run2 --headless

# Compare outputs (should be identical)
diff user_data/replays/run1.json user_data/replays/run2.json
```

No diff = perfectly deterministic ✓

---

## Performance Issues

If experiencing lag/stuttering:

1. **Check logs** for physics warnings
2. **Try headless mode** to isolate graphics
3. **Reduce world size**: `--rooms 5` instead of `--rooms 20`
4. **Include in bug report**: FPS shown in top-left corner

---

## Questions?

- Check `ARCHITECTURE.md` for technical details
- Check `POLISH_IMPROVEMENTS.md` for recent changes
- Check `REPLAY_DETERMINISM_FIX.md` for replay system details

---

## Thank You!

Your testing helps make this game better. Every bug report with proper logs and replays saves hours of debugging time!

**Remember**: Seed + Replay = Perfect Bug Reproduction
