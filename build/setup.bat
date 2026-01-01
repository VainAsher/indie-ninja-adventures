@echo off
REM Setup script for Ninja Dash build environment
REM Automatically installs Python and dependencies if needed

setlocal enabledelayedexpansion

echo ========================================
echo Ninja Dash - Build Environment Setup
echo ========================================
echo.

REM Ensure we're in the build directory
cd /d "%~dp0"

REM ========================================
REM Step 1: Check for Python
REM ========================================
echo [1/4] Checking for Python installation...

set PYTHON_FOUND=0
set PYTHON_CMD=

REM Try: python command
python --version >nul 2>&1
if !errorlevel! equ 0 (
    REM Check if it's the Windows Store stub
    where python | findstr /i "WindowsApps" >nul 2>&1
    if !errorlevel! neq 0 (
        set PYTHON_FOUND=1
        set PYTHON_CMD=python
        echo [OK] Found Python: python
    )
)

REM Try: py launcher (if python command didn't work)
if !PYTHON_FOUND! equ 0 (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_FOUND=1
        set PYTHON_CMD=py
        echo [OK] Found Python: py launcher
    )
)

REM Try: python3 command
if !PYTHON_FOUND! equ 0 (
    python3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_FOUND=1
        set PYTHON_CMD=python3
        echo [OK] Found Python: python3
    )
)

REM If still not found, try to install Python
if !PYTHON_FOUND! equ 0 (
    echo [WARNING] Python not found!
    echo.
    echo Would you like to automatically install Python?
    echo This will download and install Python 3.12 (user-only, no admin required)
    echo Download size: ~30 MB
    echo.
    choice /C YN /M "Install Python automatically"
    if !errorlevel! equ 1 (
        call :InstallPython
        if !errorlevel! neq 0 (
            echo.
            echo [ERROR] Python installation failed!
            echo Please install Python manually from: https://www.python.org/downloads/
            echo Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
        set PYTHON_CMD=python
    ) else (
        echo.
        echo Please install Python manually:
        echo 1. Go to https://www.python.org/downloads/
        echo 2. Download Python 3.11 or 3.12
        echo 3. Run the installer and CHECK "Add Python to PATH"
        echo 4. Run this script again
        pause
        exit /b 1
    )
)

REM Display Python version
echo.
echo Python installation details:
!PYTHON_CMD! --version
echo.

REM ========================================
REM Step 2: Setup Virtual Environment
REM ========================================
echo [2/4] Setting up virtual environment...

if exist "..\.venv\Scripts\activate.bat" (
    echo [OK] Virtual environment already exists
) else (
    echo Creating virtual environment in .venv...
    !PYTHON_CMD! -m venv "..\.venv"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment!
        echo Trying to install venv module...
        !PYTHON_CMD! -m pip install --user virtualenv
        !PYTHON_CMD! -m virtualenv "..\.venv"
        if !errorlevel! neq 0 (
            echo [ERROR] Could not create virtual environment!
            pause
            exit /b 1
        )
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call "..\.venv\Scripts\activate.bat"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM ========================================
REM Step 3: Upgrade pip
REM ========================================
echo [3/4] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] pip upgraded
) else (
    echo [WARNING] Could not upgrade pip, continuing anyway...
)
echo.

REM ========================================
REM Step 4: Install Dependencies
REM ========================================
echo [4/4] Installing dependencies...

REM Install PyInstaller
python -m pip show pyinstaller >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] PyInstaller already installed
) else (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install PyInstaller!
        pause
        exit /b 1
    )
    echo [OK] PyInstaller installed
)

REM Install requirements.txt dependencies
if exist "..\requirements.txt" (
    echo Installing packages from requirements.txt...
    python -m pip install -r "..\requirements.txt"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies from requirements.txt!
        pause
        exit /b 1
    )
    echo [OK] All dependencies installed
) else (
    echo [WARNING] requirements.txt not found, skipping...
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Installed packages:
python -m pip list | findstr /i "pygame pillow pyinstaller"
echo.
echo You can now run build_all.bat to build the game.
echo.

exit /b 0

REM ========================================
REM Function: Install Python
REM ========================================
:InstallPython
echo.
echo Downloading Python 3.12 installer...

REM Create temp directory
set TEMP_DIR=%TEMP%\ninja_dash_setup
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM Download Python installer using PowerShell
set PYTHON_INSTALLER=%TEMP_DIR%\python-installer.exe
set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe

echo Downloading from: %PYTHON_URL%
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing}"

if !errorlevel! neq 0 (
    echo [ERROR] Download failed!
    exit /b 1
)

if not exist "%PYTHON_INSTALLER%" (
    echo [ERROR] Installer not found after download!
    exit /b 1
)

echo [OK] Download complete
echo.
echo Installing Python (this may take a few minutes)...
echo Installation location: %USERPROFILE%\AppData\Local\Programs\Python\Python312

REM Install Python silently (user-only, add to PATH, include pip)
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0

REM Wait for installation to complete
timeout /t 5 /nobreak >nul

REM Verify installation by checking common installation paths
set PYTHON_PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe

if exist "%PYTHON_PATH%" (
    echo [OK] Python installed successfully

    REM Add to PATH for current session
    set PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python312;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts;%PATH%

    REM Clean up installer
    del "%PYTHON_INSTALLER%" >nul 2>&1

    echo.
    echo Please close and reopen this terminal for PATH changes to take full effect.
    echo Press any key to continue with setup in this session...
    pause >nul

    exit /b 0
) else (
    echo [ERROR] Python installation completed but executable not found!
    echo Expected location: %PYTHON_PATH%
    exit /b 1
)
