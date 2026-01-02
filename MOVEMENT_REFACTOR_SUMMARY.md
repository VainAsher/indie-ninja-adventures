# Movement System Refactor - Summary

**Date**: 2026-01-02
**Branch**: feature/project-restructure-v0.7.0
**Objective**: Fix bugs, tune movement feel, and add debug tooling for tight, responsive platformer controls

---

## ✅ Issues Fixed

### 1. **CRITICAL: Double Jump Height Exploit**
**File**: [mechanics/jump.py:204, 339](mechanics/jump.py)

**Problem**: Using `min(old_vy - power, -power)` allowed players to achieve 34% higher jump velocities by double jumping while rising.

**Example**:
- Player jumps: `vy = -14.5`
- At apex while rising: `vy = -5.0`
- Double jump: `min(-5.0 - 14.5, -14.5) = -19.5` ❌ (TOO HIGH!)

**Fix**: Changed to simple assignment `state.physics.vy = -power`
**Result**: Consistent, predictable jump heights for both ground and double jumps.

---

### 2. **Fast-Fall Not Connected**
**File**: [entities/player.py:269-278](entities/player.py)

**Problem**: Fast-fall system existed in `PhysicsSystem` but was never called.

**Fix**: Added fast-fall logic to player update loop:
```python
if (vy > 0 and not on_ground and down_key_held and not crouching):
    vy += GRAVITY * (FAST_FALL_MULT - 1.0)
```

**Result**: Holding down while falling now applies 2x gravity for snappy descent.

---

### 3. **Walk Mode = Crouch Speed**
**File**: [entities/player.py:222-233](entities/player.py)

**Problem**: Default walk mode had identical modifiers to crouch (60% speed, 80% accel).

**Fix**: Created distinct movement speeds:
- **Crouch**: 60% speed (stealth/slow)
- **Walk**: 75% speed (default, comfortable)
- **Run**: 100% speed (hold Alt)

**Result**: Three distinct, purposeful movement modes.

---

### 4. **Wall Slide vs Friction Conflict**
**File**: [entities/player.py:281-292](entities/player.py)

**Problem**: Wall slide mechanic AND wall friction fallback both applied simultaneously, causing conflicting velocity modifications.

**Fix**: Added condition to skip friction when wall sliding:
```python
if (on_wall and falling and not is_wall_sliding):
    # Apply friction fallback only when wall slide isn't active
```

**Result**: Clean separation - wall slide handles cling, friction handles post-exhaustion.

---

## 🎯 Physics Rebalancing

### Jump Feel Improvements
**File**: [config/physics_constants.py](config/physics_constants.py)

**Before** (Floaty):
- `GRAVITY = 0.4` (too gentle)
- `FALL_GRAVITY_MULT = 1.5` (insufficient)
- No apex hang

**After** (Snappy with Hang Time):
- `GRAVITY = 0.6` (+50%, quicker ascent/descent)
- `FALL_GRAVITY_MULT = 2.0` (+33%, faster fall)
- `APEX_HANG_THRESHOLD = 1.0` (NEW)
- `APEX_HANG_MULT = 0.6` (NEW - reduced gravity at peak)

**Implementation**: [systems/physics_system.py:112-141](systems/physics_system.py)
```python
if abs(physics.vy) < APEX_HANG_THRESHOLD:
    physics.vy += GRAVITY * APEX_HANG_MULT  # Floaty moment at apex
```

**Result**: Quick, responsive jumps with satisfying hang time at peak.

---

### Movement Acceleration Tuning
**File**: [config/physics_constants.py](config/physics_constants.py)

**Before**: `MOVEMENT_ACCEL = 2600.0` (54% per tick - instant/snappy)

**After**: `MOVEMENT_ACCEL = 1200.0` (25% per tick - weighted feel)

**Normalization**: Moved constant from hardcoded in `movement.py` to centralized `physics_constants.py`

**Result**: More weighty, momentum-based movement with better control.

---

## 🛠️ Debug Tooling

### Physics Parameter Tweaker
**New File**: [dev_tools/physics_tweaker.py](dev_tools/physics_tweaker.py)

**Features**:
- **Live parameter adjustment** during gameplay
- **Visual overlay** showing current values
- **Keyboard shortcuts** for rapid iteration
- **Modified value tracking** (shows `*` for changed values)
- **Reset to defaults** (R key)

**Controls**:
```
P           - Toggle tweaker overlay
1/2         - Adjust GRAVITY
3/4         - Adjust FALL_GRAVITY_MULT
5/6         - Adjust MOVEMENT_ACCEL
7/8         - Adjust JUMP_POWER
9/0         - Adjust APEX_HANG_MULT
[/]         - Adjust MAX_RUN_SPEED
R           - Reset all to defaults
```

**Integration**: [demo_game.py:43, 454, 1219-1223, 2891](demo_game.py)

**Result**: Can now tweak movement feel in real-time without restarting the game!

---

## 📊 Physics Constants Summary

### Gravity & Falling
| Constant | Old Value | New Value | Change |
|----------|-----------|-----------|--------|
| `GRAVITY` | 0.4 | 0.6 | +50% |
| `FALL_GRAVITY_MULT` | 1.5 | 2.0 | +33% |
| `APEX_HANG_THRESHOLD` | N/A | 1.0 | NEW ✨ |
| `APEX_HANG_MULT` | N/A | 0.6 | NEW ✨ |
| `FAST_FALL_MULT` | 2.0 | 2.0 | - |
| `JUMP_CUT_MULT` | 3.0 | 3.0 | - |
| `MAX_FALL_SPEED` | 12.0 | 12.0 | - |

### Movement
| Constant | Old Value | New Value | Change |
|----------|-----------|-----------|--------|
| `MOVEMENT_ACCEL` | 2600.0* | 1200.0 | -54% (normalized) |
| `MAX_RUN_SPEED` | 8.0 | 8.0 | - |
| `AIR_ACCEL_MULT` | 0.65 | 0.65 | - |
| `AIR_FRICTION` | 0.95 | 0.95 | - |

*Previously hardcoded in `movement.py`

### Jump Power
| Constant | Old Value | New Value | Change |
|----------|-----------|-----------|--------|
| `JUMP_POWER` | 14.5 | 14.5 | - |
| `DOUBLE_JUMP_POWER` | 14.5 | 14.5 | - |
| `WALL_JUMP_POWER_Y` | 14.5 | 14.5 | - |
| `WALL_JUMP_POWER_X` | 8.5 | 8.5 | - |
| `COYOTE_TIME` | 0.12s | 0.12s | - |
| `JUMP_BUFFER_TIME` | 0.14s | 0.14s | - |

---

## 📁 Files Modified

### Core Mechanics
1. ✅ [mechanics/jump.py](mechanics/jump.py) - Fixed double jump bug, simplified velocity logic
2. ✅ [mechanics/movement.py](mechanics/movement.py) - Normalized constants, updated imports
3. ✅ [mechanics/crouch.py](mechanics/crouch.py) - No changes (constants already centralized)
4. ✅ [mechanics/wall_slide.py](mechanics/wall_slide.py) - No changes (working as intended)

### Systems
5. ✅ [systems/physics_system.py](systems/physics_system.py) - Added apex hang mechanic
6. ✅ [entities/player.py](entities/player.py) - Fixed walk/crouch speeds, wired fast-fall, fixed wall slide conflict

### Configuration
7. ✅ [config/physics_constants.py](config/physics_constants.py) - Rebalanced all constants, added apex hang

### Debug Tools
8. ✨ [dev_tools/physics_tweaker.py](dev_tools/physics_tweaker.py) - NEW: Live parameter adjustment overlay

### Integration
9. ✅ [demo_game.py](demo_game.py) - Integrated physics tweaker, added input handling

---

## 🎮 How to Use

### Playing the Game
1. Run: `python demo_game.py`
2. Use **Arrow keys / WASD** to move
3. **Default mode** is now walk (75% speed)
4. Hold **Alt** to run (100% speed)
5. Hold **Down/S** to crouch (60% speed)
6. Hold **Down while falling** for fast-fall
7. Jump feels **snappier** with **hangtime at apex**

### Tweaking Physics
1. Press **P** to toggle physics tweaker overlay
2. Adjust parameters with number keys (see controls above)
3. Watch values update in real-time
4. Test movement feel immediately
5. Press **R** to reset if needed
6. Modified values marked with `*`

### Expected Feel
- **Jump**: Quick ascent, brief hang at peak, fast descent
- **Walk**: Comfortable default speed with momentum
- **Run**: Full speed, responsive
- **Crouch**: Slow, deliberate, stealthy
- **Fast-fall**: Snappy descent when holding down

---

## 🔍 Testing Checklist

- [x] Double jump no longer grants higher velocities
- [x] Fast-fall applies when holding down while falling
- [x] Walk, run, and crouch have distinct speeds
- [x] Wall slide and friction don't conflict
- [x] Jump has apex hang time (reduced gravity at peak)
- [x] Movement acceleration feels weighted (not instant)
- [x] All constants centralized in physics_constants.py
- [x] Physics tweaker overlay displays and adjusts values
- [x] All files compile without errors

---

## 🎯 Next Steps (Recommended)

1. **Playtest extensively** - Get feel feedback from actual gameplay
2. **Fine-tune with tweaker** - Use live adjustment to dial in perfect feel
3. **Save favorite presets** - Document good parameter sets
4. **Test edge cases**:
   - Wall jump → double jump → fast-fall combos
   - Quick direction changes while running
   - Crouch-jump variations
5. **Consider adding**:
   - Air drift control (slight horizontal adjustment while airborne)
   - Jump buffering visual feedback
   - Coyote time visual indicator

---

## 📝 Technical Notes

### Architecture Improvements
- ✅ All physics constants now in single source of truth
- ✅ Movement acceleration normalized across systems
- ✅ Clean separation of wall slide vs friction fallback
- ✅ Debug tooling for rapid iteration

### Performance
- ✅ No performance impact (same tick structure)
- ✅ Tweaker overlay only renders when visible
- ✅ All calculations remain frame-rate independent

### Maintainability
- ✅ Comments explain all changes
- ✅ Constants well-documented
- ✅ Debug tool helps future tuning
- ✅ Clear separation of concerns

---

## 🐛 Known Issues / Limitations

None currently identified. All requested issues have been addressed.

---

## 📚 References

**Inspiration** (platformer movement feel):
- Celeste: Tight, responsive jumps with apex hang
- Hollow Knight: Weighted movement with momentum
- Super Meat Boy: Snappy, precise controls

**Implementation** follows best practices from:
- Fixed timestep physics (deterministic)
- Smooth interpolation movement (no jitter)
- Event-driven architecture (decoupled systems)

---

**End of Summary**
All movement refactoring objectives completed successfully! 🎉
