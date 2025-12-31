# Ninja Dash v0.3 - Testing & Bug Reporting Guide

## Table of Contents
1. [Quick Start Testing](#quick-start-testing)
2. [What Was Fixed in This Session](#what-was-fixed)
3. [How to Test Each Fix](#testing-each-fix)
4. [Running Automated Tests](#running-automated-tests)
5. [Manual Testing Procedures](#manual-testing-procedures)
6. [How to Report Bugs](#how-to-report-bugs)
7. [Known Issues & Limitations](#known-issues)
8. [Performance Testing](#performance-testing)

---

## Quick Start Testing

### Prerequisites
```bash
# Ensure you're in the project directory
cd c:\Users\asher\Downloads\ninja_dash_v0_3

# Activate virtual environment (if using one)
.venv\Scripts\activate

# Verify Python dependencies
python -c "import pygame; print('PyGame version:', pygame.version.ver)"
```

### Run All Tests
```bash
# Run complete test suite
python run_tests.py

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --edge
```

### Launch the Game
```bash
python demo_game.py
```

---

## What Was Fixed in This Session

### ✅ Fix #1: Failing Test (test_crouch_jump.py)
**Issue**: Test used outdated API
**Fix**: Updated to use `set_crouch(True)` instead of `request_crouch_toggle()`
**Impact**: Test suite now passes 100%

### ✅ Fix #2: Event Bus Memory Leak
**Issue**: Mechanics never unsubscribed from events, causing memory leaks
**Fix**: Implemented proper cleanup in `dash.py` and `jump.py`
**Impact**: Better memory management, especially in long play sessions

### ✅ Fix #3: Enemy Movement Stall
**Issue**: Enemies would freeze during patrol due to poor physics constants
**Fix**:
- Increased acceleration: 120 → 200 px/s²
- Increased friction: 0.85 → 0.92
**Impact**: Enemies now move smoothly without stalling

### ✅ Fix #4: Removed Kickstart Workaround
**Issue**: Band-aid code manually injected velocity when enemies stalled
**Fix**: Removed workaround since root cause is now fixed
**Impact**: Cleaner, more maintainable code

### ✅ Fix #5: NPC Interaction Priority
**Issue**: Game selected first NPC found, not closest one
**Fix**: Now calculates distance and returns closest NPC
**Impact**: Better UX when multiple NPCs overlap

### ✅ Fix #6: Inventory Bounds Checking
**Issue**: No validation on inventory operations, allowing exploits
**Fix**:
- Added MAX_CURRENCY = 999,999
- Added MAX_QUANTITY_PER_OPERATION = 9,999
- Validates all add/remove operations
**Impact**: Prevents negative items, currency overflow, and save file exploits

---

## Testing Each Fix

### Test #1: Crouch Jump
**Automated Test**:
```bash
python run_tests.py --edge
# Look for: [PASS] tests/edge_cases/test_crouch_jump.py
```

**Manual Test**:
1. Launch game: `python demo_game.py`
2. Press DOWN to crouch
3. Press SPACE to jump while crouched
4. Verify: Jump is lower than normal jump
5. Expected: Crouch jump works, reduced jump height

**Pass Criteria**: ✅ Crouch jump executes with ~70% normal jump power

---

### Test #2: Memory Leak Fix
**Automated Test**:
```bash
python run_tests.py --unit
# All tests should pass without memory warnings
```

**Manual Test** (Long Session):
1. Launch game
2. Play for 10+ minutes
3. Monitor task manager for memory usage
4. Expected: Memory stays stable (~200-300 MB), no steady increase

**Pass Criteria**: ✅ Memory doesn't grow beyond 500MB in 10-minute session

---

### Test #3 & #4: Enemy Movement
**Location**: Any mission with enemies (forest regions recommended)

**Test Procedure**:
1. Launch game
2. Select "Campaign" → "Forest Region" → Any mission with enemies
3. Observe enemy patrol behavior for 30 seconds
4. Let enemies detect you and chase you
5. Break line of sight and watch them return to patrol

**What to Look For**:
- ✅ **GOOD**: Enemies move smoothly during patrol
- ✅ **GOOD**: Smooth acceleration and deceleration
- ✅ **GOOD**: No sudden stops or jittering
- ❌ **BAD**: Enemies freeze mid-patrol
- ❌ **BAD**: Enemies vibrate/jitter in place

**Pass Criteria**:
- ✅ Enemies patrol continuously without stalling
- ✅ Smooth movement transitions
- ✅ No visible kickstart "jumps" in velocity

---

### Test #5: NPC Interaction Priority
**Location**: Any hub world with multiple NPCs (Town Hub recommended)

**Test Procedure**:
1. Launch game → Campaign → Town Hub
2. Find two NPCs close together (if spawned)
3. Position player between them
4. Press 'E' to interact
5. Expected: Game interacts with the CLOSEST NPC

**Manual Setup** (if NPCs aren't close):
1. Look for overlapping NPC interaction radiuses
2. Stand equidistant between two NPCs
3. Move slightly closer to one
4. Press 'E'
5. Verify interaction happens with the closer one

**Pass Criteria**: ✅ Closest NPC is always selected, not arbitrary

---

### Test #6: Inventory Bounds Checking
**Test 6A: Positive Quantity Validation**

**Test via Save File Edit**:
1. Close game if running
2. Open: `user_data\saves\savegame.json`
3. Try to add negative quantity:
   ```json
   {"item_id": "health_potion", "quantity": -5}
   ```
4. Save and launch game
5. Expected: Negative items rejected or clamped to 0

**Test 6B: Currency Overflow**

**Test via Python Console**:
```python
# Create a test inventory
from game.inventory_system import Inventory
inv = Inventory()

# Test negative currency (should be rejected)
inv.add_currency(-1000)
print(f"Currency after negative add: {inv.currency}")  # Should be 0

# Test overflow protection
inv.add_currency(999999)
print(f"Currency at max: {inv.currency}")  # Should be 999,999

inv.add_currency(100)
print(f"Currency after overflow attempt: {inv.currency}")  # Should still be 999,999

# Test massive quantity
result = inv.add_item("health_potion", 99999)
print(f"Massive add rejected: {not result}")  # Should be True (rejected)
```

**Pass Criteria**:
- ✅ Negative amounts rejected
- ✅ Currency capped at 999,999
- ✅ Quantities > 9,999 rejected

---

### Test #7: Save File Integrity (NEW - Session 2)

**Location**: `user_data\saves\savegame.json`

**Purpose**: Verify that save file tampering is detected and corrected

**Test 7A: Save File Signature Verification**

**Test Procedure**:
1. Launch game and play for 1 minute
2. Close game (saves automatically)
3. Open `user_data\saves\savegame.json` in text editor
4. Verify new save format:
   ```json
   {
     "version": "0.6.0",
     "signature": "a3f2b8d9...",  // 64-character hex string
     "data": {
       // Actual save data here
     }
   }
   ```
5. Note the signature value

**Expected**:
- ✅ Save file has "signature" field
- ✅ Signature is 64 characters long (SHA-256 hex)
- ✅ Save file has "data" field containing actual data

---

**Test 7B: Tampering Detection (Currency)**

**Test Procedure**:
1. Open `user_data\saves\savegame.json`
2. Find `data.campaign.currency` value
3. Change it to `999999999` (999 million)
4. Save the file WITHOUT changing signature
5. Launch game

**Expected Console Output**:
```
[SAVE] WARNING: Save file signature invalid! File may have been tampered with.
[SAVE] Loading anyway but applying strict validation...
[SAVE] WARNING: Save data validation issues detected:
[SAVE]   - Currency exceeds limit: 999999999 > 999999
[SAVE] Suspicious values have been clamped to safe ranges.
```

**In-Game Verification**:
- Open inventory or check currency
- Currency should be 999,999 (MAX_CURRENCY_LIMIT)
- NOT 999,999,999 (tampered value)

**Pass Criteria**:
- ✅ Warning message displayed
- ✅ Currency clamped to 999,999
- ✅ Game loads successfully
- ✅ Next save will have valid signature

---

**Test 7C: Negative Value Tampering**

**Test Procedure**:
1. Open `user_data\saves\savegame.json`
2. Find `data.campaign.player_inventory`
3. Add: `"health_potion": -5`
4. Save the file
5. Launch game

**Expected Console Output**:
```
[SAVE] WARNING: Save file signature invalid!
[SAVE] WARNING: Save data validation issues detected:
[SAVE]   - Negative inventory item: health_potion = -5
```

**In-Game Verification**:
- Open inventory
- Health potion quantity should be 0
- NOT -5 (negative exploit prevented)

**Pass Criteria**:
- ✅ Negative value detected
- ✅ Quantity set to 0
- ✅ Game loads normally

---

**Test 7D: Backwards Compatibility (Old Saves)**

**Test Procedure**:
1. Locate an old save file (from before Session 2)
   - Old format: No "signature" field, data at root level
2. Copy to `user_data\saves\savegame.json`
3. Launch game

**Expected Console Output**:
```
[SAVE] Old save format detected (no signature)
[SAVE] Loaded save file from user_data\saves\savegame.json
```

**In-Game Verification**:
- All data loads correctly
- Progress is preserved
- Next save will use new signed format

**Pass Criteria**:
- ✅ Old save loads successfully
- ✅ No errors or warnings (unless data is actually suspicious)
- ✅ Next save will have signature

---

**Test 7E: Multiple Tampering Attempts**

**Test Procedure**:
1. Tamper with multiple values:
   ```json
   {
     "data": {
       "campaign": {
         "currency": 999999999,
         "total_deaths": -10,
         "total_play_time": -100.0,
         "player_inventory": {
           "sword": 9999999
         }
       }
     }
   }
   ```
2. Launch game

**Expected Console Output**:
```
[SAVE] WARNING: Save file signature invalid!
[SAVE] WARNING: Save data validation issues detected:
[SAVE]   - Currency exceeds limit: 999999999 > 999999
[SAVE]   - Negative total_deaths: -10
[SAVE]   - Negative total_play_time: -100.0
[SAVE]   - Excessive inventory item: sword = 9999999
[SAVE] Suspicious values have been clamped to safe ranges.
```

**Expected Corrections**:
- Currency: 999,999
- Total deaths: 0
- Total play time: 0.0
- Sword quantity: 999

**Pass Criteria**:
- ✅ All tampering detected
- ✅ All values corrected
- ✅ Game playable with safe values

---

**Test 7F: Save Integrity After Correction**

**Test Procedure**:
1. After Test 7E (multiple tampering)
2. Play game for 30 seconds
3. Close game (auto-save)
4. Open `user_data\saves\savegame.json`
5. Check signature

**Expected**:
- New signature generated
- Corrected values saved
- File can be loaded without warnings

**Pass Criteria**:
- ✅ New valid signature present
- ✅ Corrected values persisted
- ✅ Next load shows "signature verified ✓"

---

**Quick Save Integrity Test (2 minutes)**:
```bash
# 1. Play game briefly
python demo_game.py
# Collect some currency, then quit

# 2. Tamper with save
# Edit user_data\saves\savegame.json
# Change currency to 999999999

# 3. Reload and verify warning
python demo_game.py
# Should see tampering warning
# Currency should be clamped to 999,999
```

---

## Running Automated Tests

### Full Test Suite
```bash
python run_tests.py
```

**Expected Output**:
```
############################################################
# Running ALL Tests
############################################################
...
[PASS] tests/unit/test_core_infrastructure.py
[PASS] tests/unit/test_collision_system.py
[PASS] tests/unit/test_jump_mechanic.py
[PASS] tests/edge_cases/test_crouch_jump.py
...
Total: 17 tests
Passed: 17
Failed: 0
Success Rate: 100%
```

### Test Categories

**Unit Tests** (Core systems):
```bash
python run_tests.py --unit
```
Tests: Event bus, collision, jump, physics, input

**Integration Tests** (Multi-system):
```bash
python run_tests.py --integration
```
Tests: Player integration, demo game, play modes, objectives

**Edge Case Tests** (Boundary conditions):
```bash
python run_tests.py --edge
```
Tests: Wall collision, corner collision, crouch jump, falling

### Individual Test
```bash
# Run single test file
python tests/edge_cases/test_crouch_jump.py

# Must set PYTHONPATH first:
set PYTHONPATH=.
python tests/edge_cases/test_crouch_jump.py
```

---

## Manual Testing Procedures

### Enemy AI Testing

**Test Enemy Patrol**:
1. Launch game
2. Campaign → Forest → Forest Mission 1
3. Find an enemy (goblin)
4. **DON'T get detected** - stay out of range
5. Observe patrol behavior for 60 seconds

**Checklist**:
- [ ] Enemy moves between waypoints
- [ ] Enemy doesn't freeze mid-patrol
- [ ] Enemy waits ~1 second at each waypoint
- [ ] Movement is smooth (no jitter)
- [ ] Enemy returns to patrol after losing player

**Test Enemy Chase**:
1. Get close enough for enemy to detect you
2. Run away in a straight line
3. Observe chase behavior

**Checklist**:
- [ ] Enemy immediately starts chasing
- [ ] Enemy matches your speed (approximately)
- [ ] Enemy doesn't stutter or freeze
- [ ] Enemy can navigate around small obstacles
- [ ] Enemy gives up chase when you're too far

**Test Enemy Attack**:
1. Let enemy get within attack range
2. Observe attack behavior

**Checklist**:
- [ ] Enemy stops moving during attack
- [ ] Attack has ~1 second cooldown
- [ ] Enemy faces player during attack
- [ ] Damage is dealt correctly

---

### NPC Interaction Testing

**Test NPC Prompts**:
1. Campaign → Town Hub
2. Walk near an NPC
3. Observe interaction prompt

**Checklist**:
- [ ] Prompt appears when in range (~48 pixels)
- [ ] Prompt shows correct key ("Press E to interact")
- [ ] Prompt disappears when out of range
- [ ] Closest NPC prompt shows when multiple NPCs nearby

**Test NPC Types**:

**Shop NPC**:
1. Interact with "Blacksmith" or "Merchant"
2. Expected: Shop UI opens
3. Checklist:
   - [ ] Shop shows items
   - [ ] Prices displayed correctly
   - [ ] Can buy items (if have currency)
   - [ ] Inventory updates after purchase

**Mission Giver NPC**:
1. Interact with "Ranger" or "Captain"
2. Expected: Mission menu opens
3. Checklist:
   - [ ] Mission list shows available missions
   - [ ] Can select mission
   - [ ] Mission starts on selection

**Lore NPC**:
1. Interact with "Historian" or "Elder"
2. Expected: Dialogue box opens
3. Checklist:
   - [ ] Dialogue text appears
   - [ ] Can advance dialogue with key press
   - [ ] Dialogue closes at end

---

### Inventory Testing

**Test Normal Operations**:
1. Collect items during gameplay
2. Open inventory (I key)
3. Verify items appear

**Checklist**:
- [ ] Items stack correctly (same items combine)
- [ ] Max stack respected (e.g., 99 potions max)
- [ ] Currency displays correctly
- [ ] Can equip/unequip items
- [ ] Stats update when equipping items

**Test Bounds Protection**:
1. Collect 999,999 gold (via console or cheat)
2. Try to collect more gold
3. Expected: Currency stays at 999,999

**Checklist**:
- [ ] Currency doesn't exceed 999,999
- [ ] No integer overflow
- [ ] No negative currency possible
- [ ] No negative item quantities possible

---

### Physics & Movement Testing

**Test Player Movement**:
1. Launch game
2. Test all movement mechanics

**Checklist**:
- [ ] Walk left/right - smooth movement
- [ ] Run - faster movement
- [ ] Jump - responsive jump
- [ ] Double jump - works mid-air
- [ ] Wall jump - works on walls
- [ ] Dash - quick burst movement
- [ ] Crouch - reduces height
- [ ] Crouch jump - reduced jump power

**Test Collision**:
**Checklist**:
- [ ] Can't walk through walls
- [ ] Lands on platforms correctly
- [ ] No clipping into floors
- [ ] Corner collision doesn't stick
- [ ] Can slide down walls

---

## How to Report Bugs

### Bug Report Template

```markdown
## Bug Report: [Short Description]

**Date**: YYYY-MM-DD
**Version**: Ninja Dash v0.3
**Platform**: Windows 10/11

### Summary
Brief 1-sentence description of the bug.

### Steps to Reproduce
1. Launch game
2. Go to [location/menu]
3. Perform [action]
4. Observe [unexpected behavior]

### Expected Behavior
What should happen.

### Actual Behavior
What actually happens.

### Screenshots/Video
[Attach if possible]

### System Information
- OS: Windows 10/11
- Python Version: 3.11.9
- PyGame Version: 2.6.1
- RAM: 16GB
- GPU: [Your GPU]

### Additional Context
- Does it happen every time? Yes/No
- Does it happen in specific missions? Which ones?
- Any console errors? [Paste here]

### Log Files
Attach: `user_data\logs\VainAsherGamings_IndieNinjaAdventures_[date].log`
```

### Where to Report Bugs

1. **GitHub Issues** (if available):
   - Go to project repository
   - Click "Issues" → "New Issue"
   - Fill out template

2. **Email**:
   - Subject: "[NINJA DASH BUG] Short description"
   - Attach log files from `user_data\logs\`
   - Include screenshots

3. **Local File**:
   - Save report in `user_data\bug_reports\`
   - Name: `BUG_YYYY-MM-DD_description.md`

---

## Known Issues & Limitations

### 🔴 CRITICAL - NOT FIXED

**Boss AI System Not Implemented**:
- **Issue**: 5 boss types defined but have NO AI logic
- **Impact**: Boss fights don't work at all
- **Status**: Requires 220-hour implementation (5.5 weeks)
- **Workaround**: Avoid boss arenas until implemented

**No Pathfinding for Enemies**:
- **Issue**: Enemies walk into walls/obstacles
- **Impact**: Enemies get stuck on terrain
- **Status**: Requires obstacle avoidance implementation (~12 hours)
- **Workaround**: Design levels with clear patrol paths

### 🟡 MEDIUM - PARTIALLY ADDRESSED

**NPCs Don't Move**:
- **Issue**: NPCs are completely static
- **Impact**: NPCs feel lifeless
- **Status**: Movement system not implemented (~8 hours)
- **Current**: NPCs only play idle animation

**No Save File Integrity Checking**:
- **Issue**: Save files can be manually edited
- **Impact**: Players can cheat by editing saves
- **Status**: Validation system needed (~8 hours)
- **Mitigation**: Inventory bounds checking added (limits exploits)

### 🟢 LOW - KNOWN LIMITATIONS

**Test Coverage Gaps**:
- Rendering/UI: No tests
- World generation: Partial tests
- Enemy AI: Minimal tests
- **Impact**: Regressions may not be caught
- **Status**: Need comprehensive test suite (~40 hours)

---

## Performance Testing

### FPS Monitoring
```python
# Add this to demo_game.py near line 100
print(f"FPS: {clock.get_fps():.1f}")
```

**Expected Performance**:
- **Target**: 60 FPS
- **Acceptable**: 50-60 FPS
- **Poor**: <50 FPS

### Performance Test Scenarios

**Test 1: Empty World**
1. Launch game
2. Campaign → Create new mission → Empty world
3. Run around for 60 seconds
4. Expected FPS: 60 (locked)

**Test 2: 10 Enemies**
1. Mission with 10 enemies
2. Let all enemies chase you
3. Expected FPS: 55-60

**Test 3: 30 Rooms**
1. Generate large world (30 rooms)
2. Expected generation time: <5ms
3. Expected FPS while exploring: 55-60

**Performance Issues to Report**:
- FPS drops below 50
- Generation time > 10ms
- Memory usage > 500MB
- Stuttering/jittering

---

## Playtesting Checklist

Use this checklist for comprehensive playtest sessions:

### Pre-Test Setup
- [ ] Latest code pulled/downloaded
- [ ] Virtual environment activated
- [ ] All tests passing: `python run_tests.py`
- [ ] Game launches without errors

### Core Mechanics (15 minutes)
- [ ] Movement feels responsive
- [ ] Jump mechanics work (normal, double, wall, crouch)
- [ ] Dash works and has cooldown
- [ ] Collision detection accurate
- [ ] Camera follows player smoothly

### Enemy AI (20 minutes)
- [ ] Enemies patrol correctly (no stalling)
- [ ] Enemies detect and chase player
- [ ] Enemies attack when in range
- [ ] Enemies return to patrol when player escapes
- [ ] Multiple enemies coordinate (if applicable)

### NPC Interactions (10 minutes)
- [ ] NPCs show interaction prompts
- [ ] Shop NPCs open shop UI
- [ ] Mission NPCs open mission menu
- [ ] Dialogue NPCs show dialogue
- [ ] Closest NPC selected when multiple available

### Inventory & Items (15 minutes)
- [ ] Collect coins/currency
- [ ] Pick up items (potions, weapons, etc.)
- [ ] Inventory UI shows correct items
- [ ] Equipping items works
- [ ] Using consumables works
- [ ] Currency doesn't exceed 999,999
- [ ] Can't have negative items

### Progression (30 minutes)
- [ ] Complete a mission successfully
- [ ] Mission completion tracked
- [ ] Unlock next mission
- [ ] Currency/items persist between missions
- [ ] Save game works
- [ ] Load game works

### Edge Cases (20 minutes)
- [ ] Fall off map - respawn works
- [ ] Die to enemy - respawn works
- [ ] Pause during gameplay
- [ ] Return to main menu
- [ ] Quit and relaunch - save persists

### Performance (Throughout)
- [ ] FPS stays above 50
- [ ] No stuttering/lag
- [ ] Memory usage reasonable
- [ ] No crashes

---

## Testing Priorities

### High Priority (Test First)
1. **Core Movement** - Game is unplayable if broken
2. **Enemy Movement** - Major fix in this session
3. **Inventory Bounds** - Security fix
4. **NPC Interaction** - UX improvement

### Medium Priority (Test After Core)
5. **Save/Load** - Important but not immediate
6. **Mission Progression** - Verify no regressions
7. **Performance** - Monitor during all tests

### Low Priority (Test If Time)
8. **UI Polish** - Visual issues only
9. **Audio** - Non-critical
10. **Advanced Features** - Experimental content

---

## Quick Smoke Test (5 minutes)

If you only have 5 minutes, run this minimal test:

```bash
# 1. Run tests
python run_tests.py --edge

# 2. Launch game
python demo_game.py

# 3. Quick playthrough:
#    - Start campaign
#    - Move around (WASD)
#    - Jump (SPACE)
#    - Dash (SHIFT)
#    - Find an enemy - observe patrol
#    - Collect an item
#    - Open inventory (I)
#    - Quit game

# 4. Check logs for errors
# Look in: user_data\logs\
```

**Pass Criteria**:
- ✅ All tests pass
- ✅ Game launches
- ✅ No crashes
- ✅ Enemies move smoothly
- ✅ No error spam in logs

---

## Getting Help

### Debug Mode

Launch game in debug mode for extra logging:
```bash
python demo_game.py --debug
```

### Console Commands

While in-game, press ` (backtick) to open console:
```
/god - Enable god mode (invincibility)
/give gold 1000 - Add currency
/teleport x y - Teleport to coordinates
/spawn enemy goblin - Spawn enemy
/noclip - Walk through walls
```

### Log File Locations

**Session Logs**:
```
user_data\logs\VainAsherGamings_IndieNinjaAdventures_YYYY-MM-DD_HH-MM-SS.log
```

**What to Look For in Logs**:
- `[ERROR]` - Critical errors
- `[WARNING]` - Potential issues
- `[INFO]` - Normal operations
- `Traceback` - Python exceptions

### Common Error Messages

**"ModuleNotFoundError: No module named 'pygame'"**:
- Solution: `pip install pygame`

**"FileNotFoundError: [Errno 2] No such file or directory: 'data/items.json'"**:
- Solution: Run from project root, not subdirectory

**"EventBus has no attribute 'unsubscribe'"**:
- Solution: Code is out of date, pull latest changes

---

## Success Criteria

Your testing session is successful if:

✅ **All automated tests pass** (17/17)
✅ **No crashes during 15-minute playthrough**
✅ **Enemies move smoothly without stalling**
✅ **NPC interactions work correctly**
✅ **Inventory operations respect bounds**
✅ **Performance stays above 50 FPS**
✅ **No error spam in console/logs**

If ANY of these fail, report the issue using the bug template above!

---

## Next Steps After Testing

1. **Report Findings**: Submit bug reports for any issues
2. **Performance Data**: Share FPS averages and any stuttering
3. **Playability Feedback**: Rate overall feel of movement/combat
4. **Suggested Improvements**: What felt off? What could be better?

---

**End of Testing & Reporting Guide**

*Last Updated: 2025-12-22*
*Version: v0.3 Post-Session-Fixes*
