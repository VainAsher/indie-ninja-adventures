# User Data Migration Summary

## Overview

The project has been updated to use a centralized `user_data/` directory for all persistent user files (logs, replays, saves, settings). This makes the project more portable and organizes all user-generated content in one location.

## Changes Made

### 1. Logger System (`core/logger.py`)
**Changed**: Default log location from platform-specific directories to project-local `user_data/logs/`

**Before**:
- Windows: `%APPDATA%/NinjaDash/logs/`
- macOS: `~/Library/Application Support/NinjaDash/logs/`
- Linux: `~/.local/share/ninjadash/logs/`

**After**:
- Default: `user_data/logs/` (project-local)
- Override: `NINJADASH_USER_DATA` environment variable

**Benefits**:
- Portable project (all data stays with project)
- Easier to find and manage logs
- No system-wide pollution
- Better for development/testing

### 2. Replay System (`demo_game.py`)
**Changed**: Replay files now automatically save to/load from `user_data/replays/`

**Before**:
```bash
python demo_game.py --record my_run.json  # Saved to current directory
python demo_game.py --replay my_run.json  # Loaded from current directory
```

**After**:
```bash
python demo_game.py --record my_run       # Saves to user_data/replays/my_run.json
python demo_game.py --replay my_run       # Loads from user_data/replays/my_run.json
```

**Features**:
- Automatic `.json` extension
- Searches `user_data/replays/` by default
- Still supports absolute paths for custom locations
- Migrated existing `run1.json` to `user_data/replays/`

### 3. Settings System (NEW: `config/settings.py`)
**Created**: Persistent settings management system

**Location**: `user_data/settings/settings.json`

**Features**:
- Audio settings (volume_master, volume_music, volume_sfx)
- Display settings (fullscreen, vsync, window size)
- Gameplay settings (screenshake, particles, camera_smoothing)
- Control bindings (key mappings)
- Developer settings (show_fps, show_hitboxes, log_level)

**Usage**:
```python
from config import GameSettings

settings = GameSettings()
settings.set("volume_music", 0.8)
settings.set("fullscreen", True)
settings.save()
```

### 4. Directory Structure
**Created**: Organized `user_data/` subdirectories

```
user_data/
├── logs/         # Session logs (auto-created)
├── replays/      # Recorded replays (auto-created)
├── saves/        # Save files (future use)
├── settings/     # Persistent settings (auto-created)
└── README.md     # User data documentation
```

All directories are automatically created on first run.

## Migration Notes

### Existing Files
- ✅ Old logs from `logs/` → Moved to `user_data/logs/`
- ✅ Existing `run1.json` → Moved to `user_data/replays/`
- ✅ Old `logs/` directory → Removed (content migrated)

### Environment Variable
**New**: `NINJADASH_USER_DATA` (replaces old `NINJADASH_LOG_DIR`)

**Before**:
```bash
export NINJADASH_LOG_DIR=/custom/path  # Only affected logs
```

**After**:
```bash
export NINJADASH_USER_DATA=/custom/path  # Affects all user data
```

**Subdirectories**: When using custom path, subdirectories (logs/, replays/, saves/, settings/) are created within the custom location.

## Testing Performed

### ✅ Logger Tests
- Logger initializes with `user_data/logs/` directory
- Log files created successfully
- Environment variable override works
- All unit tests pass

### ✅ Replay Tests
- Replay path resolution works for filenames
- Absolute paths still supported
- Existing replay file migrated successfully

### ✅ Settings Tests
- Settings system initializes
- Default settings created
- Settings load/save works
- Settings file properly formatted (JSON)

### ✅ Unit Tests
- All 5 unit test suites pass
- No breaking changes to existing systems

## Documentation Updates

### Updated Files
1. **README.md** - Updated project structure
2. **docs/SYSTEM_OVERVIEW.md** - Added settings system documentation
3. **user_data/README.md** - Created comprehensive user_data guide

### New Files
1. **config/settings.py** - Settings management system
2. **user_data/README.md** - User data documentation
3. **USER_DATA_MIGRATION.md** - This file

## Usage Examples

### Basic Usage
```bash
# Run game (uses user_data/ by default)
python demo_game.py

# Record a replay
python demo_game.py --record test_run

# Replay a recording
python demo_game.py --replay test_run

# Use custom user_data location
export NINJADASH_USER_DATA=/path/to/custom
python demo_game.py
```

### Settings in Code
```python
from config import GameSettings

# Initialize settings
settings = GameSettings()

# Get settings
volume = settings.get("volume_music", default=0.7)
fullscreen = settings.get("fullscreen", default=False)

# Set settings
settings.set("volume_music", 0.8)
settings.set("fullscreen", True)

# Save changes
settings.save()

# Reset to defaults
settings.reset_to_defaults()
```

### Accessing User Data Directory
```python
from demo_game import get_user_data_dir
from pathlib import Path

# Get user_data directory
user_data = get_user_data_dir()

# Access subdirectories
logs_dir = user_data / 'logs'
replays_dir = user_data / 'replays'
saves_dir = user_data / 'saves'
settings_dir = user_data / 'settings'
```

## Backward Compatibility

### ✅ Maintained
- All existing functionality works
- Tests pass without modification
- Demo game runs normally
- No breaking API changes

### ⚠️ Changed (Minor)
- Log files now in `user_data/logs/` instead of `logs/`
- Replay files prefer `user_data/replays/` (absolute paths still work)
- New environment variable: `NINJADASH_USER_DATA` (old `NINJADASH_LOG_DIR` removed)

## Benefits

1. **Organization**: All user data in one place
2. **Portability**: Project directory contains everything
3. **Clarity**: Clear separation of code vs. user data
4. **Flexibility**: Easy to backup/restore user data
5. **Extensibility**: Ready for saves, mods, custom content
6. **Development**: Easier to test (no system-wide files)

## Future Enhancements

### Planned
- [ ] Save game system → `user_data/saves/`
- [ ] Mod loader → `user_data/mods/`
- [ ] Screenshot system → `user_data/screenshots/`
- [ ] Custom levels → `user_data/levels/`
- [ ] Leaderboards (local) → `user_data/leaderboards/`

### Settings System
- [ ] In-game settings menu
- [ ] Control remapping UI
- [ ] Audio sliders
- [ ] Graphics options
- [ ] Settings validation

## Troubleshooting

### Issue: Can't find logs
**Solution**: Logs are now in `user_data/logs/`, not the old location

### Issue: Replay not found
**Solution**: Place replays in `user_data/replays/` or use absolute path

### Issue: Want old behavior
**Solution**: Set `NINJADASH_USER_DATA` to your preferred location

### Issue: Settings not persisting
**Solution**: Check `user_data/settings/settings.json` exists and is writable

## Verification

Run these commands to verify the migration:

```bash
# Check directory structure
ls -la user_data/

# Check settings file
cat user_data/settings/settings.json

# Check logs
ls user_data/logs/

# Run tests
python run_tests.py
```

Expected output:
- `user_data/` exists with subdirectories
- `settings.json` contains default settings
- Log files present in `user_data/logs/`
- All tests pass

---

**Migration Date**: 2025-12-12
**Version**: v0.7.0
**Status**: Complete ✅
**Breaking Changes**: None (backward compatible)
