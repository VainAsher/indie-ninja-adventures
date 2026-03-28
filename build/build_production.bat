@echo off
echo Building PRODUCTION build...
set BUILD_MODE=PRODUCTION
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

python -m PyInstaller --clean ninja_dash_production.spec
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo Creating launcher script...
echo @echo off > "dist\ninja_dash.bat"
echo start "" "%%~dp0ninja_dash.exe" --build-mode production %%* >> "dist\ninja_dash.bat"

echo Creating README...
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

echo.
echo ========================================
echo Build Verification
echo ========================================
if exist "dist\ninja_dash.exe" (
    echo [OK] Executable created: ninja_dash.exe
) else (
    echo [ERROR] Build failed - executable not found!
)
echo.
echo Production build complete! Output: dist\ninja_dash.exe
pause
