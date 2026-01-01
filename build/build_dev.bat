@echo off
echo Building DEV build...
set BUILD_MODE=DEV
cd /d "%~dp0"

REM Run setup script to ensure Python and virtual environment exist
call setup.bat
if errorlevel 1 (
    echo [ERROR] Setup failed! Cannot proceed with build.
    pause
    exit /b 1
)

REM Activate virtual environment
if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
    echo Virtual environment activated
) else (
    echo [ERROR] Virtual environment not found!
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install pyinstaller --quiet
if exist "..\requirements.txt" (
    python -m pip install -r "..\requirements.txt" --quiet
)
echo.

python -m PyInstaller --clean ninja_dash_dev.spec
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Verification
echo ========================================
if exist "dist\ninja_dash_dev\ninja_dash_dev.exe" (
    echo [OK] Executable created: ninja_dash_dev.exe
    if exist "dist\ninja_dash_dev\_internal\assets" (
        echo [OK] Assets bundled
    ) else (
        echo [WARNING] Assets may be missing!
    )
) else (
    echo [ERROR] Build failed - executable not found!
)
echo.
echo Dev build complete! Output: dist\ninja_dash_dev\
pause
