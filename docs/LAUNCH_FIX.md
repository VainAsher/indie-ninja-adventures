# Launch Error Fix

**Date**: 2025-12-13
**Error**: `AttributeError: 'CameraSystem' object has no attribute 'screen_w'`

---

## Problem

When launching the game with `python demo_game.py --procedural --rooms 10`, the game crashed with:

```
AttributeError: 'CameraSystem' object has no attribute 'screen_w'
```

At line 587 in demo_game.py:
```python
screen_w, screen_h = camera.screen_w, camera.screen_h  # ERROR: These don't exist!
```

---

## Root Cause

The `CameraSystem` class stores screen dimensions as:
- `camera.config.game_width`
- `camera.config.game_height`

NOT as `camera.screen_w` and `camera.screen_h`.

This was an error introduced during the performance optimization when adding frustum culling.

---

## Solution

**File**: [demo_game.py](../demo_game.py:587)

Changed line 587 from:
```python
screen_w, screen_h = camera.screen_w, camera.screen_h
```

To:
```python
screen_w, screen_h = camera.config.game_width, camera.config.game_height
```

---

## Verification

**Test Command**:
```bash
python demo_game.py --procedural --rooms 10 --seed 42
```

**Result**:
```
✅ Game launches successfully
✅ World generates (10 rooms, 81.2ms)
✅ Player spawns correctly at (11040, 11040)
✅ Game loop starts
✅ No errors
```

---

## Status

✅ **FIXED** - Game now launches and runs correctly.

---

*Quick fix for camera attribute error*
*Date: 2025-12-13*
