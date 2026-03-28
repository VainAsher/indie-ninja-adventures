# Ninja Dash - Build Scripts

This directory contains scripts to build Ninja Dash executables for Windows.

## Prerequisites

**Python 3.11 or 3.12 must be installed on your system.**

### Installing Python

Choose one of these options:

#### Option 1: Microsoft Store (Easiest)
1. Open Microsoft Store
2. Search for "Python 3.12"
3. Click "Get" or "Install"
4. Done! No PATH configuration needed

#### Option 2: Python.org (Traditional)
1. Go to https://www.python.org/downloads/
2. Download Python 3.12
3. Run the installer
4. **IMPORTANT:** Check "Add Python to PATH" during installation
5. Complete installation

### Verifying Python Installation

Open Command Prompt and run:
```batch
python --version
```

You should see: `Python 3.12.x` or `Python 3.11.x`

If you get an error or Microsoft Store opens, Python is not properly installed.

## Building the Game

### First Time Setup

The build scripts will automatically:
- Create a virtual environment (`.venv`)
- Install PyInstaller
- Install dependencies from `requirements.txt`

### Build All Configurations (Recommended)

```batch
cd build
build_all.bat
```

This creates three executables:
- `dist\ninja_dash.exe` - Production build (one-file)
- `dist\ninja_dash_testing\ninja_dash_testing.exe` - Testing build with recording
- `dist\ninja_dash_dev\ninja_dash_dev.exe` - Development build with debug features

### Build Individual Configurations

```batch
cd build

REM Production only
build_production.bat

REM Testing only
build_testing.bat

REM Development only
build_dev.bat
```

## Build Preflight Checklist

Before starting any build, check these common blockers:

1. **Pause OneDrive sync** — OneDrive can hold a file lock on the output EXE while syncing, causing PyInstaller to fail with an `Access is denied` or `[WinError 32]` error.
   - Right-click the OneDrive tray icon → Pause syncing → 2 hours

2. **Pause antivirus real-time scanning** (optional but recommended) — Antivirus scanners often quarantine or lock newly-built EXEs mid-write.
   - Windows Security: Settings > Virus & threat protection > Manage settings > Real-time protection → temporarily Off
   - Re-enable immediately after the build completes

3. **Close any running game instance** — An open EXE locks itself; a rebuild over it will fail.

4. **Run from the build/ directory** — All scripts assume `cd build` first.

## Troubleshooting

### Error: "Python was not found"

**Problem:** Python is not installed or not in PATH.

**Solution:**
1. Install Python using one of the methods above
2. If installed from python.org, make sure "Add to PATH" was checked
3. If already installed, you may need to disable Windows App Execution Aliases:
   - Settings > Apps > Advanced app settings > App execution aliases
   - Turn OFF toggles for `python.exe` and `python3.exe`

### Error: "Virtual environment not found"

**Problem:** The `.venv` directory wasn't created.

**Solution:**
1. Delete `.venv` folder if it exists
2. Run `test_setup.bat` to diagnose the issue
3. Check that you have write permissions in the project directory

### Error: "Failed to install dependencies"

**Problem:** Network issue or corrupted package cache.

**Solution:**
```batch
cd ..
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Build hangs or crashes

**Problem:** Insufficient RAM or disk space.

**Solution:**
- Close other applications
- Ensure you have at least 2GB free RAM
- Ensure you have at least 500MB free disk space

## Testing Your Setup

Run the test script to verify everything is configured correctly:

```batch
cd build
test_setup.bat
```

This will check:
- Python installation
- Virtual environment creation
- Dependency installation

## Build Output

After a successful build, you'll find executables in:
- `build\dist\ninja_dash.exe` - Production build (one-file)
- `build\dist\ninja_dash_testing\` - Testing build
- `build\dist\ninja_dash_dev\` - Dev build

Production output is a single `.exe` plus optional launcher/readme in `build\dist\`.

Testing/Dev directories contain:
- `.exe` file - The game executable
- `.bat` file - Launcher script (always use this, not the .exe directly!)
- `_internal\` - Bundled dependencies and assets
- `user_data\` - Game saves, logs, and replays

## Important Notes

- Production can run `ninja_dash.exe` directly (or via `ninja_dash.bat`)
- Testing/Dev should run the `.bat` launcher files (or pass `--build-mode`)
- The first build may take 5-10 minutes
- Subsequent builds are faster (2-3 minutes)
- Virtual environment is shared across all build configurations
