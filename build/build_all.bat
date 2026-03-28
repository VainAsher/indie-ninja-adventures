@echo off
REM Build all three Ninja Dash executables

echo ========================================
echo Building Ninja Dash - All Configurations
echo ========================================
echo.

REM Ensure we're in the build directory
cd /d "%~dp0"

REM Run setup script to ensure Python and virtual environment exist
echo Running setup to verify environment...
call setup.bat
if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed! Cannot proceed with build.
    echo Please check the errors above and try again.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] Virtual environment not found!
    pause
    exit /b 1
)
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install PyInstaller
echo Installing PyInstaller...
python -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller!
    pause
    exit /b 1
)

REM Install dependencies from requirements.txt
if exist "..\requirements.txt" (
    echo Installing dependencies from requirements.txt...
    python -m pip install -r "..\requirements.txt" --quiet
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    echo [OK] All dependencies installed
) else (
    echo [WARNING] requirements.txt not found
)

echo.
echo Installed packages:
python -m pip list | findstr /i "pygame pillow pyinstaller"

echo.
echo ========================================
echo Starting Build Process
echo ========================================
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo.

REM Build PRODUCTION
echo ========================================
echo Building PRODUCTION (ninja_dash.exe)
echo ========================================
set BUILD_MODE=PRODUCTION
python -m PyInstaller --clean ninja_dash_production.spec
if errorlevel 1 (
    echo ERROR: Production build failed!
    pause
    exit /b 1
)
echo Production build complete!
echo.

REM Build TESTING
echo ========================================
echo Building TESTING (ninja_dash_testing.exe)
echo ========================================
set BUILD_MODE=TESTING
python -m PyInstaller --clean ninja_dash_testing.spec
if errorlevel 1 (
    echo ERROR: Testing build failed!
    pause
    exit /b 1
)
echo Testing build complete!
echo.

REM Build DEV
echo ========================================
echo Building DEV (ninja_dash_dev.exe)
echo ========================================
set BUILD_MODE=DEV
python -m PyInstaller --clean ninja_dash_dev.spec
if errorlevel 1 (
    echo ERROR: Dev build failed!
    pause
    exit /b 1
)
echo Dev build complete!
echo.

REM Create user_data directories for each build
echo Creating user_data templates...
REM Production is now one-file; user_data will be created on first run.
if not exist "dist\ninja_dash_testing\user_data\replays" mkdir "dist\ninja_dash_testing\user_data\replays"
if not exist "dist\ninja_dash_testing\user_data\logs" mkdir "dist\ninja_dash_testing\user_data\logs"
if not exist "dist\ninja_dash_testing\user_data\saves" mkdir "dist\ninja_dash_testing\user_data\saves"

if not exist "dist\ninja_dash_dev\user_data\replays" mkdir "dist\ninja_dash_dev\user_data\replays"
if not exist "dist\ninja_dash_dev\user_data\logs" mkdir "dist\ninja_dash_dev\user_data\logs"
if not exist "dist\ninja_dash_dev\user_data\saves" mkdir "dist\ninja_dash_dev\user_data\saves"

REM Create launcher scripts for each build
echo Creating launcher scripts...

echo @echo off > "dist\ninja_dash.bat"
echo start "" "%%~dp0ninja_dash.exe" --build-mode production %%* >> "dist\ninja_dash.bat"

echo @echo off > "dist\ninja_dash_testing\ninja_dash_testing.bat"
echo "%%~dp0ninja_dash_testing.exe" --build-mode testing %%* >> "dist\ninja_dash_testing\ninja_dash_testing.bat"

echo @echo off > "dist\ninja_dash_dev\ninja_dash_dev.bat"
echo "%%~dp0ninja_dash_dev.exe" --build-mode dev %%* >> "dist\ninja_dash_dev\ninja_dash_dev.bat"

REM Create README files for each build
echo Creating distribution README files...

echo Ninja Dash - Production Build > "dist\ninja_dash_README.txt"
echo. >> "dist\ninja_dash_README.txt"
echo This is a ONE-FILE build. Run ninja_dash.exe (or ninja_dash.bat). >> "dist\ninja_dash_README.txt"
echo. >> "dist\ninja_dash_README.txt"
echo User data will be stored in the user_data\ folder next to the exe. >> "dist\ninja_dash_README.txt"
echo. >> "dist\ninja_dash_README.txt"
echo Controls: >> "dist\ninja_dash_README.txt"
echo - Arrow keys / WASD: Move >> "dist\ninja_dash_README.txt"
echo - Space: Jump >> "dist\ninja_dash_README.txt"
echo - Shift: Dash >> "dist\ninja_dash_README.txt"
echo - S/Down: Crouch >> "dist\ninja_dash_README.txt"
echo - F3: Toggle debug overlay >> "dist\ninja_dash_README.txt"

echo Ninja Dash - Testing Build > "dist\ninja_dash_testing\README.txt"
echo. >> "dist\ninja_dash_testing\README.txt"
echo IMPORTANT: Run ninja_dash_testing.bat (NOT the .exe directly) >> "dist\ninja_dash_testing\README.txt"
echo. >> "dist\ninja_dash_testing\README.txt"
echo This is a TESTING build that automatically records gameplay. >> "dist\ninja_dash_testing\README.txt"
echo On exit, replay and log folders will open automatically. >> "dist\ninja_dash_testing\README.txt"
echo Please share these files with the development team! >> "dist\ninja_dash_testing\README.txt"
echo. >> "dist\ninja_dash_testing\README.txt"
echo Replays are saved to: user_data\replays\ >> "dist\ninja_dash_testing\README.txt"
echo Logs are saved to: user_data\logs\ >> "dist\ninja_dash_testing\README.txt"

echo Ninja Dash - Development Build > "dist\ninja_dash_dev\README.txt"
echo. >> "dist\ninja_dash_dev\README.txt"
echo IMPORTANT: Run ninja_dash_dev.bat (NOT the .exe directly) >> "dist\ninja_dash_dev\README.txt"
echo. >> "dist\ninja_dash_dev\README.txt"
echo This is a DEVELOPMENT build with all debug features enabled. >> "dist\ninja_dash_dev\README.txt"
echo. >> "dist\ninja_dash_dev\README.txt"
echo Developer Controls: >> "dist\ninja_dash_dev\README.txt"
echo - F3: Toggle debug overlay >> "dist\ninja_dash_dev\README.txt"
echo - ` (backtick): Open developer console >> "dist\ninja_dash_dev\README.txt"
echo. >> "dist\ninja_dash_dev\README.txt"
echo Developer Console Commands: >> "dist\ninja_dash_dev\README.txt"
echo - Type Python expressions to evaluate >> "dist\ninja_dash_dev\README.txt"
echo - Available objects: player, camera, entities, physics, collision >> "dist\ninja_dash_dev\README.txt"
echo - Example: player.position >> "dist\ninja_dash_dev\README.txt"
echo - Example: camera.zoom = 2.0 >> "dist\ninja_dash_dev\README.txt"

echo.
echo ========================================
echo Build Verification
echo ========================================
echo Checking build outputs...
echo.

REM Check if executables were created
if exist "dist\ninja_dash.exe" (
    echo [OK] Production build: ninja_dash.exe
) else (
    echo [ERROR] Production build failed - executable not found!
)

if exist "dist\ninja_dash_testing\ninja_dash_testing.exe" (
    echo [OK] Testing build: ninja_dash_testing.exe
) else (
    echo [ERROR] Testing build failed - executable not found!
)

if exist "dist\ninja_dash_dev\ninja_dash_dev.exe" (
    echo [OK] Dev build: ninja_dash_dev.exe
) else (
    echo [ERROR] Dev build failed - executable not found!
)

echo.
echo Checking launcher scripts...
if exist "dist\ninja_dash.bat" (
    echo [OK] Production launcher: ninja_dash.bat
) else (
    echo [WARNING] Production launcher not found!
)

if exist "dist\ninja_dash_testing\ninja_dash_testing.bat" (
    echo [OK] Testing launcher: ninja_dash_testing.bat
) else (
    echo [WARNING] Testing launcher not found!
)

if exist "dist\ninja_dash_dev\ninja_dash_dev.bat" (
    echo [OK] Dev launcher: ninja_dash_dev.bat
) else (
    echo [WARNING] Dev launcher not found!
)

echo.
echo Checking data directories...
if exist "dist\ninja_dash_testing\_internal\assets" (
    echo [OK] Testing assets bundled
) else (
    echo [WARNING] Testing assets may be missing!
)

if exist "dist\ninja_dash_dev\_internal\assets" (
    echo [OK] Dev assets bundled
) else (
    echo [WARNING] Dev assets may be missing!
)

echo.
echo ========================================
echo All builds completed successfully!
echo ========================================
echo.
echo Output directories:
echo   - dist\ninja_dash.exe        (PRODUCTION - one-file)
echo   - dist\ninja_dash_testing\   (TESTING)
echo   - dist\ninja_dash_dev\       (DEV)
echo.
echo IMPORTANT: For TESTING/DEV, run the .bat launcher files (or pass --build-mode).
echo.
pause
