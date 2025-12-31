@echo off
echo Building PRODUCTION build...
set BUILD_MODE=PRODUCTION
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "..\.venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "..\.venv\Scripts\activate.bat"
)

REM Verify dependencies
echo Checking dependencies...
if exist "..\requirements.txt" (
    pip install -q -r "..\requirements.txt"
)
echo.

pyinstaller --clean ninja_dash_production.spec
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
