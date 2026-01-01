@echo off
REM Simplified setup script for Ninja Dash build environment
REM This script checks for Python and sets up the virtual environment

REM Ensure we're in the build directory
cd /d "%~dp0"

echo ========================================
echo Ninja Dash - Environment Setup
echo ========================================
echo.

REM ========================================
REM Check for Python
REM ========================================
echo [1/3] Checking for Python...

REM Try python command first
python --version >nul 2>&1
if %errorlevel% equ 0 (
    REM Check if it's the Windows Store stub
    where python | findstr /i "WindowsApps" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [OK] Found Python
        goto :PythonFound
    )
)

REM Try py launcher
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Found Python launcher
    REM Create a python alias for this session
    doskey python=py $*
    goto :PythonFound
)

REM Try python3
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Found Python3
    doskey python=python3 $*
    goto :PythonFound
)

REM Python not found
echo [ERROR] Python not found!
echo.
echo Please install Python 3.11 or 3.12 from one of these sources:
echo   1. Microsoft Store: Search for "Python 3.12"
echo   2. Official website: https://www.python.org/downloads/
echo.
echo IMPORTANT: If installing from python.org, check "Add Python to PATH"
echo.
echo After installing, close this window and run the build script again.
pause
exit /b 1

:PythonFound
python --version
echo.

REM ========================================
REM Setup Virtual Environment
REM ========================================
echo [2/3] Setting up virtual environment...

if exist "..\.venv\Scripts\python.exe" (
    echo [OK] Virtual environment already exists
) else (
    echo Creating virtual environment...
    python -m venv "..\.venv"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        echo.
        echo The venv module might not be installed. Trying alternative...
        python -m pip install --user virtualenv
        python -m virtualenv "..\.venv"
        if %errorlevel% neq 0 (
            echo [ERROR] Could not create virtual environment!
            echo Please ensure Python is properly installed.
            pause
            exit /b 1
        )
    )
    echo [OK] Virtual environment created
)
echo.

REM ========================================
REM Install Dependencies
REM ========================================
echo [3/3] Checking dependencies...
echo Note: Dependencies will be installed when you activate the venv
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Virtual environment: .venv\
echo.
echo The build script will now activate the environment and install dependencies.
echo.

exit /b 0
