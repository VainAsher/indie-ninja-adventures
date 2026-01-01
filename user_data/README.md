# User Data Directory

This directory contains all user-specific data for Vain Asher Gaming's: Indie Ninja Adventures.

## Directory Structure

```
user_data/
├── logs/         # Game session logs
├── replays/      # Recorded gameplay replays
├── saves/        # Save game files (future)
└── settings/     # Persistent game settings
```

## Subdirectories

### logs/
Contains timestamped log files for each game session:
- Format: `VainAsherGamings_IndieNinjaAdventures_YYYY-MM-DD_HH-MM-SS.log`
- Rotating file handler: 10MB per file, 3 backups (30MB total)
- Useful for debugging and bug reports

### replays/
Stores recorded gameplay replays in JSON format:
- Used with `--record` and `--replay` flags
- Contains input commands and metadata (seed, procedural mode, etc.)
- Deterministic replay support

**Usage**:
```bash
# Record a replay
python demo_game.py --record my_run

# Replay a recording
python demo_game.py --replay my_run

# Replay with window visible
python demo_game.py --replay my_run --show-replay
```

Files are automatically saved to/loaded from `user_data/replays/`

### saves/
Reserved for future save game functionality:
- Checkpoint data
- Progress tracking
- Unlocks and achievements

### settings/
Persistent game settings stored in JSON:
- `settings.json` - Main settings file
- Audio, display, gameplay, and control settings
- Automatically created with defaults on first run

## Environment Variable Override

You can override the user_data location with an environment variable:

**Windows (PowerShell)**:
```powershell
$env:NINJADASH_USER_DATA = "C:\MyGames\NinjaDash"
python demo_game.py
```

**Windows (CMD)**:
```cmd
set NINJADASH_USER_DATA=C:\MyGames\NinjaDash
python demo_game.py
```

**Linux/macOS**:
```bash
export NINJADASH_USER_DATA="/path/to/custom/location"
python demo_game.py
```

## Default Location

By default, user_data is project-local (in the project directory). This makes the project portable and keeps all data together.

## Accessing in Code

```python
from config import GameSettings
from pathlib import Path
import os

# Get user_data directory
def get_user_data_dir():
    env_dir = os.environ.get("NINJADASH_USER_DATA")
    if env_dir:
        return Path(env_dir)

    # Default: project-local
    project_root = Path(__file__).parent
    return project_root / 'user_data'

# Use settings system
settings = GameSettings()
volume = settings.get("volume_music", default=0.7)
settings.set("fullscreen", True)
settings.save()
```

## File Management

- **Logs**: Automatically managed with rotation (old logs deleted when exceeding 30MB)
- **Replays**: Manual management (delete old replays as needed)
- **Settings**: Single file, overwritten on save
- **Saves**: Future implementation

## Privacy & Security

All data is stored locally on your machine:
- No telemetry or analytics
- No cloud sync
- No network transmission
- Safe to delete entire user_data directory to reset

## Backup

To back up your data:
1. Copy the entire `user_data/` directory
2. Or copy specific subdirectories (e.g., `saves/` for save files)

To restore:
1. Replace the `user_data/` directory with your backup
2. Or copy specific files back to their subdirectories

---

**Last Updated**: 2025-12-12
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
**Version**: v0.7.0
