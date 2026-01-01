@echo off
REM Build all three Ninja Dash executables

echo ========================================
echo Building Ninja Dash - All Configurations
echo ========================================
echo.

REM Ensure we're in the build directory
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "..\.venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "..\.venv\Scripts\activate.bat"
    echo.
) else (
    echo No virtual environment found, using global Python...
)

REM Install PyInstaller if not present
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    echo.
)

REM Verify and install dependencies from requirements.txt
echo ========================================
echo Verifying Dependencies
echo ========================================
if exist "..\requirements.txt" (
    echo Checking requirements.txt...
    python -m pip install -r "..\requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
    echo All dependencies installed successfully!
    echo.
) else (
    echo Warning: requirements.txt not found
    echo.
)

REM Display installed packages
echo Installed packages:
python -m pip list | findstr /i "pygame pillow pyinstaller"
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
if not exist "dist\ninja_dash\user_data\replays" mkdir "dist\ninja_dash\user_data\replays"
if not exist "dist\ninja_dash\user_data\logs" mkdir "dist\ninja_dash\user_data\logs"
if not exist "dist\ninja_dash\user_data\saves" mkdir "dist\ninja_dash\user_data\saves"

if not exist "dist\ninja_dash_testing\user_data\replays" mkdir "dist\ninja_dash_testing\user_data\replays"
if not exist "dist\ninja_dash_testing\user_data\logs" mkdir "dist\ninja_dash_testing\user_data\logs"
if not exist "dist\ninja_dash_testing\user_data\saves" mkdir "dist\ninja_dash_testing\user_data\saves"

if not exist "dist\ninja_dash_dev\user_data\replays" mkdir "dist\ninja_dash_dev\user_data\replays"
if not exist "dist\ninja_dash_dev\user_data\logs" mkdir "dist\ninja_dash_dev\user_data\logs"
if not exist "dist\ninja_dash_dev\user_data\saves" mkdir "dist\ninja_dash_dev\user_data\saves"

REM Create launcher scripts for each build
echo Creating launcher scripts...

echo @echo off > "dist\ninja_dash\ninja_dash.bat"
echo start "" "%%~dp0ninja_dash.exe" --build-mode production %%* >> "dist\ninja_dash\ninja_dash.bat"

echo @echo off > "dist\ninja_dash_testing\ninja_dash_testing.bat"
echo "%%~dp0ninja_dash_testing.exe" --build-mode testing %%* >> "dist\ninja_dash_testing\ninja_dash_testing.bat"

echo @echo off > "dist\ninja_dash_dev\ninja_dash_dev.bat"
echo "%%~dp0ninja_dash_dev.exe" --build-mode dev %%* >> "dist\ninja_dash_dev\ninja_dash_dev.bat"

REM Create README files for each build
echo Creating distribution README files...

echo Ninja Dash - Production Build > "dist\ninja_dash\README.txt"
echo. >> "dist\ninja_dash\README.txt"
echo IMPORTANT: Run ninja_dash.bat (NOT the .exe directly) >> "dist\ninja_dash\README.txt"
echo. >> "dist\ninja_dash\README.txt"
echo User data will be stored in the user_data\ folder. >> "dist\ninja_dash\README.txt"
echo. >> "dist\ninja_dash\README.txt"
echo Controls: >> "dist\ninja_dash\README.txt"
echo - Arrow keys / WASD: Move >> "dist\ninja_dash\README.txt"
echo - Space: Jump >> "dist\ninja_dash\README.txt"
echo - Shift: Dash >> "dist\ninja_dash\README.txt"
echo - S/Down: Crouch >> "dist\ninja_dash\README.txt"
echo - F3: Toggle debug overlay >> "dist\ninja_dash\README.txt"

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
if exist "dist\ninja_dash\ninja_dash.exe" (
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
if exist "dist\ninja_dash\ninja_dash.bat" (
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
if exist "dist\ninja_dash\_internal\assets" (
    echo [OK] Production assets bundled
) else (
    echo [WARNING] Production assets may be missing!
)

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
echo   - dist\ninja_dash\           (PRODUCTION - %~z0 bytes)
echo   - dist\ninja_dash_testing\   (TESTING)
echo   - dist\ninja_dash_dev\       (DEV)
echo.
echo IMPORTANT: Always run the .bat launcher files, NOT the .exe directly!
echo.
pause
