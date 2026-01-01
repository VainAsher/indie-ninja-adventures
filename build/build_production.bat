@echo off
echo Building PRODUCTION build...
set BUILD_MODE=PRODUCTION
cd /d "%~dp0"

REM Run setup script to ensure Python and dependencies are installed
call setup.bat
if errorlevel 1 (
    echo [ERROR] Setup failed! Cannot proceed with build.
    pause
    exit /b 1
)
echo.

python -m PyInstaller --clean ninja_dash_production.spec
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Verification
echo ========================================
if exist "dist\ninja_dash\ninja_dash.exe" (
    echo [OK] Executable created: ninja_dash.exe
    if exist "dist\ninja_dash\_internal\assets" (
        echo [OK] Assets bundled
    ) else (
        echo [WARNING] Assets may be missing!
    )
) else (
    echo [ERROR] Build failed - executable not found!
)
echo.
echo Production build complete! Output: dist\ninja_dash\
pause
